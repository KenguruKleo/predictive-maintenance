# Architecture History — Sentinel Intelligence

← [README](../README.md) · [02 Архітектура](../02-architecture.md) · [docs/architecture-decisions.md](./architecture-decisions.md) · [docs/hackathon-scope.md](./hackathon-scope.md)

> Журнал еволюції архітектури: версії, changelog та початкова AS-SUBMITTED схема, подана на hackathon. Для **цільової архітектури** див. [02-architecture.md](../02-architecture.md); для архітектурних рішень — [docs/architecture-decisions.md](./architecture-decisions.md); для скорочень прототипу — [docs/hackathon-scope.md](./hackathon-scope.md).

## Зміст

1. [Changelog архітектури (версії)](#1-changelog-архітектури-версії)
2. [AS-SUBMITTED v1.0 — початкова схема](#2-as-submitted-v10--початкова-схема)
3. [Еволюція компонентів v1.0 → TO-BE](#3-еволюція-компонентів-v10--to-be)

---

## 1. Changelog архітектури (версії)

| Дата | Версія | Суть зміни |
|---|---|---|
| 2026-04-22 | **v3.0** | Target-state rewrite. Single-level глибина, прибрано статус-маркери (`✅ / 🟡 / 🔜`) та розбивку «hackathon / post-hackathon». Компроміси винесено у [hackathon-scope.md](./hackathon-scope.md), ADR — у [architecture-decisions.md](./architecture-decisions.md), історія — у цей документ. |
| 2026-04-20 | v2.7 | Agent observability (`FOUNDRY_PROMPT_TRACE`) + admin telemetry endpoint. |
| 2026-04-17 | v2.0 | Dual-level orchestration (Durable + Foundry Connected Agents), [ADR-001](./architecture-decisions.md#adr-001--human-in-the-loop-mechanism) та [ADR-002](./architecture-decisions.md#adr-002--foundry-connected-agents) прийняті. |
| 2026-03-26 | v1.0 | AS-SUBMITTED архітектура подана на hackathon (оцінка 71/100 — див. [03-analysis.md](../03-analysis.md)). |

---

## 2. AS-SUBMITTED v1.0 — початкова схема

> Подано 26 березня 2026 (Kostiantyn Yemelianov). Оцінка 71/100 → [детальний аналіз](../03-analysis.md).

```
╔══════════════════════════════════════════════════════════════╗
║          COMPANY DATA LAYER (Azure AI Search / RAG)         ║
║  ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐  ║
║  │ SOP          │ │ GMP Rules /  │ │ Deviation & CAPA     │  ║
║  │ Repository   │ │ Policies     │ │ History              │  ║
║  └─────────────┘ └──────────────┘ └──────────────────────┘  ║
╚══════════════════════════════════════════════════════════════╝
           ↑ RAG Search          ↑ Azure MCP           ↑ Azure MCP

╔══════════════════════════════════════════════════════════════╗
║         FOUNDRY AGENT SERVICE (Agent Orchestrator)          ║
║   Multi-agent workflow · State management · Routing         ║
║                                                             ║
║  ┌────────────────────┐      ┌───────────────────────────┐  ║
║  │  Compliance Agent  │      │  CAPA / Audit Agent       │  ║
║  │  • Deviation       │      │  • CAPA recommendations   │  ║
║  │    classification  │      │  • Report draft           │  ║
║  │  • Risk scoring    │      │  • Audit trail            │  ║
║  │  • GMP validation  │      │                           │  ║
║  │  • Explainable     │      │                           │  ║
║  └────────────────────┘      └───────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════╝
                    ↑                    ↑
            Context/Alert         Decision Package
╔═══════════════════╧════════════════════╧══════════════════╗
║              CONTEXT ENRICHMENT SERVICE                   ║
║  • Retrieve batch & product context (MES)                 ║
║  • Retrieve equipment metadata (CMMS)                     ║
║  • Prefilter historical references                        ║
╚═══════════════════════════════════════════════════════════╝
                         ↑  Anomaly detect event
╔════════════════════════╧══════════════════════════════════╗
║          AZURE FUNCTIONS (Event Ingestion)                ║
╚═══════════════╤══════════════╤═══════════════╤═══════════╝
                │              │               │
        ┌───────┴──┐    ┌──────┴────┐    ┌─────┴──────┐
        │  SCADA   │    │    MES    │    │  IoT/CMMS  │
        └──────────┘    └───────────┘    └────────────┘

╔═══════════════════════════════════════════════════════════╗
║              HUMAN APPROVAL (GxP Requirement)             ║
║           [Approved] · [Denied] · [Question]              ║
╚══════════╤══════════════════════════════════════╤═════════╝
           │                                      │
    ┌──────┴──────┐                      ┌────────┴────────┐
    │ Work Order  │                      │  Audit Logging  │
    │ Service     │                      │  Service        │
    └─────────────┘                      └─────────────────┘
```

---

## 3. Еволюція компонентів v1.0 → TO-BE

| Компонент v1.0 | Компонент цільовий | Зміна |
|---|---|---|
| Azure Functions (Event Ingestion) | `ingest_alert` HTTP + `alert_processor` Service Bus trigger | Розбито: HTTP endpoint публікує у Service Bus; окремий тригер споживає чергу |
| Context Enrichment Service | `enrich_context` Durable Activity | Вбудовано у Durable orchestrator |
| Agent Orchestrator (Foundry) | Два рівні: Durable Functions (workflow) + Foundry Agent Service (AI) | Див. [ADR-001](./architecture-decisions.md#adr-001--human-in-the-loop-mechanism) |
| Compliance Agent | Research Agent (context) + Document Agent (classification / risk) | Відповідальності розподілено |
| CAPA / Audit Agent | Document Agent (CAPA drafting) + Execution Agent (execution) | Drafting відокремлено від execution після approval |
| Human Approval | `decision_handler` HTTP → `waitForExternalEvent` + SignalR push | Конкретний resume механізм |
| Work Order Service | Execution Agent → MCP `create_work_order` (CMMS) | MCP tool call |
| Audit Logging Service | `finalize_audit` Durable Activity → Cosmos `incidents` + `incident_events` | Вбудовано у Durable orchestrator |

---

← [02 Архітектура](../02-architecture.md) · [docs/architecture-decisions.md →](./architecture-decisions.md)
