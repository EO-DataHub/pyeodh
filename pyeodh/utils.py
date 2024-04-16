import urllib.parse


def is_absolute_url(url) -> bool:
    return bool(urllib.parse.urlparse(url).netloc)
