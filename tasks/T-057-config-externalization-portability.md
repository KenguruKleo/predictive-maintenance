# T-057 · Config Externalization + Environment Portability

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

> **Priority:** 🟢 LOW — does not block finals, but is required before real reuse across tenants/subscriptions
> **Source:** Portability audit (April 27, 2026)
> **Status:** 🔜 TODO

---

## Goal

Make the application reusable outside the current dev environment by removing hardcoded tenant IDs, client IDs, Azure resource endpoints, and other dev-specific fallbacks from runtime code and setup scripts.

The current codebase is demo-friendly for one environment, but still assumes one Entra tenant and one Azure footprint in several places. That is acceptable for the hackathon, but not for a reusable app.

---

## What the audit found

### 1. Auth and API config is bound to one Entra / Azure setup

- `frontend/src/authConfig.ts` has hardcoded fallback values for:
  - `VITE_ENTRA_TENANT_ID`
  - `VITE_ENTRA_SPA_CLIENT_ID`
  - `VITE_ENTRA_API_CLIENT_ID`
  - `VITE_API_BASE_URL`
- `backend/utils/auth.py` has hardcoded fallback values for `ENTRA_TENANT_ID` and `ENTRA_API_CLIENT_ID`

Impact: the frontend and backend silently bind themselves to the current dev tenant/function app if env vars are missing.

### 2. Backend shared clients still default to dev Azure resources

- `backend/shared/cosmos_client.py`
- `backend/shared/search_utils.py`
- `backend/shared/servicebus_client.py`
- `backend/mcp_qms/server.py`
- `backend/mcp_cmms/server.py`
- `backend/mcp_sentinel_db/server.py`

Impact: runtime code can connect to the current dev Cosmos/Search/Service Bus resources even when deployment config is incomplete, which hides configuration errors and blocks portable reuse.

### 3. Setup scripts are not environment-agnostic

- `scripts/create_search_indexes.py` hardcodes Search, Storage, Cosmos, DB, and embedding settings
- `scripts/seed_cosmos.py` still falls back to the current dev Cosmos endpoint
- `scripts/reset_dev_data.py` still derives multiple defaults from the current dev Azure footprint
- agent test utilities still contain fallback Foundry endpoint / Agent IDs intended for the current dev setup

This task should cover all reusable scripts under `scripts/` plus agent utilities that are expected to work across environments.

Impact: setup and maintenance scripts cannot be reused safely in another subscription or customer environment without code edits.

### 4. Reusable local configuration contract is incomplete

- the repo already has a root `.env.example`, but it is stale and inconsistent with the variable names currently used by runtime code
- `backend/local.settings.json` is gitignored, but there is still no committed reusable backend settings template or generated settings flow for a new environment
- there is no single canonical documented config contract for frontend, backend, agents, and scripts

Impact: onboarding a new environment depends on tribal knowledge instead of repeatable configuration.

### 5. Hardcoded values that are acceptable to keep

- Vite dev ports
- Playwright localhost defaults
- E2E mock auth defaults
- pure tuning constants that are not environment-specific

These are acceptable as local/test defaults as long as they remain clearly scoped to development and tests.

---

## Scope

### A. Centralize configuration

- [ ] Introduce one backend config module for required Azure/Entra/resource settings
- [ ] Introduce one shared script config path for setup utilities instead of per-file constants
- [ ] Define the frontend env contract explicitly (`VITE_*` required vs optional)

### B. Remove runtime fallbacks to real dev resources

- [ ] Replace hardcoded tenant/client/API defaults in frontend auth config with required env validation
- [ ] Replace hardcoded backend auth defaults for tenant/client/audience with required env validation
- [ ] Replace hardcoded Cosmos/Search/OpenAI/Service Bus dev endpoints with required env or generated settings
- [ ] Remove concrete resource IDs from source comments where they leak environment identity into code

### C. Parameterize reusable names and endpoints

- [ ] Move database name, queue name, index names, storage account name, and other deployment-bound names behind config where they may differ by environment
- [ ] Prefer Bicep outputs, generated settings, or one canonical env template over inline constants in scripts

### D. Add reusable environment bootstrap

- [ ] Add `backend/local.settings.example.json` or equivalent generated template
- [ ] Refresh the existing root `.env.example` so it matches the actual runtime variable names and remains the canonical template where possible
- [ ] Document a single bootstrap flow for local dev, dev Azure, and a new tenant/subscription

### E. Add guardrails

- [ ] Fail fast at startup when required config is missing instead of silently falling back to dev resources
- [ ] Add a lightweight check that rejects new hardcoded `azurewebsites.net`, `*.documents.azure.com`, tenant/client IDs, or similar environment-bound constants in runtime source files, while excluding docs, tests, generated assets, and local artifact folders

---

## Suggested implementation order

1. Create a documented env/config contract for frontend, backend, agents, and scripts.
2. Externalize auth-related identifiers first because they couple both SPA and API to one tenant.
3. Externalize Azure service endpoints and resource names in shared clients and MCP servers.
4. Refactor all reusable scripts and agent utilities to consume the same config contract or generated outputs.
5. Add startup validation and a simple CI guard against new hardcoded environment-specific values.

---

## Dependencies / related tasks

- Related to [T-038](./T-038-security.md) for Key Vault and secret handling
- Related to [T-041](./T-041-bicep-iac.md) for generating or exporting environment-specific outputs
- Related to [T-042](./T-042-cicd.md) for CI validation and environment bootstrap automation
- Related to [T-046](./T-046-foundry-agent-code-hardening.md) for Foundry-specific hardcoded fallbacks in agent workflows

---

## Definition of Done

- [ ] Frontend, backend, agents, and reusable scripts can be pointed to a different tenant/subscription via config only
- [ ] No runtime source file silently falls back to the current dev tenant, client ID, Function URL, Cosmos endpoint, Search endpoint, or Service Bus namespace
- [ ] A new developer can bootstrap local config from committed templates or generated outputs without editing source files
- [ ] CI or a lightweight repository check catches newly introduced hardcoded environment-specific values in runtime code
- [ ] Demo/test-only defaults remain explicitly scoped to test/dev surfaces only