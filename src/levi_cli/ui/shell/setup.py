from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, NamedTuple

import aiohttp
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts.choice_input import ChoiceInput
from pydantic import SecretStr

from levi_cli.config import (
    LLMModel,
    LLMProvider,
    load_config,
    save_config,
)
from levi_cli.ui.shell.console import console
from levi_cli.ui.shell.metacmd import meta_command
from levi_cli.utils.aiohttp import new_client_session

if TYPE_CHECKING:
    from levi_cli.ui.shell import Shell

class _Platform(NamedTuple):
    id: str
    name: str
    base_url: str
    allowed_prefixes: list[str] | None = None


_PLATFORMS = [
    # 1. Qwen (通义千问 / 阿里云 DashScope)
    _Platform(
        id="qwen-dashscope",
        name="Qwen (Aliyun DashScope)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        allowed_prefixes=["qwen-flash", "qwen-image-max", "qwen-plus", "qwen3-vl-plus", "qwen3-omni-flash"],
    ),
    # 2. DeepSeek (官方 API)
    _Platform(
        id="deepseek-official",
        name="DeepSeek Official",
        base_url="https://api.deepseek.com",
        allowed_prefixes=None,
    ),
    # 3. 本地模型 (Localhost)
    # 如果使用 Ollama，默认端口是 11434   
    _Platform(
        id="local-ollama",
        name="Local Model (Ollama:11434)",
        base_url="http://localhost:11434/v1",
        allowed_prefixes=None,
    ),
]


_PLATFORM_TYPE_MAP = {
    "qwen-dashscope": "qwen",
    "deepseek-official": "deepseek",
    "local-ollama": "local",
}


@meta_command
async def setup(app: Shell, args: list[str]):
    """Setup Levi CLI"""
    result = await _setup()
    if not result:
        # error message already printed
        return

    config = load_config()
    config.providers[result.platform.id] = LLMProvider(
        type=_PLATFORM_TYPE_MAP[result.platform.id],
        base_url=result.platform.base_url,
        api_key=result.api_key,
    )
    config.models[result.model_id] = LLMModel(
        provider=result.platform.id,
        model=result.model_id,
        max_context_size=result.max_context_size,
    )
    config.default_model = result.model_id

    
    save_config(config)
    console.print("[green]✓[/green] Levi CLI has been setup! Reloading...")
    await asyncio.sleep(1)
    console.clear()

    from levi_cli.cli import Reload

    raise Reload


class _SetupResult(NamedTuple):
    platform: _Platform
    api_key: SecretStr
    model_id: str
    max_context_size: int


def get_context_length(model_id: str, api_data: dict) -> int:
    """如果不返回 context_length，则手动根据模型名判断"""
    # 1. 优先使用 API 返回的值 (兼容 Kimi)
    if api_data.get("context_length"):
        return api_data["context_length"]

    mid = model_id.lower()
    
    # 2. DeepSeek
    if "deepseek" in mid:
        # 全是128k
        return 131072
    
    # 3. Qwen
    if "qwen-long" in mid:
        return 10000000  # 10M
    if "qwen" in mid and ("turbo" in mid or "plus" in mid or "2.5" in mid):
        return 131072   # 128k
    
    # 4. 本地模型 (默认给个通用值)
    if "llama" in mid or "mistral" in mid:
        return 8192
        
    # 默认保底
    return 4096


async def _setup() -> _SetupResult | None:
    # select the API platform
    platform_name = await _prompt_choice(
        header="Select the API platform",
        choices=[platform.name for platform in _PLATFORMS],
    )
    if not platform_name:
        console.print("[red]No platform selected[/red]")
        return None

    platform = next(platform for platform in _PLATFORMS if platform.name == platform_name)

    # enter the API key
    api_key = await _prompt_text("Enter your API key", is_password=True)
    if not api_key:
        return None

    # list models
    models_url = f"{platform.base_url}/models"
    try:
        async with (
            new_client_session() as session,
            session.get(
                models_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                raise_for_status=True,
            ) as response,
        ):
            resp_json = await response.json()
    except aiohttp.ClientError as e:
        console.print(f"[red]Failed to get models: {e}[/red]")
        return None

    model_dict = {model["id"]: model for model in resp_json["data"]}

    # select the model
    model_ids: list[str] = [model["id"] for model in resp_json["data"]]
    if platform.allowed_prefixes is not None:
        model_ids = [
            model_id
            for model_id in model_ids
            if model_id.startswith(tuple(platform.allowed_prefixes))
        ]

    if not model_ids:
        console.print("[red]No models available for the selected platform[/red]")
        return None

    model_id = await _prompt_choice(
        header="Select the model",
        choices=model_ids,
    )
    if not model_id:
        console.print("[red]No model selected[/red]")
        return None

    model = model_dict[model_id]

    # 计算上下文长度，防止 KeyError
    max_context = get_context_length(model_id, model)

    return _SetupResult(
        platform=platform,
        api_key=SecretStr(api_key),
        model_id=model_id,
        max_context_size=max_context,
    )


async def _prompt_choice(*, header: str, choices: list[str]) -> str | None:
    if not choices:
        return None

    try:
        return await ChoiceInput(
            message=header,
            options=[(choice, choice) for choice in choices],
            default=choices[0],
        ).prompt_async()
    except (EOFError, KeyboardInterrupt):
        return None


async def _prompt_text(prompt: str, *, is_password: bool = False) -> str | None:
    session = PromptSession[str]()
    try:
        return str(
            await session.prompt_async(
                f" {prompt}: ",
                is_password=is_password,
            )
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None


@meta_command
def reload(app: Shell, args: list[str]):
    """Reload configuration"""
    from levi_cli.cli import Reload

    raise Reload