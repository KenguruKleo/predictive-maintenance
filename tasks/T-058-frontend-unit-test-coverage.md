# T-058 · Frontend Unit Test Coverage

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

> **Priority:** 🟢 LOW — does not block finals, but reduces frontend regression risk after demo scope stabilizes
> **Source:** Frontend test coverage audit (April 28, 2026)
> **Status:** ✅ DONE

---

## Goal

Add a minimal but meaningful frontend unit/integration test layer for the React app.

Today the frontend has smoke-level E2E coverage only. That is useful for route-level confidence, but it does not protect the logic-heavy hooks, auth/role normalization, optimistic cache updates, or small UI interaction paths where regressions are most likely.

---

## Progress update — April 28, 2026

### Completed in the first implementation slice

- Added unit-test scripts to `frontend/package.json`
- Added `vitest` config with `jsdom` environment and isolated setup
- Wired the frontend unit-test baseline into GitHub Actions pull-request CI
- Added initial tests for:
  - `authRuntime`
  - `analyticsUtils`
  - `analysis` utilities
  - `useRoleGuard`
  - `CommandPalette`
  - optimistic incident mutation/cache flow in `useIncidents`
  - optimistic notification mutation/cache flow in `useNotifications`
- Current local baseline: 7 test files, 24 passing tests

### Follow-up slice

- Add `App` / auth-flow tests and API client interceptor tests
- Add at least one more interaction-heavy UI surface (`ApprovalPanel` or `NotificationCenter`)
- Add deeper backend test coverage alongside the existing Python test job

---

## Current state

### What exists now

- `frontend/tests/e2e/smoke.spec.ts` covers 4 happy-path browser flows:
  - operator dashboard loads in e2e auth mode
  - IT admin can open templates
  - IT admin can navigate from incident detail to telemetry
  - QA manager dashboard loads recent decisions
- `frontend` now has a unit-test baseline with `vitest` + `jsdom` + React Testing Library
- Current implemented unit coverage includes:
  - auth/runtime normalization helpers
  - analytics and analysis pure utilities
  - role guard behavior
  - command palette interaction
  - optimistic React Query updates for incidents and notifications

### What is still missing

- No focused tests yet for `App.tsx`, `useAuth.ts`, or `api/client.ts`
- No focused tests yet for `ApprovalPanel` or `NotificationCenter`
- No focused tests yet for `useSignalR.ts`

Frontend confidence is now better than smoke-only, but the auth flow and live-update surfaces still carry regression risk.

---

## Highest-value gaps to cover

### 1. Auth and role normalization

**Files:**

- `frontend/src/App.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/hooks/useRoleGuard.ts`
- `frontend/src/authRuntime.ts`
- `frontend/src/api/client.ts`

**Why this matters:**

This area decides whether the user sees login, loader, or app shell, and how Entra / e2e roles are interpreted. Regressions here break the entire app or silently grant/deny the wrong UI surfaces.

**Tests to add:**

- role normalization for `Operator`, `QAManager`, `ITAdmin`, aliases, and invalid values
- JWT payload decoding fallback behavior
- `App` behavior for auth loading vs login screen vs routed app
- axios interceptor behavior for e2e mock headers and bearer token injection
- redirect-on-interaction-required behavior without duplicate redirect loops

### 2. React Query optimistic update logic

**Files:**

- `frontend/src/hooks/useIncidents.ts`
- `frontend/src/hooks/useNotifications.ts`

**Why this matters:**

These hooks contain the most regression-prone frontend state logic in the app: optimistic decisions, unread counters, incident cache syncing, and rollback after mutation errors.

**Tests to add:**

- optimistic incident decision status mapping for `approved`, `rejected`, `more_info`
- optimistic patching of incident detail and incident list data
- rollback to previous cache state on mutation error
- notification summary and list cache updates when an incident is marked read
- `unread` vs `all` filter behavior in notification cache transforms

### 3. Pure utilities with business formatting logic

**Files:**

- `frontend/src/components/IncidentAnalytics/analyticsUtils.ts`
- `frontend/src/utils/analysis.ts`

**Why this matters:**

These are cheap to test and carry real product logic: grouping incidents by period/status, week/day labels, and parsing/normalizing AI output into operator-visible content.

**Tests to add:**

- period grouping by day and week
- invalid/missing date handling
- stable status labels and period labels
- analysis/recommendation parsing edge cases and empty-state handling

### 4. Interaction-heavy UI components with local logic

**Files:**

- `frontend/src/components/Layout/CommandPalette.tsx`
- `frontend/src/components/Layout/NotificationCenter.tsx`
- `frontend/src/components/Approval/ApprovalPanel.tsx`

**Why this matters:**

These components mix role-based rendering, keyboard handling, dynamic filtering, and stateful UX. They are too stateful to leave entirely to manual smoke verification, but still small enough for focused tests.

**Tests to add:**

- keyboard navigation and filtering in command palette
- role-based visibility of navigation commands
- notification center unread state rendering and mark-as-read actions
- approval panel button state / warning state for pending vs finalized incidents

### 5. Live-update plumbing and browser notification behavior

**Files:**

- `frontend/src/hooks/useSignalR.ts`

**Why this matters:**

This hook wires together SignalR lifecycle, browser notifications, desktop bridge integration, and React Query invalidation. It is operationally important and easy to regress during UI or auth changes.

**Tests to add:**

- permission helper behavior for unsupported / denied / granted cases
- event handlers invalidating the correct query keys
- desktop notification preference over browser notification when Electron bridge exists
- reconnect flow resetting registration and restoring connected state

---

## Recommended implementation order

1. Add test infrastructure: `vitest` + `jsdom` + React Testing Library + `user-event`.
2. Start with pure utilities and auth normalization because they are cheap and stable.
3. Add React Query hook tests for optimistic updates and rollback.
4. Add focused component tests for `CommandPalette` and `ApprovalPanel`.
5. Add targeted hook tests for `useSignalR` with mocked SignalR client and browser notification APIs.

---

## Suggested non-goals

- Do not chase blanket snapshot coverage.
- Do not duplicate Playwright smoke scenarios at unit-test level.
- Do not try to unit-test every presentational component.

Focus on logic-bearing hooks, state transforms, and role-sensitive UI.

---

## Dependencies / related tasks

- Related to [T-032](./T-032-frontend-core.md)
- Related to [T-033](./T-033-frontend-approval.md)
- Related to [T-034](./T-034-frontend-other-roles.md)
- Related to [T-042](./T-042-cicd.md) if unit tests are later added to CI

---

## Definition of Done

- [x] Unit test runner is configured for the frontend workspace
- [x] Frontend test scripts exist separately from Playwright e2e scripts
- [x] Auth / role normalization has focused tests
- [x] Optimistic cache logic in incidents and notifications has focused tests
- [x] At least one interaction-heavy UI surface has React Testing Library coverage
- [x] Tests run locally without requiring Entra login or live Azure services
- [x] The initial unit test suite is wired into CI
