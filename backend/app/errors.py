from __future__ import annotations


class RepositoryNotReadyError(RuntimeError):
    """Raised when the backend skeleton has not been wired to MySQL yet."""

    def __init__(self, operation: str) -> None:
        super().__init__(
            f"MySQL runtime repository is not wired for `{operation}` yet. "
            "The backend skeleton is live, but SQL-backed handlers are the next step."
        )
        self.operation = operation


class UnresolvedQueryError(ValueError):
    """Raised when a search input cannot be mapped to a known query_key."""

    def __init__(self, query_input: str) -> None:
        super().__init__("No matching query found. Try a suggested query.")
        self.query_input = query_input
