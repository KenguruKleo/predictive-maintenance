# Azure Infrastructure Diagram — Sentinel Intelligence

> **Resource Group:** `ODL-GHAZ-2177134` · **Region:** Sweden Central  
> **Subscription:** `Sandbox AI DS - 1003462`  
> **Suffix:** `erzrpo` (derived from RG id)
>
> Legend: ✅ deployed · � in progress · 🔜 planned

```mermaid
flowchart TB
    subgraph ext["External / Mock Sources"]
        SCADA["SCADA / MES\n(simulated)"]
        REACT["React + Vite SPA\n🔜 swa-sentinel-intel-dev"]
    end

    subgraph ci["CI/CD · GitHub Actions"]
        GHA["deploy.yml\npush → main"]
    end

    subgraph rg["ODL-GHAZ-2177134 · Sweden Central"]

        subgraph ingestion["Ingestion Layer"]
            SB["✅ Service Bus\nsb-sentinel-intel-dev-erzrpo\nqueue: alert-queue · DLQ ✓"]
        end

        subgraph compute["Compute · Azure Durable Functions"]
            PLAN["✅ App Service Plan\nasp-func-sentinel-intel-dev-erzrpo · Y1 · Linux"]
            FUNC["✅ Azure Functions · func-sentinel-intel-dev-erzrpo\nPython 3.11 · Durable\nPOST /api/alerts · GET /api/incidents · POST /decision\nGET /api/notifications · /notifications/summary\nGET /api/incidents/{id}/agent-telemetry"]
        end

        subgraph agents["AI Agents · Azure AI Foundry (Connected Agents)"]
            FOUNDRY["✅ AI Foundry Project\naoai-sentinel-intel-dev-erzrpo"]
            OA["✅ Orchestrator Agent\nasst_CNYK3TZIaOCH4OPKcP4N9B2r\nConnected Agents pipeline: Research → Document"]
            RA["✅ Research Agent · asst_NDuVHHTsxfRvY1mRSd7MtEGT\nRAG (5 indexes) + MCP-sentinel-db (5 tools)"]
            DA["✅ Document Agent · asst_AXgt7fxnSnUh5WXauR27S40L\ntemplates + confidence gate 0.7"]
            EA["🟡 Execution Agent\nMCP-qms + MCP-cmms\n(placeholder impl — gpt-4o direct)"]
            subgraph mcp["MCP Servers (stdio · Azure Functions hosted)"]
                MCP_DB["✅ mcp-sentinel-db\n5 Cosmos tools"]
                MCP_QMS["✅ mcp-qms\ncreate_audit_entry"]
                MCP_CMMS["✅ mcp-cmms\ncreate_work_order"]
            end
            OA --> RA & DA
            OA -->|"post-approval"| EA
        end

        subgraph data["Data Layer"]
            subgraph cosmos["✅ Cosmos DB Serverless · cosmos-sentinel-intel-dev-erzrpo"]
                CDB_INC["incidents&#xa;/equipmentId"]
                CDB_EVT["incident_events&#xa;/incidentId&#xa;audit trail + transcript"]
                CDB_NOTIF["notifications&#xa;/incidentId&#xa;unread center"]
                CDB_EQP["equipment&#xa;/id"]
                CDB_BAT["batches&#xa;/equipmentId"]
                CDB_CAPA["capa-plans&#xa;/incidentId"]
                CDB_APPR["approval-tasks&#xa;/incidentId"]
                CDB_TMPL["templates&#xa;/id"]
            end
            SEARCH["✅ AI Search\nsrch-sentinel-intel-dev-erzrpo\n5 indexes: SOP · equipment · GMP · BPR · incident-history\n117 chunks · HNSW vector"]
            BLOB["✅ Storage Account\nstsentinelintelerzrpo\n5 blob containers for ingestion"]
        end

        subgraph realtime["Real-time"]
            SIGNALR["🟡 SignalR Service\nsigr-sentinel-intel-dev-erzrpo\ndeviationHub · push notifications"]
        end

        subgraph security["Security"]
            KV["✅ Key Vault\nkv-sentinel-intel-erzrpo\nManaged Identities"]
        end

        subgraph observability["Observability"]
            APPI["✅ Application Insights\nappi-sentinel-intel-dev-erzrpo\nFOUNDRY_PROMPT_TRACE · agent telemetry"]
            LOG["✅ Log Analytics\nlog-sentinel-intel-dev-erzrpo · 30d"]
        end

    end

    %% CI/CD
    GHA -->|"bicep deploy + functions deploy"| rg

    %% External → Azure
    SCADA -->|"POST /api/alerts"| SB
    REACT -->|"REST + SignalR\nEntra ID token"| FUNC

    %% Ingestion → Compute
    SB -->|"ServiceBusTrigger"| FUNC
    PLAN --> FUNC

    %% Compute → Agents (Connected Agents via Durable activity)
    FUNC -->|"Durable: run_foundry_agents"| OA
    FOUNDRY --> OA

    %% Agents → Data via MCP
    RA -->|"MCP tools"| MCP_DB
    MCP_DB --> CDB_INC & CDB_EQP & CDB_BAT
    RA -->|"vector search · 5 indexes"| SEARCH
    DA -->|"write CAPA plan"| CDB_CAPA
    EA -->|"MCP tool call"| MCP_QMS & MCP_CMMS
    MCP_QMS --> CDB_APPR
    MCP_CMMS --> CDB_CAPA

    %% Compute → Data
    FUNC -->|"CRUD"| CDB_INC
    FUNC -->|"audit + transcript"| CDB_EVT
    FUNC -->|"notifications"| CDB_NOTIF
    FUNC -->|"read"| CDB_EQP & CDB_BAT
    FUNC -->|"blob trigger → chunk → embed"| BLOB
    BLOB -->|"index documents"| SEARCH
    FUNC -->|"finalize: auto-sync closed incidents"| SEARCH

    %% Real-time
    FUNC -->|"NotifyOperator activity"| SIGNALR
    SIGNALR -->|"push: approval pending\nstatus change"| REACT

    %% Secrets
    FUNC -.->|"Managed Identity"| KV
    FOUNDRY -.->|"Managed Identity"| KV

    %% Observability
    FUNC -->|"FOUNDRY_PROMPT_TRACE\ntraces · exceptions · metrics"| APPI
    APPI --> LOG
```

## Deployed resources

| Resource | Name | Status | Bicep module | Task |
|---|---|---|---|---|
| Storage Account | `stsentinelintelerzrpo` | ✅ | `modules/storage.bicep` | T-041 |
| Log Analytics | `log-sentinel-intel-dev-erzrpo` | ✅ | `modules/monitoring.bicep` | T-041 |
| Application Insights | `appi-sentinel-intel-dev-erzrpo` | ✅ | `modules/monitoring.bicep` | T-041 |
| Cosmos DB Serverless | `cosmos-sentinel-intel-dev-erzrpo` | ✅ | `modules/cosmos.bicep` | T-041 |
| Service Bus | `sb-sentinel-intel-dev-erzrpo` | ✅ | `modules/servicebus.bicep` | T-041 |
| App Service Plan | `asp-func-sentinel-intel-dev-erzrpo` | ✅ | `modules/functions.bicep` | T-041 |
| Azure Functions | `func-sentinel-intel-dev-erzrpo` | ✅ | `modules/functions.bicep` | T-041 |
| AI Search | `srch-sentinel-intel-dev-erzrpo` | ✅ | `modules/search.bicep` | T-037 |
| SignalR Service | `sigr-sentinel-intel-dev-erzrpo` | 🟡 | `modules/signalr.bicep` | T-030 |
| Key Vault | `kv-sentinel-intel-erzrpo` | ✅ | `modules/keyvault.bicep` | T-038 · T-041 |
| Static Web App | `swa-sentinel-intel-dev` | 🔜 | `modules/swa.bicep` | T-032 |
| AI Foundry Hub + Project | `aoai-sentinel-intel-dev-erzrpo` | ✅ | `modules/agents.bicep` | T-025 · T-041 |
| Orchestrator Agent | `asst_CNYK3TZIaOCH4OPKcP4N9B2r` | ✅ | `agents/create_agents.py` | T-024 |
| Research Agent | `asst_NDuVHHTsxfRvY1mRSd7MtEGT` | ✅ | `agents/create_agents.py` | T-025 |
| Document Agent | `asst_AXgt7fxnSnUh5WXauR27S40L` | ✅ | `agents/create_agents.py` | T-026 |

## Cosmos DB containers (`sentinel-intelligence`)

| Container | Partition key | Status |
|---|---|---|
| `incidents` | `/equipmentId` | ✅ |
| `incident_events` | `/incidentId` | ✅ |
| `notifications` | `/incidentId` | ✅ |
| `equipment` | `/id` | ✅ |
| `batches` | `/equipmentId` | ✅ |
| `capa-plans` | `/incidentId` | ✅ |
| `approval-tasks` | `/incidentId` | ✅ |
| `templates` | `/id` | ✅ |

---

> **How to update:** when a new resource is added to `main.bicep`, change `🔜` → `✅` in the table and diagram above.
