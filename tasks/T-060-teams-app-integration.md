# T-060 · Microsoft Teams App Integration

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟢 LOW  
**Status:** 🔜 TODO  
**Depends on:** T-029, T-030, T-031, T-033, T-035, T-041, T-057  
**Gap:** Enterprise collaboration channel, operator/QA adoption, post-hackathon hardening

---

## Goal

Add a Microsoft Teams app surface for Sentinel Intelligence so operators and QA managers can receive incident notifications and make human-in-the-loop decisions from Teams while the existing backend remains the system of record.

The Teams integration must not create a second approval workflow. Teams should call the existing decision API and preserve the same Durable Functions, Cosmos DB, notification, and audit trail semantics used by the React/Electron operator console.

---

## What a Teams app means here

A Microsoft Teams app is an app package, not a hosted application by itself. The package contains:

- `manifest.json` describing app capabilities, domains, tabs, bot IDs, permissions, and SSO configuration
- color and outline PNG icons
- optional packaged metadata for Microsoft 365 app capabilities

Teams installs that package and then loads external HTTPS resources:

- the existing React frontend as a Teams tab
- a notification/workflow bot endpoint hosted in Azure
- backend APIs already exposed by Azure Functions

For Sentinel Intelligence, the target Teams app should include:

| Capability | Purpose |
| --- | --- |
| Personal tab | Open the operator/QA incident console inside Teams |
| Optional channel tab | Pin an incident queue for a production or QA team |
| Notification bot | Send proactive incident approval cards |
| Adaptive Cards | Show incident summary and actions: Approve, Reject, More info, Open full package |
| Teams SSO | Reuse the signed-in Teams/Entra identity for the tab |

---

## Target architecture

```text
Durable Orchestrator
  → notify_operator
  → Cosmos notifications + SignalR
  → Teams notification adapter
  → Teams bot proactive message
  → Adaptive Card action
  → existing POST /api/incidents/{id}/decision
  → Durable raise_event("operator_decision")
```

Teams is an additional collaboration channel. SignalR remains the real-time channel for the web and Electron clients.

---

## Automation model

### What can be automated with Bicep

Bicep can provision Azure-side resources for the Teams integration:

- Azure Bot Service registration / bot channel resource where applicable
- hosting for the bot endpoint, for example Azure Functions, App Service, or Container Apps
- Key Vault entries or references for bot secrets and Graph/Teams configuration
- managed identities, app settings, Application Insights, and monitoring
- existing Azure resources consumed by the tab/backend, such as Static Web Apps and Functions outputs

### What should not be expected from Bicep alone

Bicep/ARM does not publish a Teams app package into Microsoft Teams tenant app catalog. Teams app catalog, app package upload, and many Entra app registration lifecycle steps live in Microsoft 365 / Microsoft Graph / Teams Developer Portal territory, not normal Azure Resource Manager territory.

Use one of these automation paths for the Teams app lifecycle:

| Path | Use for |
| --- | --- |
| Microsoft 365 Agents Toolkit / CLI | Preferred developer workflow: create/update Teams app, Entra app, bot app, package, validate, publish |
| Microsoft Graph app catalog APIs | CI/CD publishing to tenant app catalog when admin consent and permissions are available |
| Teams Developer Portal | Manual bootstrap and troubleshooting |
| Bicep | Azure infrastructure behind the app, not the Teams package publication itself |

Recommended approach: keep Bicep for Azure infrastructure, and add `m365agents.yml` plus CI steps for Teams manifest packaging/publishing.

---

## Scope

### A. Teams app package

- [x] Add `teamsapp/manifest.json` or manifest template with environment placeholders
- [x] Add Teams color and outline icons
- [x] Configure `validDomains` for Static Web Apps, Functions, and bot endpoints
- [x] Configure personal tab pointing to the existing React frontend route
- [ ] Configure bot capability and command descriptions
- [x] Define package output path, for example `teamsapp/dist/sentinel-intelligence.zip`

Current baseline: `teamsapp/dist/sentinel-intelligence-teams.zip` installs as `Sentinel` / `Sentinel Intelligence`, uses the production app icon, opens `https://calm-flower-0a6d7f90f.7.azurestaticapps.net/teams.html`, and keeps `teams-test.html` as a compatibility redirect.

### B. Teams tab + SSO

- [ ] Add Teams host detection in the frontend
- [ ] Add TeamsJS initialization only when running inside Teams
- [ ] Support Teams SSO token acquisition for the tab
- [ ] Send the Teams SSO token to the backend as an Authorization bearer token
- [ ] Validate the token server-side and map Entra app roles to existing roles
- [ ] Keep browser/Electron MSAL behavior unchanged

Current implementation note: the frontend now detects Teams iframe hosting, uses TeamsJS `authentication.getAuthToken()` for the Teams login path, and blocks iframe MSAL redirects from silently stalling. Browser and Electron still use the existing MSAL flow. The Teams manifest includes `webApplicationInfo` for `api://38843d08-f211-4445-bcef-a07d383f2ee6`; the Entra API registration still needs final validation for exposed scope, authorized Teams clients, and role assignments in each tenant.

### C. Notification bot

- [ ] Add a bot service endpoint for Teams messages and invoke/action payloads
- [ ] Store conversation references for operator and QA users or channels
- [ ] Add a backend notification adapter called from `notify_operator`
- [ ] Send proactive Adaptive Cards for `pending_approval` and `escalated` incidents
- [ ] Include only summary data in cards; link to the full decision package tab for evidence-heavy review
- [ ] Update original Teams card after a decision is accepted, rejected, expired, or escalated

### D. Teams approval actions

- [ ] Implement Adaptive Card actions for Approve, Reject, More info, and Open incident
- [ ] Route Teams actions through the existing decision endpoint instead of duplicating orchestration logic
- [ ] Validate actor role, incident status, stale card version, and idempotency before accepting a Teams action
- [ ] Persist Teams metadata in the audit trail: `decisionSource=teams`, `tenantId`, `aadObjectId`, `conversationId`, `activityId`, `teamsMessageId`
- [ ] Reject or require full-tab review for high-risk/blocked cases where full WO/audit forms must be edited

### E. Automation and CI/CD

- [ ] Add `m365agents.yml` for Teams app create/update/package/publish flow
- [ ] Add scripts for manifest rendering and app package validation
- [ ] Add CI job that builds the Teams app package from environment-specific values
- [ ] Optionally publish package to the tenant app catalog using Microsoft Graph after admin-approved permissions are available
- [ ] Document required Microsoft 365 admin roles, app catalog policies, and custom app upload settings
- [ ] Keep Teams app IDs, bot IDs, tenant IDs, and endpoints environment-specific and compatible with T-057 config externalization

---

## Suggested implementation order

1. Create the Teams manifest package with a read-only personal tab that opens the current frontend.
2. Enable Teams SSO and backend token validation.
3. Add notification bot and store conversation references on install/welcome events.
4. Send incident summary Adaptive Cards from the existing `notify_operator` activity.
5. Wire card actions to the existing decision API with role, status, and idempotency checks.
6. Add app package automation with Microsoft 365 Agents Toolkit CLI or Graph-based CI publishing.
7. Add operational docs for installation, tenant app catalog publishing, and troubleshooting.

---

## Open decisions

- Personal bot vs channel bot as the default notification target
- Whether Approve is allowed directly in a card or must open the full tab for high-risk incidents
- Whether Teams should use the existing SPA Entra app registration or a dedicated Teams SSO registration
- Whether the bot is implemented as Azure Functions Python, Node.js Bot Framework, or a small Container Apps service
- Whether CI publishes directly to the tenant app catalog or only produces a signed/reviewable package

---

## Definition of Done

- [ ] Teams app package can be generated reproducibly from repository files
- [ ] The app can be installed in a dev tenant and opens the Sentinel Intelligence tab inside Teams
- [ ] Teams SSO works without an extra login prompt for allowed users
- [ ] Operators/QA receive proactive Teams notifications for pending/escalated incidents
- [ ] Teams Adaptive Card actions call the existing decision API and wake the existing Durable orchestration
- [ ] Teams-originated decisions appear in the same audit trail and approval transcript as web/Electron decisions
- [ ] Stale card, duplicate click, unauthorized role, and already-finalized incident cases are rejected safely
- [ ] Bicep provisions only Azure-side dependencies; Microsoft 365 app catalog publication is automated separately via Agents Toolkit or Graph
- [ ] Installation and update steps are documented for developer sideloading and tenant-wide admin publishing
