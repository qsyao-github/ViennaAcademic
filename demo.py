import asyncio
import signal

import gradio as gr
import uvloop
from gradio.themes.utils import sizes
from python.academic_utils.llm_ocr import file_ocr
from python.chat_utils.memory import shutdown_sqlite_connection
from python.demo_utils import (
    LATEX_DELIMITERS,
    academic_search,
    check_delete,
    convert_markdown_to,
    download_paper_chatbot,
    download_paper_textbox,
    generate_paper_answer,
    get_current_user,
    respond,
    show_files,
    solve_respond,
    upload_code,
    upload_paper,
    solve_delete,
)
from python.knowledge_utils.custom_reranker import shutdown_reranker_session
from python.private.auth import check_login
from python.web_utils.arxiv_crawler import shutdown_arxiv_session

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def handle_sigint(_signum, _frame):
    print("Shutting down")
    asyncio.run(shutdown_arxiv_session())
    asyncio.run(shutdown_reranker_session())
    asyncio.run(shutdown_sqlite_connection())
    demo.close()
    print("Gradio server stopped")
    exit(0)


signal.signal(signal.SIGINT, handle_sigint)

with gr.Blocks(
    fill_height=True,
    fill_width=True,
    delete_cache=(3600, 3600),
    theme=gr.themes.Citrus(spacing_size=sizes.spacing_md),
) as demo:
    current_user_directory = gr.State("")
    code_file_list = gr.State([])
    knowledgeBase_file_list = gr.State([])
    paper_file_list = gr.State([])
    repositry_file_list = gr.State([])
    tempest_file_list = gr.State([])
    convert_file_list = gr.State([])
    demo.load(
        get_current_user,
        [],
        [
            current_user_directory,
            code_file_list,
            knowledgeBase_file_list,
            paper_file_list,
            repositry_file_list,
            tempest_file_list,
            convert_file_list,
        ],
    )
    with gr.Tab("聊天"):
        with gr.Row():
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(
                    type="messages",
                    latex_delimiters=LATEX_DELIMITERS,
                    show_copy_button=True,
                    show_copy_all_button=True,
                    label="聊天框",
                    scale=8,
                    sanitize_html=False,
                    resizable=True,
                )
                with gr.Tab("聊天"):
                    msg = gr.MultimodalTextbox(
                        label="输入框",
                        placeholder="输入文字，可点左侧按钮上传图片",
                        scale=1,
                        file_types=["image", "text"],
                        max_plain_text_length=8191,
                    )
                    with gr.Row():
                        clear_button = gr.Button(value="清除", scale=1)
                        chat_mode = gr.Radio(
                            ["常规", "工具", "多模态", "知识库", "网页搜索"],
                            value="常规",
                            label="聊天模式",
                            scale=2,
                        )

                        clear_button.click(
                            check_delete,
                            [current_user_directory, chatbot],
                            [
                                msg,
                                chatbot,
                                code_file_list,
                                knowledgeBase_file_list,
                                paper_file_list,
                                repositry_file_list,
                                tempest_file_list,
                            ],
                            concurrency_limit=28,
                        )

                    msg.submit(
                        respond,
                        [
                            msg,
                            chatbot,
                            chat_mode,
                            current_user_directory,
                        ],
                        [msg, chatbot],
                        concurrency_limit=28,
                    )
                with gr.Tab("搜索"):
                    search_box = gr.Textbox(label="搜索框", scale=1)
                    with gr.Row():
                        academicSearch_button = gr.Button(
                            "论文搜索", scale=1, min_width=64
                        )
                        academicSearch_button.click(
                            academic_search,
                            [search_box, chatbot],
                            [search_box, chatbot],
                            concurrency_id="chat related",
                            concurrency_limit=28,
                        )
            with gr.Column(scale=0, min_width=384):
                with gr.Tab("论文"):
                    with gr.Row():
                        upload_paper_button = gr.UploadButton(
                            "上传论文", scale=1, min_width=64
                        )
                        upload_paper_button.click(
                            lambda: gr.Warning(
                                "不允许上传图片或PDF扫描件(普通PDF可以)，若要上传图片，请通过聊天框上传，并使用多模态聊天"
                            )
                        )
                        upload_paper_button.upload(
                            upload_paper,
                            [upload_paper_button, current_user_directory],
                            [paper_file_list, knowledgeBase_file_list],
                            concurrency_limit=1,
                        )
                        refresh = gr.Button("刷新", scale=1, min_width=32)

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            paper_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_paper(current_dir: str) -> None:
                        show_files(
                            "paper", current_dir, paper_file_list, msg, append=True
                        )

                with gr.Tab("已解析文件"):
                    with gr.Row():
                        refresh = gr.Button("刷新", scale=1, min_width=32)
                        download_arxiv = gr.Button(
                            "arxiv论文下载", scale=1, min_width=168
                        )
                    arxiv_num = gr.Textbox(
                        placeholder="输入arxiv号，例如：1706.03762",
                        label="Arxiv ID",
                    )
                    download_arxiv.click(
                        download_paper_chatbot,
                        [arxiv_num, chatbot, current_user_directory],
                        [arxiv_num, chatbot, knowledgeBase_file_list],
                    )

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            knowledgeBase_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_knowledgeBase(current_dir: str) -> None:
                        show_files(
                            "knowledgeBase",
                            current_dir,
                            knowledgeBase_file_list,
                            msg,
                            append=True,
                        )

                with gr.Tab("代码"):
                    with gr.Row():
                        upload_code_button = gr.UploadButton(
                            "上传代码", scale=1, min_width=64
                        )
                        upload_code_button.click(
                            lambda: gr.Warning(
                                "仅允许上传纯文本文件(如.py, .cpp, .txt, .md, .tex)"
                            )
                        )
                        upload_code_button.upload(
                            upload_code,
                            [upload_code_button, current_user_directory],
                            code_file_list,
                        )
                        refresh = gr.Button("刷新", scale=1, min_width=32)

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            code_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_code(current_dir: str) -> None:
                        show_files(
                            "code", current_dir, code_file_list, msg, append=True
                        )

    with gr.Tab("论文"):
        with gr.Row():
            with gr.Column(scale=8):
                with gr.Row():
                    selected_function = gr.Dropdown(
                        ["论文解读", "论文翻译->英", "论文翻译->中", "论文润色"],
                        scale=0,
                        min_width=180,
                        label="功能",
                    )
                    selected_paper = gr.Textbox(
                        placeholder="点击右侧文件名输入",
                        scale=1,
                        label="文件名",
                        submit_btn=True,
                    )
                paper_answer = gr.Markdown(show_copy_button=True)
                selected_paper.submit(
                    generate_paper_answer,
                    [selected_function, selected_paper, current_user_directory],
                    [paper_answer, knowledgeBase_file_list],
                )
            with gr.Column(scale=1, min_width=384):
                upload_paper_button = gr.UploadButton("上传论文", scale=1, min_width=64)
                upload_paper_button.click(
                    lambda: gr.Warning(
                        "不允许上传图片或PDF扫描件(普通PDF可以)，若要上传图片，请通过聊天框上传，并使用多模态聊天"
                    )
                )
                upload_paper_button.upload(
                    upload_paper,
                    [upload_paper_button, current_user_directory],
                    [paper_file_list, knowledgeBase_file_list],
                    concurrency_limit=1,
                )
                with gr.Row():
                    paper_refresh = gr.Button("刷新", scale=1, min_width=32)
                    paper_download_arxiv = gr.Button(
                        "arxiv论文下载", scale=1, min_width=112
                    )
                paper_arxiv_num = gr.Textbox(
                    placeholder="输入arxiv号，例如：1706.03762",
                    label="Arxiv ID",
                )
                paper_download_arxiv.click(
                    download_paper_textbox,
                    [paper_arxiv_num, current_user_directory],
                    [paper_arxiv_num, paper_answer, knowledgeBase_file_list],
                )

                @gr.render(
                    triggers=[
                        paper_refresh.click,
                        knowledgeBase_file_list.change,
                        current_user_directory.change,
                    ],
                    inputs=[current_user_directory],
                )
                def paper_show_knowledgeBase(current_dir: str):
                    show_files(
                        "knowledgeBase",
                        current_dir,
                        knowledgeBase_file_list,
                        selected_paper,
                        append=False,
                    )

    with gr.Tab("解题/代码"):
        with gr.Tab("常规解题/代码"):
            with gr.Row():
                with gr.Column(scale=8):
                    solve_chatbot = gr.Chatbot(
                        type="messages",
                        latex_delimiters=LATEX_DELIMITERS,
                        show_copy_button=True,
                        show_copy_all_button=True,
                        label="聊天框",
                        scale=8,
                        sanitize_html=False,
                        resizable=True,
                    )
                    solve_msg = gr.Textbox(
                        placeholder="输入题目", label="输入框", submit_btn=True
                    )
                    with gr.Tab("解题"):
                        with gr.Row():
                            distill = gr.Dropdown(
                                ["QwQ-32B", "Deepseek-R1-671B"],
                                value="QwQ-32B",
                                label="模型",
                                scale=1,
                                type="index",
                            )
                            solve_clear = gr.Button(value="清除")
                            solve_clear.click(
                                solve_delete,
                                [solve_chatbot],
                                [solve_msg, solve_chatbot],
                                concurrency_limit=28,
                            )
                            ocr_button = gr.UploadButton(
                                "识别题目", file_types=["image"]
                            )
                            ocr_button.click(lambda: gr.Warning("仅允许上传图片"))
                            wolfram = gr.Checkbox(value=False, label="使用Wolfram")
                            ocr_button.upload(
                                file_ocr, ocr_button, solve_msg, concurrency_limit=10
                            )
                        solve_msg.submit(
                            solve_respond,
                            [
                                solve_msg,
                                solve_chatbot,
                                current_user_directory,
                                distill,
                                wolfram,
                            ],
                            [solve_msg, solve_chatbot],
                            concurrency_limit=2,
                        )
                    with gr.Tab("代码"):
                        with gr.Row():
                            readability = gr.Button("可读性优化")
                            readability.click(
                                lambda x: f"{x}\n重构代码、进行可读性优化",
                                solve_msg,
                                solve_msg,
                            )
                            performance = gr.Button("性能优化")
                            performance.click(
                                lambda x: f"{x}\n对代码进行性能优化",
                                solve_msg,
                                solve_msg,
                            )
                            safety = gr.Button("安全性优化")
                            safety.click(
                                lambda x: f"{x}\n对代码进行安全性优化",
                                solve_msg,
                                solve_msg,
                            )
                with gr.Column(scale=1, min_width=384):
                    with gr.Row():
                        solve_upload_code_button = gr.UploadButton(
                            "上传代码", scale=1, min_width=64
                        )
                        solve_upload_code_button.click(
                            lambda: gr.Warning(
                                "仅允许上传纯文本文件(如.py, .cpp, .txt, .md, .tex)"
                            )
                        )
                        solve_upload_code_button.upload(
                            upload_code,
                            [solve_upload_code_button, current_user_directory],
                            code_file_list,
                        )
                        refresh = gr.Button("刷新", scale=1, min_width=32)

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            code_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def solve_show_code(current_dir: str) -> None:
                        show_files(
                            "code", current_dir, code_file_list, solve_msg, append=True
                        )

    with gr.Tab("格式转换"):
        with gr.Row():
            with gr.Column(scale=1, min_width=384):
                to_be_converted = gr.Textbox(label="待转换文件")
                with gr.Tab("已解析文件"):
                    refresh = gr.Button("刷新", scale=1, min_width=32)

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            knowledgeBase_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_knowledgeBase(current_dir: str) -> None:
                        show_files(
                            "knowledgeBase",
                            current_dir,
                            knowledgeBase_file_list,
                            to_be_converted,
                            False,
                            True,
                        )

                with gr.Tab("写作"):
                    refresh = gr.Button("刷新", scale=1, min_width=32)

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            tempest_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_tempest(current_dir: str) -> None:
                        show_files(
                            "tempest",
                            current_dir,
                            tempest_file_list,
                            to_be_converted,
                            False,
                            True,
                        )

            with gr.Column(scale=1, min_width=384):
                with gr.Row():
                    target_ext = gr.Dropdown(
                        ["docx", "pdf", "tex", "typ"],
                        value="docx",
                        scale=1,
                        label="目标格式",
                    )
                    convert = gr.Button("转换", scale=1, min_width=32)
                    convert.click(
                        convert_markdown_to,
                        [to_be_converted, current_user_directory, target_ext],
                        [convert_file_list],
                    )
                    refresh = gr.Button("刷新", scale=1, min_width=32)

                @gr.render(
                    triggers=[
                        refresh.click,
                        current_user_directory.change,
                        convert_file_list.change,
                    ],
                    inputs=[current_user_directory],
                )
                def show_convert(current_dir: str) -> None:
                    show_files(
                        "convert",
                        current_dir,
                        convert_file_list,
                        None,
                    )


demo.launch(auth=check_login)
