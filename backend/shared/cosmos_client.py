"""
Cosmos DB client — thin singleton wrapper.

Auth priority:
  1. COSMOS_KEY env var  (local dev, scripts)
  2. DefaultAzureCredential  (Azure Functions Managed Identity)
"""

import os

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

COSMOS_ENDPOINT = os.getenv(
    "COSMOS_ENDPOINT",
    "https://cosmos-sentinel-intel-dev-erzrpo.documents.azure.com:443/",
)
COSMOS_DB = "sentinel-intelligence"

_client: CosmosClient | None = None


def get_cosmos_client() -> CosmosClient:
    global _client
    if _client is None:
        key = os.getenv("COSMOS_KEY")
        if key:
            _client = CosmosClient(COSMOS_ENDPOINT, credential=key)
        else:
            _client = CosmosClient(COSMOS_ENDPOINT, credential=DefaultAzureCredential())
    return _client


def get_container(container_name: str):
    return (
        get_cosmos_client()
        .get_database_client(COSMOS_DB)
        .get_container_client(container_name)
    )
