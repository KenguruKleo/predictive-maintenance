# T-044 · Local Playwright E2E Mode (Dev Auth + Local Backend Proxy)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** 🟡 IN PROGRESS
**Blocks:** stable frontend regression / smoke tests for T-032, T-033, T-034, T-043
**Depends on:** T-032 (frontend shell), T-035 (RBAC), completion of auth-check in T-029 for `POST /api/incidents/{incident_id}/decision`

---

## Goal

Make it possible to run the frontend locally in `Playwright` without interactive Entra login, but at the same time:

- do not open the production/dev backend for anonymous browser access
- do not sew `function key` or `master key` to the browser
- do not replace real data with mocks if the local backend can read the same Azure resources

---

## Current status and conclusion

### What is available now

- frontend strongly depends on `MSAL`:
- `frontend/src/App.tsx` renders `LoginPage` if `useIsAuthenticated() === false`
- `frontend/src/pages/LoginPage.tsx` calls `loginRedirect()`
- `frontend/src/api/client.ts` adds `Authorization: Bearer <token>` via `acquireTokenSilent()`
- backend UI endpoints mostly have `auth_level=ANONYMOUS`, but check JWT/roles themselves via `backend/utils/auth.py`
- `backend/utils/auth.py` already has a local hook:

```python
USE_LOCAL_MOCK_AUTH=true
X-Mock-Role: Operator
```

that is, the local backend already knows how to do without Entra token, but the frontend does not have this mode.

### What doesn't fit

#### 1. `function key` / `master key`

This is not a frontend E2E solution:

- they are required for Azure Functions host/admin or for endpoints with `AuthLevel.FUNCTION`
- most of our UI endpoints do not rely on function-level auth, but do app-level auth in Python code
- it is dangerous to transfer such keys to the browser or Playwright client-side state

#### 2. Locally generated JWT

It also won't work as is, because the backend now only trusts tokens signed by Entra ID JWKS. If we want to sign our tokens locally, we will have to change the trust model of the backend. This is a redundant and risky path for the first iteration.

### The main conclusion

`Playwright` does not require a “secret in the browser”, but **dev-only auth mode**:

- frontend switches to `e2e` mode and does not require MSAL login
- backend accepts mock-role only locally
- real data continues to come through a locally running backend that goes to the same Azure resources

---

## Recommended option (Phase 1)

### Architecture

```text
Playwright
  -> local Vite frontend (auth mode = e2e)
  -> /api/* same-origin requests
  -> Vite proxy
  -> local Azure Functions host (USE_LOCAL_MOCK_AUTH=true)
  -> real Azure data/services (Cosmos, SignalR, Search, etc.)
```

### Why this is the best way

- interactive login in E2E is not required
- no production bypass is required on the deployed backend
- you can test the UI on real data from Azure
- an already existing local auth-hook in the backend is used
- `Playwright` easily raises both frontend and backend through `webServer`

---

## Scope

### 1. Frontend: add auth mode `msal | e2e`

Enter an explicit runtime mode, for example:

```env
VITE_AUTH_MODE=msal
VITE_API_BASE_URL=https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api
```

and for local E2E:

```env
VITE_AUTH_MODE=e2e
VITE_API_BASE_URL=/api
```

In `e2e` mode, the frontend has:

- do not show `LoginPage`
- do not call `loginRedirect()`
- substitute mock principal (`user`, `name`, `roles`) with test state
- allow simple role switching: `operator`, `qa-manager`, `auditor`, `it-admin`

### 2. Frontend API client: transfer mock identity only in `e2e` mode

`frontend/src/api/client.ts` in `e2e` mode should:

- do not call `acquireTokenSilent()`
- add headers like:

```http
X-Mock-Role: Operator
X-Mock-User: ivan.petrenko
```

- work only with relative `/api` base URL in local E2E

This will allow setting the role at the level of a specific browser context/test, and not at the level of the entire dev server process.

### 3. Vite dev proxy: transfer local E2E to same-origin `/api`

Add a proxy to `frontend/vite.config.ts`:

```ts
server: {
  port: 4173,
  strictPort: true,
  proxy: {
    "/api": {
      target: "http://127.0.0.1:7071",
      changeOrigin: true,
    },
  },
}
```

This removes CORS problems and makes the tests more stable.

### 4. Backend: fix local-only mock auth contract

`backend/utils/auth.py` should be modified so that mock auth:

- worked only in local mode / development host
- could not be accidentally enabled in a deployed Function App
- supported not only `X-Mock-Role` but also `X-Mock-User` for audit-friendly flows

Preferred guardrail:

- `USE_LOCAL_MOCK_AUTH=true` is not enough by itself
- additionally check that the process is really started locally (`AZURE_FUNCTIONS_ENVIRONMENT=Development`, localhost origin/host, or other explicit local-only signal)

### 5. Playwright: add local boot + role-aware fixtures

Add `Playwright` to the frontend workspace:

- `playwright.config.ts`
- `webServer` for frontend and backend
- `use.baseURL`
- helper/fixture to set mock auth state before opening the page

Basic contract:

- the role is set at the test/project level
- smoke test opens dashboard without Entra login
- incident detail opens on real data
- role-based visibility is checked separately for `operator` and `auditor`/`it-admin`

---

## An important note on security

### Do not use as a first option

- `function key`
- `master key`
- any secret that must be given to the browser

### Why

Browser-based E2E inevitably makes such values ​​available to the test runtime and developer tools. For local test mode, this is a redundant and dangerous model, especially when there is a cleaner path through local-only auth bypass.

---

## Alternative (Phase 2, only if you really need to test not the local backend, but the deployed slot)

If there is a strict requirement to test exactly the remote backend, a separate stage can be considered:

- separate `e2e` deployment slot or separate test backend
- a separate short-lived secret / signed header, which is accepted only there
- IP/slot/environment restriction

But this is **not** worth doing in the first pass. At the current stage, this is more of a security surface than a benefit.

---

## Implementation slice (smallest viable)

1. Add `VITE_AUTH_MODE=e2e` + mock auth provider to the frontend
2. Transfer local API calls to `/api` + Vite proxy
3. Extend local backend auth to `X-Mock-Role` + `X-Mock-User` with local-only guard
4. Add `Playwright` config with `webServer` for frontend/backend
5. Write 2 smoke tests:
   - dashboard loads as operator
   - incident detail / role gating works
6. Document the startup commands

---

## Files likely to change

```text
frontend/package.json
frontend/vite.config.ts
frontend/src/App.tsx
frontend/src/authConfig.ts
frontend/src/hooks/useAuth.ts
frontend/src/api/client.ts
frontend/src/main.tsx
frontend/playwright.config.ts
frontend/tests/e2e/**
backend/utils/auth.py
README.md
```

## Progress (April 19, 2026)

- [x] Frontend now supports `VITE_AUTH_MODE=e2e`
- [x] Browser requests in `e2e` mode use local `/api` instead of MSAL bearer tokens
- [x] Vite dev proxy forwards `/api` to a local Functions host
- [x] Playwright config starts frontend + backend locally and runs passing smoke tests
- [x] Local E2E usage documented in `frontend/README.md`
- [x] Local Functions startup no longer resolves `utils.*` from unrelated workspace folders before this repo's `backend/`
- [x] Missing local App Insights query dependency no longer prevents the whole Functions host from starting; `/api/incidents/{id}/agent-telemetry` now degrades locally instead of crashing host startup
- [ ] Backend guardrail that guarantees mock auth is accepted only in local/development environments is still pending

## Next notification coverage

- Notification-specific E2E coverage is intentionally deferred and not required before demo.
- Browser/system notification behavior stays a manual smoke check in [T-002](./T-002-final-video.md), not a Playwright target.

### Local backend startup note

- Azure Functions Core Tools may prepend other workspace folders to `sys.path`; locally this caused `utils.auth` imports to resolve to `/workspace/nursefly-web/python/utils.py` and crash on `boto3`.
- `backend/function_app.py` now forces the repo `backend/` directory to the front of `sys.path` before importing `utils`, `shared`, `triggers`, and `activities`.
- `backend/triggers/http_agent_telemetry.py` now lazy-loads `shared.agent_telemetry`, so a missing local `azure.monitor.query` install affects only the telemetry endpoint instead of blocking all HTTP APIs needed by frontend E2E.

---

## Risks / related gaps

- `backend/triggers/http_decision.py` now does not use `utils/auth.py` and accepts `user_id` / `role` from body. For full-fledged auth-aware E2E, this should be brought to the T-029/T-035 contract.
- `backend/triggers/http_signalr.py` now returns negotiate payload without role check. This does not block local E2E start, but is a separate security debt.
- If the local backend should go to Azure resources, you need to check the local credentials / `local.settings.json` / `az login`.

---

## Definition of Done

- [x] `Playwright` starts frontend locally via `webServer` without manual login
- [x] `Playwright` can bring up a local backend or reuse an already running local Functions host
- [x] frontend in `e2e` mode does not depend on `MSAL` for basic smoke flow
- [x] API requests in `e2e` mode go through `/api` and work on real backend data
- [ ] mock auth is accepted only locally, not in the deployed environment
- [x] there are at least 2 passing smoke tests for roles
- [x] README contains instructions for starting `frontend + backend + playwright`
