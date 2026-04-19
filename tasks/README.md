# Tasks

← [04 · План дій](../04-action-plan.md)

> Кожна задача — окремий файл. Backlog і пріоритизація — у [04-action-plan.md](../04-action-plan.md).

## Deliverables (відео / презентація)

| ID | Файл | Назва | Пріоритет | Статус |
|---|---|---|---|---|
| T-001 | [T-001-architecture-presentation.md](./T-001-architecture-presentation.md) | Оновити архітектурну презентацію | 🔴 CRITICAL | 🔜 TODO |
| T-002 | [T-002-final-video.md](./T-002-final-video.md) | Фінальне відео (5 хвилин) | 🔴 CRITICAL | 🔜 TODO |
| T-010 | [T-010-cartoon-animation.md](./T-010-cartoon-animation.md) | Cartoon анімація «До і Після» | 🟠 HIGH | 🔜 TODO |

## Infrastructure & Data

| ID | Файл | Назва | Пріоритет | Статус |
|---|---|---|---|---|
| T-020 | [T-020-cosmos-db.md](./T-020-cosmos-db.md) | Cosmos DB — схема + provisioning | 🔴 CRITICAL | ✅ DONE |
| T-021 | [T-021-mock-data.md](./T-021-mock-data.md) | Mock data seed | 🔴 CRITICAL | ✅ DONE |
| T-022 | [T-022-service-bus.md](./T-022-service-bus.md) | Azure Service Bus alert-queue | 🟠 HIGH | ✅ DONE |
| T-036 | [T-036-ingestion-pipeline.md](./T-036-ingestion-pipeline.md) | Document ingestion pipeline | 🟠 HIGH | 🔜 TODO |
| T-037 | [T-037-ai-search.md](./T-037-ai-search.md) | AI Search indexes + mock docs | 🟠 HIGH | ✅ DONE |
| T-041 | [T-041-bicep-iac.md](./T-041-bicep-iac.md) | Bicep IaC templates | 🟠 HIGH | ✅ DONE |

## Backend / Workflow / Agents

| ID | Файл | Назва | Пріоритет | Статус |
|---|---|---|---|---|
| T-023 | [T-023-ingestion-api.md](./T-023-ingestion-api.md) | Ingestion API (POST /api/alerts) | 🔴 CRITICAL | ✅ DONE |
| T-024 | [T-024-durable-orchestrator.md](./T-024-durable-orchestrator.md) | Durable Functions orchestrator | 🔴 CRITICAL | ✅ DONE |
| T-025 | [T-025-research-agent.md](./T-025-research-agent.md) | Research Agent (Foundry + MCP + RAG) | 🔴 CRITICAL | ✅ DONE |
| T-026 | [T-026-document-agent.md](./T-026-document-agent.md) | Document Agent (Foundry + templates) | 🔴 CRITICAL | ✅ DONE |
| T-027 | [T-027-execution-agent.md](./T-027-execution-agent.md) | Execution Agent (Foundry + MCP-QMS/CMMS) | 🔴 CRITICAL | 🔜 TODO |
| T-028 | [T-028-mcp-servers.md](./T-028-mcp-servers.md) | MCP servers (cosmos-db, qms, cmms) | 🔴 CRITICAL | ✅ DONE |
| T-029 | [T-029-human-approval.md](./T-029-human-approval.md) | Human approval mechanism | 🔴 CRITICAL | 🔜 TODO |
| T-030 | [T-030-signalr.md](./T-030-signalr.md) | Azure SignalR setup | 🟠 HIGH | 🔜 TODO |
| T-031 | [T-031-backend-api.md](./T-031-backend-api.md) | Backend API Functions (CRUD) | 🔴 CRITICAL | 🔜 TODO |

## Frontend

| ID | Файл | Назва | Пріоритет | Статус |
|---|---|---|---|---|
| T-032 | [T-032-frontend-core.md](./T-032-frontend-core.md) | React frontend — core | 🔴 CRITICAL | 🔜 TODO |
| T-033 | [T-033-frontend-approval.md](./T-033-frontend-approval.md) | React frontend — approval UX | 🔴 CRITICAL | 🔜 TODO |
| T-034 | [T-034-frontend-other-roles.md](./T-034-frontend-other-roles.md) | React frontend — manager/auditor/IT | 🟠 HIGH | 🔜 TODO |
| T-043 | [T-043-agent-telemetry-admin-view.md](./T-043-agent-telemetry-admin-view.md) | Agent telemetry + admin incident view | 🟠 HIGH | 🔜 TODO |
| T-044 | [T-044-playwright-local-e2e.md](./T-044-playwright-local-e2e.md) | Local Playwright E2E mode (dev auth + local proxy) | 🟠 HIGH | 🟡 IN PROGRESS |

## Security / Reliability / RAI / CI-CD

| ID | Файл | Назва | Пріоритет | Статус |
|---|---|---|---|---|
| T-035 | [T-035-rbac.md](./T-035-rbac.md) | RBAC setup (Entra ID, 5 roles) | 🟠 HIGH | 🔜 TODO |
| T-038 | [T-038-security.md](./T-038-security.md) | Security layer (Key Vault, VNet, MI) | 🟡 MEDIUM | 🔜 TODO |
| T-039 | [T-039-reliability.md](./T-039-reliability.md) | Reliability layer | 🟡 MEDIUM | 🟡 IN PROGRESS |
| T-040 | [T-040-rai.md](./T-040-rai.md) | RAI layer | 🟡 MEDIUM | 🟡 IN PROGRESS |
| T-042 | [T-042-cicd.md](./T-042-cicd.md) | GitHub Actions CI/CD | 🟠 HIGH | ✅ DONE |
