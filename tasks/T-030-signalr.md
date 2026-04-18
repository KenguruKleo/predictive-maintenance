# T-030 · Azure SignalR — Real-Time Notifications

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE  
**Блокує:** T-033 (real-time UX)  
**Залежить від:** T-031 (backend API)

---

## Мета

Azure SignalR Service для real-time push notifications до React UI (оператор бачить новий incident без refresh).

---

## Hub та Events

> Детальний контракт визначено в [§8.12 архітектури](../02-architecture.md#812-azure-signalr--контракт).

```
Hub name: deviationHub  (змінено з "sentinel")

Groups (підписки):
- role:operator      → incident_pending_approval, incident_updated
- role:qa-manager    → incident_escalated, incident_pending_approval
- incident:{id}      → incident_status_changed, agent_step_completed

Events (server → client):
- "incident_pending_approval"  payload: { incident_id, equipment_id, risk_level, created_at }
- "incident_status_changed"    payload: { incident_id, old_status, new_status, timestamp }
- "agent_step_completed"       payload: { incident_id, step, result_summary }
- "incident_escalated"         payload: { incident_id, escalated_to, reason }
```

---

## Endpoints у backend

```
GET /api/negotiate       → returns { url, accessToken } for React client
POST /api/notify         → internal (called by Durable activities, not public)
```

---

## negotiate Function

```python
# backend/triggers/http_signalr.py
@app.route(route="negotiate", methods=["GET", "POST"])
@app.generic_input_binding(arg_name="connectionInfo", type="signalRConnectionInfo",
    hub_name="deviationHub", connection="AZURE_SIGNALR_CONNECTION_STRING")
def negotiate(req, connectionInfo):
    # Add userId from JWT token claim (for group assignment)
    user = get_current_user(req)
    return func.HttpResponse(connectionInfo)
```

## notify_signalr() helper

```python
# backend/signalr_client.py
async def notify_signalr(hub: str, event: str, payload: dict, target_role: str = None):
    """Send SignalR message. target_role filters by user group if provided."""
    ...
```

---

## React client (useSignalR.ts)

```typescript
import * as signalR from "@microsoft/signalr";

export function useSignalR(onIncidentUpdate: (id: string, status: string) => void) {
  useEffect(() => {
    const connection = new signalR.HubConnectionBuilder()
      .withUrl("/api/signalr", { accessTokenFactory: () => getAccessToken() })
      .withAutomaticReconnect()
      .build();

    connection.on("incident_pending_approval", ({ incident_id, equipment_id, risk_level }) => {
      onIncidentUpdate(incident_id, "pending_approval");
      toast(`Новий інцидент потребує рішення: ${incident_id} [ризик: ${risk_level}]`);
    });
    connection.on("incident_status_changed", ({ incident_id, new_status }) => {
      onIncidentUpdate(incident_id, new_status);
    });

    connection.on("incident_created", ({ incident_id, equipment_id, severity }) => {
      toast.warning(`New deviation: ${equipment_id} — ${severity.toUpperCase()}`);
      onIncidentUpdate(incident_id, "pending_approval");
    });

    connection.start();
    return () => connection.stop();
  }, []);
}
```

---

## Definition of Done

- [x] SignalR service provisioned via `infra/modules/signalr.bicep` (додати до `infra/main.bicep`)
- [x] `GET /api/negotiate` returns valid SignalR connection info (hub: `deviationHub`)
- [x] React `useSignalR` hook connects successfully
- [x] Toast notification appears in UI when new incident created (test: POST /api/alerts)
- [x] Incident list updates automatically when status changes (no page refresh needed)
