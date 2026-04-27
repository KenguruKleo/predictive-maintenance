# T-032 · React Frontend — Core (Incident List + Detail + Status Timeline)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🔴 CRITICAL
**Status:** ✅ DONE
**Blocks:** T-033 (approval UX)
**Depends on:** T-031 (backend API), T-035 (RBAC)

---

## Goal

React + Vite + TypeScript web app. Minimal working UI for demo: incident list, notification bell, unread sidebar cues, toast stack, detailed view, timeline status. Deploy to Azure Static Web Apps.

---

## Structure frontend/

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
client.ts # axios instance with base URL + auth headers
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

## Progress (April 18, 2026)

- [x] Incident detail right rail now scrolls with the page instead of using a sticky/self-scrolling approval panel
- [x] Event-driven conversation metadata (`round`, `message_kind`) is available to the incident detail transcript UI
- [x] `npm run lint` and `npm run build` pass in `frontend/`

## Progress (April 20, 2026)

- [x] `AppShell` now owns a single shared SignalR connection and renders a visible toast stack for live updates
- [x] Header notification bell implemented with unread badge and unread dropdown feed
- [x] Sidebar items now show unread highlight/dot for incidents with unread notifications
- [x] Unread incidents now keep a stronger visible attention state in the left rail, including when the incident is already open
- [x] Notification acknowledgment moved from automatic detail-page open to explicit user interaction via the bell dropdown or a click on the left active-incident item
- [x] `npm run build` passes with the notification center slice enabled
- [x] Incident detail `Status History` timeline dots now use the same shared status token palette as incident badges and sidebar status states, so status colors stay consistent across the app

---

## Definition of Done

- [ ] `npm run dev` starts without errors
- [ ] Incident list shows 5 mock incidents with correct badges
- [ ] Clicking incident → detail view with AI analysis, parameter excursion, evidence citations
- [ ] Event timeline shows chronological audit log
- [ ] SignalR connection is established, real-time updates work
- [x] Header bell shows unread count and unread dropdown without full refresh
- [x] Toast notifications are visible in UI, not only in hook state
- [x] Left sidebar highlights incidents from unread notifications
- [ ] Azure Static Web App provisioned via `infra/modules/static-web-app.bicep` (add to `infra/main.bicep`)
- [x] `npm run build` successful
- [ ] Deploy to Azure Static Web Apps
