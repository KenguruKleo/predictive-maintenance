# T-050 · Recovery Procedures Runbook (RE:09)

**Статус:** 🔜 TODO  
**Пріоритет:** 🟡 MEDIUM (post-hackathon, ~3h)  
**WAR gap:** RE:09 P:60  
**Архітектура:** [02-architecture.md §8.16](../02-architecture.md)  
**Existing doc:** [docs/operations-runbook.md](../docs/operations-runbook.md)

---

## Мета

Задокументувати процедури відновлення для вже існуючих механізмів (Durable + DLQ) та додати DLQ depth monitoring alert. RE:09 вже частково виконаний технічно — потребує оформлення runbook.

---

## Existing mechanisms ✅

| Механізм | Що робить | Де |
|---|---|---|
| **Durable retry** | 3 спроби, exponential backoff на всіх activities | `backend/orchestrators/deviation_orchestrator.py` → `retry_options` |
| **Service Bus DLQ** | Failed messages → `alert-queue/$deadletterqueue` | `backend/triggers/service_bus_trigger.py` |
| **DLQ requeue script** | Ручне відновлення incident з DLQ | `scripts/recover_live_incident.py` |
| **Cosmos serverless** | Auto-scale, регіональний failover | `infra/modules/cosmos.bicep` |

---

## Subtasks

### 1. Operator recovery runbook (~2h)

Розширити `docs/operations-runbook.md` секцією "Incident Recovery Procedures":

#### Сценарій A: Orchestrator завис (status = `in_progress`, no progress > 30 хв)

```
1. Перевір App Insights → Live Metrics → active orchestrations
   az monitor app-insights query --app "appi-sentinel-intel-dev-erzrpo" \
     --analytics-query "customEvents | where name == 'ORCHESTRATOR_START' | where timestamp > ago(1h)"

2. Якщо orchestrator не відповідає → terminate + restart:
   POST /api/admin/incidents/{id}/restart   (IT Admin role required)
   Body: { "reason": "orchestrator timeout" }

3. Перевір Cosmos DB → incidents container → incident status → скинути на "pending" якщо потрібно
   (через Azure Portal або scripts/reset_dev_data.py --incident-id {id} --status pending)
```

#### Сценарій B: Message в DLQ (alert не обробився)

```
1. Перевір DLQ depth:
   az servicebus queue show --name alert-queue --namespace-name <ns> \
     --resource-group <rg> --query "countDetails.deadLetterMessageCount"

2. Переглянь повідомлення:
   scripts/recover_live_incident.py --list-dlq

3. Requeue:
   scripts/recover_live_incident.py --requeue --message-id {id}
   # або requeue всі: --requeue-all
```

#### Сценарій C: Foundry Agent timeout (activity failed після retries)

```
1. Перевір App Insights → FOUNDRY_PROMPT_TRACE event для incident_id
2. Якщо Foundry недоступний → активується fallback mode в run_foundry_agents.py
   (fallback_response = "Analysis temporarily unavailable. Manual review required.")
3. Operator вручну заповнює CAPA report через frontend (bypass AI mode)
```

### 2. DLQ depth monitoring alert (~1h)

Додати Azure Monitor alert rule у Bicep:

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

- [ ] `docs/operations-runbook.md` — секція "Incident Recovery Procedures" з 3 сценаріями
- [ ] DLQ depth > 0 → Azure Monitor alert → email/Teams notification
- [ ] IT Admin роль дозволяє POST /api/admin/incidents/{id}/restart (або задокументовано manual процедуру)
- [ ] Runbook протестовано на dev середовищі

## Estimated effort

~3 години (1 dev session)

## Dependencies

- Доступ до Azure subscription (Monitor alert rule deployment)
- `docs/operations-runbook.md` вже існує — розширити, не створювати заново
