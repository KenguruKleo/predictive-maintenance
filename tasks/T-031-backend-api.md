# T-031 · Backend API Functions (Incidents CRUD + Templates + Equipment)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-032 (React frontend needs these endpoints)  
**Залежить від:** T-020 (Cosmos DB), T-035 (RBAC для role-filtering)

---

## Мета

REST API endpoints для React frontend: читання incidents, audit events, equipment, batches, templates.

---

## Endpoints

| Method | Route | Auth Role | Description |
|---|---|---|---|
| `GET` | `/api/incidents` | all | List incidents (role-filtered: operator sees own, manager sees all) |
| `GET` | `/api/incidents/{id}` | all | Get incident detail with AI analysis |
| `GET` | `/api/incidents/{id}/events` | all | Get audit event timeline |
| `GET` | `/api/equipment/{id}` | all | Get equipment master data |
| `GET` | `/api/batches/current/{equipment_id}` | all | Get active batch for equipment |
| `GET` | `/api/templates` | it-admin | List all templates |
| `GET` | `/api/templates/{id}` | it-admin | Get template |
| `PUT` | `/api/templates/{id}` | it-admin | Update template |
| `GET` | `/api/stats/summary` | qa-manager, it-admin | Incident stats for dashboard |

---

## Response shapes

### GET /api/incidents
```json
{
  "items": [
    {
      "id": "INC-2026-0001",
      "equipment_id": "GR-204",
      "equipment_name": "Granulator GR-204",
      "title": "...",
      "severity": "major",
      "status": "pending_approval",
      "risk_level": "medium",
      "confidence": 0.84,
      "reported_at": "2026-04-16T08:42:00Z",
      "assigned_to": "ivan.petrenko"
    }
  ],
  "total": 5,
  "page": 1
}
```

### GET /api/incidents/{id}
Full incident document including `ai_analysis` and `workflow_state`.

---

## Role-based filtering

```python
def filter_incidents_by_role(user: User, query_filter: str) -> str:
    if user.role == "operator":
        return f"{query_filter} AND c.workflow_state.assigned_to = '{user.id}'"
    elif user.role == "maintenance-tech":
        return f"{query_filter} AND c.status IN ('approved', 'closed')"
    elif user.role == "auditor":
        return query_filter  # all, read-only
    else:  # qa-manager, it-admin
        return query_filter  # all
```

---

## Files

```
backend/
  triggers/
    http_incidents.py       # GET /api/incidents, GET /api/incidents/{id}
    http_incident_events.py # GET /api/incidents/{id}/events
    http_equipment.py       # GET /api/equipment/{id}
    http_batches.py         # GET /api/batches/current/{equipment_id}
    http_templates.py       # GET/PUT /api/templates, /api/templates/{id}
    http_stats.py           # GET /api/stats/summary
  cosmos_client.py          # Shared Cosmos DB client
```

## Definition of Done

- [ ] All 9 endpoints return correct data for seeded mock incidents
- [ ] `GET /api/incidents` role-filtering works: operator sees only assigned incidents
- [ ] `GET /api/incidents/{id}/events` returns chronological event timeline
- [ ] `PUT /api/templates/{id}` validates schema before save (it-admin only)
- [ ] 403 returned for unauthorized role access
- [ ] Response time < 500ms for all GET endpoints (Cosmos point reads)
