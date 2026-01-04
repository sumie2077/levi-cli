from __future__ import annotations


class LeviCLIException(Exception):
    """Base exception class for Levi CLI."""

    pass


class ConfigError(LeviCLIException):
    """Configuration error."""

    pass


class AgentSpecError(LeviCLIException):
    """Agent specification error."""

    pass
