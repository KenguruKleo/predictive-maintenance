#!/usr/bin/env bash
# deploy-mcp.sh — Build, push, and deploy all 4 MCP server Container Apps
#
# Prerequisites:
#   - az CLI logged in: az login
#   - Bicep main.bicep already deployed at least once (so ACR + Container Apps exist)
#   - Docker available locally  OR  use --acr-build to build in Azure (no local Docker needed)
#
# Usage:
#   cd backend
#   bash scripts/deploy-mcp.sh [--acr-build] [--rg ODL-GHAZ-2177134] [--skip-deploy]
#
#   --acr-build    Use 'az acr build' instead of local Docker (builds in Azure cloud)
#   --rg <name>    Resource group (default: ODL-GHAZ-2177134)
#   --skip-deploy  Only build + push images, don't run Bicep deployment
#
# First-time workflow:
#   1. Deploy ACR only:    az deployment group create -g $RG --template-file infra/main.bicep \
#                            --parameters @infra/parameters/dev.bicepparam
#      (This creates ACR with placeholder images in Container Apps)
#   2. Build & push real images + update Container Apps:
#                          bash backend/scripts/deploy-mcp.sh --acr-build

set -euo pipefail

# ── Defaults ─────────────────────────────────────────────────────────────
RESOURCE_GROUP="${RESOURCE_GROUP:-ODL-GHAZ-2177134}"
USE_ACR_BUILD=false
SKIP_BICEP_DEPLOY=false

# ── Arg parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --acr-build)   USE_ACR_BUILD=true; shift ;;
    --skip-deploy) SKIP_BICEP_DEPLOY=true; shift ;;
    --rg)          RESOURCE_GROUP="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

RG="$RESOURCE_GROUP"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"

echo "=== Sentinel Intelligence — MCP Container Apps Deploy ==="
echo "Resource Group: $RG"
echo "Backend Dir:    $BACKEND_DIR"
echo ""

# ── Resolve unique suffix from existing Function App ─────────────────────
echo "[1/5] Resolving unique suffix from existing resources..."
FUNC_APP=$(az functionapp list -g "$RG" \
  --query "[?contains(name, 'func-sentinel-intel-dev-')].name | [0]" -o tsv 2>/dev/null || echo "")

if [[ -z "$FUNC_APP" || "$FUNC_APP" == "None" ]]; then
  echo "ERROR: No Function App found in $RG matching 'func-sentinel-intel-dev-*'"
  echo "  Run: az deployment group create -g $RG --template-file infra/main.bicep \\"
  echo "         --parameters @infra/parameters/dev.bicepparam"
  exit 1
fi

UNIQUE_SUFFIX="${FUNC_APP##func-sentinel-intel-dev-}"
echo "  Unique suffix: $UNIQUE_SUFFIX"
ACR_NAME="acrsntl${UNIQUE_SUFFIX}"

# ── Get ACR login server ──────────────────────────────────────────────────
echo "[2/5] Getting ACR login server for '$ACR_NAME'..."
ACR_LOGIN_SERVER=$(az acr show -n "$ACR_NAME" -g "$RG" --query loginServer -o tsv 2>/dev/null || echo "")

if [[ -z "$ACR_LOGIN_SERVER" || "$ACR_LOGIN_SERVER" == "None" ]]; then
  echo "ERROR: ACR '$ACR_NAME' not found in $RG."
  echo "  Deploy infra first: az deployment group create -g $RG \\"
  echo "    --template-file infra/main.bicep --parameters @infra/parameters/dev.bicepparam"
  exit 1
fi
echo "  ACR: $ACR_LOGIN_SERVER"

# ── MCP servers to build ──────────────────────────────────────────────────
declare -A MODULE_TO_APP=(
  ["mcp_sentinel_db"]="mcp-db-${UNIQUE_SUFFIX}"
  ["mcp_sentinel_search"]="mcp-search-${UNIQUE_SUFFIX}"
  ["mcp_qms"]="mcp-qms-${UNIQUE_SUFFIX}"
  ["mcp_cmms"]="mcp-cmms-${UNIQUE_SUFFIX}"
)

declare -A MODULE_TO_IMAGE=(
  ["mcp_sentinel_db"]="${ACR_LOGIN_SERVER}/mcp-sentinel-db:latest"
  ["mcp_sentinel_search"]="${ACR_LOGIN_SERVER}/mcp-sentinel-search:latest"
  ["mcp_qms"]="${ACR_LOGIN_SERVER}/mcp-qms:latest"
  ["mcp_cmms"]="${ACR_LOGIN_SERVER}/mcp-cmms:latest"
)

# ── Build & push images ───────────────────────────────────────────────────
echo "[3/5] Building and pushing MCP images..."
cd "$BACKEND_DIR"

if $USE_ACR_BUILD; then
  echo "  Using 'az acr build' (cloud-side build, no local Docker needed)"
  for MODULE in "${!MODULE_TO_IMAGE[@]}"; do
    IMAGE="${MODULE_TO_IMAGE[$MODULE]}"
    IMAGE_NAME="${IMAGE##*/}"  # strip registry prefix for the tag arg
    echo "  Building $MODULE → $IMAGE ..."
    az acr build \
      --registry "$ACR_NAME" \
      --image "$(basename "$IMAGE")" \
      --build-arg "SERVER_MODULE=${MODULE}" \
      --file Dockerfile.mcp \
      . \
      --no-wait
    echo "    Submitted (--no-wait). Check: az acr task list-runs -r $ACR_NAME -g $RG"
  done
  echo ""
  echo "  Waiting for all ACR builds to complete..."
  sleep 10  # Wait a bit then check
  az acr task list-runs -r "$ACR_NAME" -g "$RG" --output table 2>/dev/null || true
else
  echo "  Using local Docker build"
  az acr login -n "$ACR_NAME"
  for MODULE in "${!MODULE_TO_IMAGE[@]}"; do
    IMAGE="${MODULE_TO_IMAGE[$MODULE]}"
    echo "  Building $MODULE → $IMAGE ..."
    docker build \
      --build-arg "SERVER_MODULE=${MODULE}" \
      -t "$IMAGE" \
      -f Dockerfile.mcp \
      .
    echo "  Pushing $IMAGE ..."
    docker push "$IMAGE"
  done
fi

# ── Wait for ACR builds if async ──────────────────────────────────────────
if $USE_ACR_BUILD; then
  echo "[4/5] Waiting for ACR builds (up to 10 min)..."
  MAX_WAIT=600
  ELAPSED=0
  SLEEP_INTERVAL=20

  while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    RUNNING=$(az acr task list-runs -r "$ACR_NAME" -g "$RG" \
      --query "[?status=='Running' || status=='Queued'].runId" -o tsv 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$RUNNING" -eq 0 ]]; then
      echo "  All builds complete."
      break
    fi
    echo "  $RUNNING build(s) still running... (${ELAPSED}s elapsed)"
    sleep $SLEEP_INTERVAL
    ELAPSED=$((ELAPSED + SLEEP_INTERVAL))
  done

  # Check for failures
  FAILED=$(az acr task list-runs -r "$ACR_NAME" -g "$RG" \
    --query "[?status=='Failed'].runId" -o tsv 2>/dev/null || echo "")
  if [[ -n "$FAILED" ]]; then
    echo "WARNING: some ACR builds failed: $FAILED"
    echo "  Check logs: az acr task logs -r $ACR_NAME -g $RG --run-id <id>"
  fi
else
  echo "[4/5] Skipped (local build uses docker push directly)."
fi

# ── Update Container Apps with real images ────────────────────────────────
echo "[5/5] Updating Container Apps with real images..."
for MODULE in "${!MODULE_TO_APP[@]}"; do
  APP_NAME="${MODULE_TO_APP[$MODULE]}"
  IMAGE="${MODULE_TO_IMAGE[$MODULE]}"

  # Check if app exists
  APP_EXISTS=$(az containerapp show -n "$APP_NAME" -g "$RG" --query name -o tsv 2>/dev/null || echo "")
  if [[ -z "$APP_EXISTS" || "$APP_EXISTS" == "None" ]]; then
    echo "  SKIP: Container App '$APP_NAME' not found (run Bicep first)"
    continue
  fi

  echo "  Updating '$APP_NAME' → $IMAGE ..."
  az containerapp update \
    -n "$APP_NAME" \
    -g "$RG" \
    --image "$IMAGE" \
    --output table
done

echo ""
echo "=== Done! ==="
echo ""
echo "MCP server URLs (add to local.settings.json and Azure App Settings):"
for MODULE in "${!MODULE_TO_APP[@]}"; do
  APP_NAME="${MODULE_TO_APP[$MODULE]}"
  FQDN=$(az containerapp show -n "$APP_NAME" -g "$RG" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "<not-found>")
  echo "  ${APP_NAME}: https://${FQDN}/mcp"
done

echo ""
echo "After noting the URLs above, run:"
echo "  python agents/create_agents.py --update"
echo "  ...(with MCP_SENTINEL_DB_URL, MCP_SENTINEL_SEARCH_URL, MCP_QMS_URL, MCP_CMMS_URL set)"
