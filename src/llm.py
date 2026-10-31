"""Multi-provider LLM connector for Empório da Música.

Supports Replicate (Llama 3 / 3.1 8B & 70B), OpenAI (GPT-4o / GPT-4o-mini),
and an offline Mock client for deterministic unit testing.
"""

from __future__ import annotations

import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMResponse:
    """Standardized response container across all LLM providers."""

    def __init__(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        self.content = content.strip()
        self.tool_calls = tool_calls or []

    def __repr__(self) -> str:
        return f"LLMResponse(content={self.content[:40]!r}..., tool_calls={self.tool_calls})"


class BaseLLMClient(ABC):
    """Abstract interface for LLM completion and streaming."""

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        tier: str = "fast",
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        tier: str = "deep",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        pass


def format_llama3_prompt(messages: List[Dict[str, str]]) -> str:
    """Format standard OpenAI-style message dicts into Llama 3 special token format."""
    prompt = "<|begin_of_text|>"
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt


def normalize_replicate_model(name: str) -> str:
    """Normalize Meta model names for Replicate serverless endpoints."""
    if not name:
        return "meta/meta-llama-3-8b-instruct"
    if "llama-3.1-8b" in name.lower() or "llama-3-8b" in name.lower():
        return "meta/meta-llama-3-8b-instruct"
    if "llama-3.1-70b" in name.lower() or "llama-3-70b" in name.lower():
        return "meta/meta-llama-3-70b-instruct"
    return name


class ReplicateClient(BaseLLMClient):
    """Replicate serverless inference connector for Meta Llama models."""

    def __init__(self, api_token: Optional[str] = None):
        import replicate
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN environment variable is required.")
        self.client = replicate.Client(api_token=self.api_token)
        # Fast tier: 8B instruct; Deep/High tier: 70B instruct
        raw_fast = os.getenv("REPLICATE_MODEL_FAST", "meta/meta-llama-3-8b-instruct")
        raw_deep = os.getenv("REPLICATE_MODEL_HIGH") or os.getenv("REPLICATE_MODEL_DEEP", "meta/meta-llama-3-70b-instruct")
        self.model_fast = normalize_replicate_model(raw_fast)
        self.model_deep = normalize_replicate_model(raw_deep)

    def _get_model(self, tier: str) -> str:
        return self.model_deep if tier == "deep" else self.model_fast

    def complete(
        self,
        messages: List[Dict[str, str]],
        tier: str = "fast",
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> LLMResponse:
        model = self._get_model(tier)
        prompt = format_llama3_prompt(messages)
        
        # Retry loop for 429 rate limit backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                output = self.client.run(
                    model,
                    input={
                        "prompt": prompt,
                        "temperature": max(0.01, temperature),
                        "max_tokens": max_tokens,
                        "prompt_template": "{prompt}",
                    },
                )
                text = "".join(str(chunk) for chunk in output)
                return LLMResponse(content=text)
            except Exception as exc:
                err_msg = str(exc)
                if "429" in err_msg or "throttled" in err_msg:
                    if attempt < max_retries - 1:
                        time.sleep(4.0)
                        continue
                # If 70B fails or rate limited, fallback to 8B fast tier
                if model == self.model_deep and attempt == max_retries - 1:
                    try:
                        time.sleep(3.0)
                        output = self.client.run(
                            self.model_fast,
                            input={
                                "prompt": prompt,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "prompt_template": "{prompt}",
                            },
                        )
                        return LLMResponse(content="".join(str(chunk) for chunk in output))
                    except Exception:
                        pass
                raise exc

        return LLMResponse(content="Desculpe, ocorreu um erro de conexão temporário.")

    def stream(
        self,
        messages: List[Dict[str, str]],
        tier: str = "deep",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        model = self._get_model(tier)
        prompt = format_llama3_prompt(messages)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                for chunk in self.client.stream(
                    model,
                    input={
                        "prompt": prompt,
                        "temperature": max(0.01, temperature),
                        "max_tokens": max_tokens,
                        "prompt_template": "{prompt}",
                    },
                ):
                    yield str(chunk)
                return
            except Exception as exc:
                if "429" in str(exc) and attempt < max_retries - 1:
                    time.sleep(4.0)
                    continue
                # Fallback to fast model stream
                if model == self.model_deep:
                    try:
                        time.sleep(2.0)
                        for chunk in self.client.stream(
                            self.model_fast,
                            input={
                                "prompt": prompt,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "prompt_template": "{prompt}",
                            },
                        ):
                            yield str(chunk)
                        return
                    except Exception:
                        pass
                yield f"[Erro de conexão: {str(exc)}]"
                return


class OpenAIClient(BaseLLMClient):
    """OpenAI connector for GPT-4o and GPT-4o-mini."""

    def __init__(self, api_key: Optional[str] = None):
        from openai import OpenAI
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required.")
        self.client = OpenAI(api_key=self.api_key)
        self.model_fast = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
        self.model_deep = os.getenv("OPENAI_MODEL_DEEP", "gpt-4o")

    def _get_model(self, tier: str) -> str:
        return self.model_deep if tier == "deep" else self.model_fast

    def complete(
        self,
        messages: List[Dict[str, str]],
        tier: str = "fast",
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> LLMResponse:
        model = self._get_model(tier)
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        return LLMResponse(content=content)

    def stream(
        self,
        messages: List[Dict[str, str]],
        tier: str = "deep",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        model = self._get_model(tier)
        stream_response = self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class MockClient(BaseLLMClient):
    """Deterministic offline mock LLM client for automated testing and CI/CD."""

    def complete(
        self,
        messages: List[Dict[str, str]],
        tier: str = "fast",
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> LLMResponse:
        # Check last user message
        last_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_msg = m.get("content", "").lower()
                break

        # Simulate router or worker responses
        if "categoria" in last_msg or "router" in str(messages).lower():
            if any(w in last_msg for w in ["corda", "pedal", "amplificador", "palheta"]):
                return LLMResponse(content='{"intent": "OUT_OF_SCOPE", "reason": "accessory deflection"}')
            if any(w in last_msg for w in ["violao", "violões", "takamine", "yamaha", "guitarra", "preco", "custa"]):
                return LLMResponse(content='{"intent": "CATALOG_SALES", "keyword": "violão"}')
            if any(w in last_msg for w in ["brab", "rastreio", "pedido", "status"]):
                return LLMResponse(content='{"intent": "ORDER_TRACKING"}')
            return LLMResponse(content='{"intent": "STORE_POLICY"}')

        return LLMResponse(content="Olá! Sou o assistente da Empório da Música. Como posso ajudar com sua jornada musical?")

    def stream(
        self,
        messages: List[Dict[str, str]],
        tier: str = "deep",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Iterator[str]:
        full_text = self.complete(messages, tier=tier, temperature=temperature).content
        tokens = full_text.split(" ")
        for i, tok in enumerate(tokens):
            yield tok + (" " if i < len(tokens) - 1 else "")
            time.sleep(0.01)


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Factory creating configured LLM client with automatic fallback."""
    prov = (provider or os.getenv("LLM_PROVIDER", "")).strip().lower()

    if prov == "mock":
        return MockClient()
    if prov == "openai" or (not prov and os.getenv("OPENAI_API_KEY") and not os.getenv("REPLICATE_API_TOKEN")):
        return OpenAIClient()
    if prov == "replicate" or (not prov and os.getenv("REPLICATE_API_TOKEN")):
        return ReplicateClient()

    # Fallback to Mock if no keys provided
    return MockClient()


if __name__ == "__main__":
    print("Initializing LLM client...")
    llm = get_llm_client()
    print(f"Selected client: {llm.__class__.__name__}")
    res = llm.complete(
        [{"role": "user", "content": "Diga olá em uma palavra."}],
        tier="fast",
        max_tokens=10,
    )
    print("Completion result:", repr(res.content))
