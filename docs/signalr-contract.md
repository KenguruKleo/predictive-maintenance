# Azure SignalR Contract — Sentinel Intelligence

> Full hub specification for `deviationHub`. Source of truth for frontend (`useSignalR`) and backend (SignalR output bindings in Azure Functions).
>
> Linked from: [02-architecture.md §8.12](../02-architecture.md)

**Hub name:** `deviationHub`  
**Negotiate endpoint:** `GET /api/negotiate` (Azure Functions HTTP trigger with SignalR input binding)  
**Auth:** Bearer token (Entra ID) → SignalR Groups per user role

## Groups (підписки)

| Group | Хто підписується | Які events отримує |
|---|---|---|
| `role:operator` | Всі operator-role users | `incident_pending_approval`, `incident_updated` |
| `role:qa-manager` | QA Manager role | `incident_escalated`, `incident_pending_approval` |
| `incident:{id}` | Будь-хто хто відкрив деталі incident | `incident_status_changed`, `agent_step_completed` |

## Events (server → client)

| Event name | Payload | Коли |
|---|---|---|
| `incident_pending_approval` | `{ incident_id, equipment_id, risk_level, created_at }` | Після `notify_operator` activity |
| `incident_status_changed` | `{ incident_id, old_status, new_status, timestamp }` | При кожній зміні status в Cosmos |
| `agent_step_completed` | `{ incident_id, step, result_summary }` | Після completion кожної Durable activity |
| `incident_escalated` | `{ incident_id, escalated_to, reason }` | Після 24h timer → QA Manager |

## Negotiation flow

```
React UI → GET /api/negotiate (with Bearer token)
        ← { url: "https://...signalr.../client/", accessToken: "..." }
React UI → connects to SignalR hub with accessToken
        → joins group `role:{userRole}` + `incident:{currentIncidentId}`
```

## Related

- Frontend: `frontend/src/hooks/useSignalR.ts`
- Backend: `backend/triggers/http_negotiate.py`, `backend/activities/notify_operator.py`
- Task: [T-030 SignalR](../tasks/T-030-signalr.md)
