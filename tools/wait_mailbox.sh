#!/bin/sh
# Ждёт в origin/main сообщение ops/mailbox/to-cloud-NNN.md без ответа from-cloud-NNN.md.
# Проверка раз в INTERVAL секунд (по умолчанию 60). Завершается, печатая номера без ответа.
INTERVAL=${INTERVAL:-60}
while :; do
  if git fetch -q origin main 2>/dev/null; then
    files=$(git ls-tree -r --name-only origin/main ops/mailbox/)
    pending=""
    for n in $(echo "$files" | sed -n 's#.*/to-cloud-\([0-9]*\)\.md#\1#p'); do
      echo "$files" | grep -q "from-cloud-$n\.md" || pending="$pending $n"
    done
    if [ -n "$pending" ]; then echo "PENDING:$pending"; exit 0; fi
  fi
  sleep "$INTERVAL"
done
