# T-050 · Recovery Procedures Runbook (RE:09)

**Status:** 🔜 TODO
**Priority:** 🟡 MEDIUM (post-hackathon, ~3h)
**WAR gap:** RE:09 P:60  
**Architecture:** [02-architecture.md §8.16](../02-architecture.md)
**Existing doc:** [docs/operations-runbook.md](../docs/operations-runbook.md)

---

## Goal

Document recovery procedures for already existing mechanisms (Durable + DLQ) and add DLQ depth monitoring alert. RE:09 is already partially done technically — it needs a runbook.

---

## Existing mechanisms ✅

| Mechanism | What does | Where |
|---|---|---|
| **Durable retry** | 3 attempts, exponential backoff on all activities | `backend/orchestrators/deviation_orchestrator.py` → `retry_options` |
| **Service Bus DLQ** | Failed messages → `alert-queue/$deadletterqueue` | `backend/triggers/service_bus_trigger.py` |
| **DLQ requeue script** | Manual incident recovery with DLQ | `scripts/recover_live_incident.py` |
| **Cosmos serverless** | Auto-scale, regional failover | `infra/modules/cosmos.bicep` |

---

## Subtasks

### 1. Operator recovery runbook (~2h)

Extend `docs/operations-runbook.md` with the "Incident Recovery Procedures" section:

#### Scenario A: Orchestrator hangs (status = `in_progress`, no progress > 30 min)

```
1. Check App Insights → Live Metrics → active orchestrations
   az monitor app-insights query --app "appi-sentinel-intel-dev-erzrpo" \
     --analytics-query "customEvents | where name == 'ORCHESTRATOR_START' | where timestamp > ago(1h)"

2. If the orchestrator does not respond → terminate + restart:
   POST /api/admin/incidents/{id}/restart   (IT Admin role required)
   Body: { "reason": "orchestrator timeout" }

3. Check Cosmos DB → incidents container → incident status → reset to "pending" if necessary
(via Azure Portal or scripts/reset_dev_data.py --incident-id {id} --status pending)
```

#### Scenario B: Message in DLQ (alert not processed)

```
1. Check DLQ depth:
   az servicebus queue show --name alert-queue --namespace-name <ns> \
     --resource-group <rg> --query "countDetails.deadLetterMessageCount"

2. View the message:
   scripts/recover_live_incident.py --list-dlq

3. Requeue:
   scripts/recover_live_incident.py --requeue --message-id {id}
# or requeue all: --requeue-all
```

#### Scenario C: Foundry Agent timeout (activity failed after retries)

```
1. Check App Insights → FOUNDRY_PROMPT_TRACE event for incident_id
2. If Foundry is not available → fallback mode is activated in run_foundry_agents.py
   (fallback_response = "Analysis temporarily unavailable. Manual review required.")
3. The operator manually fills in the CAPA report through the frontend (bypass AI mode)
```

### 2. DLQ depth monitoring alert (~1h)

Add Azure Monitor alert rule to Bicep:

```bicep
// infra/modules/monitoring.bicep
resource dlqAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'sentinel-dlq-depth-alert'
  location: 'global'
  properties: {
    description: 'DLQ has messages — manual recovery required'
    severity: 2
    enabled: true
    scopes: [serviceBusNamespaceId]
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [{
        name: 'DLQDepth'
        metricName: 'DeadletteredMessages'
        operator: 'GreaterThan'
        threshold: 0
        timeAggregation: 'Maximum'
      }]
    }
    actions: [{
      actionGroupId: actionGroupId
    }]
  }
}
```

---

## Definition of Done

- [ ] `docs/operations-runbook.md` — "Incident Recovery Procedures" section with 3 scenarios
- [ ] DLQ depth > 0 → Azure Monitor alert → email/Teams notification
- [ ] IT Admin role allows POST /api/admin/incidents/{id}/restart (or documented manual procedure)
- [ ] Runbook tested on dev environment

## Estimated effort

~3 hours (1 dev session)

## Dependencies

- Access to Azure subscription (Monitor alert rule deployment)
- `docs/operations-runbook.md` already exists — expand, do not create anew
