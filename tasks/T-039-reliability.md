# T-039 · Reliability Layer (Retry, Fallback, Circuit Breaker, SLOs)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟡 MEDIUM  
**Статус:** 🔜 TODO  
**Gap:** Gap #3 Reliability ✅

---

## Мета

Довести до Demo-ready рівень надійності: retry policies, DLQ handling, fallback mode при деградації AI, latency budgets.

---

## Checklist

### Retry Policies
- [ ] Azure Functions: built-in retry policy (3 attempts, exponential backoff) for Service Bus
- [ ] Durable Activities: `RetryOptions(max_number_of_attempts=3, first_retry_interval=timedelta(seconds=5))`
- [ ] Cosmos DB client: `RetryOptions` з 3 retries для throttling (429)
- [ ] AI Search client: retry на timeout

### Dead-Letter Queue
- [ ] Service Bus DLQ monitored (alert якщо DLQ count > 0)
- [ ] `scripts/process_dlq.py` — manual script для перегляду та re-process DLQ messages

### Fallback Mode
```python
# backend/utils/fallback.py
# If Foundry Agent call fails (timeout / 503):
#   1. Log error to App Insights
#   2. Set incident status = "manual_review_required"
#   3. Push SignalR notification: "AI unavailable — manual review needed"
#   4. Notify qa-manager via SignalR
# Operator can still approve/reject manually (without AI recommendation)
```

### Latency Budgets (target SLOs)
| Step | Target |
|---|---|
| POST /api/alerts → queued | < 500ms |
| Service Bus → Durable start | < 5s |
| Context enrichment (Cosmos reads) | < 2s |
| Research + Document Agent | < 3 min |
| Total: alert → decision package ready | < 5 min |
| POST /decision → orchestrator resumes | < 2s |

### Cost Controls
- [ ] Cosmos DB: provisioned throughput 400 RU (auto-scale off for hackathon)
- [ ] AI Search: Basic tier (no redundancy needed for demo)
- [ ] Azure Functions: Consumption plan (pay per execution)
- [ ] Foundry Agents: monitor token usage via App Insights custom metrics
- [ ] Custom metric: `incident_total_tokens` per incident (input + output tokens, all agent calls)
- [ ] Custom metric: `incident_cost_usd` estimated (tokens × model rate) — для presentation "cost per incident" slide

---

## Files

```
backend/
  utils/
    fallback.py        # handle_agent_failure()
    retry_config.py    # shared RetryOptions constants
```

## Definition of Done

- [ ] Simulated agent failure → fallback mode activates → operator sees "Manual review required"
- [ ] Durable Activity retry fires 3 times on transient error (test with mock failure)
- [ ] DLQ demo: send invalid message → lands in DLQ after 3 attempts
- [ ] App Insights shows Durable orchestrator traces with step durations
