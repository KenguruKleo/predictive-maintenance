"""
Incident ID generator — INC-YYYY-NNNN format.

Queries the Cosmos `incidents` container for the highest existing ID in the
current year, then increments. Not perfectly atomic (race condition possible
under concurrent load), but acceptable for hackathon scale.

For production: replace with Cosmos PATCH atomic increment on a counter document.
"""

from datetime import datetime, timezone

from shared.cosmos_client import get_container


def generate_incident_id() -> str:
    """Return next available INC-{YYYY}-{NNNN} id."""
    year = datetime.now(timezone.utc).year
    prefix = f"INC-{year}-"

    container = get_container("incidents")

    query = (
        "SELECT VALUE c.id FROM c "
        f"WHERE STARTSWITH(c.id, '{prefix}') "
        "ORDER BY c.id DESC OFFSET 0 LIMIT 1"
    )

    results = list(container.query_items(query=query, enable_cross_partition_query=True))

    if not results:
        next_num = 1
    else:
        last_id: str = results[0]
        try:
            last_num = int(last_id.replace(prefix, ""))
            next_num = last_num + 1
        except ValueError:
            next_num = 1

    return f"{prefix}{next_num:04d}"
