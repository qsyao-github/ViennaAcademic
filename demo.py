import gradio as gr
from typing import Generator, Dict, List, Union, Tuple, Callable
import os
from demo_utils import LATEX_DELIMITERS, check_delete, exclusive_switch, respond, search


def get_current_user(
    request: gr.Request
) -> Tuple[str, List[str], List[str], List[str], List[str], List[str],
           List[str]]:
    username = request.username
    return username, os.listdir(f'{username}/code'), os.listdir(
        f'{username}/knowledgeBase'), os.listdir(
            f'{username}/paper'), os.listdir(
                f'{username}/repositry'), os.listdir(f'{username}/tempest')


def show_files(folder_path: str, file_list: List[str],
               msg: Dict[str, Union[str, List[str]]]) -> None:
    for file in os.listdir(folder_path):
        with gr.Row():
            file_button = gr.Button(file, scale=1, min_width=120)
            download_file_button = gr.DownloadButton(f"下载",
                                                     f'{folder_path}/{file}',
                                                     scale=0,
                                                     min_width=72)
            delete_file_button = gr.Button("删除", scale=0, min_width=72)

            def delete_file(file: str = file) -> List[str]:
                os.remove(f"{folder_path}/{file}")
                return os.listdir(folder_path)

            delete_file_button.click(delete_file,
                                     None,
                                     file_list,
                                     concurrency_limit=12)

            def append_to_msg(
                    msg: Dict[str, Union[str, List[str]]],
                    file: str = file) -> Dict[str, Union[str, List[str]]]:
                msg['text'] += file + "}"
                return msg

            file_button.click(append_to_msg, msg, msg, concurrency_limit=12)


with gr.Blocks(fill_height=True, fill_width=True,
               delete_cache=(3600, 3600)) as demo:
    current_user_directory = gr.State("")
    code_file_list = gr.State([])
    knowledgeBase_file_list = gr.State([])
    paper_file_list = gr.State([])
    repositry_file_list = gr.State([])
    tempest_file_list = gr.State([])
    demo.load(get_current_user, [], [
        current_user_directory, code_file_list, knowledgeBase_file_list,
        paper_file_list, repositry_file_list, tempest_file_list
    ])
    with gr.Tab("聊天"):
        with gr.Row():
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(type='messages',
                                     latex_delimiters=LATEX_DELIMITERS,
                                     show_copy_button=True,
                                     label="聊天框",
                                     scale=8)
                with gr.Tab("聊天"):
                    msg = gr.MultimodalTextbox(label="输入框",
                                            placeholder="输入文字，可点左侧按钮上传图片",
                                            scale=0,
                                            file_types=['image'])
                    with gr.Row():
                        clear_button = gr.ClearButton([msg, chatbot],
                                                    value="清除",
                                                    scale=1)
                        attach_button = gr.Button("引用", scale=1)
                        multimodal_switch = gr.Checkbox(
                            label="多模态",
                            info="模型可理解图片，但速度、纯文本推理能力下降。确保图片方向正确，尽可能裁剪",
                            scale=1)
                        knowledgeBase_switch = gr.Checkbox(
                            label="知识库",
                            info="查询已上传论文，将相关文段附加在用户输入前。可能干扰模型的基础推理能力",
                            scale=1)

                        clear_button.click(check_delete, [current_user_directory],
                                        None)

                        multimodal_switch.input(
                            exclusive_switch,
                            [multimodal_switch, knowledgeBase_switch],
                            [knowledgeBase_switch],
                            concurrency_limit=12)
                        knowledgeBase_switch.input(
                            exclusive_switch,
                            [knowledgeBase_switch, multimodal_switch],
                            [multimodal_switch],
                            concurrency_limit=12)

                    msg.submit(respond, [
                        msg, chatbot, multimodal_switch, knowledgeBase_switch,
                        current_user_directory
                    ], [msg, chatbot])
                with gr.Tab("搜索"):
                    search_box = gr.Textbox(label="搜索框", scale=1)
                    with gr.Row():
                        webSearch_button = gr.Button("网页搜索", scale=1, min_width=64)
                        academicSearch_button = gr.Button("论文搜索",
                                                        scale=1,
                                                        min_width=64)
                        webSearch_button.click(search('webSearch'), [search_box, chatbot],
                                            [search_box, chatbot])
                        academicSearch_button.click(search('academicSearch'),
                                                    [search_box, chatbot],
                                                    [search_box, chatbot])
            with gr.Column(scale = 0, min_width=384):
                with gr.Tab("论文"):
                    with gr.Row():
                        upload_paper = gr.UploadButton("上传论文", scale=1, min_width=64)
                        pass
demo.launch(auth=[('laowei', '1145141919810'), ('main', '2147483647')])
