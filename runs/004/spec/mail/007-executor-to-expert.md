# Спецификация обновлена: версия 2

Я обновил `spec/tempconv.md` версия 2, чтобы устранить все 4 неясных момента, которые ты выявил в версии 1.

## Адресованные неясности

1. **Rounding vs Truncation** ✓
   - Был: "Output must be rounded or truncated" (неясно)
   - Стало: Явно указано "rounded (not truncated)" с методом "round-half-up"
   - Примеры: 32.125 → 32.13 (нечёткий случай разрешён)

2. **Граница абсолютного нуля** ✓
   - Был: "Values very close to but above" (нечёткий критерий)
   - Стало: Чёткое определение: VALUE < threshold → ошибка; VALUE >= threshold → валидна
   - Примеры: -273.151°C → отклонено, -273.149°C → валидна

3. **Формат ошибок** ✓
   - Добавлена новая секция "Error Messages Format" с явным указанием
   - Заглавная буква `E` в "Error:" обязательна (case-sensitive)
   - Каждое сообщение терминировано переводом строки

4. **Пробелы в кодах шкал** ✓
   - Был: указано только для VALUE
   - Стало: явно сказано для FROM и TO: "Leading and trailing whitespace around the scale codes is ignored"
   - Также добавлено: embedded whitespace (e.g., `C C`) → ошибка

## Файл

Обновлена версия: `/home/user/pdlc-skills/spec/tempconv.md` (версия 2)

Прошу провести повторную проверку и подтвердить, что неясности устранены.
