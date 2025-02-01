import gradio as gr
from gradio_multimodalchatbot import MultimodalChatbot
from gradio.data_classes import FileData
from chat import chatBot, promptcall, remove_newlines_from_formulas, formatFormula
import os
import shutil
from codeAnalysis import analyze_folder
import datetime
from generate import generate
from downloadpaper import downloadArxivPaper
from doclingParse import parseEverything
from deepseek import solve
from qanythingClient import update, qanything_fetch

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


def addToMsg(newStr):

    def subaddToMsg(msg):
        msg['text'] = msg['text'] + newStr
        return msg

    return subaddToMsg


def constructMultimodalMessage(msg, filesConstructor):
    return {"text": msg, "files": filesConstructor}


def userFileConstructor(files):
    return [{"file": FileData(path=file)} for file in files]


def botFileConstructor(nowTime):
    files = []
    for file_type in [".png", ".mp4"]:
        file_path = nowTime + file_type
        if os.path.exists(file_path):
            files.append({"file": FileData(path=file_path)})
    return files


def doubleMessage(msg1, msg2):
    return [{"text": msg1, "files": []}, {"text": msg2, "files": []}]


with gr.Blocks(fill_height=True, fill_width=True,delete_cache=(3600, 3600)) as demo:
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
                chatbot = MultimodalChatbot(latex_delimiters=LATEX_DELIMITERS,
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
                    knowledgeBaseSwitch = gr.Checkbox(
                        label="知识库",
                        info=
                        "若勾选，模型每次回复前，服务器都将查询已经上传的论文/学术专著，供模型整合作答。大量文本可能干扰模型的基础推理能力。"
                    )

                def checkDelete():
                    file_suffixes_to_remove = {".png", ".mp4", ".txt"}
                    for file in os.listdir():
                        if any(
                                file.endswith(suffix)
                                for suffix in file_suffixes_to_remove):
                            os.remove(file)
                    if os.path.exists('media'):
                        shutil.rmtree('media')
                    if os.path.exists('arxivSource'):
                        shutil.rmtree('arxivSource')
                        os.mkdir('arxivSource')

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
                knowledgeBase = gr.State(False)

                def switch_multimodal(multimodalSwitchValue):
                    global multimodal
                    global knowledgeBase
                    multimodal = gr.State(multimodalSwitchValue)
                    if multimodal.value:
                        knowledgeBase = gr.State(False)
                        knowledgeBaseSwitch.value = False
                    return knowledgeBase.value

                def switch_knowledgeBase(knowledgeBaseSwitchValue):
                    global knowledgeBase
                    global multimodal
                    knowledgeBase = gr.State(knowledgeBaseSwitchValue)
                    if knowledgeBase.value:
                        multimodal = gr.State(False)
                        multimodalSwitch.value = False
                    return multimodal.value

                multimodalSwitch.input(switch_multimodal, [multimodalSwitch],
                                       [knowledgeBaseSwitch])
                knowledgeBaseSwitch.input(switch_knowledgeBase,
                                          [knowledgeBaseSwitch],
                                          [multimodalSwitch])

                def respond(message, chat_history):
                    # integrating multimodal conversion here
                    if type(message) != str:
                        message, files = message["text"], message["files"]
                    message = formatFormula(message)
                    message = remove_newlines_from_formulas(message)
                    message = promptcall(message)
                    if isinstance(message, str):
                        if knowledgeBase.value:
                            knowledgeBaseSearch = qanything_fetch(message)
                            if knowledgeBaseSearch:
                                message = knowledgeBaseSearch + '\n\n' + message
                        message = constructMultimodalMessage(
                            message, userFileConstructor(files))
                        nowTime = datetime.datetime.now().strftime(
                            '%y%m%d%H%M%S')
                        bot = chatBot(chat_history, multimodal.value)
                        bot_stream = bot.answer(
                            message,
                            len(''.join([
                                i[0].text + i[1].text for i in chat_history
                            ])), nowTime, multimodal.value)
                        os.chdir(r'/home/laowei/ViennaAcademic')
                        chat_history.append([
                            message,
                            constructMultimodalMessage(
                                "", botFileConstructor(nowTime))
                        ])
                        for bot_chunk in bot_stream:
                            bot_message = constructMultimodalMessage(
                                bot_chunk, botFileConstructor(nowTime))
                            chat_history.pop()
                            chat_history.append([message, bot_message])
                            yield gr.MultimodalTextbox(
                                value=None), chat_history
                    elif isinstance(message, tuple):
                        chat_history.append(
                            doubleMessage(message[0], message[1]))
                        yield gr.MultimodalTextbox(value=None), chat_history
                    else:
                        for chunk in message:
                            if chat_history:
                                chat_history.pop()
                            chat_history.append(
                                doubleMessage(chunk[0], chunk[1]))
                            yield gr.MultimodalTextbox(
                                value=None), chat_history

                msg.submit(respond, [msg, chatbot], [msg, chatbot])
            with gr.Column(min_width=350):

                def upload_paper(file):
                    simpfile = os.path.splitext(os.path.basename(file))[0]
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
                    update()
                    gr.Info("上传成功，请刷新")

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
                                """def delete_file(file=file):
                                    os.remove(f"paper/{file}")"""

                                deleteFile.click(lambda file=file: os.remove(
                                    f"paper/{file}"),
                                                 None,
                                                 None)

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
                        chat_history.append(
                            doubleMessage(f"正在下载{arxivNum}并翻译标题与摘要",
                                          downloadArxivPaper(arxivNum)))
                        update()
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
                                """def delete_file(file=file):
                                    os.remove(f"knowledgeBase/{file}")
                                    update()"""

                                deleteFile.click(lambda file=file: (os.remove(
                                    f"knowledgeBase/{file}"), update()),
                                                 None,
                                                 None)

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
                            """def delete_folder(folder=folder):
                                shutil.rmtree(f"repositry/{folder}")"""

                            deleteFolder = gr.Button("删除",
                                                     scale=0,
                                                     min_width=70)
                            deleteFolder.click(lambda folder=folder: shutil.
                                               rmtree(f"repositry/{folder}"),
                                               None,
                                               None)

                            def output_analysis(chathistory, folder=folder):
                                chathistory.append(
                                    doubleMessage(
                                        f"解析{folder}",
                                        f"{analyze_folder(f'repositry/{folder}')}"
                                    ))
                                return chathistory

                            folderBtn.click(output_analysis, chatbot, chatbot)

    with gr.Tab("实验性功能"):
        with gr.Tab("全自动生成论文"):
            title = gr.Textbox(placeholder="输入主题，例如：中华民族共同体意识, Fluid Field")
            generate_button = gr.Button("生成论文")
            thesisBox = gr.Markdown("生成的论文将显示在此，markdown源文件在VA主页面“已解析文件”下，可下载")

            def generateAndSave(title):
                if title.strip() == "":
                    return "请输入主题"
                else:
                    gr.Info(f"正在生成，大概需要600s，请不要关闭界面。稍后可去已解析文件中获取md文件")
                    thesisGenerator = generate(title)
                    for tempThesis in thesisGenerator:
                        thesis = tempThesis
                        yield thesis
                    with open(f'knowledgeBase/{title}.md', 'w') as f:
                        f.write(thesis)
                    yield thesis

            generate_button.click(generateAndSave, [title], thesisBox)
        with gr.Tab("解理科题目"):

            def reason(question):
                if question.strip() == "":
                    return "请输入题目"
                else:
                    gr.Info("正在解题，不要关闭页面，大约需2min")
                    answer = solve(question)
                    for chunk in answer:
                        yield chunk

            problem = gr.Textbox(placeholder="输入题目，难度不宜低于小学奥数，不宜高于IMO第1, 4题")
            solve_button = gr.Button("解题")
            answerBox = gr.Markdown("答案将显示在此，若存在明显错误或报错，可多次尝试。每次的回答未必相同",
                                    latex_delimiters=LATEX_DELIMITERS,
                                    show_copy_button=True)
            solve_button.click(reason, problem, answerBox)

demo.launch(auth=("laowei", "1145141919810"), server_port=7860)
