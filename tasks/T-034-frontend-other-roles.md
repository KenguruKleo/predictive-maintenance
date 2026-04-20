# T-034 · React Frontend — Manager / Auditor / IT Admin Views

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE  
**Залежить від:** T-032 (core frontend), T-031 (backend API — stats/templates endpoints)

---

## Мета

Додаткові views для non-operator ролей: QA Manager dashboard, Auditor full audit trail, IT Admin template management.

---

## QA Manager View

```
src/pages/ManagerDashboardPage.tsx

Features:
- Incident summary stats (total, by status, by severity)
- Escalation queue — incidents waiting > 8h for approval
- All incidents (not filtered by assigned_to)
- Trend chart: incidents per week (last 4 weeks)
```

## Auditor View

```
src/pages/AuditTrailPage.tsx

Features:
- Full audit trail across all incidents
- Filter by: date range, equipment, batch, deviation type
- Export to CSV (для inspection readiness demo)
- Each row: incident ID, timestamp, actor, action, result
```

## IT Admin View

```
src/pages/TemplatesPage.tsx
src/pages/IncidentTelemetryPage.tsx

Features:
- List of templates (work order, audit entry)
- Edit template fields (inline editor or modal)
- PUT /api/templates/{id} on save
- Version history display
- Agent telemetry by incident: timeline of agent/sub-agent/tool events with filters (incidentId, status, agent)

## Progress (20 квітня 2026)

- [x] `ManagerDashboardPage` no longer crashes for IT Admin / QA Manager when `/api/stats/summary` returns the current backend aggregate shape without `recent_decisions`
- [x] `frontend/src/api/stats.ts` now normalizes legacy stats payloads (`by_status`, `open_incidents`) into the `StatsSummary` shape the UI expects, defaulting `recent_decisions` to `[]`
- [x] `npm run build` passes in `frontend/`
- [x] `backend/triggers/http_stats.py` now returns real `recent_decisions` from finalized incidents (`finalDecision` + `closedAt` + AI confidence), including QA override detection and response-time calculation; focused coverage lives in `tests/test_http_stats.py`
- [x] The updated stats projection was deployed to the live Function App, and the deployed `/api/stats/summary` now returns populated `recent_decisions` for the local frontend target defined in `frontend/.env.local`
- [x] Escalated status styling was aligned to the shared status token source (`frontend/src/index.css` + `StatusBadge`), including manager escalation cards and incident timeline dots, so it now reads differently from `pending_approval`
```

---

## Definition of Done

- [x] QA Manager dashboard shows stats + escalation queue (`ManagerDashboardPage`, verified live)
- [x] IT Admin template management — list, edit, save (`TemplateManagementPage`)
- [x] IT Admin sees per-incident agent telemetry timeline (`IncidentTelemetryPage`)
- [x] Role-gating: `useRoleGuard` on all non-operator pages
- [x] Auditor CSV export — `IncidentHistoryPage` has "Export CSV" button; client-side Blob download of all loaded incidents with 15 columns (ID, title, equipment, severity, status, batch, deviation, parameter, measured value, unit, risk level, AI confidence, root cause, assigned to, created at)
- [x] Verified working: Operator, QA Manager, IT Admin, Auditor (20 April 2026)
