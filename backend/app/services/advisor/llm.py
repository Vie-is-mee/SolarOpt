"""Tool-calling chat client. Groq, Gemini and Ollama all expose an OpenAI-compatible chat endpoint with
`tools`, so one client covers the three providers SolarOpt already supports (AI_PROVIDER)."""
from __future__ import annotations

import os
from typing import Protocol

import requests

from app.services.vision import provider_settings

BASES = {"groq": "https://api.groq.com/openai/v1", "gemini": "https://generativelanguage.googleapis.com/v1beta/openai"}
# Text models with reliable tool calling; ADVISOR_MODEL overrides (the vision AI_MODEL may be image-only).
DEFAULT_MODELS = {"groq": "openai/gpt-oss-120b", "gemini": "gemini-2.5-flash", "ollama": "qwen3:4b"}


class LLMError(Exception):
    pass


class ChatClient(Protocol):
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None, json_mode: bool = False) -> dict:
        """Returns the assistant message: {'content': str|None, 'tool_calls': [...]}"""


class OpenAICompatible:
    def __init__(self, provider: str, model: str, key: str):
        self.provider, self.model, self.key = provider, model, key
        base = BASES.get(provider) or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1"
        self.url = base + "/chat/completions"

    def chat(self, messages, tools=None, json_mode=False):
        body: dict = {"model": self.model, "messages": messages, "temperature": 0.2}
        if tools:
            body["tools"], body["tool_choice"] = tools, "auto"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": "Bearer " + self.key} if self.key else {}
        try:
            response = requests.post(self.url, json=body, headers=headers, timeout=(10, 90))
        except requests.RequestException as exc:
            raise LLMError(f"Không kết nối được {self.provider}: {exc.__class__.__name__}") from exc
        if response.status_code == 429:
            raise LLMError(f"{self.provider} đang giới hạn số lượt gọi (429).")
        if not response.ok:
            raise LLMError(f"{self.provider} trả lỗi {response.status_code}: {response.text[:200]}")
        try:
            return response.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError("Phản hồi của mô hình không đúng định dạng.") from exc


def default_client() -> ChatClient | None:
    """The configured client, or None when no key is set (the advisor then runs its rule-based planner)."""
    provider, _, key = provider_settings()
    if provider not in DEFAULT_MODELS or (provider != "ollama" and not key):
        return None
    model = os.getenv("ADVISOR_MODEL", "").strip() or DEFAULT_MODELS[provider]
    return OpenAICompatible(provider, model, key)
