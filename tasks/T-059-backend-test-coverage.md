# T-059 · Backend Test Coverage

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

> **Priority:** 🟢 LOW — does not block finals, but reduces backend regression risk while the demo scope stabilizes
> **Source:** Backend test coverage follow-up (April 28, 2026)
> **Status:** ✅ DONE

---

## Goal

Expand focused backend automated coverage for the Python Functions app and shared helpers.

The repo already has a Python `pytest` suite wired into pull-request CI. The remaining gap is deeper coverage of backend HTTP triggers, auth/access helpers, and workflow utilities where business regressions can still slip through despite the current tests.

---

## Progress update — April 28, 2026

### Completed in the baseline slice

- Confirmed Python `pytest tests/` already runs in GitHub Actions pull-request CI
- Created a dedicated backend testing task and added it to the live plan
- Added the first backend coverage slice around `http_incidents`
- Added focused auth helper tests for `backend/utils/auth.py`
- Added workflow-side watchdog recovery tests for `backend/triggers/timer_watchdog.py`
- Fixed watchdog recovery for orphaned `pending_approval` incidents whose durable instance ended in `Completed`
- Repaired stale backend test drift uncovered while expanding coverage
- Current local backend baseline: `pytest tests/ -q` → `107 passed`

### Remaining in the next slice

- Add more HTTP trigger tests for `http_equipment`, `http_templates`, or `http_documents`
- Add focused execution-path tests for `backend/activities/run_execution_agent.py`

---

## Current state

### What exists now

- Root-level Python tests already cover several backend surfaces:
  - decision endpoint behavior
  - notification API normalization
  - stats helpers
  - SignalR registration
  - orchestrator role routing and evidence/citation helpers
  - incident API access and response shaping
  - auth and caller identity helpers
  - watchdog recovery / requeue behavior
- Pull-request CI already runs `pytest tests/ -v --tb=short`

### What is still missing

- Limited direct coverage of execution-agent backend flows
- Several CRUD/document endpoints still rely mostly on smoke validation or manual checks

Backend CI exists, but the regression net is still uneven across high-risk backend modules.

---

## Highest-value gaps to cover

### 1. Incident API access and response shaping

**Files:**

- `backend/triggers/http_incidents.py`

**Why this matters:**

This trigger governs who can see which incidents and what payload shape the frontend receives. Regressions here can silently expose the wrong data or break list/detail rendering for role-based views.

**Tests to add:**

- operator vs manager access to incident detail
- list endpoint response slimming and total count behavior
- invalid pagination handling
- 404 and 403 behaviors for incident detail access

### 2. Auth and caller identity helpers

**Files:**

- `backend/utils/auth.py`

**Why this matters:**

These helpers are the backend trust boundary for role extraction and caller scoping. Regressions here break RBAC and role-targeted filtering across multiple endpoints.

**Tests to add:**

- local mock auth role parsing
- caller identity extraction precedence
- primary role selection
- auth error behavior for missing or invalid roles

### 3. Workflow recovery and execution helpers

**Files:**

- `backend/triggers/timer_watchdog.py`
- `backend/activities/run_execution_agent.py`

**Why this matters:**

These modules affect stuck-incident recovery and post-approval execution, both of which are important for the live demo and production-readiness story.

**Tests to add:**

- watchdog filtering / requeue decisions
- execution-agent result normalization
- error-path handling and audit-safe fallbacks

---

## Recommended implementation order

1. Start with `http_incidents` endpoint tests because they are high-value and cheap to isolate.
2. Add pure/helper tests for `utils/auth.py`.
3. Expand into workflow-side logic (`timer_watchdog`, `run_execution_agent`).
4. Add trigger-level tests for remaining CRUD/document endpoints as needed.

---

## Definition of Done

- [x] Python backend tests are part of pull-request CI
- [x] Incident API access and response shaping has focused tests
- [x] Auth / caller identity helpers have focused tests
- [x] At least one workflow-side backend module has focused tests
- [x] Backend tests run locally without Azure login or live cloud dependencies
- [x] Remaining uncovered backend slices are explicitly documented as next steps
