import json
import logging
import urllib.parse
from typing import Any, Callable, Optional

import requests

from pyeodh import consts
from pyeodh.ades import Ades
from pyeodh.resource_catalog import CatalogService
from pyeodh.types import Headers, Params, RequestMethod
from pyeodh.utils import is_absolute_url
from pyeodh.workspace import Workspace

logger = logging.getLogger(__name__)


def _encode_json(data: dict) -> tuple[str, str]:
    return "application/json", json.dumps(data)


class Client:
    def __init__(
        self,
        base_url: str = consts.API_BASE_URL,
        username: Optional[str] = None,
        token: Optional[str] = None,
    ) -> None:
        if not is_absolute_url(base_url):
            raise ValueError("base_url must be an absolute URL")

        self.url_base = base_url
        self.username = username
        self.token = token
        self.environment = self._get_environment(base_url)
        self._build_session()
        self.workspace = Workspace(self)

    def _get_environment(self, url: str) -> str:
        """Get the environment from the base URL.

        Returns:
            str: The environment
        """
        env = urllib.parse.urlparse(url).netloc.split(".")[0]
        logger.debug(f"Environment: {env}")
        if env == "eodatahub":  # prod environment doesn't have a subdomain
            return consts.Environment.PRODUCTION.value
        if env not in set(e.value for e in consts.Environment):
            raise ValueError(f"Invalid environment: {env}")
        return env

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
        headers: Optional[Headers] = None,
        params: Optional[Params] = None,
        data: Optional[Any] = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> requests.Response:
        """Make a raw request.

        Args:
            method (RequestMethod): HTTP method to use
            url (str): Target URL
            headers (Optional[Headers], optional): Headers to send with the request.
                Defaults to None.
            params (Optional[Params], optional): Query parameters to send with the
                request. Defaults to None.
            data (Optional[Any], optional): Raw data to send with the request. Data is
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
        headers: Optional[Headers] = None,
        params: Optional[Params] = None,
        data: Optional[Any] = None,
        encode: Callable[[Any], tuple[str, Any]] = _encode_json,
    ) -> tuple[Headers, Any]:
        """Make a request and return the headers and deserialized JSON data. Input data
        can be anything, not just JSON, providing an `encode` function is supplied. Use
        when expecting JSON data in the response.

        Args:
            method (RequestMethod): HTTP method to use
            url (str): Target URL
            headers (Optional[Headers], optional): Headers to send with the request.
                Defaults to None.
            params (Optional[Params], optional): Query parameters to send with the
                request. Defaults to None.
            data (Optional[Any], optional): Raw data to send with the request. Data is
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
        data = {
            "links": [
                {
                    "rel": "self",
                    "href": (
                        f"{self.url_base}/api/catalogue/stac/catalogs/user/catalogs/"
                        f"{self.username}"
                    ),
                }
            ]
        }
        return Ades(self, Headers(), data)
