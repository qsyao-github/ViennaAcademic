from omniparse import parseDocument


def readPaper(file_Path):
    return parseDocument(file_Path) + '\n' + '''阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？'''


def translatePapertoChinese(file_Path):
    return '将论文译为中文' + '\n' + parseDocument(file_Path)


def translatePapertoEnglish(file_Path):
    return '将论文译为英文，进行nature级别润色' + '\n' + parseDocument(file_Path)


def polishPaper(file_Path):
    return '对论文进行nature级别润色' + '\n' + parseDocument(file_Path)
