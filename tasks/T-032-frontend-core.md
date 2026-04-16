# T-032 · React Frontend — Core (Incident List + Detail + Status Timeline)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🔴 CRITICAL  
**Статус:** 🔜 TODO  
**Блокує:** T-033 (approval UX)  
**Залежить від:** T-031 (backend API), T-035 (RBAC)

---

## Мета

React + Vite + TypeScript web app. Мінімальний working UI для demo: список інцидентів, детальний вигляд, статус timeline. Deploy на Azure Static Web Apps.

---

## Структура frontend/

```
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  
  src/
    main.tsx
    App.tsx
    
    api/
      client.ts              # axios instance з base URL + auth headers
      incidents.ts           # getIncidents(), getIncident(id), getIncidentEvents(id)
      equipment.ts           # getEquipment(id)
      
    types/
      incident.ts            # TypeScript types matching backend response
      
    components/
      Layout/
        Layout.tsx           # Sidebar nav + top bar + role badge
        Sidebar.tsx
      IncidentList/
        IncidentList.tsx      # Table: ID, equipment, severity, status, time
        IncidentRow.tsx
        SeverityBadge.tsx    # colored badge: minor/major/critical/LOW_CONFIDENCE
        StatusBadge.tsx      # pending_approval, in_progress, closed, rejected
      IncidentDetail/
        IncidentDetail.tsx   # Main detail view
        ParameterExcursion.tsx # Visual: measured vs limit
        AiAnalysis.tsx       # risk level + confidence bar + recommendation
        EvidenceCitations.tsx # List of SOP/case citations
        EventTimeline.tsx    # Chronological audit log
      
    pages/
      IncidentsPage.tsx
      IncidentDetailPage.tsx
      
    hooks/
      useIncidents.ts        # React Query hook
      useSignalR.ts          # SignalR connection + real-time updates
```

---

## Key views

### Incident List (operator view)
```
┌──────────────────────────────────────────────────────────┐
│  🔔 Sentinel Intelligence     Plant-01    ivan.petrenko   │
├──────────────────────────────────────────────────────────┤
│  Incidents                              [+ New Alert]     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ID          Equipment  Severity  Status    Time     │  │
│  ├────────────────────────────────────────────────────┤  │
│  │ INC-2026-0001  GR-204  🟠 MAJOR  ⏳ PENDING  now  │ ← real-time badge
│  │ INC-2026-0003  GR-204  🟡 MOD    ✅ CLOSED  28 Feb │
│  │ INC-2026-0005  GR-204  🟠 MAJOR  ✅ CLOSED  20 Jan │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Incident Detail
```
┌──────────────────────────────────────────────────────────┐
│  INC-2026-0001 · GR-204 · Impeller Speed Deviation       │
│  Status: PENDING APPROVAL  ⚠️ Assigned to you            │
├──────────────────────────────────────────────────────────┤
│  PARAMETER EXCURSION                                     │
│  Impeller Speed: 580 RPM  ████████░░░░ (limit: 600–800)  │
│  Duration: 4 min 7 sec                                   │
├──────────────────────────────────────────────────────────┤
│  AI ANALYSIS  [Confidence: 84%  ██████████░░]            │
│  Risk: 🟠 MEDIUM                                         │
│  Root cause: Motor load fluctuation during binder phase  │
│  CAPA: 1. Moisture check 2. Increase sampling...         │
│                                                          │
│  Evidence: SOP-DEV-001 §4.2 · INC-2026-0003 (similar)   │
├──────────────────────────────────────────────────────────┤
│  [✅ Approve]  [❌ Reject]  [❓ Need More Info]           │  ← T-033
└──────────────────────────────────────────────────────────┘
```

---

## SignalR real-time

```typescript
// hooks/useSignalR.ts
// On connect: subscribe to incident updates
// On message "incident_updated" with incident_id → invalidate React Query cache
// Shows toast: "New deviation: GR-204 — Pending your approval"
```

---

## Definition of Done

- [ ] `npm run dev` запускається без помилок
- [ ] Incident list показує 5 mock incidents з правильними бейджами
- [ ] Clicking incident → detail view з AI analysis, parameter excursion, evidence citations
- [ ] Event timeline показує chronological audit log
- [ ] SignalR connection встановлюється, real-time оновлення працюють
- [ ] `npm run build` успішно, deploy на Azure Static Web Apps
