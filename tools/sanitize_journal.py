#!/usr/bin/env python3
"""Очистка журналов сессий от секретов перед коммитом.

Использование: python tools/sanitize_journal.py IN OUT [--max-lines N]
IN — .json или .jsonl; OUT — того же формата. В stderr печатается счётчик замен.
Правила: значения NAME=value, где в NAME есть TOKEN/KEY/SECRET/PASSWORD; Bearer …;
ghp_/github_pat_/sk-…; пути к файлам токенов; e-mail -> <EMAIL>; значения JSON-ключей
с TOKEN/KEY/SECRET/PASSWORD в имени.
"""
import json, re, sys, collections

R = "<REDACTED>"
cnt = collections.Counter()
SENS = r"[A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Za-z0-9_]*"
RULES = [
    ("env_value", re.compile(r"(\b" + SENS + r"=)(?:\"[^\"]*\"|'[^']*'|\S+)"), r"\1" + R),
    ("bearer", re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=\-]+"), r"\1" + R),
    ("gh_token", re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{10,}"), R),
    ("sk_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}"), R),
    ("token_path", re.compile(r"(?<![<\w])(?:/[\w.\-]+)+/[\w.\-]*token[\w.\-]*", re.I), R),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "<EMAIL>"),
]
KEYRE = re.compile(SENS, re.I)

def s(x):
    for name, rx, rep in RULES:
        x, n = rx.subn(rep, x)
        cnt[name] += n
    return x

def walk(o):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if isinstance(v, str) and KEYRE.fullmatch(k) and k != "signature" and v != R:
                cnt["json_key_value"] += 1; out[k] = R
            else:
                out[k] = walk(v)
        return out
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, str):
        return s(o)
    return o

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    ml = None
    if "--max-lines" in sys.argv:
        ml = int(sys.argv[sys.argv.index("--max-lines") + 1]); a.remove(str(ml))
    src, dst = a[0], a[1]
    if src.endswith(".jsonl"):
        lines = [l for l in open(src, encoding="utf-8") if l.strip()]
        if ml: lines = lines[:ml]
        with open(dst, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(json.dumps(walk(json.loads(l)), ensure_ascii=False) + "\n")
    else:
        d = walk(json.load(open(src, encoding="utf-8")))
        json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(dict(cnt), file=sys.stderr)

if __name__ == "__main__":
    main()
