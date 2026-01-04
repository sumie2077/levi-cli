from __future__ import annotations

from pydantic import BaseModel, Field


class TMail(BaseModel):
    message: str = Field(description="The message to send.")
    checkpoint_id: int = Field(description="The checkpoint to send the message back to.", ge=0)
    # TODO: allow restoring filesystem state to the checkpoint


class TimeMachineError(Exception):
    pass


class TimeMachine:
    def __init__(self):
        self._pending_tmail: TMail | None = None
        self._n_checkpoints: int = 0

    def send_tmail(self, tmail: TMail):
        """Send a T-Mail. Intended to be called by the SendTMail tool."""
        if self._pending_tmail is not None:
            raise TimeMachineError("Only one T-Mail can be sent at a time")
        if tmail.checkpoint_id < 0:
            raise TimeMachineError("The checkpoint ID can not be negative")
        if tmail.checkpoint_id >= self._n_checkpoints:
            raise TimeMachineError("There is no checkpoint with the given ID")
        self._pending_tmail = tmail

    def set_n_checkpoints(self, n_checkpoints: int):
        """Set the number of checkpoints. Intended to be called by the soul."""
        self._n_checkpoints = n_checkpoints

    def fetch_pending_tmail(self) -> TMail | None:
        """Fetch a pending T-Mail. Intended to be called by the soul."""
        pending_tmail = self._pending_tmail
        self._pending_tmail = None
        return pending_tmail
