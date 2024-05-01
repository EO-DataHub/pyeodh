import posixpath
import urllib.parse
from typing import Any

from pyeodh.types import Link


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


def get_link_by_rel(links: list[Link], rel: str) -> Link | None:
    return next(filter(lambda ln: ln.rel == rel, links), None)


def remove_null_items(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}
