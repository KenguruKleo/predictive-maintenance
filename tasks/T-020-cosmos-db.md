# T-020 · Cosmos DB — схема + provisioning

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-021, T-023, T-024, T-025, T-028, T-031  
**Залежить від:** нічого (перша задача)

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

- [ ] `scripts/seed_cosmos.py` запускається без помилок (`python scripts/seed_cosmos.py`)
- [ ] 5 collections створені, mock дані присутні
- [ ] `backend/cosmos_client.py` повертає container reference через Managed Identity (або key для local)
- [ ] `infra/modules/cosmos-db.bicep` валідується (`az bicep build`)
