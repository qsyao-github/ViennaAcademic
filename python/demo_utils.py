import datetime
import glob
import os
import shutil
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union

import gradio as gr
from python.academic_utils.download_paper import download_arxiv_paper
from python.academic_utils.paper import (
    polish_paper,
    read_paper,
    translate_paper_to_Chinese,
    translate_paper_to_English,
)
from python.academic_utils.wolfram import attach_hints
from va_rust_utils import (
    chat_utils_attachment_processor_process_attachments as process_attachments,
)

# from python.chat_utils.attachment_processor import process_attachments
from python.chat_utils.chat import ChatManager, SolveManager
from python.chat_utils.memory import remove_thread_data
from python.file_utils.file_conversion import (
    everything_to_markdown,
    markdown_to_everything,
)
from python.knowledge_utils.bce_inference import get_response, update
from python.llm_utils.execute_code import delete_png_files
from python.web_utils.search import attach_web_result

LATEX_DELIMITERS = [
    {"left": "$$", "right": "$$", "display": True},
    {"left": "$", "right": "$", "display": False},
    {"left": r"\(", "right": r"\)", "display": False},
    {"left": r"\[", "right": r"\]", "display": True},
]


def get_current_user(
    request: gr.Request,
) -> Tuple[str, List[str], List[str], List[str], List[str], List[str], List[str]]:
    username = request.username
    return (
        username,
        os.listdir(f"{username}/code"),
        os.listdir(f"{username}/knowledgeBase"),
        os.listdir(f"{username}/paper"),
        os.listdir(f"{username}/repositry"),
        os.listdir(f"{username}/tempest"),
        os.listdir(f"{username}/convert"),
    )


def show_files(
    folder: str,
    current_dir: str,
    file_list: gr.State,
    msg: Optional[Union[gr.MultimodalTextbox, gr.Textbox]],
    append: bool = True,
    with_folder_name: bool = False,
) -> None:
    folder_path = f"{current_dir}/{folder}"
    for file in os.listdir(folder_path):
        with gr.Row():
            file_path = f"{current_dir}/{folder}/{file}"
            file_button = gr.Button(file, scale=1, min_width=120)
            gr.DownloadButton("下载", file_path, scale=0, min_width=72)
            delete_file_button = gr.Button("删除", scale=0, min_width=72)

            async def delete_file(file_path: str = file_path) -> List[str]:
                os.remove(file_path)
                await update(current_dir)
                return os.listdir(folder_path)

            delete_file_button.click(delete_file, None, file_list, concurrency_limit=28)
            if msg is None:
                continue

            def append_to_msg(
                msg: Union[Dict[str, Union[str, List[str]]], str], file: str = file
            ) -> Dict[str, Union[str, List[str]]]:
                file = f"{folder}/{file}" if with_folder_name else file
                if isinstance(msg, dict):
                    msg["text"] += "#attach{" + file + "}"
                elif append:
                    msg += "#attach{" + file + "}"
                else:
                    msg = file
                return msg

            file_button.click(append_to_msg, msg, msg, concurrency_limit=28)


def _paper_show_files(
    current_dir: str, file_list: gr.State, selected_paper: gr.Textbox
) -> None:
    folder_path = f"{current_dir}/knowledgeBase"
    for file in os.listdir(folder_path):
        with gr.Row():
            file_path = f"{current_dir}/knowledgeBase/{file}"
            file_button = gr.Button(file, scale=1, min_width=120)
            gr.DownloadButton("下载", file_path, scale=0, min_width=72)
            delete_file = gr.Button("删除", scale=0, min_width=72)

            async def delete_paper(file_path: str = file_path):
                os.remove(file_path)
                await update(current_dir)
                return os.listdir(folder_path)

            delete_file.click(delete_paper, None, file_list, concurrency_limit=28)
            file_button.click(lambda: file, None, selected_paper, concurrency_limit=28)


async def clear_thread(
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
) -> None:
    if chatbot:
        await remove_thread_data(str(chatbot[0]))


async def check_delete(
    current_user: str,
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
) -> Tuple[
    Dict[str, Union[str, List]],
    List,
    List[str],
    List[str],
    List[str],
    List[str],
    List[str],
]:
    for file_path in glob.glob("media/*.png"):
        os.remove(file_path)
    delete_png_files()
    await clear_thread(chatbot)
    now = datetime.datetime.now()
    for root, _, files in os.walk(current_user):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                file_mtime = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                )
                if (now - file_mtime).days > 3:
                    os.remove(file_path)
    await update(current_user)
    return (
        {"text": "", "files": []},
        [],
        os.listdir(f"{current_user}/code"),
        os.listdir(f"{current_user}/knowledgeBase"),
        os.listdir(f"{current_user}/paper"),
        os.listdir(f"{current_user}/repositry"),
        os.listdir(f"{current_user}/tempest"),
    )


async def solve_delete(
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
) -> Tuple[str, List]:
    await clear_thread(chatbot)
    return "", []


def append_text(
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    text: str,
    message_type: str,
) -> None:
    chatbot.append(
        {"role": message_type, "metadata": None, "content": text, "options": None}
    )


def append_file(
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    file_path: str,
    message_type: str,
) -> None:
    chatbot.append({"role": message_type, "content": {"path": file_path}})


def append_files(
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    file_paths: List[str],
    message_type: str,
) -> None:
    for file_path in file_paths:
        append_file(chatbot, file_path, message_type)


async def respond(
    msg: Dict[str, Union[str, List[str]]],
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    chat_mode: str,
    current_user_dir: str,
) -> AsyncGenerator[
    Tuple[
        Dict[str, Union[str, List[str]]],
        List[Dict[str, Union[str, Dict[str, str], None]]],
    ],
    None,
]:
    if msg["text"] or msg["files"]:
        # Main processing logic
        now_time = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        possible_media_filename = f"media/{now_time}.png"

        # Process incoming message
        text = msg["text"]
        web_search_result, reference = "", ""
        if chat_mode == "知识库":
            if knowledgeBase_search := await get_response(text, current_user_dir):
                text = knowledgeBase_search + "\n\n" + text
        elif chat_mode == "网页搜索":
            web_search_result, reference = await attach_web_result(text)
            web_search_result = f"\n{web_search_result}\n\n"
            reference = f"\n\n参考文献\n\n{reference}"
        formatted_text = process_attachments(text, current_user_dir)
        append_text(chatbot, formatted_text, "user")
        append_files(chatbot, msg["files"], "user")
        append_text(chatbot, "", "assistant")

        # Generate and stream responses
        bot_response = ChatManager.astream_response(
            f"{web_search_result}{formatted_text}",
            msg["files"],
            str(chatbot[0]),
            chat_mode,
            now_time,
        )
        yield {"text": "", "files": []}, chatbot
        async for response_chunk in bot_response:
            chatbot[-1]["content"] = response_chunk
            yield {"text": "", "files": []}, chatbot
        chatbot[-1]["content"] += reference

        # Handle generated media file if exists
        if os.path.exists(possible_media_filename):
            append_file(chatbot, possible_media_filename, "assistant")

    yield {"text": "", "files": []}, chatbot


async def academic_search(
    query: str, chatbot: List[Dict[str, Union[str, Dict[str, str], None]]]
) -> AsyncGenerator[
    Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]]], None
]:
    if query:
        append_text(chatbot, f"搜索{query}相关论文", "user")
        yield "", chatbot
        academic_search_result = ChatManager.append_search_result(
            query, str(chatbot[0])
        )
        append_text(chatbot, "", "assistant")
        async for chunk_result in academic_search_result:
            chatbot[-1]["content"] = chunk_result
            yield "", chatbot


async def upload_paper(file: str, current_dir: str) -> Tuple[List[str], List[str]]:
    gr.Info("已开始上传，请勿重复提交。10页的论文约需40s，请耐心等候")
    file_base_name = os.path.basename(file)
    simpfile = os.path.splitext(file_base_name)[0]
    knowledge_base_files = set(os.listdir(f"{current_dir}/knowledgeBase"))
    paper_directory = f"{current_dir}/paper"
    if (
        f"{simpfile}.md" in knowledge_base_files
        or f"{simpfile}.txt" in knowledge_base_files
    ):
        return os.listdir(paper_directory), list(knowledge_base_files)
    shutil.move(file, paper_directory)
    everything_to_markdown(
        f"{current_dir}/paper/{file_base_name}", f"{current_dir}/knowledgeBase"
    )
    """text = parse_everything(f"{current_dir}/paper/{file_base_name}")
    with open(f"{current_dir}/knowledgeBase/{simpfile}.md", "w", encoding="utf-8") as f:
        f.write(text)"""
    await update(current_dir)
    return os.listdir(paper_directory), list(knowledge_base_files)


async def download_paper_chatbot(
    arxiv_num: str,
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    current_dir: str,
) -> AsyncGenerator[
    Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]], List[str]], None
]:
    gr.Info("正在下载，请耐心等候")
    append_text(chatbot, f"下载{arxiv_num}并翻译标题与摘要", "user")
    yield "", chatbot, os.listdir(f"{current_dir}/knowledgeBase")
    append_text(chatbot, "", "assistant")
    async for chunk in download_arxiv_paper(arxiv_num, current_dir):
        chatbot[-1]["content"] = chunk
        yield "", chatbot, []
    await update(current_dir)
    yield "", chatbot, os.listdir(f"{current_dir}/knowledgeBase")


async def download_paper_textbox(
    arxiv_num: str, current_dir: str
) -> AsyncGenerator[Tuple[str, str, List[str]], None]:
    gr.Info("正在下载，请耐心等候")
    answer = ""
    async for chunk in download_arxiv_paper(arxiv_num, current_dir):
        answer = chunk
        yield "", chunk, []
    await update(current_dir)
    yield "", answer, os.listdir(f"{current_dir}/knowledgeBase")


def upload_code(file: str, current_dir: str) -> List[str]:
    code_directory = f"{current_dir}/code"
    shutil.move(file, code_directory)
    return os.listdir(code_directory)


paper_function_map = {
    "论文润色": polish_paper,
    "论文翻译->英": translate_paper_to_English,
    "论文翻译->中": translate_paper_to_Chinese,
}


async def generate_paper_answer(
    selected_function: str, selected_paper: str, current_dir: str
) -> AsyncGenerator[Tuple[str, List[str]], None]:
    if selected_paper not in os.listdir(f"{current_dir}/knowledgeBase"):
        yield "文件不存在", os.listdir(f"{current_dir}/knowledgeBase")
        return
    gr.Info("正在生成答案，请耐心等候")
    process_function = paper_function_map.get(selected_function, read_paper)
    final_answer = ""
    async for chunk in process_function(selected_paper, current_dir):
        final_answer = chunk
        yield final_answer, []
    gr.Info("已完成，请刷新")
    yield final_answer, os.listdir(f"{current_dir}/knowledgeBase")


async def solve_respond(
    solve_msg: str,
    solve_chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    current_dir: str,
    distill: bool,
    wolfram: bool,
) -> AsyncGenerator[
    Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]]], None
]:
    solve_msg = process_attachments(solve_msg.strip(), current_dir)
    if not solve_msg:
        yield "", solve_chatbot
        return
    solve_chatbot.append(
        {"role": "user", "metadata": None, "content": solve_msg, "options": None}
    )
    yield "", solve_chatbot
    if wolfram:
        solve_msg = await attach_hints(solve_msg)
        solve_chatbot[-1]["content"] = solve_msg
    solve_chatbot.extend(
        [
            {"role": "assistant", "content": "", "metadata": {"title": "思考过程"}},
            {"role": "assistant", "content": ""},
        ]
    )
    answer = SolveManager.astream_response(solve_msg, str(solve_chatbot[0]), distill)
    yield "", solve_chatbot
    async for chunk in answer:
        solve_chatbot[-2]["content"], solve_chatbot[-1]["content"] = chunk
        yield "", solve_chatbot


def convert_markdown_to(file_name: str, current_dir: str, target_ext: str) -> List[str]:
    markdown_to_everything(
        f"{current_dir}/{file_name}", f"{current_dir}/convert", target_ext
    )
    return os.listdir(f"{current_dir}/convert")
