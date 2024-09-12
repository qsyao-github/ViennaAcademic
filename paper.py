from omniparse import parseDocument
from scihub.scihub import SciHub
import os
sh = SciHub()
def readPaper(file_Path):
    return '''阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？'''+'\n'+parseDocument(file_Path)
def translatePapertoChinese(file_Path):
    return '将论文译为中文'+'\n'+parseDocument(file_Path)
def translatePapertoEnglish(file_Path):
    return '将论文译为英文，进行nature级别润色'+'\n'+parseDocument(file_Path)
def polishPaper(file_Path):
    return '对论文进行nature级别润色'+'\n'+parseDocument(file_Path)
def downloadPaper(doiOrArxiv):
    if doiOrArxiv[0].upper() == 'D':
        result = sh.download('http://ieeexplore.ieee.org/xpl/login.jsp?tp=&arnumber=1648853', path=f'Paper/{doiOrArxiv}/{doiOrArxiv}.pdf')
        parsedText=parseDocument(f'Paper/{doiOrArxiv}/{doiOrArxiv}.pdf')
        newTitle=parsedText.split('\n')[0].lstrip('*').rstrip('*').lstrip('#').lstrip().rstrip()
        try:
            original_directory=os.getcwd()
            os.chdir(f'Paper/{doiOrArxiv}')
            os.rename(f'{doiOrArxiv}.pdf',newTitle+'.pdf')
        except:
            newTitle=f'{doiOrArxiv}.pdf'
        os.chdir(original_directory)
        return newTitle
