"""Per-feature model selection. Cloud credentials never go to the local server."""

import json
import os

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from openai import OpenAI


class OllamaChatModel(BaseChatModel):
    """Native Ollama API so context size and thinking are explicitly controlled."""

    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout: float = 180
    num_ctx: int = 16384
    num_predict: int = 800

    @property
    def _llm_type(self):
        return "bid3-ollama"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        roles = {"human": "user", "ai": "assistant", "system": "system"}
        wire_messages = []
        for message in messages:
            if message.type not in roles or not isinstance(message.content, str):
                raise ValueError("로컬 텍스트 모델에는 텍스트 메시지만 전달할 수 있습니다.")
            wire_messages.append({"role": roles[message.type], "content": message.content})
        # Bound input conservatively by UTF-8 bytes; do not let Ollama silently
        # discard the beginning of a long source document.
        input_bound = sum(len(m["content"].encode("utf-8")) + 64 for m in wire_messages)
        schema_bound = len(json.dumps(kwargs.get("format", {})).encode("utf-8"))
        if input_bound + schema_bound + self.num_predict + 512 > self.num_ctx:
            raise ValueError(
                "문서가 로컬 모델의 안전한 입력 범위를 초과했습니다. "
                "문서를 나누거나 LOCAL_LLM_CONTEXT를 늘려 주세요."
            )
        payload = {
            "model": self.model,
            "messages": wire_messages,
            "stream": False,
            "think": False,
            "keep_alive": "5m",
            "options": {
                "temperature": 0,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
        }
        if stop:
            payload["options"]["stop"] = stop
        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        response = requests.post(
            self.base_url.rstrip("/") + "/api/chat",
            json=payload,
            timeout=(10, self.timeout),
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise ValueError("로컬 모델 요청에 실패했습니다: " + str(data["error"]))
        if data.get("done_reason") == "length":
            raise ValueError("로컬 모델 출력 한도에 도달했습니다. 출력량 설정을 확인하세요.")
        content = data["message"]["content"]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def with_structured_output(self, schema, **kwargs):
        if kwargs:
            raise ValueError("지원하지 않는 구조화 출력 옵션입니다.")
        if isinstance(schema, dict):
            schema_json, parser = schema, json.loads
        else:
            schema_json, parser = schema.model_json_schema(), schema.model_validate_json
        return self.bind(format=schema_json) | RunnableLambda(lambda message: parser(message.content))


def model_selection(role, default_model):
    provider = os.getenv(f"{role}_PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "ollama"}:
        raise ValueError(f"{role}_PROVIDER는 openai 또는 ollama여야 합니다.")
    if provider == "ollama":
        model = os.getenv(f"{role}_LOCAL_MODEL") or os.getenv("LOCAL_LLM_MODEL", "qwen3:14b")
    else:
        model = os.getenv(f"{role}_MODEL") or default_model
    return provider, model


def build_text_model(role, default_model, max_tokens, reasoning_effort="low"):
    provider, model = model_selection(role, default_model)
    if provider == "ollama":
        return OllamaChatModel(
            model=model,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            timeout=float(os.getenv("LOCAL_LLM_TIMEOUT", "180")),
            num_ctx=int(os.getenv("LOCAL_LLM_CONTEXT", "16384")),
            num_predict=max_tokens,
        )
    options = {
        "model": model,
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("BID_OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "max_completion_tokens": max_tokens,
        "timeout": float(os.getenv("OPENAI_TIMEOUT", "180")),
        "max_retries": int(os.getenv("OPENAI_MAX_RETRIES", "1")),
        "store": False,
    }
    if model.startswith(("gpt-5", "gpt-6")):
        options.update(reasoning_effort=reasoning_effort, use_responses_api=True)
    else:
        options["temperature"] = 0
    return ChatOpenAI(**options)


def cloud_options():
    return {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("BID_OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "timeout": float(os.getenv("OPENAI_TIMEOUT", "180")),
        "max_retries": int(os.getenv("OPENAI_MAX_RETRIES", "1")),
    }


def cloud_client(**overrides):
    return OpenAI(**{**cloud_options(), **overrides})
