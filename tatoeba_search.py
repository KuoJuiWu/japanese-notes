"""
tatoeba_search.py
─────────────────
Drop-in replacement for the Massif API calls in japan_bot.py.
Searches wwwjdic.csv (Tatoeba/WWWJDIC format) locally using a pre-built
index of dictionary base forms from the tag column.

CSV format (tab-separated):
  col 0 : sentence ID
  col 1 : pair ID
  col 2 : Japanese sentence
  col 3 : English translation
  col 4 : word tags  ← base forms live here, e.g. 帰る[01]{帰り}

Index:
  base_form (str) → list of (japanese_sentence, english_translation)

Usage in japan_bot.py
─────────────────────
Replace the Massif import with:
    from tatoeba_search import get_example, get_example_smart

Change any `await get_example(...)` → `get_example(...)` (now synchronous).
Everything else stays the same — same return types.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path
from random import choice

# ── adjust this path to match your project layout ──────────────────────────
CSV_PATH = Path(__file__).parent / "wwwjdic.csv"
# ───────────────────────────────────────────────────────────────────────────

# index: base_form → [(jp_sentence, en_translation), ...]
_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
_loaded = False

# Extracts the leading base form from a tag token like:
#   帰る[01]{帰り}  →  帰る
#   二十歳(はたち){２０歳}  →  二十歳
#   待つ[01]  →  待つ
_BASE_RE = re.compile(r'^([^\s({\[~#]+)')

def _is_japanese(s: str) -> bool:
    return any(
        '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'
        for c in s
    )

def _extract_bases(tag_col: str) -> list[str]:
    bases = []
    for token in tag_col.split():
        m = _BASE_RE.match(token)
        if m:
            b = m.group(1)
            if _is_japanese(b):
                bases.append(b)
    return bases


def _load() -> None:
    global _loaded
    if _loaded:
        return
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 5:
                continue
            jp, en, tags = row[2].strip(), row[3].strip(), row[4]
            for base in _extract_bases(tags):
                _index[base].append((jp, en))
    _loaded = True


# ── public API ──────────────────────────────────────────────────────────────

def get_example(word: str) -> tuple[str, str]:
    """
    Look up `word` (dictionary base form) in the pre-built index.

    Returns:
        (sentence, "Tatoeba")  on success
        ("（自動查詢無結果）", "")  if not found
    """
    _load()
    hits = _index.get(word)
    if not hits:
        return "（自動查詢無結果）", ""
    jp, _en = choice(hits)          # random pick from all matching sentences
    return jp, "Tatoeba"


def get_example_smart(text: str, words: list[dict]) -> tuple[str, str, list[str], str]:
    """
    Mirrors the Massif get_example_smart() signature used in japan_bot.py.

    Strategy:
      1. Try each content-word base form (名詞 / 動詞 / 形容詞) via index
      2. If nothing found → return empty fields (no warning needed)

    Note: we skip searching the full raw sentence because the index is keyed
    on dictionary base forms, not surface strings.

    Returns:
        (example, source, attempts, warning)
    """
    _load()
    attempts: list[str] = []
    seen: set[str] = set()

    for w in words:
        if w["pos"] not in ("名詞", "動詞", "形容詞"):
            continue
        base = w["base"]
        if base in seen:
            continue
        seen.add(base)

        attempts.append(base)
        example, source = get_example(base)
        if example != "（自動查詢無結果）":
            return example, source, attempts, ""

    # Nothing found — leave blank, no warning
    return "", "", attempts, ""