# T-039 · Reliability Layer (Retry, Fallback, Circuit Breaker, SLOs)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟡 MEDIUM
**Status:** 🟡 IN PROGRESS
**Gap:** Gap #3 Reliability ✅

---

## Goal

Bring the level of reliability to Demo-ready: retry policies, DLQ handling, fallback mode in case of AI degradation, latency budgets.

---

## Checklist

### Retry Policies
- [ ] Azure Functions: built-in retry policy (3 attempts, exponential backoff) for Service Bus
- [ ] Durable Activities: `RetryOptions(max_number_of_attempts=3, first_retry_interval=timedelta(seconds=5))`
- [ ] Cosmos DB client: `RetryOptions` with 3 retries for throttling (429)
- [ ] AI Search client: retry on timeout

### Dead-Letter Queue
- [ ] Service Bus DLQ monitored (alert if DLQ count > 0)
- [ ] `scripts/process_dlq.py` — manual script for viewing and re-processing DLQ messages

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

### Implemented on April 19, 2026
- [x] `backend/activities/run_foundry_agents.py` now emits incident-scoped structured App Insights traces behind `FOUNDRY_PROMPT_TRACE_ENABLED`
- [x] Trace envelope includes `incident_id`, `round`, `trace_kind`, chunk metadata, and `thread_id` / `run_id` when available so one incident can be reconstructed later
- [x] Trace kinds now cover the backend-visible Foundry path: prompt context, outer Orchestrator prompt, Foundry thread messages, raw response, parsed response, and normalized final result
- [ ] Live validation rerun still needs to confirm whether the returned Foundry thread exposes enough detail for Research and Document sub-agent internals

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
- [ ] Custom metric: `incident_cost_usd` estimated (tokens × model rate) — for presentation "cost per incident" slide

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
- [x] App Insights shows backend-visible Foundry prompt and response traces grouped by incident
- [ ] App Insights shows Durable orchestrator traces with step durations
