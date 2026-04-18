"""Helpers for updating incident documents in the Cosmos incidents container."""

from azure.cosmos.exceptions import CosmosResourceNotFoundError


def get_incident_by_id(db, incident_id: str) -> dict:
    """Fetch an incident by id using a cross-partition query."""
    incidents = db.get_container_client("incidents")
    items = list(
        incidents.query_items(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": incident_id}],
            enable_cross_partition_query=True,
        )
    )
    if not items:
        raise CosmosResourceNotFoundError(message=f"Incident '{incident_id}' not found")
    return items[0]


def patch_incident_by_id(db, incident_id: str, patch_operations: list[dict]) -> dict:
    """Patch an incident after resolving its real partition key.

    Older live incidents created before the ingestion normalisation do not have
    the `/equipmentId` partition key field, so Cosmos stores them in the
    undefined partition represented by `{}` in the Python SDK.
    """
    incident = get_incident_by_id(db, incident_id)
    partition_key = incident.get("equipmentId", {})
    incidents = db.get_container_client("incidents")
    return incidents.patch_item(
        item=incident_id,
        partition_key=partition_key,
        patch_operations=patch_operations,
    )
