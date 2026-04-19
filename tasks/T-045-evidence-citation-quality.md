# T-045 · Evidence Citations Quality + Historical Evidence Links

← [Tasks](./README.md) · [04 · План дій](../04-action-plan.md)

**Пріоритет:** 🟠 HIGH  
**Статус:** 🟡 IN PROGRESS  
**Блокує:** Trustworthy demo evidence UX / operator confidence in recommendation package  
**Залежить від:** T-026 (Document Agent), T-031 (Backend API), T-032 (Frontend core), T-037 (AI Search indexes)

---

## Мета

Підвищити якість блоку `Evidence From Documents`, щоб кожна видима картка була канонічною, зрозумілою, без дублікатів, з робочим посиланням, достатнім контекстом в excerpt, і без hallucinatory fallback labels на кшталт `Evidence source`.

---

## Progress (19 квітня 2026)

- [x] Frontend incident detail now reads only `ai_analysis.evidence_citations` for visible evidence cards.
- [x] Backend normalization now emits canonical citations with `resolution_status` / `unresolved_reason` instead of relying on fake fallback titles.
- [x] Dedupe moved to canonical identity (`document_id` / `source_blob` / `url` + `section`) instead of display title.
- [x] Short excerpts are backfilled from matched AI Search chunks to a contextful 180–300 character snippet.
- [x] Historical citations now resolve to `/incidents/:id` deep links instead of pretending to be blob documents.
- [x] Historical indexing now excludes `rejected` and non-approved closed incidents; only approved `closed` / `completed` precedents are indexed.
- [x] Focused regression tests cover canonical dedupe, unresolved evidence, excerpt backfill, historical links, and approved-history indexing.
- [ ] Live/manual validation on a real incident detail screen is still pending.

---

## Контекст / проблема

Поточний UX review по live incident `INC-2026-0013` показав кілька системних проблем у presentation layer evidence cards:

1. Frontend зараз змішує `evidence_citations`, `sop_refs` і `regulatory_refs`, тому одна й та сама підстава може рендеритись кілька разів у різній якості.
2. Backend допускає partial citations без стабільного `document_title` / `source_blob` / `url`, після чого UI підставляє generic labels (`Evidence source`, `GMP reference`) замість реальної назви документа.
3. Dedupe будується на display title, section і excerpt, а не на канонічній ідентичності документа, через що `Deviation Management (SOP-DEV-001)` і `Evidence source` роз'їжджаються в окремі картки.
4. `text_excerpt` часто занадто короткий або нерівномірний: іноді це 1 рядок без контексту, іноді це просто fragment без зрозумілого прив'язування до рішення.
5. Historical incidents мають окремий structural mismatch:
   - `idx-incident-history` зараз генерується напряму з Cosmos incident records, без реального blob artifact;
   - evidence normalization мапить ці результати на `blob-history`, тому historical citations не мають надійного document link contract;
   - індексер наразі бере `closed`, `resolved`, `rejected`, тоді як для evidence reuse потрібен business-rule review: враховувати лише попередні інциденти, які реально пройшли approved/closed lifecycle, а не відхилені кейси.

> **Важливо:** не виправляти legacy/test incidents у базі вручну. Потрібно виправити тільки кодовий contract, normalization, indexing rules і UI rendering.

---

## Scope

### 1. `evidence_citations` як єдиний source of truth для UI

- Frontend повинен рендерити document evidence тільки з `ai_analysis.evidence_citations`.
- `sop_refs` і `regulatory_refs` лишаються backend/model-facing fields, але не домішуються напряму в UI як окремі картки.
- Backend має сам канонізувати дані з `sop_refs` / `regulatory_refs` / `evidence_citations` у єдиний normalized список перед збереженням incident payload.

### 2. Жорсткий citation contract на бекенді

Кожна **видима** картка типу `document evidence` повинна мати:

- `document_title`
- `section`
- `text_excerpt` з нормальним контекстом
- або `url`, або пару `container + source_blob`, або окремий canonical incident link contract для historical case

Якщо citation не проходить цей contract:

- не показувати його як звичайну document card;
- переводити в окремий unresolved state з явним маркуванням на UI, а не маскувати під `Evidence source`.

### 3. Canonical dedupe

Переробити dedupe key так, щоб він базувався на канонічному document identity:

- `document_id`, якщо він є;
- інакше `source_blob`;
- інакше canonical historical incident id / URL;
- плюс `section`.

Display title не повинен брати участь як primary dedupe key.

### 4. Якість excerpt-ів

- Не показувати сирий повний chunk як є.
- Не лишати 1 короткий рядок без контексту, якщо можна backfill-ити кращий excerpt.
- Цільовий формат: приблизно 180–300 символів або 1–2 речення навколо matching fragment.
- Якщо агент повернув слабкий `text_excerpt`, backend має backfill-ити excerpt з matched AI Search hit / source chunk.

### 5. Historical incidents as evidence

- Визначити й зафіксувати business rule, які попередні incidents взагалі можна використовувати як evidence.
- Поточний кандидат на policy: включати тільки кейси, які пройшли operator approval та завершились у `closed` / `completed` (або інший явно погоджений equivalent), виключити `rejected`.
- Перевірити розбіжність між:
  - search indexing (`closed` / `resolved` / `rejected`),
  - API/list semantics (`approved` / `closed` / `executed` / `completed`),
  - UX expectations для similar cases.
- Historical citations мають відкриватися через working incident link:
  - або deep-link на incident detail,
  - або спеціальний API endpoint для historical preview,
  - але не через `blob-history`, якщо фізичного blob немає.

### 6. UI presentation

- Для canonical document cards показувати зрозумілу назву документа, section, excerpt, type badge і working link.
- Для historical evidence показувати окремий тип картки (`History` / `Similar incident`) з incident id, статусом, датою і посиланням на incident.
- Для unresolved evidence показувати окреме явне маркування (`Unresolved evidence`) замість generic fake title.

---

## Очікувані зміни у файлах

### Backend

```text
backend/activities/run_foundry_agents.py
backend/shared/search_utils.py
backend/triggers/http_incidents.py          # якщо знадобиться historical link / payload enrichment
backend/triggers/http_documents.py          # тільки якщо підтвердиться потреба в окремому historical preview route
scripts/create_search_indexes.py            # status policy for idx-incident-history
```

### Frontend

```text
frontend/src/utils/analysis.ts
frontend/src/components/Incident/EvidenceCitations.tsx
frontend/src/types/incident.ts
```

### Tests

```text
tests/...
frontend/... tests if present
```

---

## Definition of Done

- [x] UI рендерить document evidence тільки з normalized `evidence_citations`
- [x] Для одного документа/section не з'являються дублікати з різними display titles
- [x] Для canonical document cards більше не з'являються labels `Evidence source`, `SOP reference`, `GMP reference`
- [x] Кожна видима document card має working `Open document` link
- [x] Historical evidence cards мають working `Open incident` або equivalent link
- [x] Historical evidence використовує тільки incident statuses, погоджені як valid precedent (без rejected cases)
- [x] `text_excerpt` у canonical cards має достатній контекст, а не 1 рядок без сенсу
- [x] Неканонічні citations не маскуються під документ, а показуються як unresolved evidence або не рендеряться як card
- [x] Додані focused regression tests на normalization, dedupe, unresolved state і historical link semantics
- [ ] Live/manual validation на incident detail screen показує зрозумілий, недубльований, linkable evidence block

---

## Validation сценарії

1. Incident з SOP + GMP evidence, де раніше з'являлись дублікати `document title` vs `Evidence source`
2. Incident з дуже коротким `text_excerpt`, де backend повинен backfill-ити кращий snippet
3. Incident з similar historical cases, де картка повинна вести на historical incident detail, а не на fake blob link
4. Negative case: rejected historical incident не повинен потрапляти в visible precedent evidence

---

## Примітки

- Це task на code-path quality, а не на cleanup test data.
- Якщо виявиться, що historical cases логічно не є `documents`, можна перейменувати UI block або split-нути його на `Evidence From Documents` + `Similar Historical Incidents`, але тільки після узгодження UX direction.