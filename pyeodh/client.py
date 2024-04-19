from typing import Literal
import urllib.parse

import requests

from pyeodh import consts
from pyeodh.resource_catalog import ResourceCatalog
from pyeodh.types import Headers, Params
from pyeodh.utils import is_absolute_url


class Client:
    def __init__(self, base_url: str = consts.API_BASE_URL) -> None:
        if not is_absolute_url(base_url):
            raise ValueError("base_url must be an absolute URL")

        self.url_base = base_url
        self._build_session()

    def _build_session(
        self,
    ) -> None:
        # TODO Add retry count, setting auth headers etc. here
        self._session = requests.Session()

    def _request_json(
        self,
        method: Literal["GET", "POST", "DELETE", "PUT"],
        url: str,
        headers: Headers | None = None,
        params: Params | None = None,
        data: dict | None = None,
    ) -> tuple[Headers, dict]:

        if not is_absolute_url(url):
            url = urllib.parse.urljoin(self.url_base, url)

        headers = {} if headers is None else headers
        headers["Content-Type"] = "application/json"

        response = self._session.request(
            method, url, headers=headers, params=params, data=data
        )
        # TODO handle errors...
        return response.headers, response.json()

    def get_resource_catalog(self) -> ResourceCatalog:
        headers, data = self._request_json("GET", "/stac-fastapi")
        return ResourceCatalog(self, headers, data)
