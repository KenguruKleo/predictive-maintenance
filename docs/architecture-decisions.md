# Architecture Decision Records — Sentinel Intelligence

← [README](../README.md) · [02 Architecture](../02-architecture.md) · [docs/hackathon-scope.md](./hackathon-scope.md) · [docs/architecture-history.md](./architecture-history.md)

> Architecture decisions made during system design. Each ADR records context, options considered, decision, and consequences. Add new ADRs as `ADR-XXX` in chronological order.

## Contents

- [ADR-001 — Human-in-the-loop mechanism](#adr-001--human-in-the-loop-mechanism)
- [ADR-002 — Foundry Connected Agents](#adr-002--foundry-connected-agents)

---

## ADR-001 — Human-in-the-loop mechanism

> **Type:** ADR · **Date:** April 17, 2026 · **Status:** Accepted ✅

**Context.** GMP requires mandatory human approval. The operator has up to 24 hours to decide. The workflow needs a pause mechanism, resume with decision, and timeout + escalation.

**Options considered:**

- **A. Foundry function_call + `previous_response_id`.** Run expires in 10 minutes, so it is not suitable for a 24h pause. Source: [Microsoft Foundry docs (April 2026)](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/function-calling) — *"Runs expire 10 minutes after creation. Submit your tool outputs before they expire."*
- **B. Durable Functions `waitForExternalEvent` + `raise_event`.** Free pause for as long as needed (Azure Storage persists state). Resume via HTTP endpoint.

**Decision: B.**

| Criterion | A (Foundry) | B (Durable) |
|---|---|---|
| Maximum pause | 10 min | unlimited |
| Recovery after restart/crash | lost | persisted |
| Cost during pause | N/A (run expires) | $0 (Consumption) |
| Resume API | N/A | `raiseEvent` HTTP |
| Timeout + escalation | none | `create_timer` race pattern |

**Consequences.** Foundry agents run as short activity functions (≤ 10 min). Workflow state is managed by Durable (Azure Storage). The `approval-tasks` Cosmos container stores pending approvals for the React UI. SignalR pushes "operator decision required" updates. `POST /api/incidents/{id}/decision` calls `raise_event` to resume the orchestrator.

---

## ADR-002 — Foundry Connected Agents

> **Type:** ADR · **Date:** April 17, 2026 · **Status:** Accepted ✅

**Context.** The initial idea was separate Durable activities for each agent with manual result passing and a custom `loop_count` for `more_info`.

**Options considered:**

- **A. Manual orchestration in Durable.** One activity per agent, manual transfer of `ResearchAgentOutput` → Document Agent via Durable state, and `loop_count` in Python.
- **B. Foundry Connected Agents.** Single `run_foundry_agents` activity calling the Orchestrator Agent, with Research and Document connected as `AgentTool`. Foundry natively manages the reasoning loop, `max_iterations`, routing, and MCP + RAG tool connections.

**Decision: B.**

| Criterion | A (manual) | B (Connected Agents) |
|---|---|---|
| Number of activity functions | 2 | 1 |
| Data transfer between agents | through Durable state | native (Foundry thread) |
| `more_info` loop | custom counter | `max_iterations` in Foundry |
| MCP tool connections | custom wrapper | native |
| RAG tools | custom SDK code | `AzureAISearchTool` native |
| Lines of code | ~200 | ~50 |

**Consequences.** T-024 is simplified to a single `run_foundry_agents` activity. T-025/T-026 are Foundry Agent definitions, not Durable activities. For `more_info`, Durable receives the decision, appends `operator_question` to context, and calls `run_foundry_agents` again while Foundry handles the new round internally. Round limits are controlled by `max_iterations` in Foundry + `MAX_MORE_INFO_ROUNDS` in Durable (for GMP audit trail).

---

← [02 Architecture](../02-architecture.md) · [docs/architecture-history.md →](./architecture-history.md)
