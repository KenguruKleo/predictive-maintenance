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

## Azure Resources

| Resource | Name |
|---|---|
| Resource Group | `ODL-GHAZ-2177134` |
| Function App | `func-sentinel-intel-dev-erzrpo` (Python 3.11, Consumption) |
| Cosmos DB | `cosmos-sentinel-intel-dev-erzrpo` (serverless) |
| Service Bus | `sb-sentinel-intel-dev-erzrpo` (queue: `alert-queue`) |
| SignalR | `sigr-sentinel-intel-dev-erzrpo` (hub: `deviationHub`) |
| AI Foundry Project | `aip-sentinel-intel-dev-erzrpo` |
| AI Hub | `aih-sentinel-intel-dev-erzrpo` |
| OpenAI | `oai-sentinel-intel-dev-erzrpo` (gpt-4o, text-embedding-3-small) |
| AI Search | `srch-sentinel-intel-dev-erzrpo` |
| Static Web App | `swa-sentinel-intel-dev` |
| Storage | `stsentinelintelerzrpo` |

### Cosmos DB Containers (`sentinel-intelligence`)

| Container | Partition Key | Purpose |
|---|---|---|
| `incidents` | `/id` | Incident records |
| `equipment` | `/id` | Equipment master data |
| `batches` | `/equipmentId` | Active batch records |
| `sop_library` | `/id` | Standard Operating Procedures |
| `historical_deviations` | `/equipmentId` | Past deviations for context |
| `capa_actions` | `/incidentId` | CAPA action items |
| `notifications` | `/incidentId` | Operator notifications |
| `incident_events` | `/incidentId` | Audit trail events |

### Foundry Agents

| Agent | ID | MCP Tools |
|---|---|---|
| Orchestrator | `asst_CNYK3TZIaOCH4OPKcP4N9B2r` | Connected Agents (Research + Document) |
| Research | `asst_NDuVHHTsxfRvY1mRSd7MtEGT` | CMMS, Sentinel DB, AI Search |
| Document | `asst_AXgt7fxnSnUh5WXauR27S40L` | QMS, AI Search |

---

## Quick Start

### Prerequisites

- Python 3.11+, Node.js 18+
- [Azure Functions Core Tools v4](https://learn.microsoft.com/azure/azure-functions/functions-run-local)
- Azure CLI (`az login` completed)

```bash
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
pip install -r requirements-dev.txt
```

### Foundry Agent Updates

Pushes to `main` already redeploy Azure resources and update Foundry agents automatically.
The GitHub Actions workflow `.github/workflows/deploy.yml` has a dedicated `agents` job that:
- discovers the AI Foundry project in the Azure resource group;
- discovers MCP Container App URLs;
- runs `python agents/create_agents.py --update`.

If the `Deploy` workflow on `main` passes, prompt/schema changes for Research / Document / Orchestrator agents should be applied automatically.

### Update Foundry Agents From Local Machine

This script does **not** require local Azure Functions to be running.
It talks directly to the deployed Azure AI Foundry project and deployed MCP Container Apps.

Prerequisites:
- `az login` completed
- access to the target subscription/resource group
- deployed MCP Container Apps

If MCP Container Apps are not deployed yet:

```bash
bash backend/scripts/deploy-mcp.sh --acr-build
```

Then export the required environment variables and run the update:

```bash
export AZURE_RESOURCE_GROUP="ODL-GHAZ-2177134"
export AZURE_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

export AI_PROJECT_NAME="$(az resource list -g "$AZURE_RESOURCE_GROUP" \
  --resource-type "Microsoft.MachineLearningServices/workspaces" \
  --query "[?starts_with(name,'aip-')].name | [0]" -o tsv)"

export AZURE_AI_FOUNDRY_AGENTS_ENDPOINT="swedencentral.api.azureml.ms;${AZURE_SUBSCRIPTION_ID};${AZURE_RESOURCE_GROUP};${AI_PROJECT_NAME}"

export MCP_SENTINEL_DB_URL="https://$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
  --query "[?starts_with(name,'mcp-db')].properties.configuration.ingress.fqdn | [0]" -o tsv)/mcp"

export MCP_SENTINEL_SEARCH_URL="https://$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
  --query "[?starts_with(name,'mcp-search')].properties.configuration.ingress.fqdn | [0]" -o tsv)/mcp"

export MCP_QMS_URL="https://$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
  --query "[?starts_with(name,'mcp-qms')].properties.configuration.ingress.fqdn | [0]" -o tsv)/mcp"

export MCP_CMMS_URL="https://$(az containerapp list -g "$AZURE_RESOURCE_GROUP" \
  --query "[?starts_with(name,'mcp-cmms')].properties.configuration.ingress.fqdn | [0]" -o tsv)/mcp"

python agents/create_agents.py --update
```

Notes:
- `create_agents.py --update` is idempotent; it updates existing agents in place.
- If `AZURE_AI_FOUNDRY_AGENTS_ENDPOINT` is missing, the script cannot find the target Foundry project.
- If `MCP_*_URL` variables are missing, the script will run with OpenAPI tools disabled, which is not suitable for normal agent operation.

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

---

## Simulate Alerts

### Against Azure (deployed Function App)

```bash
export FUNCTION_URL="https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/alerts"
export FUNCTION_KEY=$(az functionapp keys list \
  --name func-sentinel-intel-dev-erzrpo \
  -g ODL-GHAZ-2177134 \
  --query "functionKeys.default" -o tsv)

# Run a single scenario
python scripts/simulate_alerts.py --fresh --scenario 1

# Run all 6 scenarios
python scripts/simulate_alerts.py --fresh --all
```

### Against Local Backend

```bash
cd backend && func start   # in another terminal

# No key needed for local
python scripts/simulate_alerts.py --local --fresh --scenario 1
python scripts/simulate_alerts.py --local --fresh --all
```

### Scenarios

| # | Equipment | Severity | Expected |
|---|---|---|---|
| 1 | GR-204 Granulator | major | 202 → Durable orchestrator starts |
| 2 | GR-204 Granulator | critical | 202 → Durable orchestrator starts |
| 3 | MIX-102 Mixer | minor | 202 → Durable orchestrator starts |
| 4 | DRY-303 Dryer | critical | 202 → Durable orchestrator starts |
| 5 | Duplicate of scenario 1 | — | 200 `already_exists` (idempotent) |
| 6 | Invalid payload | — | 400 validation error |

> Use `--fresh` to generate unique IDs each run. Without it, scenarios 1–4 return `already_exists`.

### What Happens After a Successful Alert

1. Incident created in Cosmos (`incidents` container)
2. Message published to Service Bus `alert-queue`
3. Durable Orchestrator starts (`durable-INC-2026-NNNN`)
4. Context enrichment from Cosmos (equipment + batch data)
5. Foundry Orchestrator Agent runs (~5–10 min) — calls Research + Document agents via MCP
6. Notification written to Cosmos + pushed via SignalR
7. Orchestrator enters HITL wait state (`wait_for_external_event("operator_decision")`)
8. Operator approves/rejects via UI → Execution Agent or close

### Send Operator Decision (HITL)

Once the orchestrator is waiting, send a decision:

```bash
SYSTEM_KEY=$(az functionapp keys list \
  --name func-sentinel-intel-dev-erzrpo \
  -g ODL-GHAZ-2177134 \
  --query "systemKeys.durabletask_extension" -o tsv)

# Approve
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision?code=${FUNCTION_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"action": "approved", "user_id": "operator@example.com", "comments": "Approved for CAPA execution"}'

# Reject
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision?code=${FUNCTION_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"action": "rejected", "user_id": "operator@example.com", "reason": "False positive"}'

# Request more info
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision?code=${FUNCTION_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"action": "more_info", "user_id": "operator@example.com", "question": "What was the batch temperature at the time of deviation?"}'
```

---

## Clean Test Data

```bash
# Dry-run — show what would be deleted
python scripts/clean_test_data.py --dry-run --all

# Delete all test incidents
python scripts/clean_test_data.py --all

# Delete specific incidents
python scripts/clean_test_data.py --ids INC-2026-0011 INC-2026-0012

# Delete incidents from the last 30 minutes
python scripts/clean_test_data.py --last-minutes 30
```

Deletes from `incidents`, `incident_events`, `notifications`, `capa_actions`. Never touches seed data (`equipment`, `batches`, `sop_library`).

---

## Backend API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/alerts` | Ingest SCADA/MES alert → create incident |
| POST | `/api/incidents/{id}/decision` | Send operator decision (approve/reject/more_info) |
| GET | `/api/incidents` | List all incidents |
| GET | `/api/incidents/{id}` | Get incident by ID |
| GET | `/api/incidents/{id}/events` | Get incident audit trail |
| GET | `/api/equipment/{id}` | Get equipment details |
| GET | `/api/batches/current/{equipment_id}` | Get active batch for equipment |
| GET/PUT | `/api/templates[/{id}]` | CAPA document templates |
| GET | `/api/stats/summary` | Dashboard statistics |
| POST | `/api/signalr/negotiate` | SignalR negotiation for real-time updates |

---

## Frontend

### Deployed App

> **URL:** [https://calm-flower-0a6d7f90f.7.azurestaticapps.net](https://calm-flower-0a6d7f90f.7.azurestaticapps.net)

Login via Entra ID: `odl_user_2177134@sandboxailabs1009.onmicrosoft.com`

### Features

- **Operations Dashboard** — real-time incident monitoring with SignalR
- **Incident Detail** — AI analysis, approval workflow, CAPA documents
- **Incident History** — filterable table with severity/status badges
- **Manager Dashboard** — aggregated KPIs and trends
- **Template Management** — CAPA document templates
- **Command Palette** — `⌘K` for quick navigation
- **Breadcrumb Navigation** — contextual page hierarchy

### Deploy Frontend

**Automatic:** push to `main` with changes in `frontend/**` → GitHub Actions [`swa-deploy.yml`](.github/workflows/swa-deploy.yml).

Required GitHub Secrets:

| Secret | Value |
|---|---|
| `SWA_DEPLOYMENT_TOKEN` | `az staticwebapp secrets list --name swa-sentinel-intel-dev --resource-group ODL-GHAZ-2177134 --query "properties.apiKey" -o tsv` |
| `VITE_ENTRA_TENANT_ID` | `baf5b083-4c53-493a-8af7-a6ae9812014c` |
| `VITE_ENTRA_SPA_CLIENT_ID` | `1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9` |
| `VITE_ENTRA_API_CLIENT_ID` | `38843d08-f211-4445-bcef-a07d383f2ee6` |
| `VITE_API_BASE_URL` | `https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api` |

**Manual:**

```bash
cd frontend && npm run build
npx @azure/static-web-apps-cli deploy dist \
  --deployment-token "$(az staticwebapp secrets list \
    --name swa-sentinel-intel-dev \
    --resource-group ODL-GHAZ-2177134 \
    --query 'properties.apiKey' -o tsv)" \
  --env production
```

---

## Deploy Backend

**Automatic:** push to `main` with changes in `backend/**` → GitHub Actions [`deploy.yml`](.github/workflows/deploy.yml).

**Manual:**

```bash
cd backend
zip -r ../deploy.zip . -x '__pycache__/*' '.venv/*' '*.pyc'
az functionapp deployment source config-zip \
  --name func-sentinel-intel-dev-erzrpo \
  --resource-group ODL-GHAZ-2177134 \
  --src ../deploy.zip \
  --build-remote true \
  --timeout 300
```

---

## Infrastructure (Bicep)

All Azure resources are defined in [infra/](./infra/):

```bash
az deployment group create \
  --resource-group ODL-GHAZ-2177134 \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

See [infra/main.bicep](./infra/main.bicep) for the full resource graph.

---

## MCP Servers

4 MCP servers provide tool access to Foundry agents (deployed as Azure Container Apps):

| Server | Tools | Purpose |
|---|---|---|
| `mcp-cmms` | `get_equipment_details`, `get_maintenance_history`, `get_calibration_status` | CMMS data from Cosmos |
| `mcp-qms` | `get_sop_document`, `search_quality_records`, `get_capa_templates` | Quality Management |
| `mcp-sentinel-db` | `query_incidents`, `get_historical_deviations`, `get_batch_info` | Sentinel DB (Cosmos) |
| `mcp-sentinel-search` | `search_documents`, `search_sops`, `search_deviations` | AI Search (vector + hybrid) |

---

## CI/CD

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | PR to `main` | Lint, type-check, test |
| [`deploy.yml`](.github/workflows/deploy.yml) | Push to `main` (`backend/**`) | Deploy Function App |
| [`swa-deploy.yml`](.github/workflows/swa-deploy.yml) | Push to `main` (`frontend/**`) | Deploy Static Web App |

---

## Project Documents

| | File | Contents |
|---|---|---|
| 📋 | [01-requirements.md](./01-requirements.md) | Hackathon requirements, compliance checklist |
| 🏗 | [02-architecture.md](./02-architecture.md) | Architecture, ADRs, component diagram |
| 🔍 | [03-analysis.md](./03-analysis.md) | Gap analysis (71/100 → improvements) |
| 📌 | [04-action-plan.md](./04-action-plan.md) | Backlog, priorities, sprint plan |
| 📁 | [tasks/](./tasks/README.md) | Individual task specs (T-001 through T-042) |
| 📐 | [docs/](./docs/) | Design system, frontend design, originals |
