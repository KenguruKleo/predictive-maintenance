# T-035 · RBAC Setup (Azure Entra ID — 5 Roles + Token Validation)

← [Tasks](./README.md) · [04 · Action Plan](../04-action-plan.md)

**Priority:** 🟠 HIGH
**Status:** ✅ DONE
**Blocks:** T-031 (role-filtering in API), T-029 (role check in decision API)
**Depends on:** Azure Entra ID tenant access
**Gap:** Gap #2 Security ✅

---

## Roles

| Role Name | App Role Claim | Description |
|---|---|---|
| `operator` | `Operator` | Production floor — receives alerts, approves/rejects |
| `qa-manager` | `QAManager` | All incidents, escalations, override approvals |
| `maintenance-tech` | `MaintenanceTech` | Work orders read-only |
| `auditor` | `Auditor` | Full audit trail read-only |
| `it-admin` | `ITAdmin` | Templates + analytics |

---

## App Registration (Azure Portal / Bicep)

```
App Registration: sentinel-intelligence-api
- Expose API: api://<client-id>
- App Roles: 5 roles above (type: User)

App Registration: sentinel-intelligence-spa  
- SPA redirect URI: https://<static-web-app-url>
- API permissions: sentinel-intelligence-api (all roles)
```

---

## Backend token validation

```python
# backend/utils/auth.py
from azure.identity import DefaultAzureCredential
import jwt

def get_current_user(req: func.HttpRequest) -> User:
    token = req.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Missing token")
    
    claims = validate_jwt(token)  # validates signature against Entra ID JWKS
    return User(
        id=claims["preferred_username"],
        name=claims["name"],
        roles=claims.get("roles", [])
    )

def require_role(user: User, allowed_roles: list[str]):
    if not any(r in user.roles for r in allowed_roles):
        raise HTTPException(403, f"Role required: {allowed_roles}")
```

---

## Frontend (MSAL)

```typescript
// src/auth/authConfig.ts
export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID}`,
  }
};

// src/auth/useAuth.ts  
// - login(), logout(), getAccessToken()
// - role extracted from token claims → stored in context
// - ProtectedRoute component wraps pages requiring specific roles
```

---

## Mock users for demo (seeded)

| User | Role | Password |
|---|---|---|
| ivan.petrenko | operator | (demo user in Entra ID) |
| olena.kovalenko | qa-manager | (demo user) |
| mykola.sydorenko | maintenance-tech | (demo user) |
| tetiana.lysenko | auditor | (demo user) |
| admin.sentinel | it-admin | (demo user) |

---

## Definition of Done

- [ ] App registrations created in Entra ID (or mocked via local `USE_LOCAL_MOCK_DATA` flag)
- [ ] Backend `require_role()` returns 403 for wrong role
- [ ] Frontend `ProtectedRoute` redirects unauthorized users
- [ ] 5 demo users created and assigned to app roles
- [ ] Token includes `roles` claim (verified in jwt.ms)
