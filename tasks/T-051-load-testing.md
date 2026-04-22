# T-051 · Azure Load Testing — Scaling & Performance (PE:05/06)

**Статус:** 🔜 TODO  
**Пріоритет:** 🟡 MEDIUM (post-finals, ~1 тиждень)  
**WAR gap:** PE:05 P:80, PE:06  
**Архітектура:** [02-architecture.md §8.16](../02-architecture.md)

---

## Мета

Валідувати, що архітектура витримує production-scale навантаження фармзаводу. Azure Load Testing запускає JMeter/Locust test plans та інтегрується з Azure Monitor для аналізу результатів.

*Очікується що Azure Functions Flex Consumption + Cosmos DB Serverless автоматично масштабуються без ручного tuning. Load test потрібен для виявлення cold start затримок, Cosmos RU throttling та SignalR connection limits.*

---

## Expected load profile

| Компонент | Peak load | SLO |
|---|---|---|
| POST /api/alerts | 200 RPS (batch close зміни) | P95 < 2s |
| GET /api/incidents | 500 RPS (50 operators polling) | P95 < 500ms |
| SignalR connections | 200 concurrent clients | Connection established < 2s |
| Foundry agent pipeline | 10 concurrent orchestrations | E2E < 120s |
| POST /api/decision | 50 RPS | P95 < 1s |

---

## Test scenarios

### Scenario 1: Alert ingestion spike (`scenario-alert-spike`)

```python
# locust/scenario_alert_spike.py
from locust import HttpUser, task, between

class AlertSpikeUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def post_alert(self):
        self.client.post("/api/alerts", json={
            "equipment_id": "EQ-001",
            "alert_type": "vibration_anomaly",
            "severity": "high",
            "sensor_data": {"vibration_rms": 8.7, "temperature": 72.3}
        }, headers={"Authorization": f"Bearer {self.token}"})
```

**Target:** 200 concurrent users × 5 min → measure Service Bus queue depth, Function scaling time, cold start latency.

### Scenario 2: SignalR concurrent connections (`scenario-signalr-concurrent`)

```python
# locust/scenario_signalr.py
# 200 clients negotiate + connect + join role group + receive events
# Measure: connection success rate, event delivery latency
```

**Target:** 200 concurrent SignalR clients over 10 min; 0% dropped events.

### Scenario 3: Agent pipeline end-to-end (`scenario-agent-e2e`)

```python
# locust/scenario_agent_pipeline.py
# 10 concurrent: POST /alerts → wait for SignalR incident_pending_approval → POST /decision
# Measure: total orchestration time, Foundry agent latency, DLQ rate
```

**Target:** 10 concurrent E2E runs; P95 < 120s; 0 DLQ messages.

### Scenario 4: Read API load (`scenario-api-read`)

```python
# locust/scenario_api_read.py
# 500 RPS GET /incidents + GET /incidents/{id}
# Measure: P95 latency, Cosmos RU consumption, Function scaling
```

**Target:** P95 < 500ms at 500 RPS.

---

## Azure Load Testing setup

```bash
# 1. Create Azure Load Testing resource (Bicep або CLI)
az load create --name "alt-sentinel-intel" \
  --resource-group rg-sentinel-intel-dev \
  --location eastus

# 2. Upload test plan
az load test create --test-id alert-spike \
  --load-test-resource alt-sentinel-intel \
  --resource-group rg-sentinel-intel-dev \
  --display-name "Alert ingestion spike" \
  --test-plan locust/scenario_alert_spike.py \
  --engine-instances 5

# 3. Run test
az load test-run create --test-id alert-spike \
  --test-run-id run-$(date +%Y%m%d-%H%M) \
  --load-test-resource alt-sentinel-intel \
  --resource-group rg-sentinel-intel-dev
```

---

## Bicep — Azure Load Testing resource

```bicep
// infra/modules/load-testing.bicep
resource loadTesting 'Microsoft.LoadTestService/loadTests@2022-12-01' = {
  name: 'alt-sentinel-intel-${environmentName}'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
}
```

---

## Integration з GitHub Actions (CI gate)

```yaml
# .github/workflows/load-test.yml (post-deploy)
- name: Run load test
  uses: azure/load-testing@v1
  with:
    loadTestConfigFile: locust/load-test-config.yaml
    loadTestResource: alt-sentinel-intel
    resourceGroup: rg-sentinel-intel-dev
    failOnThreshold: true  # fail CI if SLOs breached
```

---

## Definition of Done

- [ ] `locust/` директорія з 4 test scenarios
- [ ] Azure Load Testing resource в Bicep (optional module)
- [ ] Scenario 1 (alert spike): P95 < 2s при 200 RPS
- [ ] Scenario 2 (SignalR): 200 concurrent, 0% dropped events
- [ ] Scenario 3 (E2E pipeline): P95 < 120s, 0 DLQ
- [ ] Scenario 4 (read API): P95 < 500ms при 500 RPS
- [ ] GitHub Actions CI load test gate (optional)
- [ ] Azure Monitor dashboard з load test results

## Estimated effort

~1 тиждень (test plan writing + infra + baseline run + tuning)

## Dependencies

- Production-like environment (не dev sandbox — потрібні Flex Consumption + реальні Cosmos RU)
- Azure Load Testing resource (pay-per-use ~$0.005/VUh)
- Entra ID service principal для тестових Bearer tokens
- T-047 (VNet) бажано завершити перед load test — щоб тестувати realistic network topology
