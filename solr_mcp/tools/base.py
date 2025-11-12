"""Base tool definitions and decorators."""

from collections.abc import Callable
from functools import wraps
from typing import Any


def tool(
    name: str | None = None,
    description: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> Callable:
    """Decorator to mark a function as an MCP tool.

    Args:
        name: Tool name. Defaults to function name if not provided.
        description: Tool description. Defaults to function docstring if not provided.
        parameters: Tool parameters. Defaults to function parameters if not provided.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> list[dict[str, str]]:
            result = func(*args, **kwargs)
            if not isinstance(result, list):
                result = [{"type": "text", "text": str(result)}]
            return result

        # Mark as tool
        wrapper._is_tool = True  # type: ignore[attr-defined]

        # Set tool metadata
        wrapper._tool_name = name or func.__name__  # type: ignore[attr-defined]
        wrapper._tool_description = description or func.__doc__ or ""  # type: ignore[attr-defined]
        wrapper._tool_parameters = parameters or {}  # type: ignore[attr-defined]

        return wrapper

    return decorator
