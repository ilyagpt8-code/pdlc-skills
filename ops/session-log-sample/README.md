# Образцы журналов сессий

## list_events.json — журнал подчинённой сессии (главный)

Реальный вывод `mcp__claude-code-remote__list_events(session_id)` по пробной Haiku-сессии `session_01Fq3C6xSfZqTjh69s5Ta2V2` («probe-1»): исполнитель читает `probe/TASK.md`, создаёт файл, коммитит, пушит. 95 событий, все, без фильтра `kinds`, одна страница (`limit=100`). Очищено `tools/sanitize_journal.py` (замен: 1 значение JSON-ключа с `KEY/TOKEN/SECRET/PASSWORD` в имени; e-mail, Bearer, ghp_/sk-, токен-пути не найдено). Подписи блоков `thinking` оставлены как есть (текста мыслей в журнале нет).

### Структура

```
{ "data": [ {событие}, ... ], "first_id": "...", "last_id": "..." }   // поле has_more по описанию инструмента есть; в моих ответах не встречалось (страницы были последними)
событие = { "created_at": "...Z", "<вид>": { "uuid": "...", "internal_anthropic_catchall": { ... } } }
```

`<вид>` — единственный ключ рядом с `created_at`. Бывают: `user`, `assistant`, `result`, `system`, `control_request`, `control_response`, `env_manager_log`, `rate_limit_event` (+ `internal_anthropic_catchall` у служебных). Для анализа нужны `user`, `assistant`, `result`; запрашивать так: `kinds=["user","assistant","result"]`.

| Что нужно | Откуда |
|---|---|
| Стартовое задание | первое `user`: `…catchall.message.content` (строка), `inbound_origin="mcp_create_session"` |
| Реплика/вызов модели | `assistant.…catchall.message.content[]`: блоки `thinking` (текст пустой, есть `signature`), `text`, `tool_use` (`name`, `input`, `id`) |
| Результат инструмента | `user.…catchall.message.content[]` блок `tool_result` (`tool_use_id`, `content`, `is_error`) и рядом `tool_use_result` (stdout/stderr, diff и т. п.) |
| Токены и деньги по ходу | `result.…catchall`: `usage`, `modelUsage.<модель>` (`costUSD`, `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens`, `thinkingTokens`), `total_cost_usd` |
| Время | `result`: `duration_ms` (стенное), `duration_api_ms`; у каждого события `created_at` и `timestamp` внутри `message`; время инструмента = `created_at(tool_result) − created_at(tool_use)` |
| Число шагов | `result.num_turns` |
| Итог агента | `result.result` |

### Как считать токены

- Один ответ модели разбит на несколько событий `assistant` (по блоку на событие: thinking → text → tool_use) с одинаковым `message.id` и одинаковым `usage`. Суммировать `usage` по событиям нельзя, получится двойной счёт.
- В событиях `assistant` `usage.output_tokens` — промежуточное (в начале стрима, например 2). Достоверные итоги — в `result`: `modelUsage` (по модели) и `usage.output_tokens`.
- `result.usage.cache_read_input_tokens` суммируется по всем запросам хода (у probe-1 ≈ 994 тыс. при контексте ≈ 49 тыс.): это не размер контекста.
- На один прогон приходится одно событие `result` на ход (после ответа без вызовов инструментов); при нескольких пользовательских сообщениях их несколько. Итоговая стоимость сессии — `get_session(...).external_metadata.usage.cost_usd`.

### Пагинация и лимиты

- Параметры: `limit` (по умолчанию 20, максимум 100; фильтр `kinds` применяется после чтения страницы, поэтому с `kinds` ставить `limit=100`), `after_id` (события после), `before_id` (до). Курсоры — `first_id`/`last_id` из ответа. Страница отдаётся от старых к новым при `after_id`; без курсора — первые события сессии, пока их ≤ `limit`.
- Лимита на число событий всего я не встретил; страница на 95 событий — 115 КБ. Большой ответ вызывающая среда сохраняет в файл (`…/tool-results/…txt`), его можно обработать скриптом (так и получен этот образец).
- Журнал читается и после завершения, и **после архивации** сессии (проверено на probe-1).

## session.jsonl — собственный журнал облачной сессии

**Не положен.** Его очистка и проверка заблокированы классификатором прав среды («Sensitive-Source Provenance»: журнал содержит вывод `env`). Формат описан в `ops/mailbox/from-cloud-001.md`, п. 1. Инструмент очистки — `tools/sanitize_journal.py`; запустить его на `~/.claude/projects/*/<session-id>.jsonl` может владелец или сессия с разрешением на это.
