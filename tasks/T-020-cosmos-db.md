# T-020 · Cosmos DB — Schema + Provisioning

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL  
**Status:** ✅ DONE  
**Blocks:** T-021, T-023, T-024, T-025, T-028, T-031  
**Depends on:** nothing (first task)

> **Completed on April 17, 2026:** `cosmos-sentinel-intel-dev-erzrpo` deployed. 8 containers: `incidents` (`/equipmentId`), `incident_events` (`/incidentId`), `notifications` (`/incidentId`), `equipment` (`/id`), `batches` (`/equipmentId`), `capa-plans` (`/incidentId`), `approval-tasks` (`/incidentId`), `templates` (`/id`). 55 items seeded via `scripts/seed_cosmos.py`.

---

## Goal

Create and configure Azure Cosmos DB with 8 containers and a seed script for mock data.

---

## Collections

| Collection | Partition Key | Description |
|---|---|---|
| `incidents` | `/equipmentId` | Primary incident documents + AI analysis + workflow state |
| `incident_events` | `/incidentId` | Audit log for each event (event sourcing) |
| `notifications` | `/incidentId` | Notification records for SignalR-driven UX |
| `equipment` | `/id` | Mock CMMS equipment master data |
| `batches` | `/equipmentId` | Mock MES batch records |
| `capa-plans` | `/incidentId` | Document Agent CAPA drafts |
| `approval-tasks` | `/incidentId` | Pending approvals + execution linkage |
| `templates` | `/id` | Work order + audit entry templates |

## Indexes (Cosmos DB Composite + Range)

```python
# incidents
- partition: equipmentId
- range: status, created_at, severity
- composite: [status + created_at]

# incident_events  
- partition: incidentId
- range: timestamp

> Extension: T-043 reuses `incident_events` for agent telemetry with `type = "agent_telemetry"`; no separate collection needed for hackathon MVP.

# equipment
- partition: id (same as id — singleton lookup)

# batches
- partition: equipment_id
- range: status, start_time

# templates
- partition: type
- range: name
```

## Files to Create

```
backend/
  cosmos_client.py        # DefaultAzureCredential wrapper + get_container()
  
scripts/
  seed_cosmos.py          # Reads data/mock/*.json → upserts to Cosmos DB
  
infra/
  modules/cosmos-db.bicep # Bicep module for Cosmos DB account + database + containers
```

## Definition of Done

- [x] `infra/modules/cosmos.bicep` is validated and deployed
- [x] 8 containers in Azure: incidents, incident_events, notifications, equipment, batches, capa-plans, approval-tasks, templates
- [ ] `backend/cosmos_client.py` returns a container reference via Managed Identity (or key for local)
- [x] `scripts/seed_cosmos.py` runs without errors (`python scripts/seed_cosmos.py`)
- [x] Mock data seeded into deployed containers (T-021) — 55 items
