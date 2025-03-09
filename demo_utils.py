import os
import datetime
import glob
import subprocess
import gradio as gr
from typing import Generator, Dict, List, Union, Tuple, Callable
from chat import ChatManager, ContentProcessor, SolveManager
from bce_inference import update, get_response
import shutil
from docling_parser import parse_everything
from download_paper import download_arxiv_paper
from code_analysis import analyze_folder
from paper import (
    polish_paper,
    translate_paper_to_Chinese,
    translate_paper_to_English,
    read_paper,
)
from wolfram import attach_hints
from search import attach_web_result

LATEX_DELIMITERS = [
    {"left": "$$", "right": "$$", "display": True},
    {"left": "$", "right": "$", "display": False},
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
    )


def show_files(
    folder: str,
    current_dir: str,
    file_list: gr.State,
    msg: gr.MultimodalTextbox,
) -> None:
    folder_path = f"{current_dir}/{folder}"
    for file in os.listdir(folder_path):
        with gr.Row():
            file_path = f"{current_dir}/{folder}/{file}"
            file_button = gr.Button(file, scale=1, min_width=120)
            download_file_button = gr.DownloadButton(
                "下载", file_path, scale=0, min_width=72
            )
            delete_file_button = gr.Button("删除", scale=0, min_width=72)

            def delete_file(file_path: str = file_path) -> List[str]:
                os.remove(file_path)
                update(current_dir)
                return os.listdir(folder_path)

            delete_file_button.click(delete_file, None, file_list, concurrency_limit=28)

            def append_to_msg(
                msg: Dict[str, Union[str, List[str]]], file: str = file
            ) -> Dict[str, Union[str, List[str]]]:
                msg["text"] += "#attach{" + file + "}"
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
            download_file = gr.DownloadButton("下载", file_path, scale=0, min_width=72)
            delete_file = gr.Button("删除", scale=0, min_width=72)

            def delete_paper(file_path: str = file_path):
                os.remove(file_path)
                update(current_dir)
                return os.listdir(folder_path)

            delete_file.click(delete_paper, None, file_list, concurrency_limit=28)
            file_button.click(lambda: file, None, selected_paper, concurrency_limit=28)


def check_delete(
    current_user: str,
) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    for file_path in glob.glob("*.png"):
        os.remove(file_path)
    subprocess.run(
        f"find {current_user} -type f -mtime +2 -exec rm {{}} \\;", shell=True
    )
    update(current_user)
    return (
        os.listdir(f"{current_user}/code"),
        os.listdir(f"{current_user}/knowledgeBase"),
        os.listdir(f"{current_user}/paper"),
        os.listdir(f"{current_user}/repositry"),
        os.listdir(f"{current_user}/tempest"),
    )


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


def respond(
    msg: Dict[str, Union[str, List[str]]],
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    chat_mode: str,
    current_user_dir: str,
) -> Generator[
    Tuple[
        Dict[str, Union[str, List[str]]],
        List[Dict[str, Union[str, Dict[str, str], None]]],
    ],
    None,
    None,
]:
    if msg["text"] or msg["files"]:
        # Main processing logic
        now_time = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        possible_media_filename = f"{now_time}.png"

        # Process incoming message
        # A special suffix is added to formatted_text. This is to address gradio issue #10450
        text = msg["text"]
        if chat_mode == "知识库":
            knowledgeBase_search = get_response(text, current_user_dir)
            if knowledgeBase_search:
                text = knowledgeBase_search + "\n\n" + text
        elif chat_mode == "网页搜索":
            web_search_result = attach_web_result(text)
            if web_search_result:
                text = web_search_result + "\n\n" + text
        formatted_text = ContentProcessor.format_formula(
            ContentProcessor.process_attachments(text, current_user_dir)
        )
        append_text(chatbot, f"{formatted_text}\n$$ $$", "user")
        append_files(chatbot, msg["files"], "user")

        append_text(chatbot, "", "assistant")

        # Generate and stream responses
        bot_response = ChatManager.stream_response(
            formatted_text, msg["files"], str(chatbot[0]), chat_mode, now_time
        )
        yield {"text": "", "files": []}, chatbot
        for response_chunk in bot_response:
            chatbot[-1]["content"] = response_chunk
            yield {"text": "", "files": []}, chatbot
        # same suffix for #10450
        chatbot[-1]["content"] += "\n$$ $$"

        # Handle generated media file if exists
        if os.path.exists(possible_media_filename):
            append_file(chatbot, possible_media_filename, "assistant")

    yield {"text": "", "files": []}, chatbot


def search(
    focus_mode: str,
) -> Callable[
    [str, List[Dict[str, Union[str, Dict[str, str], None]]]],
    Generator[
        Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]]], None, None
    ],
]:

    def _search(
        query: str, chatbot: List[Dict[str, Union[str, Dict[str, str], None]]]
    ) -> Generator[
        Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]]], None, None
    ]:
        if query:
            append_text(chatbot, f"请搜索{query}", "user")
            yield "", chatbot
            append_text(
                chatbot,
                ChatManager.append_search_result(query, focus_mode, str(chatbot[0])),
                "assistant",
            )
        yield "", chatbot

    return _search


def upload_paper(file: str, current_dir: str) -> Tuple[List[str], List[str]]:
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
    text = parse_everything(f"{current_dir}/paper/{file_base_name}")
    with open(f"{current_dir}/knowledgeBase/{simpfile}.md", "w", encoding="utf-8") as f:
        f.write(text)
    update(current_dir)
    return os.listdir(paper_directory), list(knowledge_base_files)


def download_paper_chatbot(
    arxiv_num: str,
    chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    current_dir: str,
) -> Generator[
    Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]], List[str]], None, None
]:
    gr.Info("正在下载，请耐心等候")
    append_text(chatbot, f"下载{arxiv_num}并翻译标题与摘要", "user")
    yield "", chatbot, os.listdir(f"{current_dir}/knowledgeBase")
    append_text(chatbot, download_arxiv_paper(arxiv_num, current_dir), "assistant")
    update(current_dir)
    yield "", chatbot, os.listdir(f"{current_dir}/knowledgeBase")


def download_paper_textbox(
    arxiv_num: str, current_dir: str
) -> Tuple[str, str, List[str]]:
    gr.Info("正在下载，请耐心等候")
    answer = download_arxiv_paper(arxiv_num, current_dir)
    update(current_dir)
    return "", answer, os.listdir(f"{current_dir}/knowledgeBase")


def upload_code(file: str, current_dir: str) -> List[str]:
    code_directory = f"{current_dir}/code"
    shutil.move(file, code_directory)
    return os.listdir(code_directory)


def clone_repo(url: str, current_dir: str) -> Tuple[str, List[str]]:
    url = url.strip("/")
    if url and not os.path.exists(f"{current_dir}/repositry/{url[url.rfind('/')+1:]}"):
        result = subprocess.run(
            f"cd {current_dir}/repositry && git clone {url}",
            capture_output=True,
            text=True,
            shell=True,
        )
        if result.returncode == 0:
            gr.Info("克隆成功，请刷新")
        else:
            gr.Info(f"克隆失败：{result.stderr}")
    return "", os.listdir(f"{current_dir}/repositry")


def _show_repo(
    current_dir: str,
    repositry_file_list: gr.State,
    chatbot: gr.Chatbot,
) -> None:
    for folder in os.listdir(f"{current_dir}/repositry"):
        with gr.Row():
            folder_button = gr.Button(f"解析{folder}", scale=1)
            delete_folder_button = gr.Button("删除", scale=0)
            folder_directory = f"{current_dir}/repositry/{folder}"

            def delete_folder(folder_directory: str = folder_directory) -> List[str]:
                shutil.rmtree(folder_directory)
                return os.listdir("repositry")

            delete_folder_button.click(
                delete_folder, [], [repositry_file_list], concurrency_limit=28
            )

            def repo_analysis(
                chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
                folder_directory: str = folder_directory,
            ) -> Generator[
                List[Dict[str, Union[str, Dict[str, str], None]]], None, None
            ]:
                analysis_generator = analyze_folder(folder_directory)
                tree = next(analysis_generator)
                append_text(chatbot, f"解析{folder}", "user")
                append_text(chatbot, tree, "assistant")
                yield chatbot
                for chunk in analysis_generator:
                    chatbot[-1]["content"] = chunk
                    yield chatbot

            folder_button.click(repo_analysis, chatbot, chatbot)


paper_function_map = {
    "论文润色": polish_paper,
    "论文翻译->英": translate_paper_to_English,
    "论文翻译->中": translate_paper_to_Chinese,
}


def generate_paper_answer(
    selected_function: str, selected_paper: str, current_dir: str
) -> Generator[Tuple[str, List[str]], None, None]:
    if selected_paper not in os.listdir(f"{current_dir}/knowledgeBase"):
        yield "文件不存在", os.listdir(f"{current_dir}/knowledgeBase")
        return
    gr.Info("正在生成答案，请耐心等候")
    process_function = paper_function_map.get(selected_function, read_paper)
    final_answer = ""
    for chunk in process_function(selected_paper, current_dir):
        final_answer = chunk
        yield final_answer, []
    gr.Info("已完成，请刷新")
    yield final_answer, os.listdir(f"{current_dir}/knowledgeBase")


def solve_respond(
    solve_msg: str,
    solve_chatbot: List[Dict[str, Union[str, Dict[str, str], None]]],
    distill: bool,
    wolfram: bool,
) -> Generator[
    Tuple[str, List[Dict[str, Union[str, Dict[str, str], None]]]], None, None
]:
    solve_msg = solve_msg.strip()
    if not solve_msg:
        return "", solve_chatbot
    solve_msg = ContentProcessor.format_formula(solve_msg)
    solve_chatbot.append(
        {
            "role": "user",
            "metadata": None,
            "content": f"{solve_msg}\n$$ $$",
            "options": None,
        }
    )
    yield "", solve_chatbot
    if wolfram:
        solve_msg = attach_hints(solve_msg)
        solve_chatbot[-1]["content"] = f"{solve_msg}\n$$ $$"
    solve_chatbot.extend(
        [
            {"role": "assistant", "content": "", "metadata": {"title": "思考过程"}},
            {"role": "assistant", "content": ""},
        ]
    )
    answer = SolveManager.stream_response(solve_msg, str(solve_chatbot[0]), distill)
    yield "", solve_chatbot
    for chunk in answer:
        solve_chatbot[-2]["content"], solve_chatbot[-1]["content"] = chunk
        yield "", solve_chatbot
