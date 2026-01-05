from pathlib import Path
from typing import override
import os

from duckduckgo_search import DDGS
from kosong.tooling import CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field, ValidationError

from levi_cli.constant import USER_AGENT
from levi_cli.soul.toolset import get_current_tool_call_or_none
from levi_cli.tools.utils import ToolResultBuilder, load_desc
from levi_cli.utils.aiohttp import new_client_session
from loguru import logger


class Params(BaseModel):
    query: str = Field(description="The query text to search for.")
    limit: int = Field(
        description=(
            "The number of results to return. "
            "Typically you do not need to set this value. "
            "When the results do not contain what you need, "
            "you probably want to give a more concrete query."
        ),
        default=5,
        ge=1,
        le=20,
    )
    include_content: bool = Field(
        description=(
            "Whether to include the content of the web pages in the results. "
            "It can consume a large amount of tokens when this is set to True. "
            "You should avoid enabling this when `limit` is set to a large value."
        ),
        default=False,
    )


class SearchWeb(CallableTool2[Params]):
    name: str = "SearchWeb"
    description: str = load_desc(Path(__file__).parent / "search.md", {})
    params: type[Params] = Params

    def __init__(self):
        super().__init__()
        self._tavily_api_key = os.getenv("TAVILY_API_KEY")
        # 可以在这里配置 Tavily 或其他搜索服务
        
    @override
    async def __call__(self, params: Params) -> ToolReturnValue:
    # 优先使用 Tavily
        if self._tavily_api_key:
            ret = await self._search_with_tavily(params)
            if not ret.is_error:
                return ret
            logger.warning("Tavily search failed, falling back to DuckDuckGo")
        
        # 降级到 DuckDuckGo
        return await self._search_with_ddgs(params)       
        

    
    async def _search_with_tavily(self, params: Params) -> ToolReturnValue:
        """Search using Tavily API"""
        builder = ToolResultBuilder(max_line_length=None)
        
        if not self._tavily_api_key:
            return builder.error(
                "Tavily API key not found. Please set TAVILY_API_KEY environment variable.",
                brief="Tavily API key not configured",
            )
        
        try:
            async with (
                new_client_session() as session,
                session.post(
                    "https://api.tavily.com/search",
                    headers={
                        "Content-Type": "application/json",
                    },
                    json={
                        "api_key": self._tavily_api_key,
                        "query": params.query,
                        "max_results": params.limit,
                        "include_answer": False,
                        "include_raw_content": params.include_content,
                        "include_images": False,
                    },
                ) as response,
            ):
                if response.status != 200:
                    error_text = await response.text()
                    return builder.error(
                        f"Tavily API request failed. Status: {response.status}. Error: {error_text}",
                        brief=f"Tavily API error {response.status}",
                    )
                
                result = await response.json()
                
                if "results" not in result or not result["results"]:
                    return builder.error(
                        "No search results found. You may want to try a different query.",
                        brief="No results found",
                    )
                
                for i, item in enumerate(result["results"]):
                    if i > 0:
                        builder.write("---\n\n")
                    
                    title = item.get("title", "N/A")
                    url = item.get("url", "N/A")
                    snippet = item.get("content", "N/A")
                    
                    builder.write(
                        f"Title: {title}\n"
                        f"URL: {url}\n"
                        f"Summary: {snippet}\n\n"
                    )
                    
                    if params.include_content and item.get("raw_content"):
                        builder.write(f"{item['raw_content']}\n\n")
                
                return builder.ok()
                
        except Exception as e:
            logger.error("Tavily search failed: {error}", error=str(e))
            return builder.error(
                f"Failed to search via Tavily: {str(e)}",
                brief="Tavily search failed",
            )


    @staticmethod
    async def _search_with_ddgs(params: Params) -> ToolReturnValue:
        """Search using DuckDuckGo as fallback"""
        builder = ToolResultBuilder(max_line_length=None)

        # 当 LLM 请求完整内容但用 DuckDuckGo 时，提醒 LLM
        if params.include_content:
            builder.write(
                "[Using DuckDuckGo fallback - "
                "full page content not available. Snippets only.]\n\n"
            )
        try:
            # Use DuckDuckGo search (synchronous API called in async context)
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    keywords=params.query,
                    max_results=params.limit,
                ))

            if not results:
                return builder.error(
                    "No search results found. You may want to try a different query.",
                    brief="No results found",
                )

            # Format results consistently
            for i, result in enumerate(results):
                if i > 0:
                    builder.write("---\n\n")
                
                title = result.get("title", "N/A")
                url = result.get("href", "N/A")
                body = result.get("body", "N/A")
                
                builder.write(
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Summary: {body}\n\n"
                )

            return builder.ok()

        except Exception as e:
            logger.error("DuckDuckGo search failed: {error}", error=str(e))
            return builder.error(
                f"Failed to search due to error: {str(e)}. "
                "This may indicate a network issue or service unavailability.",
                brief="Search failed",
            )