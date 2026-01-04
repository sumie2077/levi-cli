from pathlib import Path
from typing import override

from duckduckgo_search import DDGS
from kosong.tooling import CallableTool2, ToolReturnValue
from pydantic import BaseModel, Field, ValidationError

from levi_cli.config import Config
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
            "This parameter is only effective when a search service is configured. "
            "When using DuckDuckGo (fallback), only snippets are returned. "
            "It can consume a large amount of tokens when this is set to True. "
            "You should avoid enabling this when `limit` is set to a large value."
        ),
        default=False,
    )


class SearchWeb(CallableTool2[Params]):
    name: str = "SearchWeb"
    description: str = load_desc(Path(__file__).parent / "search.md", {})
    params: type[Params] = Params

    def __init__(self, config: Config):
        super().__init__()
        # Service-first strategy: use configured search service if available, else fallback to DuckDuckGo
        self._service_config = config.services.search

    @override
    async def __call__(self, params: Params) -> ToolReturnValue:
        builder = ToolResultBuilder(max_line_length=None)

        # Try service-based search if configured
        if self._service_config:
            ret = await self._search_with_service(params)
            if not ret.is_error:
                return ret
            logger.warning("Failed to search via service: {error}", error=ret.message)
            # fallback to DuckDuckGo if service search fails
        
        return await self._search_with_ddgs(params)

    async def _search_with_service(self, params: Params) -> ToolReturnValue:
        """Search using configured service"""
        assert self._service_config is not None
        
        builder = ToolResultBuilder(max_line_length=None)

        if not self._service_config.base_url or not self._service_config.api_key.get_secret_value():
            return builder.error(
                "Search service is not properly configured.",
                brief="Search service not configured",
            )

        tool_call = get_current_tool_call_or_none()
        assert tool_call is not None, "Tool call is expected to be set"

        try:
            async with (
                new_client_session() as session,
                session.post(
                    self._service_config.base_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Authorization": f"Bearer {self._service_config.api_key.get_secret_value()}",
                        "X-Tool-Call-Id": tool_call.id,
                        **(self._service_config.custom_headers or {}),
                    },
                    json={
                        "text_query": params.query,
                        "limit": params.limit,
                        "enable_page_crawling": params.include_content,
                        "timeout_seconds": 30,
                    },
                ) as response,
            ):
                if response.status != 200:
                    return builder.error(
                        (
                            f"Failed to search. Status: {response.status}. "
                            "This may indicate the search service is currently unavailable."
                        ),
                        brief="Failed to search",
                    )

                try:
                    results = Response(**await response.json()).search_results
                except ValidationError as e:
                    return builder.error(
                        (
                            f"Failed to parse search results. Error: {e}. "
                            "This may indicate the search service is currently unavailable."
                        ),
                        brief="Failed to parse search results",
                    )

            for i, result in enumerate(results):
                if i > 0:
                    builder.write("---\n\n")
                builder.write(
                    f"Title: {result.title}\nDate: {result.date}\n"
                    f"URL: {result.url}\nSummary: {result.snippet}\n\n"
                )
                if result.content:
                    builder.write(f"{result.content}\n\n")

            return builder.ok()
        except Exception as e:
            return builder.error(
                f"Failed to search via service due to error: {str(e)}",
                brief="Service search error",
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


class SearchResult(BaseModel):
    site_name: str
    title: str
    url: str
    snippet: str
    content: str = ""
    date: str = ""
    icon: str = ""
    mime: str = ""


class Response(BaseModel):
    search_results: list[SearchResult]
