import os

from langchain.chat_models import init_chat_model

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL")

DEEPSEEK_V3_2_NO_REASONING = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Pro/deepseek-ai/DeepSeek-V3.2",
    temperature=1.0,
    top_p=0.95,
    extra_body={"enable_thinking": False},
)
DEEPSEEK_V3_2_REASONING = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Pro/deepseek-ai/DeepSeek-V3.2",
    temperature=1.0,
    top_p=0.95,
    extra_body={"enable_thinking": True},
)

QWEN3_VL_235B_A22B_INSTRUCT = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Qwen/Qwen3-VL-235B-A22B-Instruct",
)

QWEN3_VL_235B_A22B_THINKING = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Qwen/Qwen3-VL-235B-A22B-Thinking",
)

DEEPSEEK_OCR = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="deepseek-ai/DeepSeek-OCR",
    temperature=0.0,
)

"""
QWEN3_NEXT_80B_A3B_INSTRUCT = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Qwen/Qwen3-Next-80B-A3B-Instruct",
    temperature=0.7,
    top_p=0.8,
    extra_body={"top_k": 20, "min_p": 0},
)

QWEN3_NEXT_80B_A3B_THINKING = init_chat_model(
    model_provider="deepseek",
    api_base=SILICONFLOW_BASE_URL,
    api_key=SILICONFLOW_API_KEY,
    model="Qwen/Qwen3-Next-80B-A3B-Thinking",
    temperature=0.7,
    top_p=0.8,
    extra_body={"top_k": 20, "min_p": 0},
)"""
