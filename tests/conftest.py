import os
import time
from typing import Generator

import dotenv
import pytest
import requests


@pytest.fixture(scope="session")
def api_token() -> Generator[str, None, None]:
    dotenv.load_dotenv()
    username = os.getenv("EODH_USERNAME")
    password = os.getenv("EODH_PASSWORD")

    if not password:
        yield "token"
        return

    base_url = "https://staging.eodatahub.org.uk"

    keycloak_realm = os.getenv("EODH_KEYCLOAK_REALM")
    client_id = os.getenv("EODH_CLIENT_ID")

    token_url = (
        f"{base_url}/keycloak/realms/{keycloak_realm}/protocol/openid-connect/token"
    )
    data = {
        "client_id": client_id,
        "username": username,
        "password": password,
        "grant_type": "password",
        "scope": "workspaces",
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    token_data = response.json()
    access_token = token_data.get("access_token")

    token_url = f"{base_url}/api/workspaces/{username}/me/tokens"

    response = requests.post(
        token_url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": f"pyeodh-test-token-{int(time.time())}"},
    )
    response.raise_for_status()

    token = response.json().get("token")
    token_id = response.json().get("id")
    yield token

    token_url = f"{base_url}/api/workspaces/{username}/me/tokens/{token_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.delete(token_url, headers=headers)
    response.raise_for_status()


@pytest.fixture(scope="session")
def username() -> str:
    dotenv.load_dotenv()
    return os.getenv("EODH_USERNAME", "oxidian-test")
