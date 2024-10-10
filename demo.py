import gradio as gr
from gradio_multimodalchatbot import MultimodalChatbot
from gradio.data_classes import FileData
from chat import chatBot, promptcall
import time
import os
import shutil
from downloadpaper import downloadArxivPaper
from omniparse import parseEverything
from codeAnalysis import analyze_folder
import datetime
import re

with gr.Blocks(fill_height=True, fill_width=True) as demo:
    with gr.Row():
        with gr.Column(scale=0, min_width=150):
            websearchBtn = gr.Button("网页搜索", scale=0)
            readPaperBtn = gr.Button("论文解读", scale=0)
            translateToEng = gr.Button("论文翻译->英(如果要使用该功能，请上传txt, md文件)",
                                       scale=0)
            translateToChi = gr.Button("论文翻译->中", scale=0)
            polishPaper = gr.Button("论文润色", scale=0)
            findPaper = gr.Button("搜索论文", scale=0)
        with gr.Column(scale=8):
            chatbot = MultimodalChatbot(latex_delimiters=[{
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
            }],
                                        show_copy_button=True)
            msg = gr.Textbox()
            with gr.Row():
                clear = gr.ClearButton([msg, chatbot])
                attachBtn = gr.Button("引用")
            websearchBtn.click(lambda x: x + "#websearch{", msg, msg)
            attachBtn.click(lambda x: x + "#attach{", msg, msg)
            readPaperBtn.click(lambda x: x + "#readPaper{", msg, msg)
            translateToEng.click(lambda x: x + "#translatePapertoEnglish{",
                                 msg, msg)
            translateToChi.click(lambda x: x + "#translatePapertoChinese{",
                                 msg, msg)
            polishPaper.click(lambda x: x + "#polishPaper{", msg, msg)

            findPaper.click(lambda x: x + "#findPaper{", msg, msg)

            def respond(message, chat_history):
                # integrating multimodal conversion here
                message.replace('\\(', '$').replace('\\)', '$').replace(
                    '\\[', '$$').replace('\\]', '$$')
                message = re.sub(r'(\$\$)(\n+)', r'\1', message)
                message = promptcall(message)
                if type(message) != tuple:
                    nowTime = datetime.datetime.now().strftime('%y%m%d%H%M%S')
                    bot_message = chatBot(chat_history).answer(
                        message, len(chat_history),
                        nowTime).replace('\\(',
                                         '$').replace('\\)', '$').replace(
                                             '\\[', '$$').replace('\\]', '$$')
                    bot_message = re.sub(r'(\$\$)(\n+)', r'\1', bot_message)
                    bot_message = {
                        "text":
                        bot_message,
                        "files": [{
                            "file": FileData(path=nowTime + ".png")
                        }] if os.path.exists(nowTime + ".png") else []
                    }
                    message = {"text": message, "files": []}
                    chat_history.append([message, bot_message])
                else:
                    chat_history.append(message)
                time.sleep(2)
                return "", chat_history

            msg.submit(respond, [msg, chatbot], [msg, chatbot])
        with gr.Column(min_width=350):

            def upload_paper(file):
                simpfile = file[file.rfind("/") + 1:file.rfind(".")]
                gr.Info("已经开始上传，请不要重复提交，10页的论文大概需要2分钟，请耐心等候")
                if os.path.exists(
                        f"knowledgeBase/{simpfile}.md") or os.path.exists(
                            f"knowledgeBase/{simpfile}.txt"):
                    return
                upload_folder = "paper"
                shutil.copy(file, upload_folder)
                text = parseEverything(file)
                with open(f"knowledgeBase/{simpfile}.md", "w") as f:
                    f.write(text)
                gr.Info("上传成功，请刷新")

            def upload_file(file):
                # Windows uses \
                simpfile = file[file.rfind("\\") + 1:file.rfind(".")]
                suffix = file[file.rfind("."):]
                if suffix not in [".md", ".txt"]:
                    gr.Info("已经开始上传，请不要重复提交，10页的论文大概需要2分钟，请耐心等候")
                    if os.path.exists(f"userUpload/{simpfile}.md"):
                        return
                    shutil.copy(file, "userUpload")
                    text = parseEverything(file)
                    with open(f"userUpload/{simpfile}.md", "w") as f:
                        f.write(text)
                    gr.Info("上传成功，请刷新")
                else:
                    shutil.copy(file, "userUpload")

            with gr.Tab("论文/学术专著"):
                with gr.Row():
                    uploadThesis = gr.UploadButton("上传论文/学术专著", scale=1)
                    uploadThesis.upload(upload_paper, uploadThesis)
                    refresh = gr.Button("刷新", scale=0, min_width=120)
                arxivNum = gr.Textbox()
                downloadArxiv = gr.Button("arxiv论文下载", scale=0)

                def gradiodownloadArxivPaper(arxivNum):
                    gr.Info("正在下载，请耐心等候")
                    downloadArxivPaper(arxivNum)
                    gr.Info("下载完成，请刷新")
                    return ""

                downloadArxiv.click(downloadArxivPaper, arxivNum, arxivNum)

                @gr.render(triggers=[refresh.click])
                def show_Files():
                    for file in os.listdir(r"paper"):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0, min_width=120)
                            downloadFile = gr.DownloadButton(f"下载",
                                                             f'paper/{file}',
                                                             scale=0,
                                                             min_width=70)
                            deleteFile = gr.Button("删除", scale=0, min_width=70)

                            def delete_file(file=file):
                                os.remove(f"paper/{file}")

                            deleteFile.click(delete_file, None, None)

                        def appendToMsg(msg, file=file):
                            return msg + f"{file}" + "}"

                        fileBtn.click(appendToMsg, msg, msg)

            with gr.Tab("临时文件"):
                with gr.Row():
                    uploadFile = gr.UploadButton("上传文件", scale=0)
                    uploadFile.upload(upload_file, uploadFile)
                    refresh = gr.Button("刷新", scale=0, min_width=100)

                @gr.render(triggers=[refresh.click])
                def show_upload():
                    for file in os.listdir(r'userUpload'):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0, min_width=120)
                            deleteFile = gr.Button("删除", scale=0, min_width=70)

                            def delete_file(file=file):
                                os.remove(f"userUpload/{file}")

                            deleteFile.click(delete_file, None, None)

                        def appendToMsg(msg, file=file):
                            return msg + f"{file}" + "}"

                        fileBtn.click(appendToMsg, msg, msg)

            with gr.Tab("代码仓库"):
                refresh = gr.Button("刷新", scale=0, min_width=100)
                githubUrl = gr.Textbox()
                githubClone = gr.Button("克隆仓库", scale=0)

                def clone_repo(url):
                    if url:
                        gr.Info("正在克隆，请耐心等候")
                        os.system(f"cd repositry && git clone {url}")
                        gr.Info("克隆完成，请刷新")
                    return ""

                githubClone.click(clone_repo, githubUrl, githubUrl)

                @gr.render(triggers=[refresh.click])
                def showFolder():
                    for folder in os.listdir(r'repositry'):
                        folderBtn = gr.Button("解析" + folder,
                                              scale=0,
                                              min_width=120)

                        def delete_folder(folder=folder):
                            shutil.rmtree(f"repositry/{folder}")

                        deleteFolder = gr.Button("删除", scale=0, min_width=70)
                        deleteFolder.click(delete_folder, None, None)

                        def output_analysis(chathistory, folder=folder):
                            chathistory.append(
                                (f"分析{folder}",
                                 f"{analyze_folder(f'repositry/{folder}')}"))
                            return chathistory

                        folderBtn.click(output_analysis, chatbot, chatbot)

            with gr.Tab("已解析文件"):
                gr.Button("只有在本列表中的.md文件才可以引用、解读、翻译、润色")
                refresh = gr.Button("刷新", scale=0, min_width=120)

                @gr.render(triggers=[refresh.click])
                def show_knowledgeBase():
                    for file in os.listdir(r'knowledgeBase'):
                        gr.Button(file)


demo.launch()
