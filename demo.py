import gradio as gr
import time
import os
import re
import datetime
from chat import add_message
from io import StringIO

LATEX_DELIMITERS = [{
    'left': '$$',
    'right': '$$',
    'display': True
}, {
    'left': '$',
    'right': '$',
    'display': False
}, {
    'left': r'\(',
    'right': r'\)',
    'display': False
}, {
    'left': r'\[',
    'right': r'\]',
    'display': True
}]

FORMAT_FORMULA_PATTERN = re.compile(r'\$\$[\s]*(.*?)\s*[\s]*\$\$', flags=re.DOTALL)


def format_formula(text):
    return FORMAT_FORMULA_PATTERN.sub(r'$$\1$$', text.replace('\\(', '$').replace('\\)', '$').replace('\\[', '$$').replace('\\]', '$$'))


with gr.Blocks(fill_height=True, fill_width=True,
               delete_cache=(3600, 3600)) as demo:
    current_user_directory = "./"
    with gr.Tab("聊天"):
        with gr.Row():
            with gr.Column(scale=0, min_width=108):
                websearch_button = gr.Button("网页搜索", scale=1, min_width=64)
                find_paper = gr.Button("搜索论文", scale=1, min_width=64)
                generate_docstring = gr.Button("生成注释", scale=1, min_width=64)
                optimize_code = gr.Button("优化代码", scale=1, min_width=64)
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(type='messages', latex_delimiters=LATEX_DELIMITERS,
                                    show_copy_button=True,
                                    label="聊天框",
                                    scale=8)
                msg = gr.MultimodalTextbox(label="输入框",
                                        placeholder="输入文字，可点左侧按钮上传图片",
                                        scale=0,
                                        file_types=['image'])
                with gr.Row():
                    clear_button = gr.Button("清除")
                    attach_button = gr.Button("引用", scale=1)
                    multimodal_switch = gr.Checkbox(
                        label="多模态",
                        info="模型可理解图片，但速度、纯文本推理能力下降。确保图片方向正确，尽可能裁剪",
                        scale=1)
                    knowledgeBase_switch = gr.Checkbox(
                        label="知识库",
                        info="查询已上传论文，将相关文段附加在用户输入前。可能干扰模型的基础推理能力",
                        scale=1)

                def clear(chatbot):
                    now = time.time()
                    three_days_ago = now - 259200
                    return [], ""

                clear_button.click(clear, [chatbot], [chatbot, msg])

                def switch_multimodal(multimodal_switch, knowledgeBase_switch):
                    if multimodal_switch:
                        knowledgeBase_switch = False
                    return knowledgeBase_switch

                def switch_knowledgeBase(knowledgeBase_switch, multimodal_switch):
                    if knowledgeBase_switch:
                        multimodal_switch = False
                    return multimodal_switch

                multimodal_switch.input(switch_multimodal,
                                        [multimodal_switch, knowledgeBase_switch],
                                        [knowledgeBase_switch],
                                        concurrency_limit=12)
                knowledgeBase_switch.input(
                    switch_knowledgeBase,
                    [knowledgeBase_switch, multimodal_switch], [multimodal_switch],
                    concurrency_limit=12)

                def respond(msg, chatbot, multimodal_switch, knowledgeBase_switch):
                    possible_media_path = f'{datetime.datetime.now().strftime(
                                '%y%m%d%H%M%S')}.png'
                    text, files = msg["text"], msg["files"]
                    text = format_formula(text)
                    chatbot.append({"role": "user", 'metadata': None, "content": text, 'options': None})
                    for file in files:
                        chatbot.append({"role": "user", "content": {"path": file}})
                    chatbot.append({"role":"assistant", "content": ""})
                    thread_id = str(chatbot[0])
                    print(thread_id)
                    bot_response = add_message(text, files, thread_id, multimodal_switch)
                    temp_response = StringIO()
                    for chunk in bot_response:
                        temp_response.write(chunk)
                        chatbot[-1]["content"] = temp_response.getvalue()
                        yield {"text": "", "files": []}, chatbot
                    chatbot[-1]["content"] = format_formula(temp_response.getvalue())
                    if possible_media_path in os.listdir(current_user_directory):
                        chatbot.append({"role": "assistant", "content": {"path": possible_media_path}})
                    yield {"text": "", "files": []}, chatbot
                msg.submit(
                        respond,
                        [msg, chatbot, multimodal_switch, knowledgeBase_switch],
                        [msg, chatbot])
demo.launch()
