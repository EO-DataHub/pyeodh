import posixpath
import urllib.parse

from pyeodh.types import Link


def is_absolute_url(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)


def join_url(*args: str) -> str:
    return posixpath.join(*args)


def get_link_by_rel(links: list[Link], rel: str) -> Link:
    return next(filter(lambda ln: ln.rel == rel, links), None)
