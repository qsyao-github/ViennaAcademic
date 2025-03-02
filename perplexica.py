from typing import Dict, Union, List, Tuple, TypedDict
import requests
from modelclient import xkx_client_API_KEY, xkx_client_BASE_URL

# 常量定义
SEARCH_API_URL = "http://127.0.0.1:3001/api/search"
PROXIES = {"http": "http://localhost:7890", "https": "http://localhost:7890"}

CHAT_MODEL_CONFIG = {
    "provider": "custom_openai",
    "model": "mistral-large-latest",
    "customOpenAIBaseURL": xkx_client_BASE_URL,
    "customOpenAIKey": xkx_client_API_KEY
}

EMBEDDING_MODEL_CONFIG = {
    "provider": "ollama",
    "model": "snowflake-arctic-embed2:latest"
}


class SearchResult(TypedDict):
    message: str
    sources: List[Dict[str, Union[str, Dict[str, str]]]]


class QueryParams(TypedDict):
    chatModel: Dict[str, str]
    embeddingModel: Dict[str, str]
    optimizationMode: str
    focusMode: str
    query: str


def build_query_params(query: str, focus_mode: str) -> QueryParams:
    """构建统一的搜索查询参数"""
    return QueryParams(chatModel=CHAT_MODEL_CONFIG,
                       embeddingModel=EMBEDDING_MODEL_CONFIG,
                       optimizationMode="balanced",
                       focusMode=focus_mode,
                       query=query)


def fetch_search_results(query_params: QueryParams) -> SearchResult:
    """发送搜索请求并获取结果"""
    response = requests.post(SEARCH_API_URL,
                             json=query_params,
                             proxies=PROXIES)
    response.raise_for_status()
    return response.json()


def format_references(
        sources: List[Dict[str, Union[str, Dict[str, str]]]]) -> str:
    """格式化参考文献为Markdown格式"""
    return "\n\n".join(
        f"[{i+1}] [{source['metadata']['title']}]({source['metadata']['url']})"
        for i, source in enumerate(sources))


def execute_search(query: str, focus_mode: str) -> str:
    """执行搜索的核心逻辑"""
    try:
        query_params = build_query_params(query, focus_mode)
        result = fetch_search_results(query_params)
        references = format_references(result["sources"])
        return f"{result['message']}\n\n参考文献\n\n{references}"
    except requests.exceptions.RequestException as e:
        return f"网络请求异常: {str(e)}"
    except (KeyError, ValueError) as e:
        return f"数据处理错误: {str(e)}"


def academic_search(
        query: str) -> Tuple[str, List[Dict[str, Union[str, Dict[str, str]]]]]:
    """学术深度搜索（返回原始数据结构）"""
    try:
        query_params = build_query_params(query, "academicSearch")
        result = fetch_search_results(query_params)
        return result["message"], result["sources"]
    except requests.exceptions.RequestException as e:
        return f"请求失败: {str(e)}", []
    except KeyError:
        return "响应数据格式异常", []
