# T-023 · Ingestion API (POST /api/alerts + Context Enrichment)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-024 (Service Bus → Durable trigger)  
**Залежить від:** T-020 (Cosmos DB), T-022 (Service Bus)

---

## Мета

HTTP Azure Function `POST /api/alerts` — точка входу для SCADA/MES alerts. Валідує, збагачує базовим контекстом (equipment lookup), генерує `incident_id`, публікує в Service Bus.

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

- [ ] `POST /api/alerts` з валідним payload → 202, message in Service Bus queue
- [ ] `POST /api/alerts` з невалідним payload → 400 з описом помилки
- [ ] Невідомий `equipment_id` → 404
- [ ] Повторний `POST /api/alerts` з тим самим `alert_id` → 200 + existing `incident_id` (ідемпотентність)
- [ ] Prompt injection у string fields → sanitized або 400
- [ ] Severity classification: тест minor/major/critical кейси
