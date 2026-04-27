# Statement Update Proposals

This file lists candidate statement updates discovered during translation and repository consistency review.

## Proposal 1
- Source file: `04-action-plan.md`
- Source statement: "Final submission deadline: first week of May 2026" and sprint timelines still centered on April implementation windows.
- Why update: The current date context is late April 2026; several timeline phrases may become stale quickly and can create confusion for reviewers.
- Suggested replacement: "Final submission window: May 2026 (exact date per hackathon schedule updates)."
- Confidence: medium

## Proposal 2
- Source file: `01-requirements.md`
- Source statement: WAF pillars shown as entirely missing in some sections while other sections already mark parts of monitoring/queueing/instrumentation as implemented.
- Why update: The document contains both implemented and missing statuses for reliability/observability controls; this can read as contradictory without explicit scope boundaries.
- Suggested replacement: "WAF controls are partially implemented for the prototype; full production-grade coverage remains in backlog tasks T-038, T-039, T-040, T-047, T-048, T-049, T-050, T-051."
- Confidence: high

## Proposal 3
- Source file: `docs/hackathon-scope.md`
- Source statement: "Architecture is fully designed" wording appears alongside broad prototype omissions.
- Why update: The claim is directionally valid but can be interpreted as implementation-complete unless explicitly scoped as design-complete.
- Suggested replacement: "The target architecture is design-complete; the prototype implements critical-path flows while production-hardening controls remain in the post-hackathon backlog."
- Confidence: high

## Proposal 4
- Source file: `02-architecture.md` and linked narrative docs
- Source statement: Some sections present production controls (VNet/Private Endpoints/CA/PIM/DR/load tests) without immediate nearby note that prototype scope excludes them.
- Why update: Readers may interpret production controls as currently deployed unless a local scope note is present in the same section.
- Suggested replacement: Add a short line under each production control block: "Prototype status: planned/not deployed yet; see docs/hackathon-scope.md and tasks T-047..T-051."
- Confidence: medium

## Proposal 5
- Source file: `docs/architecture-history.md`
- Source statement: Changelog entries are clear but do not always map to explicit evidence links (PR, commit, or task file) for each major claim.
- Why update: Adding evidence links improves auditability for judges and reviewers.
- Suggested replacement: For each changelog row, add "Evidence:" links to the matching task document and/or implementation artifact.
- Confidence: medium
