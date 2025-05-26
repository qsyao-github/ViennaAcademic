"""
储存目前使用的模型
"""

from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from private.api_keys import (
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

# 文生文
deepseek_v3 = ChatOpenAI(
    model="deepseek-v3-250324",
    api_key=volcano_client_API_KEY,
    base_url=volcano_client_BASE_URL,
    logprobs=False,
)

# 多模态
mistral_small_latest = ChatMistralAI(
    model="mistral-small-latest",
    api_key=laowei_mistral_client_API_KEY,
)

glm_4v_flash = ChatOpenAI(
    model="glm-4v-flash",
    api_key=zhipu_client_API_KEY,
    base_url=zhipu_client_BASE_URL,
    logprobs=False,
)

# 推理
deepseek_r1_671b = ChatOpenAI(
    model="deepseek-r1-minda",
    api_key=xkx_client_API_KEY,
    base_url=xkx_client_BASE_URL,
    temperature=0.6,
    max_tokens=16384,
    logprobs=False,
)

glm_z1_flash = ChatOpenAI(
    model="glm-z1-flash",
    api_key=zhipu_client_API_KEY,
    base_url=zhipu_client_BASE_URL,
    temperature=0.6,
    top_p=0.95,
    max_completion_tokens=30000,
    logprobs=False,
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


def model_type(enable_tool: bool, enable_thinking: bool, multimodal: bool):
    """根据模型属性返回位掩码

    用位掩码表征模型是否支持工具调用、推理、多模态

    Parameters
    ----------
    enable_tool: bool
        是否支持工具调用
    enable_thinking: bool
        是否进行推理
    multimodal: bool
        是否支持多模态

    Returns
    ----------
    int
        位掩码
    """
    return (enable_tool << 2) | (enable_thinking << 1) | multimodal
