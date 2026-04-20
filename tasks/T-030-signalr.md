# T-030 · Azure SignalR — Real-Time Notifications

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE  
**Блокує:** T-033 (real-time UX)  
**Залежить від:** T-031 (backend API)

---

## Мета

Azure SignalR Service для real-time push notifications до React UI: оператор бачить новий incident без refresh, header bell показує unread count, а browser/system alerts працюють як progressive enhancement після дозволу користувача.

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
- "incident_pending_approval"  payload: { notification_id, incident_id, equipment_id, title, risk_level, created_at }
- "incident_status_changed"    payload: { incident_id, old_status, new_status, timestamp }
- "agent_step_completed"       payload: { incident_id, step, result_summary }
- "incident_escalated"         payload: { notification_id, incident_id, escalated_to, reason }
```

---

## Endpoints у backend

```
GET /api/negotiate       → returns { url, accessToken } for React client
POST /api/notify         → internal (called by Durable activities, not public)
GET /api/notifications   → unread notification dropdown feed for current caller
GET /api/notifications/summary → unread count + incident IDs for sidebar highlight
POST /api/incidents/{id}/notifications/read → mark all visible incident notifications as read
```

---

## Notification UX contract

- SignalR remains the live invalidation/push channel; Cosmos `notifications` is the source of truth for unread/read state.
- Header bell dropdown reads unread items from `GET /api/notifications?status=unread`.
- Sidebar highlighting is driven by `GET /api/notifications/summary` unread incident IDs.
- Opening `/incidents/{id}` alone does not clear unread state anymore; acknowledgment happens only on explicit user interaction from the bell dropdown or the left active-incident rail.
- Browser/system notifications are optional enhancement only: request permission from a user gesture, then show alerts only when the tab is hidden or unfocused.

## Progress (20 квітня 2026)

- [x] Notification documents now persist read-state fields (`isRead`, `readAt`, `readBy`) in Cosmos
- [x] SignalR approval payloads now include `notification_id` and `title` for frontend reconciliation / browser alerts
- [x] Backend unread APIs implemented for feed, summary, and incident-level mark-read
- [x] Frontend hook invalidates notification queries on live SignalR events
- [x] Browser alert opt-in added as progressive enhancement from the notification bell dropdown
- [x] Live notification scope was finalized around actionable / awareness states only: `incident_created`, `incident_pending_approval`, and `incident_escalated` are surfaced, while terminal or self-initiated decision outcomes (`approved`, `rejected`, `more_info`) are intentionally not bell notifications
- [x] SignalR delivery reliability was hardened for the live app: authenticated connections now register into role groups via `POST /api/signalr/register`, registration retries after MSAL auth becomes ready, and notification feed queries recover on focus/reconnect after early auth timing failures
- [x] Bell UX polish shipped: unread feed is deduplicated by incident, click-through marks items read optimistically, and rejected / approved read-only decision summaries no longer hide operator comments
- [x] Left-rail acknowledgment UX was refined: unread incidents keep a stronger visible attention state until the user explicitly clicks the bell item or the incident itself in the active rail, even if that incident was already open when the update arrived

## Remaining non-blocking follow-up

- Manual secure-context popup smoke can be exercised during demo prep in [T-002](./T-002-final-video.md); it is not blocking implementation closure for T-030

## Live hotfix note (20 квітня 2026)

- Multi-user bell visibility bug was fixed in production after investigating `INC-2026-0025`: backend unread state is now caller-scoped, notification visibility uses the full caller role set instead of only `primary role`, and the old operator fallback assignee `ivan.petrenko` was removed from new approval notifications/tasks/incidents.
- Existing active Cosmos records polluted by that demo assignee were backfilled so already-open pending operator incidents recover notification visibility without waiting for a fresh re-ingest.

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
- [x] Header bell shows unread count and unread dropdown items from backend notification feed
- [x] Sidebar highlights incidents with unread notifications
- [x] Explicit bell-item click or active-rail incident click marks the related incident notifications as read
- [x] Notification center scope is aligned to the final UX contract: actionable / awareness events are pushed live, while terminal or self-originated decision outcomes are intentionally suppressed from the bell feed
- [x] Browser/system notifications are implemented as optional enhancement behind explicit user permission; final demo-time popup smoke remains tracked separately outside this implementation task
