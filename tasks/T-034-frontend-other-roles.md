# T-034 · React Frontend — Manager / Auditor / IT Admin Views

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🔜 TODO  
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

Features:
- List of templates (work order, audit entry)
- Edit template fields (inline editor or modal)
- PUT /api/templates/{id} on save
- Version history display
```

---

## Definition of Done

- [ ] QA Manager dashboard shows stats + escalation queue
- [ ] Auditor view renders full audit trail with filter controls
- [ ] Auditor CSV export works
- [ ] IT Admin can edit and save template (change propagates to mock seeded data)
- [ ] Role-gating: auditor cannot see IT Admin page, operator cannot see manager dashboard
