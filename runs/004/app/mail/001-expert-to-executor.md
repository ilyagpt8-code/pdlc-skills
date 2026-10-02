# Сообщение эксперта к исполнителю (Ход 1)

Готов к работе. Прочитал спецификацию `spec/tempconv.md`.

## Ключевые требования спецификации:

1. **Аргументы**: `tempconv <VALUE> <FROM> <TO>`
   - VALUE: число (int, decimal, scientific notation)
   - FROM, TO: ровно одно из C, F, K (только uppercase)

2. **Валидация**:
   - VALUE должна быть числом (иначе exit code 1)
   - FROM и TO должны быть C, F или K (иначе exit code 2)
   - Проверка absolute zero для исходной шкалы (exit code 3 если ниже):
     - C: VALUE ≥ −273.15
     - F: VALUE ≥ −459.67
     - K: VALUE ≥ 0

3. **Вывод**:
   - На stdout: число с ровно 2 знаками после запятой
   - На stderr при ошибке: точное сообщение и exit code
   - Нет лишнего текста

4. **Формулы**:
   - C → F: (C × 9/5) + 32
   - C → K: C + 273.15
   - F → C: (F − 32) × 5/9
   - F → K: ((F − 32) × 5/9) + 273.15
   - K → C: K − 273.15
   - K → F: (K − 273.15) × 9/5 + 32
   - Одна шкала → одна шкала: просто VALUE с 2 знаками

5. **Ошибки**:
   - Неверное число аргументов: exit 1, "Usage: tempconv <value> <from> <to>"
   - Неверное число: exit 1, "Error: invalid number"
   - Неверная шкала: exit 2, "Error: invalid scale"
   - Ниже absolute zero: exit 3, "Error: temperature below absolute zero"

6. **Рounding**: round-half-up (32.125 → 32.13, −32.125 → −32.13)

Готов ответить на вопросы и проверить работу. Создай код в `app/tempconv.py`, тесты в `app/tests/` (pytest). Утилита запускается как `python app/tempconv.py ...`.
