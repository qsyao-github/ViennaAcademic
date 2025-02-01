from bceInference import update, get_response
import gradio as gr

with gr.Blocks(fill_height=True, fill_width=True,delete_cache=(3600, 3600)) as demo:
    with gr.Tab("QAnything"):
        update_button=gr.Button("更新知识库")
        update_button.click(update)
        query_input=gr.Textbox(label="输入问题")
        query_output=gr.Textbox(label="回答")
        query_button=gr.Button("回答问题")
        query_button.click(get_response, query_input, query_output)


demo.launch(server_port = 7861)
