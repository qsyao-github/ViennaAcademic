import gradio as gr
from gradio_multimodalchatbot import MultimodalChatbot
from gradio.data_classes import FileData
from chat import chatBot, toolcall, promptcall, remove_newlines_from_formulas, formatFormula, insertMultimodalHistory, QvQchatBot
import os
import shutil
from codeAnalysis import analyze_folder
import datetime
import time
import subprocess
from io import StringIO
from generate import generate
from downloadpaper import downloadArxivPaper
from doclingParse import parseEverything
from deepseek import deepseek, attachHints
from bceInference import update, get_response
from fileConversion import convert_to_pptx, convert_to
from imageUtils import encode_image
from modelclient import client1, client2
from paper import readPaper, translatePapertoChinese, translatePapertoEnglish, polishPaper

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

    return lambda msg: {**msg, 'text': msg['text'] + newStr}


def constructMultimodalMessage(msg, filesConstructor):
    return {"text": msg, "files": filesConstructor}


def userFileConstructor(files):
    return [{"file": FileData(path=file)} for file in files]


def botFileConstructor(nowTime):
    # 获取当前目录下的所有文件和目录
    with os.scandir() as entries:
        files = [{
            "file": FileData(path=entry.name)
        } for entry in entries if entry.is_file() and entry.name.endswith((
            ".png", ".mp4")) and nowTime in entry.name]
    return files


def doubleMessage(msg1, msg2):
    return [{"text": msg1, "files": []}, {"text": msg2, "files": []}]


with gr.Blocks(fill_height=True, fill_width=True,
               delete_cache=(3600, 3600)) as demo:
    code_file_list = gr.State(os.listdir("code"))
    knowledgeBase_file_list = gr.State(os.listdir("knowledgeBase"))
    paper_file_list = gr.State(os.listdir("paper"))
    repositry_folder_list = gr.State(os.listdir("repositry"))
    tempest_file_list = gr.State(os.listdir("tempest"))

    def clean_old_files():
        # 获取当前时间
        now = time.time()
        # 计算3天前的时间戳
        three_days_ago = now - 259200

        # 遍历文件夹中的文件
        for folder_path in [
                'code', 'knowledgeBase', 'paper', 'repositry', 'tempest'
        ]:
            with os.scandir(folder_path) as entries:
                files_to_remove = [
                    entry.path for entry in entries if entry.is_file()
                    and entry.stat().st_mtime < three_days_ago
                ]
                for file_path in files_to_remove:
                    os.remove(file_path)

    with gr.Tab("聊天"):
        with gr.Row():
            with gr.Column(scale=0, min_width=150):
                websearchBtn = gr.Button("网页搜索", scale=0)
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
                    file_suffixes_to_remove = (".png", ".mp4", ".txt")
                    files_to_remove = [
                        file for file in os.listdir()
                        if file.endswith(file_suffixes_to_remove)
                    ]
                    for file in files_to_remove:
                        os.remove(file)
                    if os.path.exists('media'):
                        shutil.rmtree('media')
                    clean_old_files()
                    update()
                    return os.listdir('code'), os.listdir(
                        'knowledgeBase'), os.listdir('paper'), os.listdir(
                            'repositry'), os.listdir('tempest')

                clear.click(checkDelete,
                            None, [
                                code_file_list, knowledgeBase_file_list,
                                paper_file_list, repositry_folder_list,
                                tempest_file_list
                            ],
                            concurrency_limit=12)
                websearchBtn.click(addToMsg("#websearch{"),
                                   msg,
                                   msg,
                                   concurrency_limit=12)
                attachBtn.click(addToMsg("#attach{"),
                                msg,
                                msg,
                                concurrency_limit=12)
                findPaper.click(addToMsg("#findPaper{"),
                                msg,
                                msg,
                                concurrency_limit=12)
                generateDocstring.click(addToMsg("#generateDocstring{"),
                                        msg,
                                        msg,
                                        concurrency_limit=12)
                optimizeCode.click(addToMsg("#optimizeCode{"),
                                   msg,
                                   msg,
                                   concurrency_limit=12)

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
                                       [knowledgeBaseSwitch],
                                       concurrency_limit=12)
                knowledgeBaseSwitch.input(
                    switch_knowledgeBase,
                    [knowledgeBaseSwitch, multimodalSwitch],
                    [multimodalSwitch],
                    concurrency_limit=12)

                def respond(message, chat_history, multimodal, knowledgeBase):
                    # integrating multimodal conversion here
                    if not isinstance(message, str):
                        message, files = message["text"], message["files"]
                    message = formatFormula(message)
                    message = remove_newlines_from_formulas(message)
                    message = promptcall(message)
                    if isinstance(message, str):
                        if knowledgeBase:
                            knowledgeBaseSearch = get_response(message)
                            if knowledgeBaseSearch:
                                message = knowledgeBaseSearch + '\n\n' + message
                        message = constructMultimodalMessage(
                            message, userFileConstructor(files))
                        nowTime = datetime.datetime.now().strftime(
                            '%y%m%d%H%M%S')
                        bot = chatBot(chat_history, multimodal)
                        bot_stream = bot.answer(message, nowTime, multimodal)
                        chat_history.append(
                            [message,
                             constructMultimodalMessage("", [])])
                        bot_message = StringIO()
                        for bot_chunk in bot_stream:
                            bot_message.write(bot_chunk)
                            chat_history[-1][-1][
                                'text'] = bot_message.getvalue()
                            yield gr.MultimodalTextbox(
                                value=None), chat_history
                        full_bot_message = bot_message.getvalue()
                        bot_message.close()
                        full_bot_message = remove_newlines_from_formulas(
                            formatFormula(toolcall(full_bot_message, nowTime)))
                        chat_history[-1][-1] = constructMultimodalMessage(
                            full_bot_message, botFileConstructor(nowTime))
                        yield gr.MultimodalTextbox(value=None), chat_history
                    elif isinstance(message, tuple):
                        chat_history.append(
                            doubleMessage(message[0], message[1]))
                        yield gr.MultimodalTextbox(value=None), chat_history
                    else:
                        chunk = next(message)
                        chat_history.append(doubleMessage(chunk[0], chunk[1]))
                        yield gr.MultimodalTextbox(value=None), chat_history
                        for chunk in message:
                            chat_history[-1][-1]["text"] = chunk[1]
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
                    knowledge_base_files = set(os.listdir('knowledgeBase'))
                    if simpfile + '.md' in knowledge_base_files or simpfile + '.txt' in knowledge_base_files:
                        return os.listdir('paper'), list(knowledge_base_files)
                    shutil.copy(file, "paper")
                    text = parseEverything(file)
                    with open(f"knowledgeBase/{simpfile}.md", "w", encoding='utf-8') as f:
                        f.write(text)
                    update()
                    return os.listdir('paper'), list(knowledge_base_files)

                def base_show_regular_files(folder, listener):
                    for file in os.listdir(folder):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0, min_width=120)
                            downloadFile = gr.DownloadButton(
                                f"下载",
                                f'{folder}/{file}',
                                scale=0,
                                min_width=70)
                            deleteFile = gr.Button("删除", scale=0, min_width=70)

                            def delete_file(file=file):
                                os.remove(f"{folder}/{file}")
                                update()
                                return os.listdir(folder)

                            deleteFile.click(delete_file,
                                             None,
                                             listener,
                                             concurrency_limit=12)

                        def appendToMsg(msg, file=file):
                            msg['text'] += f"{file}" + "}"
                            return msg

                        fileBtn.click(appendToMsg,
                                      msg,
                                      msg,
                                      concurrency_limit=12)

                with gr.Tab("论文"):
                    with gr.Row():
                        uploadThesis = gr.UploadButton("上传论文", scale=1)
                        uploadThesis.upload(
                            upload_paper, uploadThesis,
                            [paper_file_list, knowledgeBase_file_list])
                        refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load, paper_file_list.change
                    ])
                    def show_paper():
                        base_show_regular_files("paper", paper_file_list)

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
                        return "", chat_history, os.listdir('knowledgeBase')

                    downloadArxiv.click(
                        gradiodownloadArxivPaper, [arxivNum, chatbot],
                        [arxivNum, chatbot, knowledgeBase_file_list])

                    @gr.render(triggers=[
                        refresh.click, demo.load,
                        knowledgeBase_file_list.change
                    ])
                    def show_knowledgeBase():
                        base_show_regular_files("knowledgeBase",
                                                knowledgeBase_file_list)

                with gr.Tab("代码"):

                    def upload_code(file):
                        shutil.copy(file, "code")
                        return os.listdir('code')

                    with gr.Row():
                        uploadCode = gr.UploadButton("上传代码", scale=1)
                        uploadCode.upload(upload_code, uploadCode,
                                          code_file_list)
                        refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load, code_file_list.change
                    ])
                    def show_code():
                        base_show_regular_files("code", code_file_list)

                with gr.Tab("Github仓库"):
                    refresh = gr.Button("刷新", scale=0, min_width=100)
                    githubUrl = gr.Textbox()
                    githubClone = gr.Button("克隆仓库", scale=0)

                    # unoptimized from here
                    def clone_repo(url):
                        if url:
                            gr.Info("正在克隆，请耐心等候")
                            subprocess.run(
                                ["cd", "repositry", "&&", "git", "clone", url],
                                shell=True)
                        return "", os.listdir('repositry')

                    githubClone.click(clone_repo, githubUrl,
                                      [githubUrl, repositry_folder_list])

                    @gr.render(triggers=[
                        refresh.click, demo.load, repositry_folder_list.change
                    ])
                    def showFolder():
                        for folder in os.listdir(r'repositry'):
                            with gr.Row():
                                folderBtn = gr.Button("解析" + folder,
                                                      scale=0,
                                                      min_width=120)

                                deleteFolder = gr.Button("删除",
                                                         scale=0,
                                                         min_width=70)

                                def delete_folder(folder=folder):
                                    shutil.rmtree(f'repositry/{folder}')
                                    return os.listdir('repositry')

                                deleteFolder.click(delete_folder,
                                                   None,
                                                   repositry_folder_list,
                                                   concurrency_limit=12)

                                def output_analysis(chathistory,
                                                    folder=folder):
                                    analysis_generator = analyze_folder(
                                        f'repositry/{folder}')
                                    analysis = next(analysis_generator)
                                    chathistory.append(
                                        doubleMessage(f"解析{folder}", analysis))
                                    yield chathistory
                                    for chunk in analysis_generator:
                                        chathistory[-1][-1]["text"] = chunk
                                        yield chathistory

                                folderBtn.click(output_analysis, chatbot,
                                                chatbot)

    with gr.Tab("论文"):
        with gr.Row():
            with gr.Column(scale=8):
                with gr.Row():
                    selected_function = gr.Dropdown(
                        ['论文解读', '论文翻译->英', '论文翻译->中', '论文润色'],
                        scale=0,
                        min_width=192)
                    selected_paper = gr.Textbox(placeholder='点击右侧文件名输入',
                                                scale=1)
                paper_answer = gr.Markdown(show_copy_button=True)

                def generate_paper_answer(selected_function, selected_paper):
                    if selected_paper not in os.listdir('knowledgeBase'):
                        return '文件不存在', os.listdir('knowledgeBase')
                    gr.Info('正在生成答案，请耐心等候')
                    function_map = {
                        '论文润色': polishPaper,
                        '论文翻译->英': translatePapertoEnglish,
                        '论文翻译->中': translatePapertoChinese
                    }
                    process_function = function_map.get(
                        selected_function, readPaper)
                    answer = process_function(selected_paper)
                    for chunk in answer:
                        yield chunk, []
                    yield chunk, os.listdir('knowledgeBase')

                selected_paper.submit(generate_paper_answer,
                                      [selected_function, selected_paper],
                                      [paper_answer, knowledgeBase_file_list],
                                      concurrency_limit=3)

            with gr.Column(scale=1, min_width=350):
                paper_refresh = gr.Button('刷新')
                paper_arxivNum = gr.Textbox(
                    placeholder="输入arxiv号，例如：1706.03762")
                downloadArxiv = gr.Button("arxiv论文下载", scale=0)

                def gradiodownloadArxivPaper(paper_arxivNum):
                    gr.Info("正在下载，请耐心等候")
                    answer = downloadArxivPaper(paper_arxivNum)
                    update()
                    return "", answer, os.listdir('knowledgeBase')

                downloadArxiv.click(
                    gradiodownloadArxivPaper, [paper_arxivNum],
                    [paper_arxivNum, paper_answer, knowledgeBase_file_list])

                @gr.render(triggers=[
                    paper_refresh.click, demo.load,
                    knowledgeBase_file_list.change
                ])
                # unoptimized
                def base_show_paper():
                    time.sleep(0.125)
                    for file in os.listdir('knowledgeBase'):
                        with gr.Row():
                            fileBtn = gr.Button(file, scale=0, min_width=120)
                            downloadFile = gr.DownloadButton(
                                f"下载",
                                f'knowledgeBase/{file}',
                                scale=0,
                                min_width=70)
                            deleteFile = gr.Button("删除", scale=0, min_width=70)

                            def delete_paper(file=file):
                                os.remove(f"knowledgeBase/{file}")
                                update()
                                return os.listdir('knowledgeBase')

                            deleteFile.click(delete_paper,
                                             None,
                                             knowledgeBase_file_list,
                                             concurrency_limit=12)

                        def appendToMsg(file=file):
                            return file

                        fileBtn.click(appendToMsg,
                                      None,
                                      selected_paper,
                                      concurrency_limit=12)

    with gr.Tab("写作"):
        with gr.Tab("全自动生成论文"):
            with gr.Row():
                with gr.Column(scale=3, min_width=150):
                    title = gr.Textbox(
                        placeholder="输入主题，例如：中华民族共同体意识, Fluid Field")
                    generate_button = gr.Button("生成论文")
                    thesisBox = gr.Markdown("生成的论文将显示在此，markdown源文件可在右侧下载")
                with gr.Column(scale=1, min_width=150):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load, tempest_file_list.change
                    ])
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

                                def delete_tempest_file(file=file):
                                    os.remove(f"tempest/{file}")
                                    return os.listdir("tempest")

                                deleteFile.click(delete_tempest_file, None,
                                                 tempest_file_list)

            def generateAndSave(title):
                if title.strip() == "":
                    return "请输入主题", os.listdir('tempest')
                gr.Info(f"正在生成，大概需要240s，请不要关闭界面。稍后可获取md文件")
                thesisGenerator = generate(title)
                for tempThesis in thesisGenerator:
                    thesis = tempThesis
                    yield thesis, []
                with open(f'tempest/{title}.md', 'w',
                            encoding='utf-8') as f:
                    f.write(thesis)
                gr.Info('已完成，请刷新')
                yield thesis, os.listdir('tempest')

            generate_button.click(generateAndSave, [title],
                                  [thesisBox, tempest_file_list],
                                  concurrency_limit=1)
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
                            return "请输入主题", os.listdir('tempest')
                        do_parse = not os.path.exists(f"tempest/{title}ppt.md")
                        final_response = ""
                        for chunk in convert_to_pptx(f'tempest/{title}',
                                                     do_parse):
                            final_response = chunk
                            yield chunk, []
                        gr.Info('已完成，请刷新')
                        yield final_response, os.listdir('tempest')

                    generate_button.click(generate_ppt, [title],
                                          [pptBox, tempest_file_list])

                with gr.Column(scale=1, min_width=150):

                    def upload_paper(file):
                        simpfile = os.path.splitext(os.path.basename(file))[0]
                        existing_files = set(os.listdir('tempest'))
                        if f"{simpfile}.md" in existing_files or f"{simpfile}.txt" in existing_files:
                            return
                        shutil.copy(file, "tempest")
                        return os.listdir('tempest')

                    uploadDraft = gr.UploadButton("上传markdown文案", scale=0)
                    uploadDraft.upload(upload_paper, uploadDraft,
                                       tempest_file_list)
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load, tempest_file_list.change
                    ])
                    def show_Tempest():
                        time.sleep(0.125)
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

                                fileBtn.click(add_to_title,
                                              None,
                                              title,
                                              concurrency_limit=12)

                                def delete_tempest_file(file=file):
                                    os.remove(f"tempest/{file}")
                                    return os.listdir('tempest')

                                deleteFile.click(delete_tempest_file,
                                                 None,
                                                 tempest_file_list,
                                                 concurrency_limit=12)

    with gr.Tab("理科解题"):
        with gr.Tab("常规解题"):

            def respond(message, chat_history):
                message = message.strip()
                if message == "":
                    return "", chat_history
                if not chat_history:
                    message = attachHints(message)
                chat_history.append({"role": 'user', "content": message})
                answer = deepseek(chat_history)
                chat_history.append({"role": 'assistant', "content": ''})
                temp_answer = StringIO()
                for chunk in answer:
                    temp_answer.write(chunk)
                    chat_history[-1]['content'] = temp_answer.getvalue()
                    yield "", chat_history
                final_answer = temp_answer.getvalue()
                temp_answer.close()
                index = final_answer.rfind(r'</think>')
                if index != -1:
                    final_answer = final_answer[index + 8:]
                final_answer = remove_newlines_from_formulas(
                    formatFormula(final_answer))
                chat_history[-1]['content'] = final_answer
                yield "", chat_history

            def ocr(file):
                encoded_image = encode_image(file)
                ocr_message = [
                    insertMultimodalHistory('请准确返回题目的文字与公式，不要返回其它内容',
                                            encoded_image)
                ]
                response = client2.chat.completions.create(
                    model='glm-4v-flash', messages=ocr_message)
                return remove_newlines_from_formulas(
                    formatFormula(response.choices[0].message.content))

            solve_chatbot = gr.Chatbot(type="messages",
                                       latex_delimiters=LATEX_DELIMITERS,
                                       show_copy_button=True,
                                       show_copy_all_button=True)
            solve_msg = gr.Textbox(placeholder="输入题目，难度不宜低于小学奥数，不宜高于IMO第1, 4题",
                                   interactive=True)
            with gr.Row():
                clear = gr.ClearButton([solve_msg, solve_chatbot])
                ocr_button = gr.UploadButton("识别题目(可手动纠错)")
            ocr_button.upload(ocr, ocr_button, solve_msg)
            solve_msg.submit(respond, [solve_msg, solve_chatbot],
                             [solve_msg, solve_chatbot],
                             concurrency_limit=2)
        with gr.Tab("多模态解题(需要上传图片)"):
            qvqchatbot = MultimodalChatbot(latex_delimiters=LATEX_DELIMITERS,
                                           show_copy_button=True)
            solve_box = gr.MultimodalTextbox(
                placeholder=
                "请上传一个图片(严格=1)，可以输入文字，此功能仅适用于必须看懂配图的题目(电路、几何等)，其余题目请移步常规解题。如果模型回答意外终止，请回复“继续”"
            )
            clearBtn = gr.ClearButton([solve_box, qvqchatbot])

            def solve_multimodal(message, chat_history):
                if not isinstance(message, str):
                    message, files = message["text"], message["files"]
                message = formatFormula(message)
                message = remove_newlines_from_formulas(message)
                message = constructMultimodalMessage(
                    message, userFileConstructor(files))
                bot = QvQchatBot(chat_history)
                bot_stream = bot.answer(message)
                chat_history.append(
                    [message, constructMultimodalMessage("", [])])
                bot_message = StringIO()
                for bot_chunk in bot_stream:
                    bot_message.write(bot_chunk)
                    chat_history[-1][-1]['text'] = bot_message.getvalue()
                    yield gr.MultimodalTextbox(value=None), chat_history
                full_bot_message = bot_message.getvalue()
                bot_message.close()
                chat_history[-1][-1]['text'] = remove_newlines_from_formulas(
                    formatFormula(full_bot_message))
                yield gr.MultimodalTextbox(value=None), chat_history

            solve_box.submit(solve_multimodal, [solve_box, qvqchatbot],
                             [solve_box, qvqchatbot],
                             concurrency_limit=12)
    with gr.Tab("markdown导出"):
        convert_Button = gr.Button("转换")
        with gr.Row():
            with gr.Column(scale=4):
                file_to_convert = gr.Textbox(
                    placeholder="输入需要转换的文件名或点击下方的按钮填入")

                def base_show_files(folder, listener):
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

                        def delete_file(file=file):
                            os.remove(f"{folder}/{file}")
                            return os.listdir(folder)

                        deleteBtn.click(delete_file, None, listener)

                with gr.Tab("已解析文件"):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load,
                        knowledgeBase_file_list.change
                    ])
                    def show_knowledgeBase():
                        time.sleep(0.25)
                        base_show_files("knowledgeBase",
                                        knowledgeBase_file_list)

                with gr.Tab("论文/PPT生成产物"):
                    refresh = gr.Button("刷新", scale=0, min_width=120)

                    @gr.render(triggers=[
                        refresh.click, demo.load, tempest_file_list.change
                    ])
                    def show_Tempest():
                        time.sleep(0.25)
                        base_show_files("tempest", tempest_file_list)

            convert_to_format = gr.Dropdown(["html", "tex", "pdf", "docx"],
                                            label="选择格式")

            def convert_file(file_to_convert, convert_to_format):
                if file_to_convert:
                    convert_to(file_to_convert, convert_to_format)
                return "", os.listdir('knowledgeBase'), os.listdir('tempest')

            convert_Button.click(
                convert_file, [file_to_convert, convert_to_format],
                [file_to_convert, knowledgeBase_file_list, tempest_file_list],
                concurrency_limit=12)

demo.launch(auth=("laowei", "1145141919810"), server_port=7860)
