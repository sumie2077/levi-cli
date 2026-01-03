from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, get_args

from kosong.chat_provider import ChatProvider
from pydantic import SecretStr

from levi_cli.constant import USER_AGENT

if TYPE_CHECKING:
    from levi_cli.config import LLMModel, LLMProvider

type ProviderType = Literal[
    "qwen",
    "deepseek",
    "local",
    "_chaos",
]

type ModelCapability = Literal["image_in", "thinking"]
ALL_MODEL_CAPABILITIES: set[ModelCapability] = set(get_args(ModelCapability.__value__))


@dataclass(slots=True)
class LLM:
    chat_provider: ChatProvider
    max_context_size: int
    capabilities: set[ModelCapability]

    @property
    def model_name(self) -> str:
        return self.chat_provider.model_name


def augment_provider_with_env_vars(provider: LLMProvider, model: LLMModel) -> dict[str, str]:
    """Override provider/model settings from environment variables.

    Returns:
        Mapping of environment variables that were applied.
    """
    applied: dict[str, str] = {}

    match provider.type:
        case "qwen":
            if base_url := os.getenv("DASHSCOPE_BASE_URL"):
                provider.base_url = base_url
                applied["DASHSCOPE_BASE_URL"] = base_url
            if api_key := os.getenv("DASHSCOPE_API_KEY"):
                provider.api_key = SecretStr(api_key)
                applied["DASHSCOPE_API_KEY"] = "******"
            if model_name := os.getenv("QWEN_MODEL_NAME"):
                model.model = model_name
                applied["QWEN_MODEL_NAME"] = model_name
            if max_context_size := os.getenv("QWEN_MODEL_MAX_CONTEXT_SIZE"):
                model.max_context_size = int(max_context_size)
                applied["QWEN_MODEL_MAX_CONTEXT_SIZE"] = max_context_size
            if capabilities := os.getenv("QWEN_MODEL_CAPABILITIES"):
                caps_lower = (cap.strip().lower() for cap in capabilities.split(",") if cap.strip())
                model.capabilities = set(
                    cast(ModelCapability, cap)
                    for cap in caps_lower
                    if cap in get_args(ModelCapability)
                )
                applied["QWEN_MODEL_CAPABILITIES"] = capabilities
        case "deepseek":
            if base_url := os.getenv("DEEPSEEK_BASE_URL"):
                provider.base_url = base_url
                applied["DEEPSEEK_BASE_URL"] = base_url
            if api_key := os.getenv("DEEPSEEK_API_KEY"):
                provider.api_key = SecretStr(api_key)
                applied["DEEPSEEK_API_KEY"] = "******"
            if model_name := os.getenv("DEEPSEEK_MODEL_NAME"):
                model.model = model_name
                applied["DEEPSEEK_MODEL_NAME"] = model_name
            if max_context_size := os.getenv("DEEPSEEK_MODEL_MAX_CONTEXT_SIZE"):
                model.max_context_size = int(max_context_size)
                applied["DEEPSEEK_MODEL_MAX_CONTEXT_SIZE"] = max_context_size
            if capabilities := os.getenv("DEEPSEEK_MODEL_CAPABILITIES"):
                caps_lower = (cap.strip().lower() for cap in capabilities.split(",") if cap.strip())
                model.capabilities = set(
                    cast(ModelCapability, cap)
                    for cap in caps_lower
                    if cap in get_args(ModelCapability)
                )
                applied["DEEPSEEK_MODEL_CAPABILITIES"] = capabilities
        case "local":
            if base_url := os.getenv("LOCAL_BASE_URL"):
                provider.base_url = base_url
                applied["LOCAL_BASE_URL"] = base_url
            if api_key := os.getenv("LOCAL_API_KEY"):
                provider.api_key = SecretStr(api_key)
                applied["LOCAL_API_KEY"] = "******"
            if model_name := os.getenv("LOCAL_MODEL_NAME"):
                model.model = model_name
                applied["LOCAL_MODEL_NAME"] = model_name
            if max_context_size := os.getenv("LOCAL_MODEL_MAX_CONTEXT_SIZE"):
                model.max_context_size = int(max_context_size)
                applied["LOCAL_MODEL_MAX_CONTEXT_SIZE"] = max_context_size
            if capabilities := os.getenv("LOCAL_MODEL_CAPABILITIES"):
                caps_lower = (cap.strip().lower() for cap in capabilities.split(",") if cap.strip())
                model.capabilities = set(
                    cast(ModelCapability, cap)
                    for cap in caps_lower
                    if cap in get_args(ModelCapability)
                )
                applied["LOCAL_MODEL_CAPABILITIES"] = capabilities
        case _:
            pass

    return applied


def create_llm(
    provider: LLMProvider,
    model: LLMModel,
    *,
    session_id: str | None = None,
) -> LLM:
    match provider.type:
        case "qwen":
            from kosong.contrib.chat_provider.openai_responses import OpenAIResponses

            chat_provider = OpenAIResponses(
                model=model.model,
                base_url=provider.base_url,
                api_key=provider.api_key.get_secret_value(),
            )
        case "deepseek":
            from kosong.contrib.chat_provider.openai_responses import OpenAIResponses

            chat_provider = OpenAIResponses(
                model=model.model,
                base_url=provider.base_url,
                api_key=provider.api_key.get_secret_value(),
            )
        case "local":
            from kosong.contrib.chat_provider.openai_responses import OpenAIResponses

            chat_provider = OpenAIResponses(
                model=model.model,
                base_url=provider.base_url,
                api_key=provider.api_key.get_secret_value(),
            )
        case "_chaos":
            from kosong.chat_provider.chaos import ChaosChatProvider, ChaosConfig
            from kosong.contrib.chat_provider.openai_responses import OpenAIResponses

            chat_provider = ChaosChatProvider(
                provider=OpenAIResponses(
                    model=model.model,
                    base_url=provider.base_url,
                    api_key=provider.api_key.get_secret_value(),
                ),
                chaos_config=ChaosConfig(
                    error_probability=0.8,
                    error_types=[429, 500, 503],
                ),
            )

    return LLM(
        chat_provider=chat_provider,
        max_context_size=model.max_context_size,
        capabilities=_derive_capabilities(model),
    )


def _derive_capabilities(model: LLMModel) -> set[ModelCapability]:
    capabilities = model.capabilities or set()
    
    model_name_lower = model.model.lower()
    
    # Auto-detect thinking/reasoning capability from model name
    thinking_keywords = ["thinking", "reasoning", "reasoner", "r1"]
    if any(keyword in model_name_lower for keyword in thinking_keywords):
        capabilities.add("thinking")
    
    # Auto-detect image capability from model name
    image_keywords = ["vl", "vision", "multimodal", "mm"]
    if any(keyword in model_name_lower for keyword in image_keywords):
        capabilities.add("image_in")
    
    return capabilities
