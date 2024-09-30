import gradio as gr
from chat import chatBot
import time
import os
import shutil
from downloadpaper import downloadArxivPaper
from omniparse import parseEverything
from codeAnalysis import analyze_folder

with gr.Blocks(fill_height=True, fill_width=True) as demo:
    with gr.Row():
        with gr.Column(scale=0, min_width=150):
            readPaperBtn = gr.Button("论文解读", scale=0)
            translateToEng = gr.Button("论文翻译->英", scale=0)
            translateToChi = gr.Button("论文翻译->中", scale=0)
            polishPaper = gr.Button("论文润色", scale=0)
            findPaper = gr.Button("搜索论文", scale=0)
        with gr.Column(scale=8):
            chatbot = gr.Chatbot()
            msg = gr.Textbox()
            with gr.Row():
                clear = gr.ClearButton([msg, chatbot])
                attachBtn = gr.Button("引用")
            attachBtn.click(lambda x: x + "#attach(", msg, msg)
            readPaperBtn.click(lambda x: x + "#readPaper(", msg, msg)
            translateToEng.click(lambda x: x + "#translatePapertoEnglish(",
                                 msg, msg)
            translateToChi.click(lambda x: x + "#translatePapertoChinese(",
                                 msg, msg)
            polishPaper.click(lambda x: x + "#polishPaper(", msg, msg)

            findPaper.click(lambda x: x + "#findPaper(", msg, msg)

            def respond(message, chat_history):
                bot_message = chatBot(chat_history).answer(message)
                chat_history.append((message, bot_message))
                print(chat_history)
                time.sleep(2)
                return "", chat_history

            msg.submit(respond, [msg, chatbot], [msg, chatbot])
        with gr.Column(min_width=350):

            def upload_paper(file):
                upload_folder = "paper"
                text = parseEverything(file)
                shutil.copy(file, upload_folder)
                file = file[file.rfind("\\") + 1:file.rfind(".")]
                with open(f"knowledgeBase/{file}.md", "w") as f:
                    f.write(text)

            def upload_file(file):
                upload_folder = "userUpload"
                text = parseEverything(file)
                file = file[file.rfind("\\") + 1:file.rfind(".")]
                with open(f"userUploads/{file}.md", "w") as f:
                    f.write(text)

            def upload_folderorFile(file):
                upload_folder = "repositry"
                shutil.copy(file, upload_folder)

            with gr.Tab("论文/学术专著"):
                with gr.Row():
                    uploadThesis = gr.UploadButton("上传论文/学术专著", scale=1)
                    uploadThesis.upload(upload_paper, uploadThesis)
                    refresh = gr.Button("刷新", scale=0, min_width=120)
                arxivNum = gr.Textbox()
                downloadArxiv = gr.Button("arxiv论文下载", scale=0)
                downloadArxiv.click(downloadArxivPaper, arxivNum, None)

                @gr.render(triggers=[refresh.click])
                def show_Files():
                    for file in os.listdir(r"paper"):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=1)
                            downloadFile = gr.DownloadButton(f"下载",
                                                             f'paper/{file}',
                                                             scale=0,
                                                             min_width=120)

                        def appendToMsg(msg, file=file):
                            return msg + f"{file})"

                        fileBtn.click(appendToMsg, msg, msg)

            with gr.Tab("上传文件"):
                with gr.Row():
                    uploadFile = gr.UploadButton("临时文件", scale=0)
                    uploadFile.upload(upload_file, uploadFile)
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                @gr.render(triggers=[refresh.click])
                def show_upload():
                    for file in os.listdir(r'userUploads'):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=1)

                        def appendToMsg(msg, file=file):
                            return msg + f"{file})"

                        fileBtn.click(appendToMsg, msg, msg)

            with gr.Tab("test"):
                with gr.Row():
                    uploadFolder = gr.UploadButton("上传文件夹", scale=0)
                    uploadFolder.upload(upload_folderorFile, uploadFolder)
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                @gr.render()
                def showFolder():
                    for folder in os.listdir(r'repositry'):
                        folderBtn = gr.Button(folder, scale=1, min_width=120)

                        def output_analysis(chathistory, folder=folder):
                            chathistory.append(
                                (f"分析{folder}",
                                 f"{analyze_folder(f'repositry/{folder}')}"))
                            return chathistory

                        folderBtn.click(output_analysis, chatbot, chatbot)


demo.launch()
