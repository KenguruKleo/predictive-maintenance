# T-022 · Azure Service Bus — Alert Queue Setup

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE (17 квітня 2026)  
**Блокує:** T-023 (ingestion API publishes here), T-024 (trigger reads from here)  
**Залежить від:** T-041 (Bicep IaC) ✅

> **Що задеплоєно:** `sb-sentinel-intel-dev-erzrpo` (Standard tier, Sweden Central). Черга `alert-queue`: maxDeliveryCount=5, DLQ активний. Відмінність від задачі: maxDeliveryCount=5 (задокументовано 3), змінюється просто в `infra/modules/servicebus.bicep` у T-041.

---

## Мета

Налаштувати Azure Service Bus з чергою `alert-queue` як reliability layer між ingestion API і Durable Functions orchestrator.

---

## Конфігурація

```
Namespace: sentinel-intelligence-sb  
Tier: Standard (достатньо для hackathon)

Queue: alert-queue
  - Max size: 1 GB
  - Message TTL: 7 days
  - Lock duration: 5 minutes (достатньо для orchestrator start)
  - Max delivery count: 3 → then DLQ
  - Dead-letter queue: alert-queue/$DeadLetterQueue
  - Session: false
```

---

## Файли

```
infra/
  modules/service-bus.bicep    # Service Bus namespace + queue + DLQ config

backend/
  service_bus_client.py        # publish_alert(payload) helper
```

## publish_alert() helper

```python
# backend/service_bus_client.py
from azure.servicebus.aio import ServiceBusClient
from azure.identity.aio import DefaultAzureCredential

async def publish_alert(payload: dict) -> str:
    """Publish alert to Service Bus alert-queue. Returns message_id."""
    credential = DefaultAzureCredential()
    async with ServiceBusClient(
        fully_qualified_namespace=os.environ["SERVICE_BUS_NAMESPACE"],
        credential=credential
    ) as client:
        sender = client.get_queue_sender("alert-queue")
        async with sender:
            msg = ServiceBusMessage(
                body=json.dumps(payload),
                message_id=payload["incident_id"],
                content_type="application/json"
            )
            await sender.send_messages(msg)
            return msg.message_id
```

## Definition of Done

- [ ] Service Bus namespace provisioned (Bicep або Azure Portal для dev)
- [ ] `alert-queue` queue існує з DLQ enabled
- [ ] `publish_alert()` puts message in queue (test з `scripts/test_service_bus.py`)
- [ ] DLQ contains messages after max delivery count exceeded (manual test)
- [ ] Connection string / namespace в `.env.example`
