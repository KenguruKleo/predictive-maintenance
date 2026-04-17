# T-020 · Cosmos DB — схема + provisioning

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** � IN PROGRESS  
**Блокує:** T-021, T-023, T-024, T-025, T-028, T-031  
**Залежить від:** нічого (перша задача)

> **Що зроблено (Bicep):** `cosmos-sentinel-intel-dev-erzrpo` задеплоєно. 5 containers: `incidents` (`/equipmentId`), `equipment` (`/id`), `batches` (`/equipmentId`), `capa-plans` (`/incidentId`), `approval-tasks` (`/incidentId`).  
> **Що залишилось:** `backend/cosmos_client.py`, `scripts/seed_cosmos.py`.

---

## Мета

Створити і налаштувати Azure Cosmos DB з 5 collections та seed script для mock даних.

---

## Collections

| Collection | Partition Key | Опис |
|---|---|---|
| `incidents` | `/equipment_id` | Основні incident документи + AI analysis + workflow state |
| `incident_events` | `/incident_id` | Audit log кожної події (event sourcing) |
| `equipment` | `/id` | Mock CMMS equipment master data |
| `batches` | `/equipment_id` | Mock MES batch records |
| `templates` | `/type` | Work order + audit entry templates |

## Indexes (Cosmos DB Composite + Range)

```python
# incidents
- partition: equipment_id
- range: status, created_at, severity
- composite: [status + created_at]

# incident_events  
- partition: incident_id
- range: timestamp

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
- [x] 5 containers в Azure: incidents, equipment, batches, capa-plans, approval-tasks
- [ ] `backend/cosmos_client.py` повертає container reference через Managed Identity (або key для local)
- [ ] `scripts/seed_cosmos.py` запускається без помилок (`python scripts/seed_cosmos.py`)
- [ ] 5 collections заповнені mock даними (T-021)
