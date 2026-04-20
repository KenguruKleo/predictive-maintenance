# T-046 · Foundry Agent Code Hardening (post-demo)

← [04 · План дій](../04-action-plan.md)

> **Пріоритет:** 🟢 LOW — не блокує demo, виконати після фіналів  
> **Походження:** Code review `run_foundry_agents.py` (20 квітня 2026)  
> **Статус:** 🔜 TODO

---

## Контекст

Під час глибокого ревью `backend/activities/run_foundry_agents.py` виявлено ряд проблем, які не впливають на demo, але важливі для production-ready коду та GxP compliance.

**Вже виправлено (20 квітня 2026):**
- ✅ `_build_agents_client()` — прибрано `os.environ.setdefault("AZURE_AI_AGENTS_TESTS_IS_TEST_RUN", "True")` (тестовий прапор у production коді)
- ✅ `_infer_known_document()` — додано явний коментар HACKATHON ONLY + `KNOWN_DOCUMENT_FALLBACK_DISABLED` env var для вимкнення
- ✅ Hardcoded fallback Agent ID — задокументовано як HACKATHON, видно що треба прибрати перед production

---

## Залишкові проблеми для вирішення

### 1. `_infer_known_document()` — видалити або замінити (MEDIUM)

**Файл:** `backend/activities/run_foundry_agents.py`

Функція хардкодить blob paths для конкретних документів (SOP-DEV-001, SOP-MAN-GR-001, GMP-Annex15, BPR-MET-500). Якщо документ перейменувати в Azure Blob Storage, посилання тихо стануть невалідними але UI покаже "розв'язану" цитату.

**Правильний підхід:** AI Search індекс — єдине джерело правди. Документ матчиться через `_find_matching_hit`. Якщо `source_blob` не приходить з індексу — це проблема якості індексу (поле треба індексувати), а не привід хардкодити маппінг в Python.

**Дія:** Перевірити що AI Search `idx-sop-documents`, `idx-gmp-policies`, `idx-bpr-documents` повертають `source` поле для всіх mock документів → видалити `_infer_known_document()` → увімкнути через `KNOWN_DOCUMENT_FALLBACK_DISABLED=true`.

---

### 2. `_has_direct_stop_requirement()` — keyword matching для GxP діалогу (MEDIUM)

**Файл:** `backend/activities/run_foundry_agents.py`

```python
stop_markers = (
    "stop the line", "must stop", "halt production",
    "production must be stopped", "hold the batch",
    "batch must be held", "reject the batch",
)
```

Ця функція визначає що сказати оператору ("документ вимагає зупинки"). Якщо SOP використовує `"cease operations"`, `"suspend batch"`, `"discontinue processing"` — вони не спрацюють. Для GxP діалогу — це ризик.

**Правильний підхід:** Нехай Document Agent відповідає на це питання явно в `operator_dialogue`. Додати в `document_system.md` секцію: якщо оператор питає "чи документ вимагає зупинки" — Document Agent повинен дати пряму відповідь "Yes/No, because [excerpt]", не покладаючись на post-processing.

**Дія:** Вдосконалити `document_system.md` + `orchestrator_system.md` → поступово замінити `_has_direct_stop_requirement()` → перевірити через Foundry evaluation.

---

### 3. `time.sleep(stagger)` в Durable Activity (LOW)

**Файл:** `backend/activities/run_foundry_agents.py`

```python
# рядок ~153 — до 60 сек sleep, 25% від 240-секундного бюджету
time.sleep(stagger)
```

Thundering herd prevention через `time.sleep` в Activity має недоліки:
- 60 сек = 25% бюджету Activity витрачається на очікування до старту
- При orchestrator replay stagger обчислюється знову (може відрізнятися)
- Durable Activity не призначений для довгих sleep-ів

**Правильний підхід:** Rate limit throttling треба вирішувати в оркестраторі через `context.create_timer()` (Durable-aware) або через Service Bus sessions/lease. Або ж покладатися на retry-з-backoff в `_call_orchestrator_agent()` (він вже є і добре реалізований).

**Дія:** Перевірити чи реально thundering herd — проблема після retry-backoff реалізації → якщо ні, прибрати sleep → якщо так, перенести в оркестратор.

---

### 4. Confidence gate — тільки лог, не блокування (LOW)

**Файл:** `backend/activities/run_foundry_agents.py`

```python
if confidence < CONFIDENCE_THRESHOLD:
    result["confidence_flag"] = "LOW_CONFIDENCE"
    # але нічого не блокується
```

`confidence_flag` встановлюється, але orchestrator нічого не робить з ним автоматично. Оператор може approve incident з `confidence=0.1`.

**Дія:** Перевірити що approval UX (T-033) показує confidence badge → вирішити: чи потрібно блокувати approve коли `confidence_flag == LOW_CONFIDENCE`, чи достатньо попередження.

---

### 5. RAG параметри не конфігуровані (LOW)

**Файл:** `backend/activities/run_foundry_agents.py`

```python
search_all_indexes(query=search_query, equipment_id=equipment_id, top_k=3)
# ...
hit['text'][:600]  # prompt truncation hardcoded
```

`top_k=3` і обрізання 600 символів впливають на якість аналізу і мають бути env vars.

**Дія:** Додати `RAG_TOP_K` (default 3) та `RAG_EXCERPT_CHARS` (default 600) env vars.

---

### 6. Шар перезапису діалогу — спростити або видалити (LOW)

`_normalize_operator_dialogue()` → `_should_rewrite_followup_dialogue()` — складна пост-обробка LLM виводу з `SequenceMatcher` threshold `0.88`. Логіка правильна але:
- Маскує проблеми якості system prompt
- Ускладнює дебаг (що сказав LLM vs. що показується)
- Може перезаписати коректний вивід

**Дія:** Після фіналів — провести Foundry evaluation `operator_dialogue` якості → якщо LLM з покращеним промптом стабільно дає якісний вивід, прибрати або суттєво спростити `_normalize_operator_dialogue()`.

---

## Що не чіпати

| Рішення | Чому залишити |
|---|---|
| Жорстка JSON schema в промпті | Правильно для GxP |
| `raw_response` завжди зберігається | Audit trail |
| RAG pre-fetch перед промптом | Grounding до LLM |
| `NEVER fabricate` в orchestrator system prompt | Знижує галюцинації |
| `_citation_points_to_incident()` фільтр | Поточний інцидент ≠ доказ |
| Rate limit retry з backoff + jitter | Production-ready |
| `_build_agent_failure_result()` | Контрольований деградований режим |
| `_parse_response()` graceful fallback | Не падати на некоректному JSON |

---

## Definition of Done

- [ ] `_infer_known_document()` видалено або замінено на index-based lookup
- [ ] `KNOWN_DOCUMENT_FALLBACK_DISABLED=true` в production settings
- [ ] `_has_direct_stop_requirement()` замінено на LLM-based відповідь у `document_system.md`
- [ ] Стартовий sleep (`time.sleep(stagger)`) прибрано або перенесено в оркестратор
- [ ] `RAG_TOP_K` та `RAG_EXCERPT_CHARS` env vars додані
- [ ] Regression tests пройшли
