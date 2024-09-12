import ollama
import perplexica
from ipython import execute_code
class chatbot:
  def __init__(self):
    self.chatHistory=[{'role': 'system', 'content': """如有必要，请用以下命令请求搜索引擎或执行python代码：\\websearch{your_query}，\\python{your_code}。python可使用numpy, scipy, sympy"""}]
  def answer(self, query=None):
    if query is not None:
      self.chatHistory.append({'role': 'user', 'content': query})
    message=""
    stream = ollama.chat(model='glm4',messages=self.chatHistory,stream=True)
    for chunk in stream:
      print(chunk['message']['content'], end='', flush=True)
      message+=chunk['message']['content']
    self.chatHistory.append({'role':'assistant', 'content': message})
    return message
  def toolcall(self, message):
    tooluse=False
    while "\\websearch{" in message:
      queryStart=message.find("\\websearch{")+11
      queryEnd=message.find("}",queryStart)
      query=message[queryStart:queryEnd]
      searchResult = perplexica.search(query)
      self.chatHistory.append({'role': 'search engine', 'content': searchResult})
      tooluse=True
    while "\\python{" in message:
      codeStart=message.find("\\python{")+8
      codeEnd=message.find("}",codeStart)
      code=message[codeStart:codeEnd]
      execResult = execute_code(code)
      self.chatHistory.append({'role': 'python', 'content': execResult})
      print('Debugger Code', code)
      print('Debugger Result', execResult)
      message=message[codeEnd+1:]
      tooluse=True
    if tooluse:
      self.answer()
  def chat(self, query):
    self.toolcall(self.answer(query))
glmchatbot=chatbot()
glmchatbot.chat("计算半径为31的圆的面积")