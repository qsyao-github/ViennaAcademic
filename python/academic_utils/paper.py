"""
论文模块
"""

import asyncio
import os
from io import StringIO
from typing import AsyncGenerator, List, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import BaseChatOpenAI
from llm_utils.modelclient import deepseek_v3
from llm_utils.system_prompt import (
    POLISH_PROMPT,
    TRANSLATE_TO_CHINESE_PROMPT,
    TRANSLATE_TO_ENGLISH_PROMPT,
)
from semaphore import semaphore1024
from va_rust_utils import academic_utils_paper_attach as attach
from va_rust_utils import academic_utils_paper_chunk as chunk

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


async def read_paper(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文解读

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户根目录

    Yields
    ----------
    str
        解读结果。Gradio不支持增量更新，每次均返回完整字符串
    """
    prompt = await read_paper_prompt_template.ainvoke(
        {"content": attach(file_path, current_user_directory)}
    )
    answer = StringIO()
    async for answer_chunk in deepseek_v3.astream(prompt):
        answer.write(answer_chunk.content)
        yield answer.getvalue()
    answer.close()


async def worker(
    text: str,
    system_prompt: str,
    model: BaseChatOpenAI,
    index: int,
    result: List[str],
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        if text.strip():
            prompt = await process_paper_prompt_template.ainvoke(
                {"system": system_prompt, "content": text}
            )
            result[index] = (await model.ainvoke(prompt)).content


async def process_paper(
    file_path: str,
    suffix: Literal["Chi", "Eng", "Pol"],
    prompt: str,
    current_user_directory: str,
    model: BaseChatOpenAI,
) -> AsyncGenerator[str, None]:
    """处理论文

    论文翻译、润色的抽象函数。

    Parameters
    ----------
    file_path: str
        文件路径
    suffix: Literal['Chi', 'Eng', 'Pol']
        文件后缀。分别对应英译中、中译英、润色
    prompt: str
        系统提示词
    current_user_directory: str
        当前用户目录
    model: BaseChatOpenAI
        模型，目前都使用deepseek-v3

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    # 初始化输出路径和内容块
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    knowledgeBase_file_path = (
        f"{current_user_directory}/knowledgeBase/{base_name}{suffix}.md"
    )
    document_chunks = chunk(attach(file_path, current_user_directory))

    # 并行处理文本块
    processed_chunks = [""] * len(document_chunks)
    tasks = [
        worker(chunk, prompt, model, index, processed_chunks, semaphore1024)
        for index, chunk in enumerate(document_chunks)
    ]
    for future in asyncio.as_completed(tasks):
        await future
        yield "\n\n".join(processed_chunks)

    # 写入最终结果并返回
    final_content = "\n\n".join(processed_chunks)
    with open(knowledgeBase_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(final_content)
    yield final_content


async def translate_paper_to_Chinese(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文英译中

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path,
        "Chi",
        TRANSLATE_TO_CHINESE_PROMPT,
        current_user_directory,
        deepseek_v3,
    ):
        yield item


async def translate_paper_to_English(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文中译英

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path,
        "Eng",
        TRANSLATE_TO_ENGLISH_PROMPT,
        current_user_directory,
        deepseek_v3,
    ):
        yield item


async def polish_paper(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文润色

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path, "Pol", POLISH_PROMPT, current_user_directory, deepseek_v3
    ):
        yield item
