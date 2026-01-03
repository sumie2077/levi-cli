from __future__ import annotations


class LeviCLIException(Exception):
    """Base exception class for Kimi CLI."""

    pass


class ConfigError(LeviCLIException):
    """Configuration error."""

    pass


class AgentSpecError(LeviCLIException):
    """Agent specification error."""

    pass
