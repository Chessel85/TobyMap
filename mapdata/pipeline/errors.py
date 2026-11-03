"""Why a build stops (DMT-2).

Every message names what went wrong, the source or feature involved, and
what to do next, in plain sentences for a screen reader.
"""
from __future__ import annotations


class BuildStopped(Exception):
    """A build, fetch or check stopped before finishing. The message says why and what to do next."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
