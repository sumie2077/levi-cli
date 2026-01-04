from pathlib import Path
from typing import override

from kosong.tooling import CallableTool2, ToolError, ToolOk, ToolReturnValue

from levi_cli.soul.timemachine import TimeMachine, TimeMachineError, TMail
from levi_cli.tools.utils import load_desc

NAME = "SendTMail"


class SendTMail(CallableTool2[TMail]):
    name: str = NAME
    description: str = load_desc(Path(__file__).parent / "tmail.md")
    params: type[TMail] = TMail

    def __init__(self, time_machine: TimeMachine) -> None:
        super().__init__()
        self._time_machine = time_machine

    @override
    async def __call__(self, params: TMail) -> ToolReturnValue:
        try:
            self._time_machine.send_tmail(params)
        except TimeMachineError as e:
            return ToolError(
                output="",
                message=f"Failed to send T-Mail. Error: {str(e)}",
                brief="Failed to send T-Mail",
            )
        return ToolOk(
            output="",
            message=(
                "If you see this message, the T-Mail was NOT sent successfully. "
                "This may be because some other tool that needs approval was rejected."
            ),
            brief="hide",
        )
