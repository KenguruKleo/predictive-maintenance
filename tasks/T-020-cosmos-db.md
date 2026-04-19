# T-020 · Cosmos DB — схема + provisioning

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** ✅ DONE  
**Блокує:** T-021, T-023, T-024, T-025, T-028, T-031  
**Залежить від:** нічого (перша задача)

> **Завершено 17 квітня 2026:** `cosmos-sentinel-intel-dev-erzrpo` задеплоєно. 8 containers: `incidents` (`/equipmentId`), `incident_events` (`/incidentId`), `notifications` (`/incidentId`), `equipment` (`/id`), `batches` (`/equipmentId`), `capa-plans` (`/incidentId`), `approval-tasks` (`/incidentId`), `templates` (`/id`). 55 items seeded через `scripts/seed_cosmos.py`.

---

## Мета

Створити і налаштувати Azure Cosmos DB з 8 containers та seed script для mock даних.

---

## Collections

| Collection | Partition Key | Опис |
|---|---|---|
| `incidents` | `/equipmentId` | Основні incident документи + AI analysis + workflow state |
| `incident_events` | `/incidentId` | Audit log кожної події (event sourcing) |
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

## Файли для створення

```
backend/
  cosmos_client.py        # DefaultAzureCredential wrapper + get_container()
  
scripts/
  seed_cosmos.py          # Reads data/mock/*.json → upserts to Cosmos DB
  
infra/
  modules/cosmos-db.bicep # Bicep module для Cosmos DB account + database + containers
```

## Definition of Done

- [x] `infra/modules/cosmos.bicep` валідується і задеплоєно
- [x] 8 containers в Azure: incidents, incident_events, notifications, equipment, batches, capa-plans, approval-tasks, templates
- [ ] `backend/cosmos_client.py` повертає container reference через Managed Identity (або key для local)
- [x] `scripts/seed_cosmos.py` запускається без помилок (`python scripts/seed_cosmos.py`)
- [x] Mock дані засіяні у задеплоєні containers (T-021) — 55 items
