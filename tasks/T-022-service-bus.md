# T-022 · Azure Service Bus — Alert Queue Setup

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH  
**Status:** ✅ DONE (April 17, 2026)  
**Blocks:** T-023 (ingestion API publishes here), T-024 (trigger reads from here)  
**Depends on:** T-041 (Bicep IaC) ✅

> **What is deployed:** `sb-sentinel-intel-dev-erzrpo` (Standard tier, Sweden Central). Queue `alert-queue`: `maxDeliveryCount=5`, DLQ enabled. Difference from this task: `maxDeliveryCount=5` (documented as 3 here), easily updated in `infra/modules/servicebus.bicep` under T-041.

---

## Goal

Configure Azure Service Bus with `alert-queue` as a reliability layer between the ingestion API and the Durable Functions orchestrator.

---

## Configuration

```
Namespace: sentinel-intelligence-sb  
Tier: Standard (sufficient for hackathon)

Queue: alert-queue
  - Max size: 1 GB
  - Message TTL: 7 days
  - Lock duration: 5 minutes (sufficient for orchestrator start)
  - Max delivery count: 3 → then DLQ
  - Dead-letter queue: alert-queue/$DeadLetterQueue
  - Session: false
```

---

## Files

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

- [ ] Service Bus namespace provisioned (Bicep or Azure Portal for dev)
- [ ] `alert-queue` queue exists with DLQ enabled
- [ ] `publish_alert()` puts a message in queue (test with `scripts/test_service_bus.py`)
- [ ] DLQ contains messages after max delivery count exceeded (manual test)
- [ ] Connection string / namespace in `.env.example`
