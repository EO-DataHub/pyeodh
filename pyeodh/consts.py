from enum import Enum


class Environment(Enum):
    PRODUCTION = "prod"
    STAGING = "staging"
    TEST = "test"


API_BASE_URL = f"https://{Environment.STAGING.value}.eodatahub.org.uk"
S3_BASE_URL_TEMPLATE = (
    "https://{workspace_name}.{environment}.eodatahub-workspaces.org.uk/files/"
    "workspaces-eodhp-{environment}"
)
PAGINATION_LIMIT = 10
