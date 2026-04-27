# Foundry Follow-up Analysis And Prompt Trace Design

## Purpose

This note explains who actually prepares the operator-facing answer, what model, prompt, and data each agent receives, what can and cannot be observed with the current `azure-ai-agents` SDK, and how prompt and response traces are now logged so they can be retrieved later per incident.

The immediate trigger for this analysis was the poor follow-up quality on BPR-focused questions such as `INC-2026-0004` and `INC-2026-0006`.

---

## Short Answer

- The final human-facing follow-up answer is produced by the **Document Agent**.
- The **Orchestrator Agent** should coordinate the flow only: call Research first, then Document, then return the Document JSON unchanged.
- The backend can still overwrite the final `operator_dialogue` with a guardrail rewrite if the Document output is too vague or just repeats the previous recommendation.
- Because of that, the final text seen by the operator has two possible authors:
  1. **Document Agent** — normal path
  2. **Backend guardrail in `run_foundry_agents.py`** — fallback rewrite path

---

## Runtime Control Flow

### 1. Durable orchestrator owns the workflow

`backend/orchestrators/incident_orchestrator.py`

- builds incident context via `enrich_context`
- stores operator follow-up questions in `context_data["operator_questions"]`
- calls one activity: `run_foundry_agents`
- sends the resulting `ai_result` to `notify_operator`

### 2. Backend builds one outer user prompt

`backend/activities/run_foundry_agents.py::_build_prompt(...)`

The backend sends one large user message to the Foundry Orchestrator Agent. That prompt includes:

- raw alert payload JSON
- compact equipment summary JSON
- compact active batch summary JSON
- compact recent incident decision JSON
- operator follow-up questions
- previous recommendation snapshot for follow-up rounds

The backend no longer pre-fetches RAG snippets from all AI Search indexes before calling Foundry.
The Research Agent is the single evidence collector, which avoids duplicate retrieval and reduces
tokens in the Orchestrator prompt.

### 3. Foundry Orchestrator Agent receives that outer prompt

`agents/prompts/orchestrator_system.md`

The system prompt explicitly says the Orchestrator must:

- call `research_agent`
- then call `document_agent`
- make the final analysis and decision itself from grounded Research Agent evidence
- call Document Agent only to prepare/persist documentation that matches the decision

### 4. Research Agent gathers evidence

`agents/prompts/research_system.md`

The Research prompt requires evidence collection from SOP, GMP, manuals, BPR, and historical incidents. Its expected job is to return structured grounding such as:

- `bpr_constraints`
- `relevant_sops`
- `gmp_references`
- equipment and manual findings
- historical matches

### 5. Orchestrator produces the final package; Document Agent prepares records

`agents/prompts/document_system.md`

The Orchestrator is responsible for the final structured decision package, including:

- recommendation
- root cause
- batch disposition
- evidence citations
- `operator_dialogue`

The Document Agent must not decide or override these fields. It receives only a compact
documentation package from the Orchestrator and returns QMS/CMMS outputs:

- `audit_entry_draft`
- `work_order_draft` when corrective work is required
- `audit_entry_id`
- `work_order_id`
- `execution_error`

### 6. Backend normalizes the final dialogue

`backend/activities/run_foundry_agents.py::_normalize_operator_dialogue(...)`

If the Document Agent returns low-quality follow-up language, the backend may rewrite `operator_dialogue` before saving it to Cosmos DB and before the UI shows it.

---

## Models In Use

Current defaults in code:

- `agents/research_agent.py` → `gpt-4o-mini`
- `agents/orchestrator_agent.py` → `gpt-4o-mini`
- `agents/document_agent.py` → `gpt-4o`

Override rules:

- global override: `FOUNDRY_AGENT_MODEL`
- per-agent overrides:
  - `FOUNDRY_RESEARCH_AGENT_MODEL`
  - `FOUNDRY_DOCUMENT_AGENT_MODEL`
  - `FOUNDRY_ORCHESTRATOR_AGENT_MODEL`

Current quality hypothesis after the split-model rollback:

- model choice matters for fluency and synthesis quality
- but the bad BPR follow-up behavior is **not explained by model choice alone**
- likely failure is still upstream in grounding, forwarding, or synthesis discipline

---

## What Each Agent Actually Gets

### Backend → Orchestrator

Visible and fully loggable from our code.

Input sources:

- alert payload
- enriched context
- pre-fetched local RAG snippets
- operator follow-up questions
- previous recommendation snapshot

### Orchestrator → Research

Controlled by Foundry Connected Agents inside one thread.

What we know:

- the Research system prompt is fixed and stored in repo
- the Orchestrator system prompt instructs that Research must run first
- the Research Agent should receive the same incident and follow-up context carried inside the Foundry run

What we do **not** get directly from the current backend code:

- the exact sub-agent invocation payload generated by Foundry for the Research Agent

### Research → Document

Also happens inside the Foundry Connected Agents flow.

What we know:

- the Document system prompt is fixed and stored in repo
- the Document Agent should receive Research output plus the incident context required to synthesize the final JSON package

What we do **not** get directly from the current backend code:

- the exact internal payload that Foundry sent from Orchestrator and Research to Document

---

## Observability Limitation In Current SDK

Installed SDK inspection on 19 April 2026 shows:

- `client.runs` is available
- `client.messages` is available
- `client.threads` is available
- there is **no public run-step API exposed in this SDK build** for connected sub-agent internals

Implication:

- we can log the outer prompt sent to Orchestrator
- we can log the system prompts configured for Orchestrator, Research, and Document
- we can log the final thread messages returned by the run
- we can log the raw top-level response, parsed JSON, and normalized final result
- but we cannot yet guarantee exact per-sub-agent prompt and response capture through this SDK alone

So the current trace gives **full visibility at the backend boundary** and **partial visibility inside Foundry**.

---

## Implemented Trace Contract

`backend/activities/run_foundry_agents.py`

Opt-in environment flags:

- `FOUNDRY_PROMPT_TRACE_ENABLED=1`
- `FOUNDRY_PROMPT_TRACE_CHUNK_SIZE=12000` (optional)

Marker:

- `FOUNDRY_PROMPT_TRACE`

Trace kinds emitted:

- `prompt_context`
- `orchestrator_user_prompt`
- `thread_messages`
- `raw_response`
- `parsed_response`
- `normalized_result`

Stable fields on every trace record:

- `incident_id`
- `round`
- `trace_kind`
- `content_type`
- `chunk_index`
- `chunk_count`
- `metadata`
- `content`

Additional metadata when available:

- `thread_id`
- `run_id`
- `agent_id`
- configured models

This is intentionally designed so an admin page can later group traces by:

- incident
- follow-up round
- run and thread
- trace kind

---

## Why This Helps Root-Cause Analysis

For one incident we can now compare:

1. the exact follow-up prompt sent to Orchestrator
2. the configured system prompts for all three agents
3. the full thread message dump returned by Foundry
4. the raw top-level response
5. the parsed JSON package
6. the normalized final result stored to Cosmos and UI

This lets us answer the most important question quickly:

- Did the Document Agent already produce the wrong BPR answer?
- Or did the backend rewrite a good answer into a worse one?

If `parsed_response.operator_dialogue` is already bad, the issue is upstream.
If `parsed_response.operator_dialogue` is good but `normalized_result.operator_dialogue` becomes generic, the backend guardrail is at fault.

---

## Incident-Scoped Retrieval Pattern

The traces are emitted to Application Insights as structured JSON log lines with the `FOUNDRY_PROMPT_TRACE` marker.

Example KQL to fetch one incident:

```kusto
traces
| where message has "FOUNDRY_PROMPT_TRACE"
| where message has '"incident_id":"INC-2026-0006"'
| order by timestamp asc
```

More structured version for later admin and API work:

```kusto
traces
| where message has "FOUNDRY_PROMPT_TRACE"
| extend payload = parse_json(extract("FOUNDRY_PROMPT_TRACE\\s+(\\{.*\\})", 1, message))
| where tostring(payload.incident_id) == "INC-2026-0006"
| project
    timestamp,
    incident_id = tostring(payload.incident_id),
    round = toint(payload.round),
    trace_kind = tostring(payload.trace_kind),
    chunk_index = toint(payload.chunk_index),
    chunk_count = toint(payload.chunk_count),
    metadata = payload.metadata,
    content = tostring(payload.content)
| order by timestamp asc, round asc, trace_kind asc, chunk_index asc
```

That query shape is enough to back a future endpoint such as:

- `GET /api/incidents/{id}/agent-traces`

which can then power an IT Admin or Auditor troubleshooting page.

---

## Current Root-Cause Hypothesis Before Rerun

Most likely failure order:

1. Research grounding for BPR-specific constraints is incomplete or wrong.
2. Document synthesis falls back to the previous recommendation instead of answering the follow-up question directly.
3. Backend guardrail may hide some nuance, but is probably not the primary cause unless the parsed response looks good and the normalized result looks worse.

So the next validation step is not another model swap. It is:

1. enable prompt trace logging
2. rerun the BPR-focused follow-up scenario
3. inspect `parsed_response` vs `normalized_result`
4. inspect whether thread messages reveal missing BPR evidence or missing direct-answer behavior

---

## Validated Findings From `INC-2026-0007`

Prompt trace logging was enabled and validated live on `INC-2026-0007`.

### 1. The bad operator text is already present in the Foundry response

Round 0 and round 1 both showed the same pattern:

- `raw_response.operator_dialogue` was already poor
- `parsed_response.operator_dialogue` matched the same poor text
- `normalized_result.operator_dialogue` matched it again

This rules out the backend normalization layer as the primary source of the bad BPR follow-up answer for this incident.

In other words: **the backend did not degrade a good answer into a bad one**.
The weak answer was already produced inside the Foundry agent flow.

### 2. The live Foundry agent instructions match the repo prompts exactly

The live Foundry agent definitions were fetched directly with `client.get_agent(...)` for:

- `asst_NDuVHHTsxfRvY1mRSd7MtEGT` (Research)
- `asst_AXgt7fxnSnUh5WXauR27S40L` (Document)
- `asst_CNYK3TZIaOCH4OPKcP4N9B2r` (Orchestrator)

The SHA-256 hashes of the live instructions matched the repo prompt files exactly:

- Research: `11ebad734e3ce0ea6602d64df2e5023e87ddcdd443665c701569dec5d72349ce`
- Document: `9189ab17267ab5f6565e7b8deaeeed970aba847462cc0bb63b5f3734243216a4`
- Orchestrator: `8e4981288998c3ad81b1247211a12ce83f34fed0ffb8e902ff807dc692aa7621`

This rules out one earlier hypothesis: **the live Foundry agents were not stale**.
They were already using the prompt text currently stored in the repository.

### 3. The live Document response still violates its contract

Even with the correct live instructions, the Foundry output still violated the intended contract.

Examples seen in `INC-2026-0007` output:

- round 0 `operator_dialogue` used follow-up phrasing (`recommendation remains`) even though there was no follow-up yet
- round 1 follow-up did not answer the specific BPR question and instead returned a generic recommendation rewrite
- required fields from the Document prompt contract were missing from the live output in the earlier rounds, such as `tool_calls_log`, `work_order_id`, and `audit_entry_id`

That means the dominant problem is currently **instruction adherence / runtime behavior inside the Foundry multi-agent flow**, not a stale prompt deployment and not backend post-processing.

### 4. Current Python SDK cannot enable strict JSON schema mode

The installed `azure-ai-agents` package exposes the Document agent `response_format` with `strict: false` in the service response.

The backend provisioning script was tested with `ResponseFormatJsonSchema(..., strict=True)` and failed at runtime with:

```text
TypeError: ResponseFormatJsonSchema.__init__() got an unexpected keyword argument 'strict'
```

Implication:

- the service clearly knows about `strict`
- but the currently installed Python SDK model class does not allow setting it directly
- so strict schema enforcement cannot currently be enabled from this repo with the installed SDK alone

This is an important platform limitation because it explains why the Document output can drift away from the intended contract even though a schema is attached.

### 5. Two local issues were still worth fixing

Two repo-side problems were confirmed and corrected even though they were not the main source of the BPR answer quality bug:

1. **Prompt trace path bug in Azure Functions deployment**
  - runtime tried to read prompts from `/home/site/agents/prompts/...`
  - deployed files actually live under the function app content root
  - fix: trace logging now resolves prompts more defensively and prefers live Foundry agent instructions when available

2. **Outer prompt schema drift in `run_foundry_agents.py`**
  - the backend’s illustrative JSON schema no longer matched the stricter Document Agent contract
  - fix: the prompt example now includes the missing contract fields and avoids the older evidence citation shape that conflicted with the Document schema

### 6. Additional operational finding

`INC-2026-0007` also showed a runtime stability issue unrelated to the BPR reasoning bug:

- the first `run_foundry_agents` attempt started and logged the startup stagger
- then it disappeared without completion or Foundry run start
- Durable later re-ran the same activity and the second attempt succeeded

So there are now two separate problems to track:

1. **Reasoning / follow-up quality problem** inside the Foundry agent flow
2. **Occasional activity stall / retry behavior** before the Foundry run starts

### 7. Function App agent ID configuration was also broken in live dev

During the same investigation, the live Function App settings were checked and these values were blank:

- `ORCHESTRATOR_AGENT_ID`
- `RESEARCH_AGENT_ID`
- `DOCUMENT_AGENT_ID`

The repo root cause was in IaC:

- `infra/modules/functions.bicep` hardcoded those three app settings to empty strings

That did not explain the poor BPR answer itself, but it did explain why some prompt traces showed:

- `<prompt file unavailable: research_system.md>`
- `<prompt file unavailable: document_system.md>`

Fix applied:

1. parameterized all three agent IDs through `infra/modules/functions.bicep`
2. threaded them through `infra/main.bicep`
3. pinned the current dev values in `infra/parameters/dev.bicepparam`
4. updated the live Function App settings to the actual agent IDs

After that fix, fresh prompt-context traces again contained actual prompt content for the connected agents instead of the placeholder text.

### 8. Fresh post-deploy validation on `INC-2026-0008` confirmed the backend safeguard

A fresh spray-rate incident (`INC-2026-0008`) was created after the latest backend deploy so the validation would not be contaminated by the earlier mixed `INC-2026-0007` rounds.

Observed sequence:

1. round 0 completed normally and returned the incident to `pending_approval`
2. the same operator follow-up question was replayed:
  - `Check if the BPR for Metformin HCl 500mg has a direct requirement to stop the line at a spray rate of 138 g/min for 35 minutes. If there is no direct requirement, adjust the recommendation and batch disposition using the actual BPR and SOP limits.`
3. App Insights showed a clean follow-up run:
  - `run_foundry_agents: incident=INC-2026-0008 round=1`
  - `prompt_context` was emitted for round 1
4. the follow-up response persisted successfully as `INC-2026-0008-agent-response-1-...`

Persisted round 1 `operator_dialogue`:

```text
I reviewed your follow-up question: "Check if the BPR for Metformin HCl 500mg has a direct requirement to stop the line at a spray rate of 138 g/min for 35 minutes. If there is no direct requirement, adjust the...". I did not find retrieved BPR or SOP evidence in bpr Product NOR/PAR that directly says to stop the line at this condition; the closest cited requirement is "Product NOR: 75–105 g/min; Product PAR: 50–200 g/min.". The recommendation and root-cause hypothesis remain unchanged based on the available evidence. Recommendation remains: Immediately verify the calibration of the flowmeter and inspect the tubing and nozzle for wear or blockages.
```

Persisted `ai_analysis` after round 1 also showed:

- `batch_disposition = hold_pending_review`
- recommendation unchanged

This is the important validation result:

- the follow-up answer now explicitly answers the direct document-requirement question
- it states that no retrieved BPR/SOP evidence directly requires stopping the line at that condition
- it cites the closest retrieved constraint instead of only repeating the previous recommendation

So the new backend normalization path is now validated on a fresh live incident.

Residual quality gap still visible in the live wording:

- the phrasing is still awkward (`in bpr Product NOR/PAR`)
- the echoed operator question is truncated
- the final sentence still repeats the recommendation text verbatim

So the fix is effective for the core yes/no requirement-answering failure, but the wording is still not fully polished.

---

## Updated Root-Cause Position

After the live trace validation, the strongest current conclusion is:

1. The original poor BPR follow-up answer was being produced inside the Foundry agent flow.
2. The backend normalization layer was not the main source of the originally validated defect on `INC-2026-0007`.
3. A separate live configuration problem existed: Function App agent IDs were blank in IaC and in the deployed app settings, which degraded prompt trace visibility for Research and Document.
4. The live Foundry prompts are the same as the repo prompts, so the main answer-quality issue was not caused by stale prompt deployment.
5. The platform is not currently giving us strict response-schema enforcement through the installed Python SDK, which likely contributes to contract drift.
6. A narrow backend safeguard is now validated for one important class of failure: follow-up questions that ask whether a BPR/SOP/document directly requires an action.

The next effective remediation path is therefore:

1. keep incident-scoped traces enabled
2. preserve the new backend safeguard for direct-requirement follow-up questions
3. optionally polish the rewrite wording so it sounds less mechanical while keeping the explicit yes/no answer shape
4. re-run on a fresh incident after each prompt or orchestration change
5. separately investigate the intermittent pre-run stall in `run_foundry_agents`