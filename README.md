# Sentinel Intelligence — GMP CAPA Operations Assistant

### Microsoft Agentic Industry Hackathon 2026 · Capgemini + Microsoft · Track A

> **Use Case:** LS / Supply Chain — Deviation Management & CAPA in GMP Manufacturing  
> **Stack:** GitHub · Azure Functions (Durable) · Azure AI Foundry Agents · Cosmos DB · Service Bus · SignalR · React  
> **Status:** ✅ E2E pipeline working (alert → AI analysis → HITL approval → CAPA execution)

---

## What it does

An AI-powered system for GMP pharmaceutical manufacturing that:

1. **Ingests** SCADA/MES alerts via REST API → Cosmos DB + Service Bus
2. **Orchestrates** a Durable Functions workflow (6 steps, stateful)
3. **Analyzes** deviations using 3 Azure AI Foundry Agents with MCP tool access:
   - **Research Agent** — queries CMMS, Sentinel DB, and AI Search (SOPs, historical deviations)
   - **Document Agent** — queries QMS, generates draft CAPA documents
   - **Orchestrator Agent** — coordinates Research + Document via Connected Agents pattern
4. **Notifies** operators via SignalR push + Cosmos DB notification
5. **Waits** for human decision (approve / reject / request more info) — HITL loop with 24h timeout + escalation
6. **Executes** approved CAPA plans via Execution Agent, or closes rejected incidents

---

## Architecture

```
SCADA Alert → POST /api/alerts → Cosmos DB (incidents) + Service Bus
                                                            ↓
                                          Durable Orchestrator (incident_orchestrator)
                                                            ↓
                                    ┌── enrich_context (Cosmos: equipment, batches)
                                    ├── run_foundry_agents (Orchestrator → Research + Document)
                                    │     └── MCP Servers: CMMS, QMS, Sentinel DB, AI Search
                                    ├── notify_operator (SignalR + Cosmos: notifications)
                                    ├── wait_for_external_event("operator_decision") ← HITL
                                    ├── run_execution_agent (CAPA execution, if approved)
                                    └── finalize_audit (audit trail + close)
```

See [02-architecture.md](./02-architecture.md) for the full component diagram and ADRs.

---

## Quick Start

### Prerequisites

- Python 3.11+, Node.js 20+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- Azure CLI (`az login` completed)

```bash
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
pip install -r requirements-dev.txt
```

### Operations Runbooks

Operational procedures that are useful after first-time setup are kept out of the overview README:

- Foundry agent update flow and prompt traces: [docs/operations-runbook.md](./docs/operations-runbook.md)
- Alert simulation scenarios and manual HITL testing: [docs/operations-runbook.md](./docs/operations-runbook.md)
- Dev data reset and stuck-incident recovery: [docs/operations-runbook.md](./docs/operations-runbook.md)

### Reference Docs

- Platform inventory, API surface, deployment, MCP, and CI/CD: [docs/platform-reference.md](./docs/platform-reference.md)
- Entra auth config, demo login, and role assignment: [docs/entra-role-assignment.md](./docs/entra-role-assignment.md)
- Frontend UX structure and role behavior: [docs/frontend-design.md](./docs/frontend-design.md)

### Run Backend Locally

```bash
cd backend
func start
```

Backend reads credentials from `backend/local.settings.json` (not committed — ask team for values).

### Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

To point at local backend, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:7071/api
```

### Build Frontend and Desktop App

```bash
cd frontend
npm ci

# Web/SWA production build
npm run build

# Electron production smoke run
npm run electron:start

# macOS desktop distributables: DMG + ZIP in frontend/release/
npm run electron:dist:mac
```

The Electron build serves the packaged React app from `http://localhost:5173` so the same Entra redirect URI works in dev and packaged macOS builds. Quit any existing Vite/Electron process using port `5173` before running a packaged desktop smoke test. The macOS package is currently unsigned; Gatekeeper may require right-click → Open until a Developer ID certificate/notarization step is added.

GitHub Actions workflow [electron-macos.yml](./.github/workflows/electron-macos.yml) builds the macOS app only when a Git tag matching `release-*` is pushed, for example `release-0.1.0`. Every successful run uploads DMG/ZIP files as workflow artifacts and attaches the same files to the GitHub Release for that tag.

## Project Documents

| | File | Contents |
|---|---|---|
| 📋 | [01-requirements.md](./01-requirements.md) | Hackathon requirements, compliance checklist |
| 🏗 | [02-architecture.md](./02-architecture.md) | Architecture, ADRs, component diagram |
| 🔍 | [03-analysis.md](./03-analysis.md) | Gap analysis (71/100 → improvements) |
| 📌 | [04-action-plan.md](./04-action-plan.md) | Backlog, priorities, sprint plan |
| 🧭 | [docs/platform-reference.md](./docs/platform-reference.md) | Azure inventory, API surface, deployment, MCP and CI/CD reference |
| 🔐 | [docs/entra-role-assignment.md](./docs/entra-role-assignment.md) | Entra auth config, demo login, manual token flow and app role assignment |
| 🛠 | [docs/operations-runbook.md](./docs/operations-runbook.md) | Foundry ops, alert simulation, reset and recovery runbooks |
| 🎨 | [docs/frontend-design.md](./docs/frontend-design.md) | Frontend UX structure, routes, roles and screen design |
| 📁 | [tasks/](./tasks/README.md) | Individual task specs (T-001 through T-042) |
| 📐 | [docs/](./docs/) | Design system, frontend design, originals |
