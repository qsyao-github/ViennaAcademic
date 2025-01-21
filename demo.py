import gradio as gr
from gradio_multimodalchatbot import MultimodalChatbot
from gradio.data_classes import FileData
from chat import chatBot, promptcall
import os
import shutil
from codeAnalysis import analyze_folder
import datetime
import regex as re
from laoweiService import generate
from downloadpaper import downloadArxivPaper
from doclingParse import parseEverything
from gptmath import solve
from collections.abc import Iterator


def remove_newlines_from_formulas(text):
    # 用正则表达式匹配并替换
    pattern = r'\$\$[\s\r\n]*(.*?)\s*[\s\r\n]*\$\$'
    replacement = r'$$\1$$'
    result = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return result


def addToMsg(newStr):

    def subaddToMsg(msg):
        msg['text'] = msg['text'] + newStr
        return msg

    return subaddToMsg


with gr.Blocks(fill_height=True, fill_width=True) as demo:
    with gr.Tab("ViennaAcademic"):
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
                msg = gr.MultimodalTextbox()
                with gr.Row():
                    clear = gr.ClearButton([msg, chatbot])
                    attachBtn = gr.Button("引用")
                    multimodalSwitch = gr.Checkbox(
                        label="多模态",
                        info=
                        "若勾选，模型可直接理解图片，但速度与纯文本推理能力下降。确保图片方向正确，尽可能裁剪，用输入框左侧按钮上传"
                    )

                def checkDelete():
                    for file in os.listdir():
                        if file.endswith(".png") or file.endswith(
                                ".mp4") or file.endswith(".txt"):
                            os.remove(file)

                clear.click(checkDelete, None, None)
                websearchBtn.click(addToMsg("#websearch{"), msg, msg)
                attachBtn.click(addToMsg("#attach{"), msg, msg)
                readPaperBtn.click(addToMsg("#readPaper{"), msg, msg)
                translateToEng.click(addToMsg("#translatePapertoEnglish{"),
                                     msg, msg)
                translateToChi.click(addToMsg("#translatePapertoChinese{"),
                                     msg, msg)
                polishPaper.click(addToMsg("#polishPaper{"), msg, msg)

                findPaper.click(addToMsg("#findPaper{"), msg, msg)
                multimodal = gr.State(False)

                def switch_multimodal():
                    global multimodal
                    multimodal = gr.State(not multimodal.value)

                multimodalSwitch.input(switch_multimodal)

                def respond(message, chat_history):
                    # integrating multimodal conversion here
                    if type(message) != str:
                        message, files = message["text"], message["files"]
                    message.replace('\\(', '$').replace('\\)', '$').replace(
                        '\\[', '$$').replace('\\]', '$$')
                    message = remove_newlines_from_formulas(message)
                    message = promptcall(message)
                    if not isinstance(message, Iterator):
                        message = {
                            "text":
                            message,
                            "files": [{
                                "file": FileData(path=file)
                            } for file in files]
                        }
                        nowTime = datetime.datetime.now().strftime(
                            '%y%m%d%H%M%S')
                        bot_stream = chatBot(chat_history,
                                             multimodal.value).answer(
                                                 message,
                                                 len(''.join([
                                                     i[0].text + i[1].text
                                                     for i in chat_history
                                                 ])), nowTime,
                                                 multimodal.value)
                        os.chdir(r'/home/laowei/ViennaAcademic')
                        chat_history.append([
                            message, {
                                "text":
                                "",
                                "files":
                                ([{
                                    "file": FileData(path=nowTime + ".png")
                                }] if os.path.exists(nowTime + ".png") else [])
                                + ([{
                                    "file": FileData(path=nowTime + ".mp4")
                                }] if os.path.exists(nowTime + ".mp4") else [])
                            }
                        ])
                        for bot_chunk in bot_stream:
                            bot_message = {
                                "text":
                                bot_chunk,
                                "files":
                                ([{
                                    "file": FileData(path=nowTime + ".png")
                                }] if os.path.exists(nowTime + ".png") else [])
                                + ([{
                                    "file": FileData(path=nowTime + ".mp4")
                                }] if os.path.exists(nowTime + ".mp4") else [])
                            }
                            chat_history.pop()
                            chat_history.append([message, bot_message])
                            yield gr.MultimodalTextbox(
                                value=None), chat_history
                    else:
                        for chunk in message:
                            if chat_history:
                                chat_history.pop()
                            chat_history.append([{
                                "text": chunk[0],
                                "files": []
                            }, {
                                "text": chunk[1],
                                "files": []
                            }])
                            yield gr.MultimodalTextbox(value=None), chat_history

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
                    simpfile = file[file.rfind("/") + 1:file.rfind(".")]
                    suffix = file[file.rfind("."):]
                    if suffix not in [".md", ".txt"]:
                        gr.Info("已经开始上传，请不要重复提交，10页的论文大概需要1分钟，请耐心等候")
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

                    @gr.render(triggers=[refresh.click])
                    def show_Files():
                        for file in os.listdir(r"paper"):
                            with gr.Row():
                                fileBtn = gr.Button(file,
                                                    scale=0,
                                                    min_width=120)
                                downloadFile = gr.DownloadButton(
                                    f"下载",
                                    f'paper/{file}',
                                    scale=0,
                                    min_width=70)
                                deleteFile = gr.Button("删除",
                                                       scale=0,
                                                       min_width=70)

                                def delete_file(file=file):
                                    os.remove(f"paper/{file}")

                                deleteFile.click(delete_file, None, None)

                            def appendToMsg(msg, file=file):
                                msg['text'] = msg['text'] + f"{file}" + "}"
                                return msg

                            fileBtn.click(appendToMsg, msg, msg)

                with gr.Tab("已解析文件"):
                    gr.Button("只有在本列表中的.md文件才可以引用、解读、翻译、润色")
                    refresh = gr.Button("刷新", scale=0, min_width=120)
                    arxivNum = gr.Textbox(placeholder="输入arxiv号，例如：1706.03762")
                    downloadArxiv = gr.Button("arxiv论文下载", scale=0)

                    def gradiodownloadArxivPaper(arxivNum,
                                                 chat_history=chatbot):
                        gr.Info("正在下载，请耐心等候")
                        chat_history.append([{
                            "text": f"下载{arxivNum}并翻译标题与摘要",
                            "files": []
                        }, {
                            "text":
                            downloadArxivPaper(arxivNum),
                            "files": []
                        }])
                        gr.Info("下载完成，请刷新")
                        return "", chat_history

                    downloadArxiv.click(gradiodownloadArxivPaper,
                                        [arxivNum, chatbot],
                                        [arxivNum, chatbot])

                    @gr.render(triggers=[refresh.click])
                    def show_knowledgeBase():
                        for file in os.listdir(r'knowledgeBase'):
                            with gr.Row():
                                fileBtn = gr.Button(file,
                                                    scale=0,
                                                    min_width=120)
                                downloadFile = gr.DownloadButton(
                                    f"下载",
                                    f'knowledgeBase/{file}',
                                    scale=0,
                                    min_width=70)
                                deleteFile = gr.Button("删除",
                                                       scale=0,
                                                       min_width=70)

                                def delete_file(file=file):
                                    os.remove(f"knowledgeBase/{file}")

                                deleteFile.click(delete_file, None, None)
                            def appendToMsg(msg, file=file):
                                msg['text'] = msg['text'] + f"{file}" + "}"
                                return msg

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

                            deleteFolder = gr.Button("删除",
                                                     scale=0,
                                                     min_width=70)
                            deleteFolder.click(delete_folder, None, None)

                            def output_analysis(chathistory, folder=folder):
                                chathistory.append([{
                                    "text": f"解析{folder}",
                                    "files": []
                                }, {
                                    "text":
                                    f"{analyze_folder(f'repositry/{folder}')}",
                                    "files": []
                                }])
                                return chathistory

                            folderBtn.click(output_analysis, chatbot, chatbot)

    with gr.Tab("实验性功能"):
        with gr.Tab("全自动生成论文"):
            title = gr.Textbox(placeholder="输入主题，例如：中华民族共同体意识, Fluid Field")
            with gr.Row():
                max_conv_turn = gr.Number(label="Brain Storm轮数",
                                          info="与文章丰富程度正相关。默认为3，可不填写",
                                          precision=0)
                perspective = gr.Number(label="切入角度数",
                                        info="与文章丰富程度正相关，按需填写(或不填写)，默认为3",
                                        precision=0)
                top_k = gr.Number(label="搜索引擎返回结果数",
                                  info="与文章丰富程度正相关。默认为3，可不填写",
                                  precision=0)
            generate_button = gr.Button("生成论文")
            thesisBox = gr.Markdown("生成的论文将显示在此，markdown源文件在VA主页面“已解析文件”下，可下载")

            def generateAndSave(title, max_conv_turn, perspective, top_k):
                max_conv_turn = max_conv_turn if max_conv_turn > 3 else 3
                max_perspective = perspective if perspective > 3 else 3
                search_top_k = top_k if top_k > 3 else 3
                if title.strip() == "":
                    return "请输入主题"
                else:
                    gr.Info(
                        f"正在生成，大概需要{int(600/27*max_conv_turn*max_perspective*search_top_k)}s，请不要关闭界面。稍后可去已解析文件中获取md文件"
                    )
                    thesis = generate(title, max_conv_turn, max_perspective,
                                      search_top_k)
                    with open(f'knowledgeBase/{title}.md', 'w') as f:
                        f.write(thesis)
                    return thesis

            generate_button.click(generateAndSave,
                                  [title, max_conv_turn, perspective, top_k],
                                  thesisBox)
        with gr.Tab("解理科题目"):

            def reason(question):
                if question.strip() == "":
                    return "请输入题目"
                else:
                    gr.Info("正在解题，不要关闭页面，大约需2min")
                    print(question)
                    answer = solve(question)
                    # answer = answer.replace('\\(', '$').replace('\\)', '$').replace('\\[', '$$').replace('\\]', '$$')
                    # answer = remove_newlines_from_formulas(answer)
                    for chunk in answer:
                        yield chunk

            problem = gr.Textbox(placeholder="输入题目，难度不宜低于小学奥数，不宜高于IMO第1, 4题")
            solve_button = gr.Button("解题")
            answerBox = gr.Markdown("答案将显示在此，若存在明显错误或报错，可多次尝试。每次的回答未必相同",
                                    latex_delimiters=[{
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
            solve_button.click(reason, problem, answerBox)

demo.launch(auth=("laowei", "1145141919810"))
