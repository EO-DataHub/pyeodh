import json
import logging
import urllib.parse
from typing import Any, Callable

import requests
from owslib.map import wms111, wms130
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService

from pyeodh import consts
from pyeodh.ades import Ades
from pyeodh.resource_catalog import CatalogService
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
        data: Any | None = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[int, Headers, str]:
        logger.debug(
            f"_request_json_raw received {locals()}",
        )
        if not is_absolute_url(url):
            logger.debug(f"Received not absolute url: {url}")
            url = urllib.parse.urljoin(self.url_base, url)
            logger.debug(f"Created url from base: {url}")

        if ".org.uk/search" in url:
            url = url.replace(".org.uk/search", ".org.uk/api/catalogue/stac/search")

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
        data: Any | None = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[Headers, Any]:
        status, resp_headers, resp_data = self._request_json_raw(
            method, url, headers, params, data, encode
        )

        if not len(resp_data):
            return resp_headers, None

        return resp_headers, json.loads(resp_data)

    def get_catalog_service(self) -> CatalogService:
        """Initializes the resource catalog API client.

        Calls: GET /api/catalogue/stac

        Returns:
            CatalogService: Object representing the Resource catalog service.
        """
        headers, data = self._request_json("GET", "/api/catalogue/stac")
        return CatalogService(self, headers, data)

    def get_ades(self) -> Ades:
        """Initializes the workflow execution service (ADES) client.

        Calls: GET /ades/ogc-api

        Returns:
            Ades: Object representing the ADES.
        """
        headers, data = self._request_json("GET", "/ades/test_oxidian/ogc-api/")
        return Ades(self, headers, data)

    def get_wmts(self) -> WebMapTileService:
        """Initializes the OWSLib WebMapTileService

        Returns:
            WebMapTileService: Initialized WMTS
        """
        url = join_url(self.url_base, "/vs/cache/ows/wmts/")
        wmts = WebMapTileService(url)

        # Patch wmts object attribute error
        # see https://github.com/geopython/OWSLib/issues/572
        for i, op in enumerate(wmts.operations):
            if not hasattr(op, "name"):
                wmts.operations[i].name = ""

        return wmts

    def get_wms(self) -> wms111.WebMapService_1_1_1 | wms130.WebMapService_1_3_0:
        """Initialized the OWSLib WebMapService

        Returns:
            WebMapService: Initialized WMS
        """
        url = join_url(self.url_base, "/vs/cache/ows")
        wms = WebMapService(url, version="1.1.1")
        return wms
