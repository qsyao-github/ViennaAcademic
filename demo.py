import gradio as gr
from chat import chatBot
import time
import os
from downloadpaper import downloadArxivPaper

with gr.Blocks(fill_height=True, fill_width=True) as demo:
    with gr.Row():
        with gr.Column(scale=0):
            readPaperBtn = gr.Button("论文解读", scale=0)
            translateToEng = gr.Button("论文翻译->英", scale=0)
            translateToChi = gr.Button("论文翻译->中", scale=0)
            polishPaper = gr.Button("论文润色", scale=0)
            findPaper = gr.Button("搜索论文", scale=0)
            sourceCodeAnalysis = gr.Button("源代码解析", scale=0)
            autoComment = gr.Button("生成注释", scale=0)
        with gr.Column(scale=8):
            chatbot = gr.Chatbot()
            msg = gr.Textbox()
            clear = gr.ClearButton([msg, chatbot])
            attachBtn = gr.Button("引用")
            attachBtn.click(lambda x: x + "\n#attach(", msg, msg)
            readPaperBtn.click(lambda x: x + "\n#readPaper(", msg, msg)
            translateToEng.click(lambda x: x + "\n#translatePapertoEnglish(",
                                 msg, msg)
            translateToChi.click(lambda x: x + "\n#translatePapertoChinese(",
                                 msg, msg)
            polishPaper.click(lambda x: x + "\n#polishPaper(", msg, msg)

            findPaper.click(lambda x: x + "\n#findPaper(", msg, msg)
            sourceCodeAnalysis.click(lambda x: x + "\n#analyzeFolder(", msg,
                                     msg)
            autoComment.click(lambda x: x + "\n#comment(", msg, msg)

            def respond(message, chat_history):
                bot_message = chatBot(chat_history).answer(message)
                chat_history.append((message, bot_message))
                print(chat_history)
                time.sleep(2)
                return "", chat_history

            msg.submit(respond, [msg, chatbot], [msg, chatbot])
        with gr.Column(scale=0):
            def upload_file(files):
                file_paths = [file.name for file in files]
                return file_paths
            with gr.Tab("论文/学术专著"):
                @gr.render()
                def show_Files():
                    for file in os.listdir(
                            r"C:\Users\15081\Desktop\glmacademic\paper"):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0)
                            downloadFile=gr.DownloadButton("下载文件",file,scale=0)
                            def appendToMsg(msg, file=file):
                                return msg + f"{file})"

                            fileBtn.click(appendToMsg, msg, msg)
                            
                uploadThesis = gr.UploadButton("上传论文/学术专著", scale=0)
                arxivNum = gr.Textbox()
                downloadArxiv = gr.Button("arxiv论文下载", scale=0)
                downloadArxiv.click(downloadArxivPaper,arxivNum,None)
            with gr.Tab("上传文件"):
                uploadFile= gr.UploadButton("上传文件", scale=0)
                uploadFile.upload()
                @gr.render()
                def show_upload():
                    for file in os.listdir(r'C:\Users\15081\Desktop\glmacademic\userUploads'):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0)
                            downloadFile=gr.DownloadButton("下载文件",file,scale=0)
                            def appendToMsg(msg, file=file):
                                return msg + f"{file})"
                            fileBtn.click(appendToMsg, msg, msg)


demo.launch()
