from api_keys import (
    laowei_mistral_client_API_KEY,
    silicon_client_API_KEY,
    silicon_client_BASE_URL,
    volcano_client_API_KEY,
    volcano_client_BASE_URL,
    xkx_client_API_KEY,
    xkx_client_BASE_URL,
    zhipu_client_API_KEY,
    zhipu_client_BASE_URL,
)
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# 文生文
deepseek_v3 = ChatOpenAI(
    model="deepseek-v3-250324",
    api_key=volcano_client_API_KEY,
    base_url=volcano_client_BASE_URL,
)

# 多模态
mistral_small_latest = ChatMistralAI(
    model="mistral-small-latest", api_key=laowei_mistral_client_API_KEY
)

pixtral_large_latest = ChatOpenAI(
    model="pixtral-large-latest",
    api_key=xkx_client_API_KEY,
    base_url=xkx_client_BASE_URL,
)

glm_4v_flash = ChatOpenAI(
    model="glm-4v-flash",
    api_key=zhipu_client_API_KEY,
    base_url=zhipu_client_BASE_URL,
)

# 推理
# ChatDeepSeek中base_url疑似没有作用，必须使用api_base
deepseek_r1_671b = ChatOpenAI(
    model="deepseek-r1-minda",
    api_key=xkx_client_API_KEY,
    base_url=xkx_client_BASE_URL,
    temperature=0.6,
    max_tokens=16384,
)

qwq_32b = ChatOpenAI(
    model="qwen-qwq-32b",
    api_key=xkx_client_API_KEY,
    base_url=xkx_client_BASE_URL,
    top_p=0.95,
    temperature=0.6,
    presence_penalty=1.3,
)

# 代码
codestral_latest = ChatOpenAI(
    model="codestral-latest",
    api_key=xkx_client_API_KEY,
    base_url=xkx_client_BASE_URL,
)

# 嵌入
bce_embedding_base = OpenAIEmbeddings(
    model="netease-youdao/bce-embedding-base_v1",
    api_key=silicon_client_API_KEY,
    base_url=silicon_client_BASE_URL,
    embedding_ctx_length=511,
    chunk_size=32,
    check_embedding_ctx_length=False,
)
