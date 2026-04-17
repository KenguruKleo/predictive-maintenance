# T-042 · GitHub Actions CI/CD Pipeline

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** ✅ DONE (17 квітня 2026)  
**Gap:** Gap #1 — Track A (GitHub + CI/CD) ✅

> **Що працює:** `ci.yml` (ruff lint + pytest + az bicep build) запускається на PR; `deploy.yml` (Bicep deploy + Functions deploy) запускається на push в `main`. CI/CD зелений.  
> **Що не додано:** frontend build step (коментар — чекає T-032), Foundry eval pipeline (чекає T-025/T-026).

---

## Мета

GitHub Actions pipelines для build, test, Bicep validation, і deploy. Доводить Track A compliance для hackathon judges.

---

## Workflows

```
.github/
  workflows/
    ci.yml           # On PR: lint + test (Python + TypeScript)
    deploy-infra.yml # On push main: Bicep what-if (PR) → deploy (main)
    deploy-app.yml   # On push main: deploy Functions + Static Web App
    eval.yml         # On schedule/manual: Foundry evaluation runs
```

---

## ci.yml

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: pytest tests/ -v --tb=short
      - run: ruff check backend/

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
        working-directory: frontend/
      - run: npm run build
        working-directory: frontend/
      - run: npm run type-check
        working-directory: frontend/
```

---

## deploy-app.yml

```yaml
name: Deploy App

on:
  push:
    branches: [main]

jobs:
  deploy-functions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - uses: azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTIONS_APP_NAME }}
          package: backend/

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
        working-directory: frontend/
      - uses: azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.SWA_DEPLOYMENT_TOKEN }}
          action: upload
          app_location: frontend/
          output_location: dist/
```

---

## Required GitHub Secrets

```
AZURE_CREDENTIALS          # Service principal JSON for az login
SWA_DEPLOYMENT_TOKEN       # Static Web App deployment token
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP
FUNCTIONS_APP_NAME
```

---

## Definition of Done

- [ ] PR → CI runs Python tests + frontend build (green badge in README)
- [ ] Push to main → Functions deployed to Azure
- [ ] Push to main → Static Web App deployed
- [ ] Bicep what-if runs on PR (infrastructure changes visible in PR comments)
- [ ] GitHub Actions badge in README.md showing CI status
