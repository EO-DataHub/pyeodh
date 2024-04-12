from __future__ import annotations

from typing import Literal
import requests


class Client:

    def __init__(self) -> None:
        self._build_session()

    def _build_session(
        self,
    ) -> None:
        # TODO Add retry count, setting auth headers etc. here
        self._session = requests.Session()
        self.url_base = "https://api.stac.ceda.ac.uk/"  # TODO create a const module

    def _request_json(
        self,
        method: Literal["GET", "POST", "DELETE", "PUT"],
        url: str,
        params: dict | None = None,
        data: dict | None = None,
    ):
        if not url.startswith("http"):
            url = self.url_base + url
        # TODO construct headers
        headers = {}
        headers["Content-Type"] = "application/json"
        response = self._session.request(
            method, url, headers=headers, params=params, data=data
        )
        # TODO handle errors...
        return response.headers, response.json()
