import gradio as gr
from gradio_multimodalchatbot import MultimodalChatbot
from gradio.data_classes import FileData
from chat import chatBot, promptcall, remove_newlines_from_formulas, formatFormula, insertMultimodalHistory, QvQchatBot
import os
import shutil
from codeAnalysis import analyze_folder
import datetime
from generate import generate
from downloadpaper import downloadArxivPaper
from doclingParse import parseEverything
from deepseek import deepseek, attachHints
from qanythingClient import update, qanything_fetch
from fileConversion import convert_to_pptx, convert_to
from imageUtils import encode_image
from modelclient import client1

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


with gr.Blocks(fill_height=True, fill_width=True,
               delete_cache=(3600, 3600)) as demo:
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
                generateDocstring = gr.Button("生成注释", scale=0)
                optimizeCode = gr.Button("优化代码", scale=0)
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
                generateDocstring.click(addToMsg("#generateDocstring{"), msg,
                                        msg)
                optimizeCode.click(addToMsg("#optimizeCode{"), msg, msg)

                def switch_multimodal(multimodalSwitch, knowledgeBaseSwitch):
                    if multimodalSwitch:
                        knowledgeBaseSwitch = False
                    return knowledgeBaseSwitch

                def switch_knowledgeBase(knowledgeBaseSwitch,
                                         multimodalSwitch):
                    if knowledgeBaseSwitch:
                        multimodalSwitch = False
                    return multimodalSwitch

                multimodalSwitch.input(switch_multimodal,
                                       [multimodalSwitch, knowledgeBaseSwitch],
                                       [knowledgeBaseSwitch])
                knowledgeBaseSwitch.input(
                    switch_knowledgeBase,
                    [knowledgeBaseSwitch, multimodalSwitch],
                    [multimodalSwitch])

                def respond(message, chat_history, multimodal, knowledgeBase):
                    # integrating multimodal conversion here
                    if type(message) != str:
                        message, files = message["text"], message["files"]
                    message = formatFormula(message)
                    message = remove_newlines_from_formulas(message)
                    message = promptcall(message)
                    if isinstance(message, str):
                        if knowledgeBase:
                            knowledgeBaseSearch = qanything_fetch(message)
                            if knowledgeBaseSearch:
                                message = knowledgeBaseSearch + '\n\n' + message
                        message = constructMultimodalMessage(
                            message, userFileConstructor(files))
                        nowTime = datetime.datetime.now().strftime(
                            '%y%m%d%H%M%S')
                        bot = chatBot(chat_history, multimodal)
                        bot_stream = bot.answer(message, nowTime, multimodal)
                        os.chdir(r'/home/laowei/ViennaAcademic')
                        chat_history.append([
                            message,
                            constructMultimodalMessage(
                                "", botFileConstructor(nowTime))
                        ])
                        for bot_chunk in bot_stream:
                            bot_message = constructMultimodalMessage(
                                bot_chunk, botFileConstructor(nowTime))
                            chat_history[-1] = [message, bot_message]
                            yield gr.MultimodalTextbox(
                                value=None), chat_history
                    elif isinstance(message, tuple):
                        chat_history.append(
                            doubleMessage(message[0], message[1]))
                        yield gr.MultimodalTextbox(value=None), chat_history
                    else:
                        chunk = next(message)
                        chat_history.append(doubleMessage(chunk[0], chunk[1]))
                        yield gr.MultimodalTextbox(value=None), chat_history
                        for chunk in message:
                            chat_history[-1] = doubleMessage(
                                chunk[0], chunk[1])
                            yield gr.MultimodalTextbox(
                                value=None), chat_history

                msg.submit(
                    respond,
                    [msg, chatbot, multimodalSwitch, knowledgeBaseSwitch],
                    [msg, chatbot])
            with gr.Column(min_width=350):

                def upload_paper(file):
                    gr.Info("已经开始上传，请不要重复提交，10页的论文大概需要40s，请耐心等候")
                    simpfile = os.path.splitext(os.path.basename(file))[0]
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

                def base_show_regular_files(folder):
                    for file in os.listdir(folder):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0, min_width=120)
                            downloadFile = gr.DownloadButton(
                                f"下载",
                                f'{folder}/{file}',
                                scale=0,
                                min_width=70)
                            deleteFile = gr.Button("删除", scale=0, min_width=70)

                            deleteFile.click(
                                lambda file=file:
                                (os.remove(f"{folder}/{file}"), update()),
                                None,
                                None)

                        def appendToMsg(msg, file=file):
                            msg['text'] = msg['text'] + f"{file}" + "}"
                            return msg

                        fileBtn.click(appendToMsg, msg, msg)

                with gr.Tab("论文/学术专著"):
                    with gr.Row():
                        uploadThesis = gr.UploadButton("上传论文/学术专著", scale=1)
                        uploadThesis.upload(upload_paper, uploadThesis)
                        refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_paper():
                        base_show_regular_files("paper")

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
                        base_show_regular_files("knowledgeBase")

                with gr.Tab("代码"):

                    def upload_code(file):
                        simpfile = os.path.splitext(os.path.basename(file))[0]
                        upload_folder = "code"
                        shutil.copy(file, upload_folder)
                        gr.Info("上传成功，请刷新")

                    with gr.Row():
                        uploadCode = gr.UploadButton("上传代码", scale=1)
                        uploadCode.upload(upload_code, uploadCode)
                        refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_code():
                        base_show_regular_files("code")

                with gr.Tab("Github仓库"):
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
                            with gr.Row():
                                folderBtn = gr.Button("解析" + folder,
                                                      scale=0,
                                                      min_width=120)

                                deleteFolder = gr.Button("删除",
                                                         scale=0,
                                                         min_width=70)
                                deleteFolder.click(
                                    lambda folder=folder: shutil.rmtree(
                                        f"repositry/{folder}"),
                                    None,
                                    None)

                                def output_analysis(chathistory,
                                                    folder=folder):
                                    analysis_generator = analyze_folder(
                                        f'repositry/{folder}')
                                    analysis = next(analysis_generator)
                                    chathistory.append(
                                        doubleMessage(f"解析{folder}",
                                                      f"{analysis}"))
                                    yield chathistory
                                    for chunk in analysis_generator:
                                        chathistory.pop()
                                        chathistory.append(
                                            doubleMessage(
                                                f"解析{folder}", f"{chunk}"))
                                        yield chathistory

                                folderBtn.click(output_analysis, chatbot,
                                                chatbot)

    with gr.Tab("markdown导出"):
        convert_Button = gr.Button("转换")
        with gr.Row():
            with gr.Column(scale=4):
                file_to_convert = gr.Textbox(
                    placeholder="输入需要转换的文件名或点击下方的按钮填入")

                def base_show_files(folder):
                    for file in os.listdir(folder):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=1, min_width=120)
                            downloadBtn = gr.DownloadButton("下载",
                                                            f'{folder}/{file}',
                                                            scale=0,
                                                            min_width=70)
                            deleteBtn = gr.Button("删除", scale=0, min_width=70)

                        def appendToCandidate(file=file):
                            if file.endswith(".md"):
                                return f"{folder}/{file}"
                            gr.Info("格式必须为.md")
                            return ''

                        fileBtn.click(appendToCandidate, None, file_to_convert)
                        deleteBtn.click(
                            lambda file=file: os.remove(f"{folder}/{file}"),
                            None,
                            None)

                with gr.Tab("已解析文件"):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_knowledgeBase():
                        base_show_files("knowledgeBase")

                with gr.Tab("论文/PPT生成产物"):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_Tempest():
                        base_show_files("tempest")

            convert_to_format = gr.Dropdown(["html", "tex", "pdf", "docx"],
                                            label="选择格式")

            def convert_file(file_to_convert, convert_to_format):
                if file_to_convert.strip() == "":
                    return ""
                else:
                    convert_to(file_to_convert, convert_to_format)
                    gr.Info("转换完成，请刷新")
                return ""

            convert_Button.click(convert_file,
                                 [file_to_convert, convert_to_format],
                                 file_to_convert)

    with gr.Tab("文科"):
        with gr.Tab("全自动生成论文"):
            with gr.Row():
                with gr.Column(scale=3, min_width=150):
                    title = gr.Textbox(
                        placeholder="输入主题，例如：中华民族共同体意识, Fluid Field")
                    generate_button = gr.Button("生成论文")
                    thesisBox = gr.Markdown("生成的论文将显示在此，markdown源文件可在右侧下载")
                with gr.Column(scale=1, min_width=150):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_Tempest():
                        for file in os.listdir(r"tempest"):
                            with gr.Row():
                                fileBtn = gr.Button(file,
                                                    scale=0,
                                                    min_width=120)
                                downloadFile = gr.DownloadButton(
                                    f"下载",
                                    f'tempest/{file}',
                                    scale=0,
                                    min_width=70)
                                deleteFile = gr.Button("删除",
                                                       scale=0,
                                                       min_width=70)

                                deleteFile.click(lambda file=file: os.remove(
                                    f"tempest/{file}"),
                                                 None,
                                                 None)

            def generateAndSave(title):
                if title.strip() == "":
                    return "请输入主题"
                else:
                    gr.Info(f"正在生成，大概需要240s，请不要关闭界面。稍后可获取md文件")
                    thesisGenerator = generate(title)
                    for tempThesis in thesisGenerator:
                        thesis = tempThesis
                        yield thesis
                    with open(f'tempest/{title}.md', 'w') as f:
                        f.write(thesis)
                    gr.Info(f"已完成，请刷新")
                    yield thesis

            generate_button.click(generateAndSave, [title], thesisBox)
        with gr.Tab("全自动生成PPT"):
            with gr.Row():
                with gr.Column(scale=3, min_width=150):
                    title = gr.Textbox(
                        placeholder=
                        "需要转换为PPT的markdown文案，点击文件对应按钮即可填入。搭配全自动生成论文使用效果更佳")
                    generate_button = gr.Button("生成PPT")
                    pptBox = gr.Markdown(
                        """生成的PPT文案将显示在此，markdown源文件和ppt可在右侧下载。后缀分别为ppt.md和.pdf。

推荐与全自动论文生成搭配使用。

注意：如果您想要自己撰写文案，请确保上传的文件后缀为.md，以下为部分重要语法：
```markdown
# 一级标题(即PPT第一页的主标题，必须存在，否则报错)
## 二级标题(即单开一页居中的子标题，若有参考文献部分也应当为二级标题)
像这样添加内容。每个段落都会被VA整理为无序列表，所以请确保每个段落都有较为充实的内容。

参考文献部分的标题必须写作“参考文献”或"References"，否则会出现格式、内容问题。

### 三级标题(即位于每一页左上方的子标题)
其余等级的标题即对应内容将会以文本框形式嵌入PPT页面中。
```
""")

                    def generate_ppt(title):
                        if title.endswith(".md"):
                            title = title[:-3]
                        if title.endswith("ppt"):
                            title = title[:-3]
                        if title.strip() == "":
                            return "请输入主题"
                        do_parse = not os.path.exists(f"tempest/{title}ppt.md")
                        for chunk in convert_to_pptx(f'tempest/{title}',
                                                     do_parse):
                            yield chunk
                        gr.Info('已完成，请刷新')

                    generate_button.click(generate_ppt, [title], pptBox)

                with gr.Column(scale=1, min_width=150):

                    def upload_paper(file):
                        simpfile = os.path.splitext(os.path.basename(file))[0]
                        if os.path.exists(
                                f"tempest/{simpfile}.md") or os.path.exists(
                                    f"tempest/{simpfile}.txt"):
                            return
                        upload_folder = "tempest"
                        shutil.copy(file, upload_folder)
                        gr.Info("上传成功，请刷新")

                    uploadDraft = gr.UploadButton("上传markdown文案", scale=0)
                    uploadDraft.upload(upload_paper, uploadDraft)
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[refresh.click])
                    def show_Tempest():
                        for file in os.listdir(r"tempest"):
                            with gr.Row():
                                fileBtn = gr.Button(file,
                                                    scale=0,
                                                    min_width=120)
                                downloadFile = gr.DownloadButton(
                                    f"下载",
                                    f'tempest/{file}',
                                    scale=0,
                                    min_width=70)
                                deleteFile = gr.Button("删除",
                                                       scale=0,
                                                       min_width=70)

                                def add_to_title(file=file):
                                    if file.endswith("ppt.md"):
                                        return file[:-6]
                                    elif file.endswith(".md"):
                                        return file[:-3]
                                    gr.Info("格式不正确")
                                    return ''

                                fileBtn.click(add_to_title, None, title)
                                deleteFile.click(lambda file=file: os.remove(
                                    f"tempest/{file}"),
                                                 None,
                                                 None)

    with gr.Tab("理科"):
        with gr.Tab("理科解题"):

            def normal_reply(chat_history):
                tempAnswer = deepseek(chat_history)
                finalAnswer = ""
                for chunk in tempAnswer:
                    finalAnswer = chunk
                    yield finalAnswer
                finalAnswer = remove_newlines_from_formulas(
                    formatFormula(finalAnswer))
                yield finalAnswer

            def respond(message, chat_history):
                message = message.strip()
                if message == "":
                    return "", chat_history
                if chat_history == []:
                    message = attachHints(message)
                chat_history.append({"role": 'user', "content": message})
                answer = normal_reply(chat_history)
                tempResponse = next(answer)
                chat_history.append({
                    "role": 'assistant',
                    "content": tempResponse
                })
                yield "", chat_history
                for chunk in answer:
                    chat_history[-1] = {"role": 'assistant', "content": chunk}
                    yield "", chat_history

            def ocr(file):
                encoded_image = encode_image(file)
                ocr_message = [
                    insertMultimodalHistory('请准确返回题目的文字与公式，不要返回其它内容',
                                            encoded_image)
                ]
                response = client1.chat.completions.create(
                    model='pixtral-large-latest', messages=ocr_message)
                return remove_newlines_from_formulas(
                    formatFormula(response.choices[0].message.content))

            chatbot = gr.Chatbot(type="messages",
                                 latex_delimiters=LATEX_DELIMITERS,
                                 show_copy_button=True,
                                 show_copy_all_button=True)
            solve_msg = gr.Textbox(placeholder="输入题目，难度不宜低于小学奥数，不宜高于IMO第1, 4题",
                                   interactive=True)
            with gr.Row():
                clear = gr.ClearButton([solve_msg, chatbot])
                ocr_button = gr.UploadButton("识别题目(可手动纠错)")
            ocr_button.upload(ocr, ocr_button, solve_msg)
            solve_msg.submit(respond, [solve_msg, chatbot],
                             [solve_msg, chatbot])
        with gr.Tab("理科解题(需要上传图片)"):
            qvqchatbot = MultimodalChatbot(latex_delimiters=LATEX_DELIMITERS,
                                           show_copy_button=True)
            solve_box = gr.MultimodalTextbox(
                placeholder="请上传一个图片(严格=1)，可以输入文字。如果模型回答意外终止，请回复“继续”")
            clearBtn = gr.ClearButton([solve_box, qvqchatbot])

            def solve_multimodal(message, chat_history):
                if type(message) != str:
                    message, files = message["text"], message["files"]
                message = formatFormula(message)
                message = remove_newlines_from_formulas(message)
                message = constructMultimodalMessage(
                    message, userFileConstructor(files))
                bot = QvQchatBot(chat_history)
                bot_stream = bot.answer(message)
                chat_history.append(
                    [message, constructMultimodalMessage("", [])])
                for bot_chunk in bot_stream:
                    bot_message = constructMultimodalMessage(bot_chunk, [])
                    chat_history[-1] = [message, bot_message]
                    yield gr.MultimodalTextbox(value=None), chat_history

            solve_box.submit(solve_multimodal, [solve_box, qvqchatbot],
                             [solve_box, qvqchatbot])

demo.launch(auth=("laowei", "1145141919810"), server_port=7860)
