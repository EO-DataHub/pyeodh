import logging
import posixpath
import urllib.parse
from typing import Any

from pyeodh.consts import S3_BASE_URL_TEMPLATE

logger = logging.getLogger(__name__)


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


def s3_url(workspace_name: str, environment: str, path_to_file: str) -> str:
    """Generate an S3 URL for a file in a workspace.

    Args:
        workspace_name (str): Name of the workspace
        path_to_file (str): Path to file within workspace, leading '/' will be stripped

    Returns:
        str: The formatted S3 URL
    """

    if path_to_file.startswith("/"):
        logger.warning(f"Leading '/' in path_to_file: {path_to_file}")
        logger.debug("Stripping leading '/'")
    path_stripped = path_to_file.lstrip("/")
    base = S3_BASE_URL_TEMPLATE.format(
        workspace_name=workspace_name, environment=environment
    )
    return posixpath.join(base, path_stripped)
