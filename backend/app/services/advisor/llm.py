"""Tool-calling chat client. Groq, Gemini, Ollama and any OpenAI-compatible gateway (OpenRouter, NVIDIA, ...)
expose the same chat endpoint with `tools`, so one client covers every provider SolarOpt supports."""
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
    """Tries the models in order: a model that errors or runs out of quota hands over to the next one,
    and stays skipped for the rest of the proposal."""

    def __init__(self, base: str, key: str, models: list[str], name: str = ""):
        self.url, self.key, self.models, self.name = base.rstrip("/") + "/chat/completions", key, models, name or base

    @property
    def model(self) -> str:
        return self.models[0] if self.models else ""

    def chat(self, messages, tools=None, json_mode=False):
        errors = []
        while self.models:
            try:
                return self._call(self.models[0], messages, tools, json_mode)
            except LLMError as exc:
                errors.append(f"{self.models[0]}: {exc}")
                if len(self.models) == 1:
                    break
                self.models = self.models[1:]
        raise LLMError("; ".join(errors) or "Chưa khai báo mô hình.")

    def _call(self, model, messages, tools, json_mode):
        body: dict = {"model": model, "messages": messages, "temperature": 0.2}
        if tools:
            body["tools"], body["tool_choice"] = tools, "auto"
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": "Bearer " + self.key} if self.key else {}
        try:
            response = requests.post(self.url, json=body, headers=headers, timeout=(10, 120))
        except requests.RequestException as exc:
            raise LLMError(f"không kết nối được ({exc.__class__.__name__})") from exc
        if response.status_code == 429:
            raise LLMError("đang giới hạn số lượt gọi (429)")
        if not response.ok:
            raise LLMError(f"lỗi {response.status_code}: {response.text[:160]}")
        try:
            return response.json()["choices"][0]["message"]
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError("phản hồi không đúng định dạng") from exc


def _models(value: str) -> list[str]:
    return [m.strip() for m in value.split(",") if m.strip()]


def default_client() -> ChatClient | None:
    """The configured client, or None when nothing usable is set (the advisor then runs its rule-based planner).

    ADVISOR_BASE_URL / ADVISOR_API_KEY send the advisor to its own gateway; otherwise it follows AI_PROVIDER.
    ADVISOR_MODEL may list fallbacks separated by commas, best first."""
    provider, vision_model, key = provider_settings()
    models = _models(os.getenv("ADVISOR_MODEL", ""))
    if base := os.getenv("ADVISOR_BASE_URL", "").strip():
        key = os.getenv("ADVISOR_API_KEY", "").strip() or key
        return OpenAICompatible(base, key, models, "advisor") if models and key else None
    if provider == "openai":
        base = os.getenv("AI_BASE_URL", "").strip()
        models = models or _models(vision_model)
        return OpenAICompatible(base, key, models, "openai") if base and key and models else None
    if provider not in DEFAULT_MODELS or (provider != "ollama" and not key):
        return None
    base = BASES.get(provider) or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1"
    return OpenAICompatible(base, key, models or [DEFAULT_MODELS[provider]], provider)
