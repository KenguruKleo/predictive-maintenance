# Microsoft Entra Auth And App Role Guide

← [README](../README.md) · [T-035](../tasks/T-035-rbac.md)

> **Purpose:** central reference for Sentinel Intelligence Entra auth settings and app role assignment.
> **Scope:** project authentication and application roles, not Azure resource IAM.

---

## Project Entra/Auth Reference

| Item | Value | Notes |
| --- | --- | --- |
| Deployed frontend URL | `https://calm-flower-0a6d7f90f.7.azurestaticapps.net` | Azure Static Web App |
| Entra login user | `odl_user_2177134@sandboxailabs1009.onmicrosoft.com` | current documented demo login |
| Tenant ID | `baf5b083-4c53-493a-8af7-a6ae9812014c` | used by MSAL authority |
| SPA client ID | `1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9` | `sentinel-intelligence-spa` |
| API client ID | `38843d08-f211-4445-bcef-a07d383f2ee6` | `sentinel-intelligence-api` |
| API base URL | `https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api` | frontend backend target |

### Frontend Auth Flow

- The frontend signs users in with Entra ID through the SPA app registration `sentinel-intelligence-spa`.
- Initial login uses OIDC scopes only: `openid`, `profile`, `email`.
- After login, the frontend acquires an API access token for `sentinel-intelligence-api`.
- The backend authorizes requests from the access token `roles` claim.

### Frontend Deploy-Time Auth Values

These values are currently passed to the frontend as deploy-time configuration/secrets:

- `VITE_ENTRA_TENANT_ID=baf5b083-4c53-493a-8af7-a6ae9812014c`
- `VITE_ENTRA_SPA_CLIENT_ID=1bdb80fb-950c-45b8-be9c-8f8a7fa26ca9`
- `VITE_ENTRA_API_CLIENT_ID=38843d08-f211-4445-bcef-a07d383f2ee6`
- `VITE_API_BASE_URL=https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api`

### Manual CLI Token For Protected API Calls

Use this flow when you want to call protected backend endpoints manually from `curl`.

```bash
az login --tenant "baf5b083-4c53-493a-8af7-a6ae9812014c"

TOKEN=$(az account get-access-token \
  --scope "api://38843d08-f211-4445-bcef-a07d383f2ee6/access_as_user" \
  --query accessToken -o tsv)
```

Notes:

- Use the delegated scope `api://38843d08-f211-4445-bcef-a07d383f2ee6/access_as_user` for Azure CLI manual testing.
- Do **not** use `az login --scope "api://38843d08-f211-4445-bcef-a07d383f2ee6/.default"` for this CLI flow. With Azure CLI that can fail with `AADSTS650057 invalid resource` because `/.default` expects pre-configured delegated permissions on the Azure CLI client.
- If `az account get-access-token --scope "api://38843d08-f211-4445-bcef-a07d383f2ee6/access_as_user"` returns a consent error, grant user or admin consent for that API delegated scope in Microsoft Entra ID and retry.

### Manual HITL Decision Request

Once you have a valid bearer token, call the deployed decision endpoint like this:

```bash
# Approve
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "approved", "comments": "Approved for CAPA execution"}'

# Reject
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "rejected", "reason": "False positive"}'

# Request more info
curl -X POST "https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api/incidents/INC-2026-NNNN/decision" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "more_info", "question": "What was the batch temperature at the time of deviation?"}'
```

Decision endpoint notes:

- The deployed `decision` endpoint derives caller identity and role from the Entra bearer token.
- Do **not** send `user_id` or role fields in the request body.

---

## When To Use This Guide

Use this guide when you need to:

- assign a new project role to a user
- change a user from `ITAdmin` to `QAManager`
- verify why the UI still shows the old role after a change

---

## Important Distinction

For this project, user access is controlled by **Entra app roles** in the `roles` claim of the access token.

- Use **Microsoft Entra ID** → **Enterprise applications** → **sentinel-intelligence-api** → **Users and groups**
- Do **not** use Azure subscription or resource group **IAM** for these app roles
- Built-in tenant roles such as **IT Administrator** are separate from project roles like `ITAdmin` and `QAManager`

The application role names used by this project are:

| Portal role / claim | UI role | Purpose |
| --- | --- | --- |
| `Operator` | `operator` | production-floor incident decisions |
| `QAManager` | `qa-manager` | escalations, overrides, manager dashboard |
| `MaintenanceTech` | `maintenance-tech` | work-order follow-up |
| `Auditor` | `auditor` | audit trail read-only |
| `ITAdmin` | `it-admin` | templates + analytics |

---

## Portal Steps: Change A User From IT Admin To QA Manager

1. Open [Azure Portal](https://portal.azure.com).
2. Go to **Microsoft Entra ID**.
3. Open **Enterprise applications**.
4. Search for and open **sentinel-intelligence-api**.
5. Open **Users and groups**.
6. Select the user whose role you want to change.
7. Remove the existing `ITAdmin` assignment.
8. Click **Add user/group**.
9. Select the same user.
10. In **Role**, choose `QAManager`.
11. Click **Assign**.

This is the primary place to manage roles for the deployed app because the frontend acquires an API access token and the backend authorizes requests from the token's `roles` claim.

---

## If You Also Need To Remove A Built-In Tenant Admin Role

If the same user was given the real Entra directory role **IT Administrator**, remove it separately:

1. Go to **Microsoft Entra ID**.
2. Open **Roles and administrators**.
3. Search for **IT Administrator**.
4. Open **Assignments**.
5. Remove the user if they should no longer have tenant admin permissions.

This step is optional and independent from the project app role change above.

---

## Verify The Change

After updating the role assignment:

1. Sign out from the web app.
2. Sign in again.
3. If the old role still appears, clear session storage or retry in an incognito window.
4. If needed, paste the fresh access token into [jwt.ms](https://jwt.ms) and confirm the `roles` claim contains `QAManager` instead of `ITAdmin`.

---

## Notes For This Repository

- App roles are defined in [tasks/T-035-rbac.md](../tasks/T-035-rbac.md).
- The frontend requests an API token for `sentinel-intelligence-api` and uses its `roles` claim for role-aware UI.
- The backend validates the same `roles` claim before allowing protected actions.
