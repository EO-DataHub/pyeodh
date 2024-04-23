import posixpath
import urllib.parse
from typing import Any


def is_absolute_url(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)


def join_url(*args: str) -> str:
    return posixpath.join(*args)


def get_href_by_rel(links: list[dict[str, Any]], rel: str) -> str | None:
    return get_link_by_rel(links, rel).get("href")


def get_link_by_rel(links: list[dict[str, Any]], rel: str) -> dict[str, Any]:
    return next(filter(lambda ln: ln["rel"] == rel, links), {})
