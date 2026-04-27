# T-055 · AI Pipeline Status Contract Hardening (post-hackathon)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

> **Priority:** 🟡 MEDIUM — important for a correct live UX, but does not block the demo thanks to a temporary frontend workaround
> **Source:** Demo debugging, April 23, 2026
> **Status:** 🔜 TODO

---

## Context

During demo-debugging, a desynchronization was detected between the backend incident statuses, SignalR events and the frontend AI Pipeline widget.

**What's available now:**
- `http_ingest_alert.py` creates an incident with status `open` and sends only SignalR event `incident_created`;
- Durable orchestrator starts `run_foundry_agents`, but does not transfer the incident to `ingested` or `analyzing`;
- after completing the Foundry run, the backend immediately sets `pending_approval` or `escalated`;
- frontend widget on Operations Dashboard counts only `ingested`, `analyzing`, `awaiting_agents`.

Consequence: During the **first real AI run**, the agent is running, but the AI ​​Pipeline widget may remain empty. For the hackathon demo, this is temporarily bypassed by frontend mapping `open -> first pipeline bucket`, but the correct fix should be at the backend/status-contract level.

---

## Goal

Make the backend the only source of truth for AI pipeline states and live updates, so that the frontend shows the real lifecycle of the incident without workarounds.

Target status contract:

1. `open` — the incident has just been created, not yet started by Durable/Service Bus;
2. `ingested` — Service Bus message accepted, Durable instance started;
3. `analyzing` — `run_foundry_agents` is actually executed;
4. `awaiting_agents` — the operator requested `more_info`, the incident is queued for a repeat AI run;
5. `pending_approval` / `escalated` — AI has finished preparing the decision package;
6. `in_progress` / `completed` / `rejected` — execution / terminal flow.

---

## What to change

### 1. Normalize statuses in the backend

#### `backend/triggers/service_bus_trigger.py`

- After successful `start_new(...)` update incident `status = "ingested"`;
- record `workflow_state.current_step = "ingested"` or a similar early step;
- add update timestamp;
- send SignalR event `incident_status_changed` from `new_status: "ingested"`.

#### `backend/orchestrators/incident_orchestrator.py`

- Before `run_foundry_agents`, call activity/helper, which sets `status = "analyzing"`;
- with each repeated `more_info` run, go to `analyzing` again before starting the activity;
- do not leave the incident in `open` if Durable is already actually processing the payload.

#### `backend/triggers/http_decision.py`

- `more_info` should transfer the incident to `awaiting_agents` as an explicit pre-run state;
- after starting the rerun orchestrator/activity, the incident should go from `awaiting_agents` to `analyzing`.

### 2. Really send live events that are already expected by the frontend

#### `backend/shared/signalr_client.py`

Add small helpers for status/event pushes so as not to duplicate the payload format throughout the code:

```python
notify_incident_status_changed(
    incident_id="INC-2026-0049",
    new_status="analyzing",
    previous_status="ingested",
)
```

#### Using helper

- `service_bus_trigger.py` → `incident_status_changed(ingested)`
- status transition helper/activity before AI run → `incident_status_changed(analyzing)`
- `http_decision.py` on `more_info` → `incident_status_changed(awaiting_agents)`
- `notify_operator.py` → or `incident_status_changed(pending_approval|escalated)`, or leave the existing domain-specific event + add a general status event too

### 3. Align frontend and backend contract

#### `frontend/src/pages/OperationsDashboard.tsx`

- After the backend fix, remove the demo workaround `open -> first pipeline bucket`;
- AI Pipeline widget should count only real pipeline statuses from the backend again;
- optionally rename the first bucket back from `Received` to `Ingested` if the contract is stable.

#### `frontend/src/hooks/useSignalR.ts`

- Check that `incident_status_changed` and `agent_step_completed` are either actually used, or delete redundant listeners;
- if `agent_step_completed` is left, the backend should actually send it at least after completing major steps (eg `run_foundry_agents`, `run_execution_agent`).

### 4. Remove legacy drift

#### `backend/triggers/timer_watchdog.py`

- View legacy statuses `queued` and `analyzing_agents`;
- reduce the watchdog to the current set of statuses;
- make sure that recovery logic does not depend on old names.

---

## Definition of Done

- [ ] The first AI run no longer stays in `open` after starting the Durable orchestrator
- [ ] `service_bus_trigger.py` sets `ingested` and sends `incident_status_changed`
- [ ] Before each `run_foundry_agents` incident goes to `analyzing`
- [ ] `more_info` flow uses `awaiting_agents -> analyzing -> pending_approval`
- [ ] Frontend AI Pipeline widget no longer needs `open` workaround
- [ ] `incident_status_changed` actually comes to the frontend during pipeline transitions
- [ ] Watchdog no longer relies on deprecated `queued` / `analyzing_agents`
- [ ] Smoke test: during an active Foundry run, the AI ​​Pipeline widget shows at least 1 in-flight incident

---

## Smoke script after implementation

1. Send a new alert via `POST /api/alerts`.
2. Make sure that the incident goes to `open -> ingested -> analyzing`.
3. During operation, the Foundry widget on the Operations Dashboard shows an incident in the pipeline.
4. After the AI ​​run completes, the incident moves to `pending_approval` and disappears from the AI ​​in-flight bucket.
5. Press `More info` and check `awaiting_agents -> analyzing -> pending_approval`.
