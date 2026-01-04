"""
The local version of the Grep tool using ripgrep.
Requires ripgrep to be installed system-wide.
"""

import platform
import shutil
from pathlib import Path
from typing import override

import ripgrepy  # pyright: ignore[reportMissingTypeStubs]
from kosong.tooling import CallableTool2, ToolError, ToolReturnValue
from pydantic import BaseModel, Field

from levi_cli.tools.utils import ToolResultBuilder, load_desc
from loguru import logger


class Params(BaseModel):
    pattern: str = Field(
        description="The regular expression pattern to search for in file contents"
    )
    path: str = Field(
        description=(
            "File or directory to search in. Defaults to current working directory. "
            "If specified, it must be an absolute path."
        ),
        default=".",
    )
    glob: str | None = Field(
        description=(
            "Glob pattern to filter files (e.g. `*.js`, `*.{ts,tsx}`). No filter by default."
        ),
        default=None,
    )
    output_mode: str = Field(
        description=(
            "`content`: Show matching lines (supports `-B`, `-A`, `-C`, `-n`, `head_limit`); "
            "`files_with_matches`: Show file paths (supports `head_limit`); "
            "`count_matches`: Show total number of matches. "
            "Defaults to `files_with_matches`."
        ),
        default="files_with_matches",
    )
    before_context: int | None = Field(
        alias="-B",
        description=(
            "Number of lines to show before each match (the `-B` option). "
            "Requires `output_mode` to be `content`."
        ),
        default=None,
    )
    after_context: int | None = Field(
        alias="-A",
        description=(
            "Number of lines to show after each match (the `-A` option). "
            "Requires `output_mode` to be `content`."
        ),
        default=None,
    )
    context: int | None = Field(
        alias="-C",
        description=(
            "Number of lines to show before and after each match (the `-C` option). "
            "Requires `output_mode` to be `content`."
        ),
        default=None,
    )
    line_number: bool = Field(
        alias="-n",
        description=(
            "Show line numbers in output (the `-n` option). Requires `output_mode` to be `content`."
        ),
        default=False,
    )
    ignore_case: bool = Field(
        alias="-i",
        description="Case insensitive search (the `-i` option).",
        default=False,
    )
    type: str | None = Field(
        description=(
            "File type to search. Examples: py, rust, js, ts, go, java, etc. "
            "More efficient than `glob` for standard file types."
        ),
        default=None,
    )
    head_limit: int | None = Field(
        description=(
            "Limit output to first N lines, equivalent to `| head -N`. "
            "Works across all output modes: content (limits output lines), "
            "files_with_matches (limits file paths), count_matches (limits count entries). "
            "By default, no limit is applied."
        ),
        default=None,
    )
    multiline: bool = Field(
        description=(
            "Enable multiline mode where `.` matches newlines and patterns can span "
            "lines (the `-U` and `--multiline-dotall` options). "
            "By default, multiline mode is disabled."
        ),
        default=False,
    )


class Grep(CallableTool2[Params]):
    """Grep tool using ripgrep for fast code search."""
    
    name: str = "Grep"
    description: str = load_desc(Path(__file__).parent / "grep.md")
    params: type[Params] = Params
    
    # 类级别缓存，避免重复查找 ripgrep
    _rg_path_cache: str | None = None
    _rg_check_error: RuntimeError | None = None

    @classmethod
    def _ensure_rg_available(cls) -> str:
        """
        确保 ripgrep 可用，结果会被缓存。
        
        首次调用时会检查系统 PATH，之后直接返回缓存结果。
        
        Returns:
            ripgrep 的完整路径
            
        Raises:
            RuntimeError: 如果 ripgrep 未安装
        """
        # 如果之前已经检查过并失败，直接抛出相同错误
        if cls._rg_check_error is not None:
            raise cls._rg_check_error
        
        # 如果已经缓存了路径，直接返回
        if cls._rg_path_cache is not None:
            return cls._rg_path_cache

        # 首次调用，开始查找
        rg_path = shutil.which("rg")
        if rg_path:
            cls._rg_path_cache = rg_path
            logger.info("Ripgrep found at: {path}", path=rg_path)
            return rg_path

        # 没找到，生成友好的错误信息
        system = platform.system()
        install_instructions = {
            "Darwin": "brew install ripgrep",
            "Linux": (
                "sudo apt-get install ripgrep  # Debian/Ubuntu\n"
                "  or\n"
                "sudo dnf install ripgrep  # Fedora/RHEL"
            ),
            "Windows": (
                "choco install ripgrep  # 使用 Chocolatey\n"
                "  or\n"
                "scoop install ripgrep  # 使用 Scoop\n"
                "  or\n"
                "winget install BurntSushi.ripgrep  # Windows 11"
            ),
        }.get(system, "pip install ripgrep")

        error_msg = (
            f"❌ ripgrep is not installed on your system ({system}).\n\n"
            f"Please install it using one of these commands:\n"
            f"  {install_instructions}\n\n"
            f"Official docs: https://github.com/BurntSushi/ripgrep#installation"
        )
        
        error = RuntimeError(error_msg)
        cls._rg_check_error = error
        raise error

    @override
    async def __call__(self, params: Params) -> ToolReturnValue:
        try:
            builder = ToolResultBuilder()
            message = ""

            # 获取 ripgrep 路径（第一次查找，后续使用缓存）
            rg_path = self._ensure_rg_available()
            logger.debug("Using ripgrep binary: {rg_bin}", rg_bin=rg_path)

            # Initialize ripgrep with pattern and path
            rg = ripgrepy.Ripgrepy(params.pattern, params.path, rg_path=rg_path)

            # Apply search options
            if params.ignore_case:
                rg = rg.ignore_case()
            if params.multiline:
                rg = rg.multiline().multiline_dotall()

            # Content display options (only for content mode)
            if params.output_mode == "content":
                if params.before_context is not None:
                    rg = rg.before_context(params.before_context)
                if params.after_context is not None:
                    rg = rg.after_context(params.after_context)
                if params.context is not None:
                    rg = rg.context(params.context)
                if params.line_number:
                    rg = rg.line_number()

            # File filtering options
            if params.glob:
                rg = rg.glob(params.glob)
            if params.type:
                rg = rg.type_(params.type)

            # Set output mode
            if params.output_mode == "files_with_matches":
                rg = rg.files_with_matches()
            elif params.output_mode == "count_matches":
                rg = rg.count_matches()

            # Execute search
            result = rg.run(universal_newlines=False)
            output = result.as_string

            # Apply head limit if specified
            if params.head_limit is not None:
                lines = output.split("\n")
                if len(lines) > params.head_limit:
                    lines = lines[: params.head_limit]
                    output = "\n".join(lines)
                    message = f"Results truncated to first {params.head_limit} lines"
                    if params.output_mode in ["content", "files_with_matches", "count_matches"]:
                        output += f"\n... (results truncated to {params.head_limit} lines)"

            if not output:
                return builder.ok(message="No matches found")

            builder.write(output)
            return builder.ok(message=message)

        except RuntimeError as e:
            # ripgrep 未安装的错误
            return ToolError(
                message=str(e),
                brief="ripgrep is required",
            )
        except Exception as e:
            return ToolError(
                message=f"Failed to grep. Error: {str(e)}",
                brief="Failed to grep",
            )