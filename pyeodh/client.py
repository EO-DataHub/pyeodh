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
from pyeodh.workspace import Workspace

logger = logging.getLogger(__name__)


def _encode_json(data: dict) -> tuple[str, str]:
    return "application/json", json.dumps(data)


class Client:
    def __init__(
        self,
        base_url: str = consts.API_BASE_URL,
        username: str | None = None,
        token: str | None = None,
    ) -> None:
        if not is_absolute_url(base_url):
            raise ValueError("base_url must be an absolute URL")

        self.url_base = base_url
        self.username = username
        self.token = token
        self._build_session()
        self.workspace = Workspace(self)

    def _build_session(
        self,
    ) -> None:
        self._session = requests.Session()
        if self.token is not None:
            self._session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _request_raw(
        self,
        method: RequestMethod,
        url: str,
        headers: Headers | None = None,
        params: Params | None = None,
        data: Any | None = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> requests.Response:
        """Make a raw request.

        Args:
            method (RequestMethod): HTTP method to use
            url (str): Target URL
            headers (Headers | None, optional): Headers to send with the request.
                Defaults to None.
            params (Params | None, optional): Query parameters to send with the request.
                Defaults to None.
            data (Any | None, optional): Raw data to send with the request. Data is
                encoded by the `encode` function before sending. Defaults to None.
            encode (Callable[[Any], tuple[str, Any]], optional): Function to encode the
                data. Has to return a tuple of (content-type string, encoded data).
                Defaults to _encode_json.

        Returns:
            requests.Response: Response from the request
        """
        logger.debug(f"_request_raw received {locals()}")
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

        return response

    def _request_json(
        self,
        method: RequestMethod,
        url: str,
        headers: Headers | None = None,
        params: Params | None = None,
        data: Any | None = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[Headers, Any]:
        """Make a request and return the headers and deserialized JSON data. Input data
        can be anything, not just JSON, providing an `encode` function is supplied. Use
        when expecting JSON data in the response.

        Args:
            method (RequestMethod): HTTP method to use
            url (str): Target URL
            headers (Headers | None, optional): Headers to send with the request.
                Defaults to None.
            params (Params | None, optional): Query parameters to send with the request.
                Defaults to None.
            data (Any | None, optional): Raw data to send with the request. Data is
                encoded by the `encode` function before sending. Defaults to None.
            encode (Callable[[Any], tuple[str, Any]], optional): Function to encode the
                data. Has to return a tuple of (content-type string, encoded data).
                Defaults to _encode_json.

        Returns:
            tuple[Headers, Any]: Response headers and deserialized JSON data
        """
        response = self._request_raw(method, url, headers, params, data, encode)

        if not len(response.text):
            return response.headers, None

        return response.headers, json.loads(response.text)

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
        if self.username is None or self.token is None:
            raise ValueError(
                "Valid username and token required for accessing protected API "
                "endpoints."
            )
        # headers, data = self._request_json("GET", f"/ades/{self.username}/ogc-api/")

        # * TEMP
        # * ADES root endpoint is not available ATM

        headers = Headers()
        data = {
            "links": [
                {
                    "href": join_url(self.url_base, f"ades/{self.username}/ogc-api/"),
                    "rel": "self",
                },
                {
                    "href": join_url(
                        self.url_base, f"ades/{self.username}/ogc-api/processes"
                    ),
                    "rel": "http://www.opengis.net/def/rel/ogc/1.0/processes",
                },
                {
                    "href": join_url(
                        self.url_base, f"ades/{self.username}/ogc-api/jobs"
                    ),
                    "rel": "http://www.opengis.net/def/rel/ogc/1.0/job-list",
                },
            ],
        }

        # * ^^^^

        return Ades(self, headers, data)

    def get_wmts(self) -> WebMapTileService:
        """Initializes the OWSLib WebMapTileService

        Returns:
            WebMapTileService: Initialized WMTS
        """
        url = join_url(self.url_base, "vs/cache/ows/wmts/")
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
        url = join_url(self.url_base, "vs/cache/ows")
        wms = WebMapService(url, version="1.1.1")
        return wms
