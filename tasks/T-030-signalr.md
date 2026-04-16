# T-030 · Azure SignalR — Real-Time Notifications

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
**Блокує:** T-033 (real-time UX)  
**Залежить від:** T-031 (backend API)

---

## Мета

Azure SignalR Service для real-time push notifications до React UI (оператор бачить новий incident без refresh).

---

## Hub та Events

```
Hub name: sentinel

Events:
- "incident_created"    payload: { incident_id, equipment_id, severity }
- "incident_updated"    payload: { incident_id, new_status }
- "escalation"          payload: { incident_id, message, assigned_to_role }
```

---

## Endpoints у backend

```
GET /api/signalr/negotiate    → returns { url, accessToken } for React client
POST /api/signalr/notify      → internal (called by activities, not public)
```

---

## negotiate Function

```python
# backend/triggers/http_signalr.py
@app.route(route="signalr/negotiate", methods=["GET", "POST"])
@app.generic_input_binding(arg_name="connectionInfo", type="signalRConnectionInfo",
    hub_name="sentinel", connection="AZURE_SIGNALR_CONNECTION_STRING")
def negotiate(req, connectionInfo):
    # Add userId from JWT token claim
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

    connection.on("incident_updated", ({ incident_id, new_status }) => {
      onIncidentUpdate(incident_id, new_status);
      toast(`Incident ${incident_id} updated: ${new_status}`);
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

- [ ] SignalR service provisioned (Bicep або portal)
- [ ] `/api/signalr/negotiate` returns valid connection info
- [ ] React `useSignalR` hook connects successfully
- [ ] Toast notification appears in UI when new incident created (test: POST /api/alerts)
- [ ] Incident list updates automatically when status changes (no page refresh needed)
