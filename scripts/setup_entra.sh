#!/usr/bin/env bash
# =============================================================================
# scripts/setup_entra.sh
# T-035 · RBAC Setup — Azure Entra ID App Registrations + Demo Users
#
# Creates:
#   1. App Registration: sentinel-intelligence-api  (backend, defines 5 app roles)
#   2. App Registration: sentinel-intelligence-spa  (React SPA, public client)
#   3. 5 demo users with app role assignments
#
# Prerequisites:
#   az login  (account must have Application Administrator or Global Admin role in Entra)
#
# Usage:
#   ./scripts/setup_entra.sh                     # full setup
#   ./scripts/setup_entra.sh --delete            # remove all created resources
#   ./scripts/setup_entra.sh --show              # show existing app IDs
#
# After running, copy the output values into:
#   backend/local.settings.json   (AZURE_TENANT_ID, AZURE_CLIENT_ID)
#   frontend/.env.local            (VITE_AZURE_TENANT_ID, VITE_AZURE_CLIENT_ID)
#   GitHub Secrets (for CI/CD)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — change these if your project uses different names
# ---------------------------------------------------------------------------
API_APP_NAME="sentinel-intelligence-api"
SPA_APP_NAME="sentinel-intelligence-spa"
DEMO_USER_PASSWORD="SentinelDemo2026!"   # Minimum complexity: upper+lower+digit+special

# Demo users (will be created in Entra ID)
# Parallel arrays — compatible with bash 3.2 (macOS default)
DEMO_USERNAMES=("ivan.petrenko" "olena.kovalenko" "mykola.sydorenko" "tetiana.lysenko" "admin.sentinel")
DEMO_ROLES=("Operator" "QAManager" "MaintenanceTech" "Auditor" "ITAdmin")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()    { echo -e "\033[0;36m[INFO]\033[0m  $*"; }
success() { echo -e "\033[0;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[0;33m[WARN]\033[0m  $*"; }
error()   { echo -e "\033[0;31m[ERR]\033[0m   $*" >&2; }

check_az() {
    if ! command -v az &>/dev/null; then
        error "Azure CLI not found. Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi
    if ! az account show &>/dev/null; then
        error "Not logged in. Run: az login"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# --show mode
# ---------------------------------------------------------------------------
cmd_show() {
    info "Looking up existing app registrations..."
    TENANT_ID=$(az account show --query tenantId -o tsv)
    echo ""
    echo "Tenant ID: $TENANT_ID"

    API_CLIENT_ID=$(az ad app list --filter "displayName eq '$API_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)
    SPA_CLIENT_ID=$(az ad app list --filter "displayName eq '$SPA_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)

    echo "API App Client ID ($API_APP_NAME): ${API_CLIENT_ID:-<not found>}"
    echo "SPA App Client ID ($SPA_APP_NAME): ${SPA_CLIENT_ID:-<not found>}"
    echo ""
    echo "# backend/local.settings.json"
    echo "  \"AZURE_TENANT_ID\": \"${TENANT_ID}\","
    echo "  \"AZURE_CLIENT_ID\": \"${API_CLIENT_ID:-<api-client-id>}\","
    echo ""
    echo "# frontend/.env.local"
    echo "  VITE_AZURE_TENANT_ID=${TENANT_ID}"
    echo "  VITE_AZURE_CLIENT_ID=${SPA_CLIENT_ID:-<spa-client-id>}"
}

# ---------------------------------------------------------------------------
# --delete mode
# ---------------------------------------------------------------------------
cmd_delete() {
    warn "Deleting app registrations and demo users..."

    API_CLIENT_ID=$(az ad app list --filter "displayName eq '$API_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)
    SPA_CLIENT_ID=$(az ad app list --filter "displayName eq '$SPA_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)

    if [[ -n "$API_CLIENT_ID" ]]; then
        az ad app delete --id "$API_CLIENT_ID"
        success "Deleted: $API_APP_NAME ($API_CLIENT_ID)"
    else
        warn "$API_APP_NAME not found, skipping"
    fi

    if [[ -n "$SPA_CLIENT_ID" ]]; then
        az ad app delete --id "$SPA_CLIENT_ID"
        success "Deleted: $SPA_APP_NAME ($SPA_CLIENT_ID)"
    else
        warn "$SPA_APP_NAME not found, skipping"
    fi

    TENANT_DOMAIN=$(az account show --query "user.name" -o tsv | cut -d@ -f2)
    for username in "${DEMO_USERNAMES[@]}"; do
        UPN="${username}@${TENANT_DOMAIN}"
        USER_EXISTS=$(az ad user show --id "$UPN" --query id -o tsv 2>/dev/null || true)
        if [[ -n "$USER_EXISTS" ]]; then
            az ad user delete --id "$UPN"
            success "Deleted user: $UPN"
        fi
    done

    success "Cleanup complete."
}

# ---------------------------------------------------------------------------
# Main setup
# ---------------------------------------------------------------------------
cmd_setup() {
    TENANT_ID=$(az account show --query tenantId -o tsv)
    TENANT_DOMAIN=$(az account show --query "user.name" -o tsv | cut -d@ -f2)
    info "Tenant: $TENANT_ID ($TENANT_DOMAIN)"

    # -------------------------------------------------------------------------
    # 1. API App Registration
    # -------------------------------------------------------------------------
    info "Creating API app registration: $API_APP_NAME"

    EXISTING_API=$(az ad app list --filter "displayName eq '$API_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)
    if [[ -n "$EXISTING_API" ]]; then
        warn "$API_APP_NAME already exists (appId=$EXISTING_API) — reusing"
        API_CLIENT_ID="$EXISTING_API"
    else
        API_CLIENT_ID=$(az ad app create \
            --display-name "$API_APP_NAME" \
            --sign-in-audience "AzureADMyOrg" \
            --query appId -o tsv)
        success "Created API app: $API_CLIENT_ID"
    fi

    # Expose API scope: api://<client-id>/access_as_user
    info "Setting API identifier URI..."
    az ad app update \
        --id "$API_CLIENT_ID" \
        --identifier-uris "api://${API_CLIENT_ID}" \
        2>/dev/null || warn "Could not set identifier URI (may already be set)"

    # -------------------------------------------------------------------------
    # 2. Define 5 App Roles on the API registration (idempotent — add missing only)
    # -------------------------------------------------------------------------
    info "Defining app roles on API registration..."

    # Get existing role values so we don't attempt to re-add enabled roles
    EXISTING_ROLES=$(az ad app show --id "$API_CLIENT_ID" --query "appRoles[?isEnabled].value" -o json 2>/dev/null || echo "[]")

    # Build list of roles to add (skip ones that already exist)
    # macOS mktemp requires XXXXXX at the end — use /tmp/approles_$RANDOM.json instead
    ROLES_TMP="/tmp/approles_${RANDOM}.json"

    python3 - <<PYEOF > "$ROLES_TMP"
import json, subprocess, uuid

existing = json.loads('''$EXISTING_ROLES''')

desired = [
    ("Operator",      "Operator",             "Production floor operator — receives alerts, approves or rejects incidents"),
    ("QAManager",     "QA Manager",           "QA Manager — all incidents, escalations, override approvals"),
    ("MaintenanceTech","Maintenance Technician","Maintenance Technician — work orders read-only"),
    ("Auditor",       "Auditor",              "Auditor — full audit trail read-only"),
    ("ITAdmin",       "IT Administrator",     "IT Administrator — templates and analytics"),
]

roles_to_add = [
    {
        "allowedMemberTypes": ["User"],
        "description": desc,
        "displayName": display,
        "id": str(uuid.uuid4()),
        "isEnabled": True,
        "value": value,
    }
    for value, display, desc in desired
    if value not in existing
]

print(json.dumps(roles_to_add, indent=2))
PYEOF

    ROLES_TO_ADD=$(python3 -c "import json,sys; d=json.load(open('$ROLES_TMP')); print(len(d))")

    if [[ "$ROLES_TO_ADD" -eq 0 ]]; then
        success "All app roles already exist — skipping"
        rm -f "$ROLES_TMP"
    else
        info "Adding $ROLES_TO_ADD missing app role(s)..."

        # Merge existing roles + new roles into one array for the update
        MERGED_TMP="/tmp/approles_merged_${RANDOM}.json"
        python3 - <<PYEOF2 > "$MERGED_TMP"
import json

existing_full = json.loads(subprocess.check_output(
    ["az", "ad", "app", "show", "--id", "$API_CLIENT_ID", "--query", "appRoles", "-o", "json"]
).decode()) if False else []

try:
    import subprocess
    existing_full = json.loads(subprocess.check_output(
        ["az", "ad", "app", "show", "--id", "$API_CLIENT_ID", "--query", "appRoles", "-o", "json"]
    ).decode())
except Exception:
    existing_full = []

new_roles = json.load(open("$ROLES_TMP"))
print(json.dumps(existing_full + new_roles, indent=2))
PYEOF2

        az ad app update --id "$API_CLIENT_ID" --app-roles @"$MERGED_TMP"
        rm -f "$ROLES_TMP" "$MERGED_TMP"
        success "App roles defined"
    fi

    # Get Service Principal (needed for role assignments)
    SP_ID=$(az ad sp show --id "$API_CLIENT_ID" --query id -o tsv 2>/dev/null || true)
    if [[ -z "$SP_ID" ]]; then
        SP_ID=$(az ad sp create --id "$API_CLIENT_ID" --query id -o tsv)
        success "Created service principal: $SP_ID"
    fi

    # -------------------------------------------------------------------------
    # 3. SPA App Registration (public client, no secret)
    # -------------------------------------------------------------------------
    info "Creating SPA app registration: $SPA_APP_NAME"

    EXISTING_SPA=$(az ad app list --filter "displayName eq '$SPA_APP_NAME'" --query "[0].appId" -o tsv 2>/dev/null || true)
    if [[ -n "$EXISTING_SPA" ]]; then
        warn "$SPA_APP_NAME already exists (appId=$EXISTING_SPA) — reusing"
        SPA_CLIENT_ID="$EXISTING_SPA"
    else
        SPA_CLIENT_ID=$(az ad app create \
            --display-name "$SPA_APP_NAME" \
            --sign-in-audience "AzureADMyOrg" \
            --is-fallback-public-client true \
            --query appId -o tsv)
        success "Created SPA app: $SPA_CLIENT_ID"
    fi

    # Add SPA redirect URIs
    info "Configuring SPA redirect URIs..."
    az ad app update \
        --id "$SPA_CLIENT_ID" \
        --web-redirect-uris "http://localhost:5173" "http://localhost:3000" \
        2>/dev/null || warn "Could not set redirect URIs via --web-redirect-uris (set manually in portal)"

    # Grant SPA access to API scope (requires admin consent)
    info "Granting SPA access to API..."
    API_SCOPE_RESOURCE_ACCESS=$(cat <<EOF
[{"resourceAppId":"${API_CLIENT_ID}","resourceAccess":[{"id":"e4f37ec0-e67d-4b12-a5c1-4e3d15a07e00","type":"Scope"}]}]
EOF
)
    # Note: the scope UUID above is a placeholder — actual scope ID is set automatically
    # when you expose an API. The portal/Graph is the canonical way to grant delegated perms.

    # -------------------------------------------------------------------------
    # 4. Create demo users (requires User Administrator role — graceful skip)
    # -------------------------------------------------------------------------
    info "Creating demo users..."

    # Parallel array to store created user IDs (index matches DEMO_USERNAMES)
    USER_IDS=()
    USERS_SKIPPED=false

    for i in "${!DEMO_USERNAMES[@]}"; do
        username="${DEMO_USERNAMES[$i]}"
        UPN="${username}@${TENANT_DOMAIN}"

        USER_EXISTS=$(az ad user show --id "$UPN" --query id -o tsv 2>/dev/null || true)
        if [[ -n "$USER_EXISTS" ]]; then
            warn "User $UPN already exists — reusing"
            USER_IDS[$i]="$USER_EXISTS"
        else
            CREATE_OUT=$(az ad user create \
                --display-name "${username//./ }" \
                --user-principal-name "$UPN" \
                --password "$DEMO_USER_PASSWORD" \
                --force-change-password-next-sign-in false \
                --query id -o tsv 2>&1) || true

            if echo "$CREATE_OUT" | grep -qi "insufficient privileges\|Authorization_RequestDenied\|Forbidden"; then
                warn "Insufficient privileges to create user $UPN — skipping (requires User Administrator role)"
                USER_IDS[$i]=""
                USERS_SKIPPED=true
            else
                USER_IDS[$i]="$CREATE_OUT"
                success "Created user: $UPN (id=$CREATE_OUT)"
            fi
        fi
    done

    if [[ "$USERS_SKIPPED" == "true" ]]; then
        warn "Some users could not be created automatically."
        warn "Create them manually in Azure Portal → Entra ID → Users, then re-run this script."
    fi

    # -------------------------------------------------------------------------
    # 5. Assign app roles to users
    # -------------------------------------------------------------------------
    info "Assigning app roles to demo users..."

    # Refresh role list from the registered app
    ROLE_LIST=$(az ad app show --id "$API_CLIENT_ID" --query "appRoles[].{id:id,value:value}" -o json)

    for i in "${!DEMO_USERNAMES[@]}"; do
        username="${DEMO_USERNAMES[$i]}"
        ROLE_VALUE="${DEMO_ROLES[$i]}"
        USER_ID="${USER_IDS[$i]:-}"
        UPN="${username}@${TENANT_DOMAIN}"

        if [[ -z "$USER_ID" ]]; then
            warn "No user ID for $UPN — skipping role assignment"
            continue
        fi

        # Find the role ID by value
        ROLE_ID=$(echo "$ROLE_LIST" | python3 -c "
import json, sys
roles = json.load(sys.stdin)
target = '$ROLE_VALUE'
match = next((r['id'] for r in roles if r['value'] == target), None)
print(match or '')
")

        if [[ -z "$ROLE_ID" ]]; then
            warn "Could not find role ID for $ROLE_VALUE — skipping $UPN"
            continue
        fi

        # Check if assignment already exists
        EXISTING_ASSIGN=$(az rest \
            --method GET \
            --url "https://graph.microsoft.com/v1.0/servicePrincipals/${SP_ID}/appRoleAssignedTo" \
            --query "value[?principalId=='${USER_ID}' && appRoleId=='${ROLE_ID}'].id" \
            -o tsv 2>/dev/null || true)

        if [[ -n "$EXISTING_ASSIGN" ]]; then
            warn "$UPN already has role $ROLE_VALUE — skipping"
            continue
        fi

        az rest \
            --method POST \
            --url "https://graph.microsoft.com/v1.0/servicePrincipals/${SP_ID}/appRoleAssignedTo" \
            --body "{\"principalId\":\"${USER_ID}\",\"resourceId\":\"${SP_ID}\",\"appRoleId\":\"${ROLE_ID}\"}" \
            --headers "Content-Type=application/json" \
            --output none

        success "Assigned role '$ROLE_VALUE' to $UPN"
    done

    # -------------------------------------------------------------------------
    # 6. Print summary
    # -------------------------------------------------------------------------
    echo ""
    echo "============================================================"
    echo "  T-035 RBAC Setup Complete"
    echo "============================================================"
    echo ""
    echo "  Tenant ID:       $TENANT_ID"
    echo "  API Client ID:   $API_CLIENT_ID"
    echo "  SPA Client ID:   $SPA_CLIENT_ID"
    echo ""
    echo "  Demo users (password: $DEMO_USER_PASSWORD):"
    for i in "${!DEMO_USERNAMES[@]}"; do
        printf "    %-25s → %s\n" "${DEMO_USERNAMES[$i]}@${TENANT_DOMAIN}" "${DEMO_ROLES[$i]}"
    done
    echo ""
    if [[ "$USERS_SKIPPED" == "true" ]]; then
        echo "  ⚠  Users need manual creation (Insufficient privileges):"
        echo "     1. Go to: https://portal.azure.com/#view/Microsoft_AAD_UsersAndTenants"
        echo "     2. Create each user above with password: $DEMO_USER_PASSWORD"
        echo "     3. Re-run this script to assign roles automatically"
        echo ""
    fi
    echo "  Next steps:"
    echo "  1. Add to backend/local.settings.json:"
    echo "     \"AZURE_TENANT_ID\": \"$TENANT_ID\","
    echo "     \"AZURE_CLIENT_ID\": \"$API_CLIENT_ID\","
    echo ""
    echo "  2. Add to frontend/.env.local:"
    echo "     VITE_AZURE_TENANT_ID=$TENANT_ID"
    echo "     VITE_AZURE_CLIENT_ID=$SPA_CLIENT_ID"
    echo ""
    echo "  3. Grant admin consent in Azure Portal:"
    echo "     https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade"
    echo "     → $SPA_APP_NAME → API permissions → Grant admin consent"
    echo ""
    echo "  4. Verify tokens at https://jwt.ms (check 'roles' claim)"
    echo "============================================================"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
check_az

case "${1:-}" in
    --delete) cmd_delete ;;
    --show)   cmd_show ;;
    *)        cmd_setup ;;
esac
