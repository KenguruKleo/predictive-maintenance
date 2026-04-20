# Platform Reference

← [README](../README.md) · [Operations Runbook](./operations-runbook.md) · [Entra Auth And App Role Guide](./entra-role-assignment.md)

> Environment-specific resource inventory, API surface, deployment commands, MCP topology, and CI/CD references.

---

## Azure Resources

| Resource | Name |
| --- | --- |
| Resource Group | `ODL-GHAZ-2177134` |
| Function App | `func-sentinel-intel-dev-erzrpo` (Python 3.11, Consumption) |
| Cosmos DB | `cosmos-sentinel-intel-dev-erzrpo` (serverless) |
| Service Bus | `sb-sentinel-intel-dev-erzrpo` (queue: `alert-queue`) |
| SignalR | `sigr-sentinel-intel-dev-erzrpo` (hub: `deviationHub`) |
| AI Foundry Project | `aip-sentinel-intel-dev-erzrpo` |
| AI Hub | `aih-sentinel-intel-dev-erzrpo` |
| OpenAI | `oai-sentinel-intel-dev-erzrpo` (`gpt-4o`, `text-embedding-3-small`) |
| AI Search | `srch-sentinel-intel-dev-erzrpo` |
| Static Web App | `swa-sentinel-intel-dev` |
| Storage | `stsentinelintelerzrpo` |

## Cosmos DB Containers

Database: `sentinel-intelligence`

| Container | Partition Key | Purpose |
| --- | --- | --- |
| `incidents` | `/id` | Incident records |
| `equipment` | `/id` | Equipment master data |
| `batches` | `/equipmentId` | Active batch records |
| `sop_library` | `/id` | Standard Operating Procedures |
| `historical_deviations` | `/equipmentId` | Past deviations for context |
| `capa_actions` | `/incidentId` | CAPA action items |
| `notifications` | `/incidentId` | Operator notifications |
| `incident_events` | `/incidentId` | Audit trail events |

## Foundry Agents

| Agent | ID | MCP Tools |
| --- | --- | --- |
| Orchestrator | `asst_CNYK3TZIaOCH4OPKcP4N9B2r` | Connected Agents (Research + Document) |
| Research | `asst_NDuVHHTsxfRvY1mRSd7MtEGT` | CMMS, Sentinel DB, AI Search |
| Document | `asst_AXgt7fxnSnUh5WXauR27S40L` | QMS, AI Search |

## Backend API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/alerts` | Ingest SCADA or MES alert and create incident |
| POST | `/api/incidents/{id}/decision` | Send operator decision (`approved`, `rejected`, `more_info`) |
| GET | `/api/incidents` | List incidents |
| GET | `/api/incidents/{id}` | Get incident by ID |
| GET | `/api/incidents/{id}/events` | Get incident audit trail |
| GET | `/api/equipment/{id}` | Get equipment details |
| GET | `/api/batches/current/{equipment_id}` | Get active batch for equipment |
| GET/PUT | `/api/templates[/{id}]` | CAPA document templates |
| GET | `/api/stats/summary` | Dashboard statistics |
| POST | `/api/signalr/negotiate` | SignalR negotiation for real-time updates |

## Frontend Reference

Deployed app URL:

- `https://calm-flower-0a6d7f90f.7.azurestaticapps.net`

Entra auth config, demo login, and role assignment are documented in [docs/entra-role-assignment.md](./entra-role-assignment.md).

Frontend feature areas:

- Operations Dashboard
- Incident Detail
- Incident History
- Manager Dashboard
- Template Management
- Command Palette
- Breadcrumb Navigation

## Deploy Frontend

Automatic deploy:

- push to `main` with changes in `frontend/**`
- GitHub Actions workflow: `.github/workflows/swa-deploy.yml`

Required GitHub Secrets:

| Secret | Value |
| --- | --- |
| `SWA_DEPLOYMENT_TOKEN` | `az staticwebapp secrets list --name swa-sentinel-intel-dev --resource-group ODL-GHAZ-2177134 --query "properties.apiKey" -o tsv` |
| `VITE_API_BASE_URL` | `https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api` |

Entra-specific frontend auth values are documented in [docs/entra-role-assignment.md](./entra-role-assignment.md).

Manual deploy:

```bash
cd frontend && npm run build
npx @azure/static-web-apps-cli deploy dist \
  --deployment-token "$(az staticwebapp secrets list \
    --name swa-sentinel-intel-dev \
    --resource-group ODL-GHAZ-2177134 \
    --query 'properties.apiKey' -o tsv)" \
  --env production
```

## Deploy Backend

Automatic deploy:

- push to `main` with changes in `backend/**`
- GitHub Actions workflow: `.github/workflows/deploy.yml`

Manual deploy:

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

## Infrastructure (Bicep)

All Azure resources are defined in [infra/](../infra/).

```bash
az deployment group create \
  --resource-group ODL-GHAZ-2177134 \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam
```

See [infra/main.bicep](../infra/main.bicep) for the full resource graph.

## MCP Servers

4 MCP servers provide tool access to Foundry agents and are deployed as Azure Container Apps.

| Server | Tools | Purpose |
| --- | --- | --- |
| `mcp-cmms` | `get_equipment_details`, `get_maintenance_history`, `get_calibration_status` | CMMS data from Cosmos |
| `mcp-qms` | `get_sop_document`, `search_quality_records`, `get_capa_templates` | Quality Management |
| `mcp-sentinel-db` | `query_incidents`, `get_historical_deviations`, `get_batch_info` | Sentinel DB (Cosmos) |
| `mcp-sentinel-search` | `search_documents`, `search_sops`, `search_deviations` | AI Search (vector + hybrid) |

## CI/CD

| Workflow | Trigger | What it does |
| --- | --- | --- |
| [`ci.yml`](../.github/workflows/ci.yml) | PR to `main` | Lint, type-check, test |
| [`deploy.yml`](../.github/workflows/deploy.yml) | Push to `main` (`backend/**`) | Deploy Function App |
| [`swa-deploy.yml`](../.github/workflows/swa-deploy.yml) | Push to `main` (`frontend/**`) | Deploy Static Web App |
