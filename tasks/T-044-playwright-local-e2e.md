# T-044 · Local Playwright E2E Mode (Dev Auth + Local Backend Proxy)

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🟡 IN PROGRESS  
**Блокує:** стабільні frontend regression / smoke tests для T-032, T-033, T-034, T-043  
**Залежить від:** T-032 (frontend shell), T-035 (RBAC), завершення auth-check у T-029 для `POST /api/incidents/{incident_id}/decision`

---

## Мета

Дати можливість запускати frontend локально в `Playwright` без інтерактивного Entra login, але при цьому:

- не відкривати production/dev backend для анонімного browser access
- не зашивати `function key` або `master key` у браузер
- не підміняти реальні дані моками, якщо локальний backend може читати ті самі Azure ресурси

---

## Поточний стан і висновок

### Що є зараз

- frontend жорстко залежить від `MSAL`:
  - `frontend/src/App.tsx` рендерить `LoginPage`, якщо `useIsAuthenticated() === false`
  - `frontend/src/pages/LoginPage.tsx` викликає `loginRedirect()`
  - `frontend/src/api/client.ts` додає `Authorization: Bearer <token>` через `acquireTokenSilent()`
- backend UI endpoints в основному мають `auth_level=ANONYMOUS`, але самі перевіряють JWT/ролі через `backend/utils/auth.py`
- у `backend/utils/auth.py` вже є локальний hook:

```python
USE_LOCAL_MOCK_AUTH=true
X-Mock-Role: Operator
```

тобто локальний backend вже вміє обходитися без Entra token, але frontend цього режиму не має.

### Що не підходить

#### 1. `function key` / `master key`

Це не рішення для frontend E2E:

- вони потрібні для Azure Functions host/admin або для endpoint-ів з `AuthLevel.FUNCTION`
- більшість UI endpoint-ів у нас не покладаються на function-level auth, а роблять app-level auth у Python code
- передавати такі ключі у браузер або Playwright client-side state небезпечно

#### 2. Локально згенерований JWT

Також не спрацює як є, бо backend зараз довіряє тільки токенам, підписаним Entra ID JWKS. Якщо ми хочемо локально підписувати свої токени, доведеться змінювати trust model бекенду. Це зайвий і ризикований шлях для першої ітерації.

### Головний висновок

Для `Playwright` потрібен не “секрет у браузері”, а **dev-only auth mode**:

- frontend переходить у `e2e` режим і не вимагає MSAL login
- backend приймає mock-role тільки локально
- реальні дані продовжують приходити через локально запущений backend, який ходить у ті ж Azure ресурси

---

## Рекомендований варіант (Phase 1)

### Архітектура

```text
Playwright
  -> local Vite frontend (auth mode = e2e)
  -> /api/* same-origin requests
  -> Vite proxy
  -> local Azure Functions host (USE_LOCAL_MOCK_AUTH=true)
  -> real Azure data/services (Cosmos, SignalR, Search, etc.)
```

### Чому це найкращий шлях

- не потрібен інтерактивний login в E2E
- не потрібен production bypass на deployed backend
- можна тестувати UI на реальних даних з Azure
- використовується вже наявний локальний auth-hook у backend
- `Playwright` легко піднімає і frontend, і backend через `webServer`

---

## Scope

### 1. Frontend: додати auth mode `msal | e2e`

Ввести явний runtime mode, наприклад:

```env
VITE_AUTH_MODE=msal
VITE_API_BASE_URL=https://func-sentinel-intel-dev-erzrpo.azurewebsites.net/api
```

і для локального E2E:

```env
VITE_AUTH_MODE=e2e
VITE_API_BASE_URL=/api
```

У `e2e` режимі frontend має:

- не показувати `LoginPage`
- не викликати `loginRedirect()`
- підставляти mock principal (`user`, `name`, `roles`) з test state
- дозволяти просте перемикання ролей: `operator`, `qa-manager`, `auditor`, `it-admin`

### 2. Frontend API client: передавати mock identity тільки в `e2e` режимі

`frontend/src/api/client.ts` у `e2e` режимі повинен:

- не викликати `acquireTokenSilent()`
- додавати заголовки на кшталт:

```http
X-Mock-Role: Operator
X-Mock-User: ivan.petrenko
```

- працювати тільки з відносним `/api` base URL у local E2E

Це дозволить задавати роль на рівні конкретного browser context/test, а не на рівні всього dev server process.

### 3. Vite dev proxy: перевести local E2E на same-origin `/api`

У `frontend/vite.config.ts` додати proxy:

```ts
server: {
  port: 4173,
  strictPort: true,
  proxy: {
    "/api": {
      target: "http://127.0.0.1:7071",
      changeOrigin: true,
    },
  },
}
```

Це прибирає CORS-проблеми і робить тести стабільнішими.

### 4. Backend: зафіксувати local-only mock auth contract

`backend/utils/auth.py` треба допрацювати так, щоб mock auth:

- працював лише в локальному режимі / development host
- не міг бути випадково увімкнений у deployed Function App
- підтримував не тільки `X-Mock-Role`, а й `X-Mock-User` для audit-friendly flows

Бажаний guardrail:

- `USE_LOCAL_MOCK_AUTH=true` недостатньо саме по собі
- додатково перевіряти, що процес реально запущений локально (`AZURE_FUNCTIONS_ENVIRONMENT=Development`, localhost origin/host, або інший явний local-only сигнал)

### 5. Playwright: додати локальний boot + role-aware fixtures

Додати `Playwright` у frontend workspace:

- `playwright.config.ts`
- `webServer` для frontend і backend
- `use.baseURL`
- helper/fixture для встановлення mock auth state до відкриття сторінки

Базовий контракт:

- роль задається на рівні test/project
- smoke test відкриває dashboard без Entra login
- incident detail відкривається на реальних даних
- role-based visibility перевіряється окремо для `operator` і `auditor`/`it-admin`

---

## Важлива примітка по security

### Не використовувати як перший варіант

- `function key`
- `master key`
- будь-який secret, який треба віддати в браузер

### Чому

Browser-based E2E неминуче робить такі значення доступними test runtime і developer tools. Для локального тестового режиму це зайва і небезпечна модель, особливо коли є чистіший шлях через local-only auth bypass.

---

## Альтернатива (Phase 2, лише якщо справді треба тестувати не локальний backend, а deployed slot)

Якщо буде жорстка вимога тестувати саме віддалений backend, окремим етапом можна розглянути:

- окремий `e2e` deployment slot або окремий test backend
- окремий short-lived secret / signed header, який приймається тільки там
- IP/slot/environment restriction

Але це **не** варто робити у першому проході. На поточному етапі це більший security surface, ніж користь.

---

## Implementation slice (smallest viable)

1. Додати `VITE_AUTH_MODE=e2e` + mock auth provider на frontend
2. Перевести local API calls на `/api` + Vite proxy
3. Розширити local backend auth до `X-Mock-Role` + `X-Mock-User` з local-only guard
4. Додати `Playwright` config з `webServer` для frontend/backend
5. Написати 2 smoke tests:
   - dashboard loads as operator
   - incident detail / role gating works
6. Задокументувати команди запуску

---

## Files likely to change

```text
frontend/package.json
frontend/vite.config.ts
frontend/src/App.tsx
frontend/src/authConfig.ts
frontend/src/hooks/useAuth.ts
frontend/src/api/client.ts
frontend/src/main.tsx
frontend/playwright.config.ts
frontend/tests/e2e/**
backend/utils/auth.py
README.md
```

## Progress (19 квітня 2026)

- [x] Frontend now supports `VITE_AUTH_MODE=e2e`
- [x] Browser requests in `e2e` mode use local `/api` instead of MSAL bearer tokens
- [x] Vite dev proxy forwards `/api` to a local Functions host
- [x] Playwright config starts frontend + backend locally and runs passing smoke tests
- [x] Local E2E usage documented in `frontend/README.md`
- [x] Local Functions startup no longer resolves `utils.*` from unrelated workspace folders before this repo's `backend/`
- [x] Missing local App Insights query dependency no longer prevents the whole Functions host from starting; `/api/incidents/{id}/agent-telemetry` now degrades locally instead of crashing host startup
- [ ] Backend guardrail that guarantees mock auth is accepted only in local/development environments is still pending

### Local backend startup note

- Azure Functions Core Tools may prepend other workspace folders to `sys.path`; locally this caused `utils.auth` imports to resolve to `/workspace/nursefly-web/python/utils.py` and crash on `boto3`.
- `backend/function_app.py` now forces the repo `backend/` directory to the front of `sys.path` before importing `utils`, `shared`, `triggers`, and `activities`.
- `backend/triggers/http_agent_telemetry.py` now lazy-loads `shared.agent_telemetry`, so a missing local `azure.monitor.query` install affects only the telemetry endpoint instead of blocking all HTTP APIs needed by frontend E2E.

---

## Risks / related gaps

- `backend/triggers/http_decision.py` зараз не використовує `utils/auth.py` і приймає `user_id` / `role` з body. Для повноцінного auth-aware E2E це треба довести до контракту T-029/T-035.
- `backend/triggers/http_signalr.py` зараз повертає negotiate payload без role check. Це не блокує local E2E start, але є окремим security debt.
- Якщо local backend має ходити в Azure ресурси, треба перевірити локальні credentials / `local.settings.json` / `az login`.

---

## Definition of Done

- [x] `Playwright` запускає frontend локально через `webServer` без ручного login
- [x] `Playwright` може підняти локальний backend або перевикористати вже запущений local Functions host
- [x] frontend у `e2e` режимі не залежить від `MSAL` для базового smoke flow
- [x] API requests у `e2e` режимі йдуть через `/api` і працюють на реальних backend даних
- [ ] mock auth приймається тільки локально, не в deployed environment
- [x] є щонайменше 2 проходящі smoke tests для ролей
- [x] README містить інструкцію запуску `frontend + backend + playwright`
