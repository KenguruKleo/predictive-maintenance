# T-023 · Ingestion API (POST /api/alerts + Context Enrichment)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE
**Blocks:** T-024 (Service Bus → Durable trigger)
**Depends on:** T-020 (Cosmos DB), T-022 (Service Bus)

> **Finished 17 Apr 2026:** `POST /api/alerts` implemented. Structure: `shared/` (cosmos_client, servicebus_client), `utils/` (validation, severity, id_generator), `triggers/http_ingest_alert.py`. `scripts/simulate_alerts.py` with 6 demo scenarios.

---

## Goal

HTTP Azure Function `POST /api/alerts` is the entry point for SCADA/MES alerts. Validates, enriches the basic context (equipment lookup), generates `incident_id`, publishes to Service Bus.

---

## Endpoint

```
POST /api/alerts
Content-Type: application/json

Body:
{
  "equipment_id": "GR-204",
  "deviation_type": "process_parameter_excursion",
  "parameter": "impeller_speed_rpm",
  "measured_value": 580,
  "lower_limit": 600,
  "upper_limit": 800,
  "unit": "RPM",
  "duration_seconds": 247,
  "detected_by": "scada_monitor",
  "detected_at": "2026-04-17T08:42:00Z",
  "batch_id": "BATCH-2026-0416-GR204"   // optional
}

Response 202 Accepted:
{
  "incident_id": "INC-2026-0006",
  "status": "queued",
  "message": "Alert received and queued for processing"
}
```

---

## Logic

```python
# backend/triggers/http_ingest_alert.py

@app.route(route="alerts", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def ingest_alert(req: func.HttpRequest) -> func.HttpResponse:
    # 1. Parse + validate body
    body = req.get_json()
    validate_alert_payload(body)  # raises 400 if invalid

    # 2. **Idempotency check** (added per arch review §8.11)
    # Check if incident with sourceAlertId already exists in Cosmos
    alert_id = body.get("alert_id")
    if alert_id:
        existing = await get_incident_by_source_alert_id(alert_id)
        if existing:
            return func.HttpResponse(
                status_code=200,
                body=json.dumps({"incident_id": existing["id"], "status": "already_exists"})
            )

    # 3. Prompt injection guard on string fields
    sanitize_string_fields(body)

    # 3. Generate incident_id
    incident_id = generate_incident_id()  # INC-{YYYY}-{NNNN}

    # 4. Quick equipment lookup (validate equipment exists)
    equipment = await get_equipment_from_cosmos(body["equipment_id"])
    if not equipment:
        return func.HttpResponse(status_code=404, body="Equipment not found")

    # 5. Determine severity
    severity = classify_severity(body)  # minor/moderate/major/critical

    # 6. Build full payload
    payload = {
        **body,
        "incident_id": incident_id,
        "source_alert_id": body.get("alert_id"),  # for idempotency
        "severity": severity,
        "reported_at": datetime.utcnow().isoformat() + "Z",
        "equipment_name": equipment["name"],
        "equipment_criticality": equipment["criticality"]
    }

    # 7. Publish to Service Bus
    await publish_alert(payload)

    return func.HttpResponse(
        status_code=202,
        body=json.dumps({"incident_id": incident_id, "status": "queued"})
    )
```

## Severity classification logic

```python
def classify_severity(body: dict) -> str:
    magnitude_pct = abs(body["measured_value"] - body["lower_limit"]) / abs(body["upper_limit"] - body["lower_limit"]) * 100
    duration_min = body.get("duration_seconds", 0) / 60
    
    if duration_min > 30 or magnitude_pct > 20:
        return "critical"
    elif duration_min > 2 or magnitude_pct > 5:
        return "major"
    else:
        return "minor"
```

---

## Files

```
backend/
  function_app.py               # app = func.FunctionApp() + register all routes
  triggers/
    http_ingest_alert.py
  utils/
    validation.py               # validate_alert_payload(), sanitize_string_fields()
    severity.py                 # classify_severity()
    id_generator.py             # generate_incident_id() with Cosmos counter
```

## Definition of Done

- [x] `POST /api/alerts` with valid payload → 202, message in Service Bus queue
- [x] `POST /api/alerts` with invalid payload → 400 with error description
- [x] Unknown `equipment_id` → 404
- [x] Repeated `POST /api/alerts` with the same `alert_id` → 200 + existing `incident_id` (idempotency)
- [x] Prompt injection in string fields → 400 with description
- [x] Severity classification: minor/major/critical cases (in `utils/severity.py`)
- [x] `scripts/simulate_alerts.py` — 6 demo scenarios (local + Azure mode)
