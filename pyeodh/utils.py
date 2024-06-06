import posixpath
import urllib.parse
from typing import Any


def is_absolute_url(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)


def join_url(*args: str) -> str:
    for a in args[1:]:
        if a.startswith("/"):
            raise ValueError(
                f"Argument {a} is an absolute path! "
                "Only the first argument can start with '/'. "
                "See posixpath.join() documentation."
            )
    return posixpath.join(*args)


def remove_null_items(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


class ConformanceError(Exception):
    """Raise when the API does not coform to requested functionality."""

    def __str__(self):
        return f"API does not conform to {', '.join(self.args)}"
