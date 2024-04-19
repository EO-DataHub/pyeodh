import posixpath
import urllib.parse


def is_absolute_url(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)


def join_url(*args: str) -> str:
    return posixpath.join(*args)


def get_href_by_rel(links: list[dict[str, str]], rel: str) -> str | None:
    link = next(filter(lambda ln: ln["rel"] == rel, links), None)
    return link.get("href")
