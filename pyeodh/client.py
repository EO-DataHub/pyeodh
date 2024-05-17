import json
import logging
import urllib.parse
from typing import Any, Callable

import requests

from pyeodh import consts
from pyeodh.ades import Ades
from pyeodh.resource_catalog import Catalog
from pyeodh.types import Headers, Params, RequestMethod
from pyeodh.utils import is_absolute_url, join_url

logger = logging.getLogger(__name__)


def _encode_json(data: dict) -> tuple[str, str]:
    return "application/json", json.dumps(data)


class Client:
    def __init__(
        self, base_url: str = consts.API_BASE_URL, auth: tuple[str, str] | None = None
    ) -> None:
        if not is_absolute_url(base_url):
            raise ValueError("base_url must be an absolute URL")

        self.url_base = base_url
        self._build_session()

        # TEMP:
        if auth:
            self._session.auth = auth

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
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[int, Headers, str]:
        logger.debug(
            f"_request_json_raw received {locals()}",
        )
        if not is_absolute_url(url):
            logger.debug(f"Received not absolute url: {url}")
            url = urllib.parse.urljoin(self.url_base, url)
            logger.debug(f"Created url from base: {url}")

        headers = Headers() if headers is None else headers
        encoded_data = None
        if data is not None:
            headers["Content-Type"], encoded_data = encode(data)
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
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[Headers, Any]:
        status, resp_headers, resp_data = self._request_json_raw(
            method, url, headers, params, data, encode
        )

        if not len(resp_data):
            return resp_headers, None

        return resp_headers, json.loads(resp_data)

    def get_resource_catalog(self, catalog_id) -> Catalog:
        url = join_url("/stac-fastapi/catalogs", catalog_id)
        headers, data = self._request_json("GET", url)
        return Catalog(self, headers, data)

    def get_resource_catalogs(self) -> list[Catalog]:
        headers, data = self._request_json("GET", "/stac-fastapi/catalogs")
        return [Catalog(self, headers, cat) for cat in data.get("catalogs")]

    def get_ades(self) -> Ades:
        headers, data = self._request_json("GET", "/ades/test_cluster_3/ogc-api/")
        return Ades(self, headers, data)
