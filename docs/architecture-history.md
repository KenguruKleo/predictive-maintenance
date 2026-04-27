# Architecture History — Sentinel Intelligence

← [README](../README.md) · [02 Architecture](../02-architecture.md) · [docs/architecture-decisions.md](./architecture-decisions.md) · [docs/hackathon-scope.md](./hackathon-scope.md)

> Architecture evolution log: versions, changelog, and the initial AS-SUBMITTED diagram provided for the hackathon. For the **target architecture**, see [02-architecture.md](../02-architecture.md); for architecture decisions, see [docs/architecture-decisions.md](./architecture-decisions.md); for prototype scope reductions, see [docs/hackathon-scope.md](./hackathon-scope.md).

## Contents

1. [Architecture changelog (versions)](#1-architecture-changelog-versions)
2. [AS-SUBMITTED v1.0 — initial diagram](#2-as-submitted-v10--initial-diagram)
3. [Component evolution v1.0 → TO-BE](#3-component-evolution-v10--to-be)

---

## 1. Architecture changelog (versions)

| Date | Version | Change summary |
|---|---|---|
| 2026-04-22 | **v3.0** | Target-state rewrite. Single-level depth, removed status markers (`✅ / 🟡 / 🔜`) and removed the "hackathon / post-hackathon" split. Compromises moved to [hackathon-scope.md](./hackathon-scope.md), ADRs moved to [architecture-decisions.md](./architecture-decisions.md), history kept in this document. |
| 2026-04-20 | v2.7 | Agent observability (`FOUNDRY_PROMPT_TRACE`) + admin telemetry endpoint. |
| 2026-04-17 | v2.0 | Dual-level orchestration (Durable + Foundry Connected Agents), [ADR-001](./architecture-decisions.md#adr-001--human-in-the-loop-mechanism) and [ADR-002](./architecture-decisions.md#adr-002--foundry-connected-agents) accepted. |
| 2026-03-26 | v1.0 | AS-SUBMITTED architecture delivered to the hackathon (score 71/100 — see [03-analysis.md](../03-analysis.md)). |

---

## 2. AS-SUBMITTED v1.0 — initial diagram

> Submitted on March 26, 2026 (Kostiantyn Yemelianov). Score: 71/100 → [detailed analysis](../03-analysis.md).

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

## 3. Component evolution v1.0 → TO-BE

| v1.0 component | Target component | Change |
|---|---|---|
| Azure Functions (Event Ingestion) | `ingest_alert` HTTP + `alert_processor` Service Bus trigger | Split architecture: HTTP endpoint publishes to Service Bus; separate trigger consumes the queue |
| Context Enrichment Service | `enrich_context` Durable Activity | Embedded into the Durable orchestrator |
| Agent Orchestrator (Foundry) | Two layers: Durable Functions (workflow) + Foundry Agent Service (AI) | See [ADR-001](./architecture-decisions.md#adr-001--human-in-the-loop-mechanism) |
| Compliance Agent | Research Agent (context) + Document Agent (classification / risk) | Responsibilities split |
| CAPA / Audit Agent | Document Agent (CAPA drafting) + Execution Agent (execution) | Drafting separated from execution after approval |
| Human Approval | `decision_handler` HTTP → `waitForExternalEvent` + SignalR push | Concrete resume mechanism |
| Work Order Service | Execution Agent → MCP `create_work_order` (CMMS) | MCP tool call |
| Audit Logging Service | `finalize_audit` Durable Activity → Cosmos `incidents` + `incident_events` | Embedded into the Durable orchestrator |

---

← [02 Architecture](../02-architecture.md) · [docs/architecture-decisions.md →](./architecture-decisions.md)
