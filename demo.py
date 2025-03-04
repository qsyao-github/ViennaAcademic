import gradio as gr
from typing import List, Dict, Tuple, Union
from gradio.themes.utils import sizes
from demo_utils import (
    LATEX_DELIMITERS,
    get_current_user,
    show_files,
    check_delete,
    exclusive_switch,
    respond,
    search,
    append_attach_to_msg,
    upload_paper,
    download_paper,
    upload_code,
    clone_repo,
    _show_repo,
)

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
        ],
    )
    with gr.Tab("聊天"):
        with gr.Row():
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(
                    type="messages",
                    latex_delimiters=LATEX_DELIMITERS,
                    show_copy_button=True,
                    label="聊天框",
                    scale=8,
                )
                with gr.Tab("聊天"):
                    msg = gr.MultimodalTextbox(
                        label="输入框",
                        placeholder="输入文字，可点左侧按钮上传图片",
                        scale=1,
                        file_types=["image"],
                    )
                    with gr.Row():
                        clear_button = gr.ClearButton(
                            [msg, chatbot], value="清除", scale=1
                        )
                        attach_button = gr.Button("引用", scale=1)
                        multimodal_switch = gr.Checkbox(
                            label="多模态",
                            scale=1,
                        )
                        knowledgeBase_switch = gr.Checkbox(
                            label="知识库",
                            scale=1,
                        )

                        clear_button.click(
                            check_delete,
                            [current_user_directory],
                            [
                                code_file_list,
                                knowledgeBase_file_list,
                                paper_file_list,
                                repositry_file_list,
                                tempest_file_list,
                            ],
                            concurrency_limit=28,
                        )

                        multimodal_switch.input(
                            exclusive_switch,
                            [multimodal_switch, knowledgeBase_switch],
                            [knowledgeBase_switch],
                            concurrency_limit=28,
                        )
                        knowledgeBase_switch.input(
                            exclusive_switch,
                            [knowledgeBase_switch, multimodal_switch],
                            [multimodal_switch],
                            concurrency_limit=28,
                        )
                        attach_button.click(
                            append_attach_to_msg, msg, msg, concurrency_limit=28
                        )

                    msg.submit(
                        respond,
                        [
                            msg,
                            chatbot,
                            multimodal_switch,
                            knowledgeBase_switch,
                            current_user_directory,
                        ],
                        [msg, chatbot],
                        concurrency_id="chat related",
                        concurrency_limit=1,
                    )
                with gr.Tab("搜索"):
                    search_box = gr.Textbox(label="搜索框", scale=1)
                    with gr.Row():
                        webSearch_button = gr.Button("网页搜索", scale=1, min_width=64)
                        academicSearch_button = gr.Button(
                            "论文搜索", scale=1, min_width=64
                        )
                        webSearch_button.click(
                            search("webSearch"),
                            [search_box, chatbot],
                            [search_box, chatbot],
                            concurrency_id="chat related",
                            concurrency_limit=1,
                        )
                        academicSearch_button.click(
                            search("academicSearch"),
                            [search_box, chatbot],
                            [search_box, chatbot],
                            concurrency_id="chat related",
                            concurrency_limit=1,
                        )
            with gr.Column(scale=0, min_width=384):
                with gr.Tab("论文"):
                    with gr.Row():
                        upload_paper_button = gr.UploadButton(
                            "上传论文", scale=1, min_width=64
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
                        show_files(f"{current_dir}/paper", paper_file_list, msg)

                with gr.Tab("已解析文件"):
                    with gr.Row():
                        refresh = gr.Button("刷新", scale=1, min_width=32)
                        download_arxiv = gr.Button(
                            "arxiv论文下载", scale=1, min_width=168
                        )
                    arxiv_num = gr.Textbox(
                        placeholder="输入arxiv号，例如：1706.03762", label="Arxiv ID"
                    )
                    download_arxiv.click(
                        download_paper,
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
                            f"{current_dir}/knowledgeBase", knowledgeBase_file_list, msg
                        )

                with gr.Tab("代码"):
                    with gr.Row():
                        upload_code_button = gr.UploadButton(
                            "上传代码", scale=1, min_width=64
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
                        show_files(f"{current_dir}/code", code_file_list, msg)

                with gr.Tab("Github仓库"):
                    with gr.Row():
                        refresh = gr.Button("刷新", scale=1, min_width=32)
                        github_clone = gr.Button("克隆仓库", scale=1, min_width=64)
                    github_url = gr.Textbox(
                        label="仓库url", placeholder="输入Github仓库的url，点击克隆仓库"
                    )
                    github_clone.click(
                        clone_repo,
                        [github_url, current_user_directory],
                        [github_url, repositry_file_list],
                    )

                    @gr.render(
                        triggers=[
                            refresh.click,
                            current_user_directory.change,
                            repositry_file_list.change,
                        ],
                        inputs=[current_user_directory],
                    )
                    def show_repo(
                        current_dir: str,
                    ) -> None:
                        _show_repo(current_dir, repositry_file_list, chatbot)


demo.launch(auth=[("laowei", "1145141919810"), ("main", "2147483647")])
