from pathlib import Path
from typing import Literal, override
import aiofiles
import aiofiles.os

from kosong.tooling import CallableTool2, ToolError, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field

from levi_cli.soul.agent import BuiltinSystemPromptArgs
from levi_cli.soul.approval import Approval
from levi_cli.tools.file import FileActions
from levi_cli.tools.utils import ToolRejectedError, load_desc
from levi_cli.utils.path import is_within_directory


class Params(BaseModel):
    path: str = Field(description="The absolute path to the file to write")
    content: str = Field(description="The content to write to the file")
    mode: Literal["overwrite", "append"] = Field(
        description=(
            "The mode to use to write to the file. "
            "Two modes are supported: `overwrite` for overwriting the whole file and "
            "`append` for appending to the end of an existing file."
        ),
        default="overwrite",
    )


class WriteFile(CallableTool2[Params]):
    name: str = "WriteFile"
    description: str = load_desc(Path(__file__).parent / "write.md")
    params: type[Params] = Params

    def __init__(self, builtin_args: BuiltinSystemPromptArgs, approval: Approval):
        super().__init__()
        self._work_dir = builtin_args.LEVI_WORK_DIR
        self._approval = approval

    async def _validate_path(self, path: Path) -> ToolError | None:
        """Validate that the path is safe to write."""
        # Check for path traversal attempts
        resolved_path = path.resolve()

        # Ensure the path is within work directory
        if not is_within_directory(resolved_path, self._work_dir):
            return ToolError(
                message=(
                    f"`{path}` is outside the working directory. "
                    "You can only write files within the working directory."
                ),
                brief="Path outside working directory",
            )
        return None

    @override
    async def __call__(self, params: Params) -> ToolReturnValue:
        # TODO: checks:
        # - check if the path may contain secrets
        # - check if the file format is writable
        try:
            p = Path(params.path)

            if not p.is_absolute():
                return ToolError(
                    message=(
                        f"`{params.path}` is not an absolute path. "
                        "You must provide an absolute path to write a file."
                    ),
                    brief="Invalid path",
                )

            # Validate path safety
            path_error = await self._validate_path(p)
            if path_error:
                return path_error

            if not await aiofiles.os.path.exists(p.parent):
                return ToolError(
                    message=f"`{params.path}` parent directory does not exist.",
                    brief="Parent directory not found",
                )

            # Validate mode parameter
            if params.mode not in ["overwrite", "append"]:
                return ToolError(
                    message=(
                        f"Invalid write mode: `{params.mode}`. "
                        "Mode must be either `overwrite` or `append`."
                    ),
                    brief="Invalid write mode",
                )

            # Request approval
            if not await self._approval.request(
                self.name,
                FileActions.EDIT,
                f"Write file `{params.path}`",
            ):
                return ToolRejectedError()

            # Write content to file
            match params.mode:
                case "overwrite":
                    async with aiofiles.open(p, 'w', encoding='utf-8') as f:
                        await f.write(params.content)
                case "append":
                    async with aiofiles.open(p, 'a', encoding='utf-8') as f:
                        await f.write(params.content)
            # Get file info for success message
            file_stat = await aiofiles.os.stat(p)
            file_size = file_stat.st_size
            action = "overwritten" if params.mode == "overwrite" else "appended to"
            return ToolOk(
                output="",
                message=(f"File successfully {action}. Current size: {file_size} bytes."),
            )

        except Exception as e:
            return ToolError(
                message=f"Failed to write to {params.path}. Error: {e}",
                brief="Failed to write file",
            )
