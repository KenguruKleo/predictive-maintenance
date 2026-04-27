# Operator Test Scenario for INC-2026-0049

## Goal
Validate that after a More Info request, the agent:
- responds in clear human language in the operator dialog;
- explains what it checked;
- explicitly states what changed (or why nothing changed) in the recommendation.

## Preconditions
- Incident created: INC-2026-0049
- Status: Pending Approval
- The right-side panel includes the Need More Info button and Send question form

## Recommended Test Order
1. Check an alternative hypothesis (sensor vs tubing)
2. Re-check batch disposition
3. Explicitly verify whether the agent explains changes between rounds

## Ready-to-use Request Texts

### Request 1 (alternative cause)
Check if the cause could be in the sensor or flowmeter calibration, rather than the tubing. If so, review the root cause and recommendation with this hypothesis in mind.

### Request 2 (BPR requirement check)
Check if the BPR for Metformin HCl 500mg has a direct requirement to stop the line at a spray rate of 138 g/min for 35 minutes. If there is no direct requirement, adjust the recommendation to be less stringent and explain why.

### Request 3 (historical incidents)
Compare the current case with historical incidents for GR-204: how many times a similar deviation was closed without tubing replacement. If most cases were closed without replacement, update the recommendation and justify it.

### Request 4 (alternative action plan)
Provide an alternative plan: what do we do if tubing inspection finds no defects? Update the root cause hypothesis and provide 2-3 next steps with priorities.

### Request 5 (batch disposition re-evaluation)
Re-evaluate the batch disposition: is hold pending review truly mandatory for this case, or is a conditional release pending testing possible? Provide clear decision criteria.

### Request 6 (cross-round change control)
State exactly what changed after my request: recommendation, root cause, risk level, or batch disposition. If nothing changed, explain why based on evidence.

## What Counts as a Good Agent Response
- Starts with a short explanation of what it checked based on the operator request.
- Provides a clear conclusion: recommendation changed or did not change.
- If unchanged: explains why with facts from available data.
- If changed: explicitly names what was updated (recommendation, root cause, risk, or disposition).

## Minimal Check After Each Request
1. A new agent follow-up appears in chat.
2. The text does not fully duplicate the central Decision Package block.
3. The response directly addresses the operator's question.
4. The response explains either the change or no-change outcome.
