from __future__ import annotations


class RepositoryNotReadyError(RuntimeError):
    """Raised when the backend skeleton has not been wired to MySQL yet."""

    def __init__(self, operation: str) -> None:
        super().__init__(
            f"MySQL runtime repository is not wired for `{operation}` yet. "
            "The backend skeleton is live, but SQL-backed handlers are the next step."
        )
        self.operation = operation
