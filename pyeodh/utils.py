import urllib.parse


def is_absolute_url(url: str) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)
