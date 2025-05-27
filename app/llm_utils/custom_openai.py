import asyncio
from collections.abc import AsyncIterator, Mapping
from typing import (
    Any,
    Dict,
    Optional,
    cast,
)

import aiohttp
import httpx
import orjson
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    ChatMessageChunk,
    FunctionMessageChunk,
    HumanMessageChunk,
    SystemMessageChunk,
    ToolMessageChunk,
)
from langchain_core.messages.ai import (
    UsageMetadata,
)
from langchain_core.messages.tool import tool_call_chunk
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai.chat_models.base import (
    BaseChatOpenAI,
    _create_usage_metadata,
    agenerate_from_stream,
    generate_from_stream,
)
from pydantic import Field


# 参考langchain_openai.chat_models.base._convert_delta_to_message_chunk，增加处理reasoning_content的逻辑
def _convert_delta_to_message_chunk(
    _dict: Mapping[str, Any], default_class: type[BaseMessageChunk]
) -> BaseMessageChunk:
    id_ = _dict.get("id")
    role = cast(str, _dict.get("role"))
    content = cast(str, _dict.get("content") or "")
    additional_kwargs: dict = {}
    if _dict.get("function_call"):
        function_call = dict(_dict["function_call"])
        if "name" in function_call and function_call["name"] is None:
            function_call["name"] = ""
        additional_kwargs["function_call"] = function_call
    tool_call_chunks = []
    if raw_tool_calls := _dict.get("tool_calls"):
        additional_kwargs["tool_calls"] = raw_tool_calls
        try:
            tool_call_chunks = [
                tool_call_chunk(
                    name=rtc["function"].get("name"),
                    args=rtc["function"].get("arguments"),
                    id=rtc.get("id"),
                    index=rtc["index"],
                )
                for rtc in raw_tool_calls
            ]
        except KeyError:
            pass
    # 新增reasoning_content字段处理，放于additional_kwargs中
    if reasoning_content := _dict.get("reasoning_content"):
        additional_kwargs["reasoning_content"] = reasoning_content

    if role == "user" or default_class == HumanMessageChunk:
        return HumanMessageChunk(content=content, id=id_)
    elif role == "assistant" or default_class == AIMessageChunk:
        return AIMessageChunk(
            content=content,
            additional_kwargs=additional_kwargs,
            id=id_,
            tool_call_chunks=tool_call_chunks,  # type: ignore[arg-type]
        )
    elif role in ("system", "developer") or default_class == SystemMessageChunk:
        if role == "developer":
            additional_kwargs = {"__openai_role__": "developer"}
        else:
            additional_kwargs = {}
        return SystemMessageChunk(
            content=content, id=id_, additional_kwargs=additional_kwargs
        )
    elif role == "function" or default_class == FunctionMessageChunk:
        return FunctionMessageChunk(content=content, name=_dict["name"], id=id_)
    elif role == "tool" or default_class == ToolMessageChunk:
        return ToolMessageChunk(
            content=content, tool_call_id=_dict["tool_call_id"], id=id_
        )
    elif role or default_class == ChatMessageChunk:
        return ChatMessageChunk(content=content, role=role, id=id_)
    else:
        return default_class(content=content, id=id_)  # type: ignore


class CustomOpenAI(BaseChatOpenAI):
    """
    基本兼容langchain接口，支持自定义字段&更好推理处理的自定义OpenAI类

    继承自BaseChatOpenAI，同步非流式用httpx，异步(非)流式用aiohttp，连接全局复用。支持enable_thinking, min_p, top_k等OpenAI官方sdk不支持的参数。支持处理部分推理模型返回的reasoning_content字段

    需手动调用init初始化和close关闭Client
    """

    api_key: str
    base_url: str
    # 同步连接
    httpx_session: httpx.Client = Field(default=None, exclude=True)
    # 异步连接
    aiohttp_session: aiohttp.ClientSession = Field(default=None, exclude=True)
    aiohttp_session_lock: asyncio.Lock = Field(default=asyncio.Lock(), exclude=True)
    # 请求头，包含api_key
    headers: Dict[str, str] = Field(default=None, exclude=True)

    async def init(self):
        """
        初始化同步/异步Session
        """
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with self.aiohttp_session_lock:
            if self.aiohttp_session is None or self.aiohttp_session.closed:
                connector = aiohttp.TCPConnector(
                    limit_per_host=100,
                    ssl=False,
                )
                self.aiohttp_session = aiohttp.ClientSession(
                    base_url=f"{self.base_url}/",
                    connector=connector,
                    headers=self.headers,
                    json_serialize=lambda x: orjson.dumps(x).decode("utf-8"),
                )
        if not self.httpx_session or self.httpx_session.is_closed:
            self.httpx_session = httpx.Client(
                base_url=self.base_url, headers=self.headers
            )

    async def close(self):
        """
        关闭同步/异步Session
        """
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()
        if self.httpx_session and not self.httpx_session.is_closed:
            self.httpx_session.close()

    # 参考super()._convert_chunk_to_generation_chunk，但重写_convert_delta_to_message_chunk处理reasoning_content
    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: Optional[dict],
    ) -> Optional[ChatGenerationChunk]:
        if chunk.get("type") == "content.delta":  # from beta.chat.completions.stream
            return None
        token_usage = chunk.get("usage")
        choices = (
            chunk.get("choices", [])
            # from beta.chat.completions.stream
            or chunk.get("chunk", {}).get("choices", [])
        )

        usage_metadata: Optional[UsageMetadata] = (
            _create_usage_metadata(token_usage) if token_usage else None
        )
        if len(choices) == 0:
            # logprobs is implicitly None
            generation_chunk = ChatGenerationChunk(
                message=default_chunk_class(content="", usage_metadata=usage_metadata)
            )
            return generation_chunk

        choice = choices[0]
        if choice["delta"] is None:
            return None

        message_chunk = _convert_delta_to_message_chunk(
            choice["delta"], default_chunk_class
        )
        generation_info = {**base_generation_info} if base_generation_info else {}

        if finish_reason := choice.get("finish_reason"):
            generation_info["finish_reason"] = finish_reason
            if model_name := chunk.get("model"):
                generation_info["model_name"] = model_name
            if system_fingerprint := chunk.get("system_fingerprint"):
                generation_info["system_fingerprint"] = system_fingerprint
            if service_tier := chunk.get("service_tier"):
                generation_info["service_tier"] = service_tier

        logprobs = choice.get("logprobs")
        if logprobs:
            generation_info["logprobs"] = logprobs

        if usage_metadata and isinstance(message_chunk, AIMessageChunk):
            message_chunk.usage_metadata = usage_metadata

        generation_chunk = ChatGenerationChunk(
            message=message_chunk, generation_info=generation_info or None
        )
        return generation_chunk

    # 以下函数参考ChatOpenAI类的实现，删去了暂时不需要的逻辑，改用httpx, aiohttp session
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.streaming:
            stream_iter = self._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return generate_from_stream(stream_iter)
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        response = self.httpx_session.post(
            "chat/completions", data=orjson.dumps(payload)
        )
        response.raise_for_status()
        return self._create_chat_result(response.json(), None)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.streaming:
            stream_iter = self._astream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return await agenerate_from_stream(stream_iter)
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        async with self.aiohttp_session.post(
            "chat/completions",
            data=orjson.dumps(payload),
        ) as response:
            response.raise_for_status()
            return self._create_chat_result(await response.json(), None)

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        *,
        stream_usage: Optional[bool] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        kwargs["stream"] = True
        stream_usage = self._should_stream_usage(stream_usage, **kwargs)
        if stream_usage:
            kwargs["stream_options"] = {"include_usage": stream_usage}
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        default_chunk_class: type[BaseMessageChunk] = AIMessageChunk
        base_generation_info = {}
        async with self.aiohttp_session.post(
            "chat/completions",
            data=orjson.dumps(payload),
        ) as response:
            response.raise_for_status()
            # return self._create_chat_result(await response.json(), None)
            is_first_chunk = True
            async for chunk in response.content:
                chunk = chunk[6:-1]
                if chunk == b"[DONE]":
                    return
                if not chunk:
                    continue
                chunk = orjson.loads(chunk)
                generation_chunk = self._convert_chunk_to_generation_chunk(
                    chunk,
                    default_chunk_class,
                    base_generation_info if is_first_chunk else {},
                )
                if generation_chunk is None:
                    continue
                default_chunk_class = generation_chunk.message.__class__
                logprobs = (generation_chunk.generation_info or {}).get("logprobs")
                if run_manager:
                    await run_manager.on_llm_new_token(
                        generation_chunk.text,
                        chunk=generation_chunk,
                        logprobs=logprobs,
                    )
                is_first_chunk = False
                yield generation_chunk
        if hasattr(response, "get_final_completion") and "response_format" in payload:
            final_completion = await response.get_final_completion()
            generation_chunk = self._get_generation_chunk_from_completion(
                final_completion
            )
            if run_manager:
                await run_manager.on_llm_new_token(
                    generation_chunk.text, chunk=generation_chunk
                )
            yield generation_chunk
