"""
论文模块
"""

import asyncio
import re
from pathlib import Path
from typing import AsyncGenerator, Literal

import aiofiles
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import BaseChatOpenAI
from llm_utils.modelclient import deepseek_v3
from llm_utils.system_prompt import (
    POLISH_PROMPT,
    TRANSLATE_TO_CHINESE_PROMPT,
    TRANSLATE_TO_ENGLISH_PROMPT,
)
from semaphore import semaphore1024
from va_rust_utils import attach, chunk

ENGLISH_AND_CHINESE_PATTERN = re.compile(r"[a-zA-Z\u4e00-\u9fa5]")
read_paper_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？""",
        ),
        ("user", "{content}"),
    ]
)
process_paper_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "{system}"),
        ("user", "{content}"),
    ]
)


async def read_paper(file_path: str) -> AsyncGenerator[str, None]:
    """论文解读

    Parameters
    ----------
    file_path: str
        文件路径

    Yields
    ----------
    str
        解读结果，返回增量部分
    """
    async for answer_chunk in deepseek_v3.astream(
        await read_paper_prompt_template.ainvoke(
            {"content": attach(file_path)[:-4].strip("`\n ")}
        )
    ):
        yield f"""event: read_paper\ndata: {{content: {answer_chunk.content}, status: "typing"}}\n\n"""


async def worker(
    text: str,
    system_prompt: str,
    model: BaseChatOpenAI,
    semaphore: asyncio.Semaphore,
) -> str:
    if ENGLISH_AND_CHINESE_PATTERN.search(text):
        async with semaphore:
            return (
                await model.ainvoke(
                    await process_paper_prompt_template.ainvoke(
                        {"system": system_prompt, "content": text}
                    )
                )
            ).content
    return text


async def process_paper(
    file_path: str,
    user: str,
    suffix: Literal["Chi", "Eng", "Pol"],
    prompt: str,
    model: BaseChatOpenAI,
) -> AsyncGenerator[str, None]:
    """
    处理论文

    论文翻译、润色的抽象函数。

    Parameters
    ----------
    file_path: str
        文件路径
    user: str
        用户名
    suffix: Literal['Chi', 'Eng', 'Pol']
        文件后缀。分别对应英译中、中译英、润色
    prompt: str
        系统提示词
    model: BaseChatOpenAI
        模型，目前都使用deepseek-v3

    Yields
    ----------
    str
        已处理的文段。返回处理好的一个段落
    """
    # 初始化输出路径和内容块
    base_path = Path(file_path).stem
    knowledgeBase_path = f"documents/{user}/knowledgeBase/{base_path}{suffix}.md"
    document_chunks = chunk(file_path)

    # 并行处理文本块
    tasks = [
        asyncio.create_task(worker(chunk, prompt, model, semaphore1024))
        for chunk in document_chunks
    ]
    async with aiofiles.open(knowledgeBase_path, "w", encoding="utf-8") as output_file:
        for i, task in enumerate(tasks):
            # 等待任务完成
            await task
            processed_chunk = task.result()
            if not processed_chunk:
                continue
            # 写入文件
            await output_file.write(processed_chunk)
            yield processed_chunk


async def translate_paper_to_Chinese(
    file_path: str, user: str
) -> AsyncGenerator[str, None]:
    """论文英译中

    Parameters
    ----------
    file_path: str
        文件路径
    user: str
        用户名

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path, user, "Chi", TRANSLATE_TO_CHINESE_PROMPT, deepseek_v3
    ):
        yield item


async def translate_paper_to_English(
    file_path: str, user: str
) -> AsyncGenerator[str, None]:
    """论文中译英

    Parameters
    ----------
    file_path: str
        文件路径
    user: str
        用户名

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path, user, "Eng", TRANSLATE_TO_ENGLISH_PROMPT, deepseek_v3
    ):
        yield item


async def polish_paper(file_path: str, user: str) -> AsyncGenerator[str, None]:
    """论文润色

    Parameters
    ----------
    file_path: str
        文件路径
    user: str
        用户名

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(file_path, user, "Pol", POLISH_PROMPT, deepseek_v3):
        yield item
