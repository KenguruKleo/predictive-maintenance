# Operations Runbook

← [README](../README.md) · [Entra Auth And App Role Guide](./entra-role-assignment.md)

> Operational procedures that are useful during local development, live demo runs, and troubleshooting.

---

## Foundry Agent Updates

Pushes to `main` already redeploy Azure resources and update Foundry agents automatically.
The GitHub Actions workflow `.github/workflows/deploy.yml` has a dedicated `agents` job that:

- discovers the AI Foundry project in the Azure resource group
- discovers MCP Container App URLs
- runs `python agents/create_agents.py --update`

If the `Deploy` workflow on `main` passes, prompt or schema changes for Research, Document, and Orchestrator agents should be applied automatically.

## Update Foundry Agents From Local Machine

This script does **not** require local Azure Functions to be running.
It talks directly to the deployed Azure AI Foundry project and deployed MCP Container Apps.

Prerequisites:

- `az login` completed
- access to the target subscription and resource group
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

Operational notes:

- `agents/create_agents.py` uses role-aligned defaults: `Orchestrator Agent` defaults to `gpt-4o` because it owns the final analysis and recommendation; `Research` and `Document` default to `gpt-4o-mini` because they gather evidence and prepare records.
- Override all agents at once when needed: `FOUNDRY_AGENT_MODEL=gpt-4o python agents/create_agents.py --update`
- Override agents individually when needed: `FOUNDRY_ORCHESTRATOR_AGENT_MODEL=gpt-4o FOUNDRY_RESEARCH_AGENT_MODEL=gpt-4o-mini FOUNDRY_DOCUMENT_AGENT_MODEL=gpt-4o-mini python agents/create_agents.py --update`
- Local runs use Azure CLI auth by default; set `FOUNDRY_AGENT_CREDENTIAL=default` only if you specifically want `DefaultAzureCredential`.
- To capture incident-scoped prompt and response traces for troubleshooting, set `FOUNDRY_PROMPT_TRACE_ENABLED=1`. Optional: `FOUNDRY_PROMPT_TRACE_CHUNK_SIZE=12000`.

Additional notes:

- `create_agents.py --update` is idempotent; it updates existing agents in place.
- If `AZURE_AI_FOUNDRY_AGENTS_ENDPOINT` is missing, the script cannot find the target Foundry project.
- If `MCP_*_URL` variables are missing, the script will run with OpenAPI tools disabled, which is not suitable for normal agent operation.

## Foundry Prompt Traces

When `FOUNDRY_PROMPT_TRACE_ENABLED=1` is set, `backend/activities/run_foundry_agents.py` writes structured App Insights traces with the marker `FOUNDRY_PROMPT_TRACE`.

Every trace record includes stable incident-scoped fields so the logs can later back an admin troubleshooting page:

- `incident_id`
- `round`
- `trace_kind`
- `thread_id` and `run_id` when available
- chunk metadata for long prompts and responses

Current trace kinds:

- `prompt_context`
- `orchestrator_user_prompt`
- `thread_messages`
- `raw_response`
- `parsed_response`
- `normalized_result`

Example App Insights query for one incident:

```kusto
traces
| where message has "FOUNDRY_PROMPT_TRACE"
| extend payload = parse_json(extract("FOUNDRY_PROMPT_TRACE\\s+(\\{.*\\})", 1, message))
| where tostring(payload.incident_id) == "INC-2026-0006"
| project timestamp, round = toint(payload.round), trace_kind = tostring(payload.trace_kind), chunk_index = toint(payload.chunk_index), content = tostring(payload.content)
| order by timestamp asc, round asc, trace_kind asc, chunk_index asc
```

Design notes and current SDK limitations are captured in [docs/foundry-followup-analysis.md](./foundry-followup-analysis.md).

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

### Scenario Catalog

| # | Equipment | Severity | Expected |
| --- | --- | --- | --- |
| 1 | GR-204 Granulator | major | 202 → Durable orchestrator starts |
| 2 | GR-204 Granulator | critical | 202 → Durable orchestrator starts |
| 3 | MIX-102 Mixer | minor | 202 → Durable orchestrator starts |
| 4 | DRY-303 Dryer | critical | 202 → Durable orchestrator starts |
| 5 | Duplicate of scenario 1 | — | 200 `already_exists` (idempotent) |
| 6 | Invalid payload | — | 400 validation error |

> Use `--fresh` to generate unique IDs each run. Without it, scenarios 1–4 return `already_exists`.

### What Happens After A Successful Alert

1. Incident created in Cosmos (`incidents` container)
2. Message published to Service Bus `alert-queue`
3. Durable Orchestrator starts (`durable-INC-2026-NNNN`)
4. Context enrichment from Cosmos (equipment + batch data)
5. Foundry Orchestrator Agent runs (~5–10 min) and calls Research + Document agents via MCP
6. Notification written to Cosmos and pushed via SignalR
7. Orchestrator enters HITL wait state with `wait_for_external_event("operator_decision")`
8. Operator approves or rejects via UI, which triggers Execution Agent or closes the incident

### Send Operator Decision (HITL)

Entra login, token acquisition, and consent notes for this protected endpoint are documented in [docs/entra-role-assignment.md](./entra-role-assignment.md).

```bash
# Approve
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "approved", "comments": "Approved for CAPA execution"}'

# Reject
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "rejected", "reason": "False positive"}'

# Request more info
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "more_info", "question": "What was the batch temperature at the time of deviation?"}'
```

---

## Reset Dev Data

```bash
# Dry-run — show what would be reset without changing Azure data
python scripts/reset_dev_data.py --dry-run

# Safe one-command reset with interactive confirmation
python scripts/reset_dev_data.py

# Non-interactive reset
python scripts/reset_dev_data.py --yes
```

The reset script does all of the following in one run:

- Recreates only the incident-related Cosmos containers: `incidents`, `incident_events`, `notifications`, `approval-tasks`, `capa-plans`
- Clears Azure AI Search historical RAG documents from `idx-incident-history`
- Terminates active Durable orchestrations, then purges Durable Functions instance history
- Preserves reference or seed data in `equipment`, `batches`, and `templates`

Requirements:

- Azure CLI installed and already signed in with access to `ODL-GHAZ-2177134`
- Local `backend/local.settings.json` or equivalent env vars for service endpoints and keys

Legacy alias still works:

```bash
python scripts/clean_test_data.py --dry-run
```

---

## Recover Stuck Live Incident

```bash
# Preview the recovery plan without touching Azure state
python scripts/recover_live_incident.py --incident-id INC-2026-0001 --dry-run

# Full recovery: terminate + purge + requeue + wait + replay the stored more_info
python scripts/recover_live_incident.py --incident-id INC-2026-0001 --yes

# Recover only the initial round and stop before replaying more_info
python scripts/recover_live_incident.py --incident-id INC-2026-0001 --skip-more-info-replay --yes

# Override the stored follow-up question
python scripts/recover_live_incident.py \
  --incident-id INC-2026-0001 \
  --question "Re-check the sensor calibration hypothesis before concluding tubing failure." \
  --yes
```

The recovery script does all of the following in one run:

- Reads the current incident document from Cosmos DB and reconstructs the original alert payload
- Terminates the matching Durable instance if it is still active, then purges its history
- Requeues the original payload to Service Bus and waits for a fresh initial response to return the incident to `pending_approval`
- Replays the latest stored `more_info` question only after the fresh initial round is ready, unless `--skip-more-info-replay` is used

Operational notes:

- Start with `--dry-run` when the incident state is unclear
- The script expects Azure CLI access plus the same local settings used by the backend (`backend/local.settings.json` or equivalent env vars)
