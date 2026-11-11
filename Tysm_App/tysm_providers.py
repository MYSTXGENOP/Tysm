"""Tysm provider adapters. Standard-library only; no secrets stored in files.

Default: local Ollama. Optional cloud fallback requires explicit opt-in.
"""
import json
import os
import urllib.error
import urllib.request


class ProviderError(RuntimeError):
    pass


def _post_json(url, payload, headers, timeout=180):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never echo response bodies: they can contain private data.
        raise ProviderError(f"HTTP {exc.code} from provider") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise ProviderError(f"Provider connection or response failed: {type(exc).__name__}") from exc


class OllamaProvider:
    name = "Ollama (local)"

    def __init__(self, model="qwen3:8b", url="http://localhost:11434/api/chat"):
        self.model = model
        self.url = url

    def reply(self, messages):
        result = _post_json(
            self.url,
            {"model": self.model, "messages": messages, "stream": False, "keep_alive": "2m", **({"think": False} if self.model.startswith("qwen3:") else {})},
            {"Content-Type": "application/json"},
        )
        try:
            return result["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderError("Ollama returned an unexpected response") from exc


class OpenAIProvider:
    name = "OpenAI (cloud)"

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def reply(self, messages):
        result = _post_json(
            "https://api.openai.com/v1/chat/completions",
            {"model": self.model, "messages": messages},
            {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("No text content")
            return content
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Cloud provider returned an unexpected response") from exc


def _latest_user_message(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _route(messages, kind="chat"):
    """Return (preferred_provider, reason) without sending any data.

    Local is always preferred for private data, attachments, check-ins,
    and ordinary conversation. A cloud preference requires explicit opt-in.
    """
    user_text = _latest_user_message(messages)
    lower = user_text.lower()
    if kind != "chat":
        return "local", "Background check-in stays local"
    if "--- file content ---" in lower:
        return "local", "Shared files stay local"
    private_terms = (
        "password", "passcode", "api key", "secret key", "token", "my address",
        "my phone", "my email", "medical", "diagnosis", "therapy", "my bank",
        "credit card", "private", "confidential", "remember:", "my name",
        "my family", "my friend", "personal", "my school",
    )
    if any(term in lower for term in private_terms):
        return "local", "Potentially personal information stays local"
    complex_terms = (
        "debug this code", "refactor", "architecture", "complex", "in-depth",
        "detailed analysis", "analyze this code", "compare these approaches",
        "step-by-step implementation", "design a system", "write a program",
    )
    if any(term in lower for term in complex_terms) or len(user_text) > 2500:
        return "cloud", "Complex task"
    return "local", "Ordinary conversation"


def _cloud_config():
    if os.getenv("TYSM_ALLOW_CLOUD") != "1":
        return None
    key = os.getenv("TYSM_OPENAI_API_KEY", "").strip()
    model = os.getenv("TYSM_OPENAI_MODEL", "").strip()
    return OpenAIProvider(key, model) if key and model else None


def get_reply(messages, kind="chat", cloud_messages=None, local_only=False):
    """Automatic selection with explicit cloud consent and local-first privacy.

    Returns (reply, provider_name). Cloud requires TYSM_ALLOW_CLOUD=1,
    TYSM_OPENAI_API_KEY, TYSM_OPENAI_MODEL. Fallback to cloud is never
    performed for private messages, file content, or check-ins.
    """
    local = OllamaProvider(
        model=os.getenv("TYSM_OLLAMA_MODEL", "qwen3:8b"),
        url=os.getenv("TYSM_OLLAMA_URL", "http://localhost:11434/api/chat"),
    )
    cloud = _cloud_config()
    preferred, reason = _route(messages, kind)
    if local_only:
        preferred, reason = "local", "Explicit local-only request"
    private = reason in (
        "Background check-in stays local", "Shared files stay local",
        "Potentially personal information stays local", "Explicit local-only request",
    )
    if preferred == "cloud" and cloud is not None:
        try:
            return cloud.reply(cloud_messages if cloud_messages is not None else messages), cloud.name
        except ProviderError as cloud_error:
            try:
                return local.reply(messages), local.name
            except ProviderError as local_error:
                raise ProviderError(
                    f"Both providers failed (cloud: {cloud_error}; local: {local_error})."
                ) from local_error
    try:
        return local.reply(messages), local.name
    except ProviderError as local_error:
        if private or cloud is None:
            raise ProviderError(
                f"Local Ollama failed ({local_error}). "
                "Cloud is unavailable or this request is local-only."
            ) from local_error
        try:
            return cloud.reply(cloud_messages if cloud_messages is not None else messages), cloud.name
        except ProviderError as cloud_error:
            raise ProviderError(
                f"Both providers failed (local: {local_error}; cloud: {cloud_error})."
            ) from cloud_error
