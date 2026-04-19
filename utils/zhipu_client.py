from __future__ import annotations

import os
import socket
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover - exercised in unit tests via monkeypatch
    httpx = None  # type: ignore[assignment]

try:
    import zai
    from zai import ZhipuAiClient
except ImportError:  # pragma: no cover - exercised in unit tests via monkeypatch
    zai = None  # type: ignore[assignment]
    ZhipuAiClient = None  # type: ignore[assignment]

DEFAULT_ZHIPU_TIMEOUT_SECONDS = 22
DEFAULT_ZHIPU_CHAT_MAX_TOKENS = 512
DEFAULT_ZHIPU_CHAT_RETRIES = 1
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"


def _get_config() -> dict[str, str]:
    api_key = os.environ.get("ZHIPU_API_KEY", "").strip()
    base_url = os.environ.get("ZHIPU_API_BASE", ZHIPU_BASE_URL).strip().rstrip("/")
    embedding_model = os.environ.get("ZHIPU_EMBEDDING_MODEL", "embedding-3").strip() or "embedding-3"
    chat_model = os.environ.get("ZHIPU_CHAT_MODEL", "GLM-4.5-AirX").strip() or "GLM-4.5-AirX"
    return {
        "api_key": api_key,
        "base_url": base_url,
        "embedding_model": embedding_model,
        "chat_model": chat_model,
    }


def is_zhipu_enabled() -> bool:
    config = _get_config()
    return bool(config["api_key"] and config["base_url"])


def _get_timeout_seconds() -> float:
    raw = os.environ.get("ZHIPU_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return float(DEFAULT_ZHIPU_TIMEOUT_SECONDS)
    try:
        value = float(raw)
    except ValueError:
        return float(DEFAULT_ZHIPU_TIMEOUT_SECONDS)
    return value if value > 0 else float(DEFAULT_ZHIPU_TIMEOUT_SECONDS)


def _get_chat_max_tokens() -> int:
    raw = os.environ.get("ZHIPU_CHAT_MAX_TOKENS", "").strip()
    if not raw:
        return DEFAULT_ZHIPU_CHAT_MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_ZHIPU_CHAT_MAX_TOKENS
    return max(64, min(4096, value))


def _get_chat_retries() -> int:
    raw = os.environ.get("ZHIPU_CHAT_RETRIES", "").strip()
    if not raw:
        return DEFAULT_ZHIPU_CHAT_RETRIES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_ZHIPU_CHAT_RETRIES
    return max(0, min(2, value))


def _get_timeout_config() -> Any:
    timeout_seconds = _get_timeout_seconds()
    if httpx is None:
        return timeout_seconds
    return httpx.Timeout(timeout=timeout_seconds, connect=min(timeout_seconds, 8.0))


def _get_timeout_error_types() -> tuple[type[BaseException], ...]:
    timeout_types: list[type[BaseException]] = [TimeoutError, socket.timeout]
    if zai is not None:
        timeout_error = getattr(getattr(zai, "core", None), "APITimeoutError", None)
        if isinstance(timeout_error, type):
            timeout_types.append(timeout_error)
    return tuple(timeout_types)


def _raise_sdk_runtime_error(err: Exception) -> None:
    if isinstance(err, _get_timeout_error_types()):
        raise RuntimeError("智谱 API 请求超时，请稍后重试。") from err

    response = getattr(err, "response", None)
    status_code = getattr(err, "status_code", None) or getattr(response, "status_code", None)
    response_text = getattr(response, "text", None)
    if status_code:
        detail = response_text or str(err)
        raise RuntimeError(f"智谱 API 调用失败（HTTP {status_code}）：{detail}") from err

    raise RuntimeError("智谱 API 调用失败，请检查网络或 API Key 配置。") from err


def _create_client(max_retries: int = 0) -> Any:
    config = _get_config()
    if not config["api_key"]:
        raise RuntimeError("ZHIPU_API_KEY 未配置。")
    if ZhipuAiClient is None:
        raise RuntimeError("未安装智谱官方 Python SDK，请先执行 `pip install zai-sdk==0.2.2`。")

    return ZhipuAiClient(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=_get_timeout_config(),
        max_retries=max(0, max_retries),
    )


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", "")
        if isinstance(text, str) and text:
            parts.append(text)
    return "".join(parts).strip()


def create_embeddings(texts: list[str], dimensions: int | None = None) -> list[list[float]]:
    if not texts:
        return []
    if len(texts) > 64:
        raise ValueError("embedding 单次最多 64 条文本，请分批请求。")

    config = _get_config()
    payload: dict[str, Any] = {
        "model": config["embedding_model"],
        "input": texts,
    }
    if dimensions is not None:
        payload["dimensions"] = dimensions

    client = _create_client()
    try:
        response = client.embeddings.create(**payload)
    except Exception as err:
        _raise_sdk_runtime_error(err)

    rows = getattr(response, "data", [])
    if not isinstance(rows, list):
        raise RuntimeError("智谱 embedding 返回数据异常。")

    vectors: list[list[float]] = []
    for row in rows:
        embedding = getattr(row, "embedding", None)
        if not isinstance(embedding, list):
            continue
        vectors.append([float(value) for value in embedding])

    if len(vectors) != len(texts):
        raise RuntimeError("embedding 返回条数与输入不一致。")
    return vectors


def generate_answer(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    config = _get_config()
    client = _create_client(max_retries=_get_chat_retries())

    try:
        response = client.chat.completions.create(
            model=config["chat_model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=_get_chat_max_tokens(),
        )
    except Exception as err:
        _raise_sdk_runtime_error(err)

    choices = getattr(response, "choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("智谱对话模型返回为空。")

    first = choices[0]
    message = getattr(first, "message", None)
    if message is None:
        raise RuntimeError("智谱对话模型返回 message 异常。")

    content = _extract_message_text(getattr(message, "content", ""))
    if not content:
        raise RuntimeError("智谱对话模型未返回有效文本。")
    return content
