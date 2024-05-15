import json
import logging
import urllib.parse
from typing import Any

import requests

from pyeodh import consts
from pyeodh.resource_catalog import EodhCatalog
from pyeodh.types import Headers, Params, RequestMethod
from pyeodh.utils import is_absolute_url

logger = logging.getLogger(__name__)


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

    def _request_json_raw(
        self,
        method: RequestMethod,
        url: str,
        headers: Headers | None = None,
        params: Params | None = None,
        data: dict | None = None,
    ) -> tuple[int, Headers, str]:
        logger.debug(
            f"_request_json_raw received {locals()}",
        )
        if not is_absolute_url(url):
            logger.debug(f"Received not absolute url: {url}")
            url = urllib.parse.urljoin(self.url_base, url)
            logger.debug(f"Created url from base: {url}")

        headers = Headers() if headers is None else headers
        headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data) if data else None
        logger.debug(
            f"Making request: {method} {url}\nheaders: {headers}\nparams: {params}"
            f"\nbody: {encoded_data}"
        )
        response = self._session.request(
            method,
            url,
            headers=headers,
            params=params,
            data=encoded_data,
        )
        logger.debug(
            f"Received response {response.status_code}\nheaders: {response.headers}"
            f"\ncontent: {response.text}"
        )
        # TODO consider moving this to _requst_json() and raise own exceptions
        # so that we can user _raw in e.g. delete methods where we expect a 409 and
        # want to recover
        response.raise_for_status()

        return response.status_code, response.headers, response.text

    def _request_json(
        self,
        method: RequestMethod,
        url: str,
        headers: Headers | None = None,
        params: Params | None = None,
        data: dict | None = None,
    ) -> tuple[Headers, Any]:
        status, resp_headers, resp_data = self._request_json_raw(
            method, url, headers, params, data
        )

        if not len(resp_data):
            return resp_headers, None

        return resp_headers, json.loads(resp_data)

    def get_resource_catalog(self) -> EodhCatalog:
        headers, data = self._request_json("GET", "/stac-fastapi")
        return EodhCatalog._from_dict(self, headers, data)
