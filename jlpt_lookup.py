"""
jlpt_lookup.py
──────────────
JLPT vocabulary bank lookup module.

Provides:
  - jlpt_level(word)         → "N3" | None
  - wordbank(level, n)       → list of 20 random words with reading + meaning + example
  - already_saved(notes_dir) → set of words already in saved notes
"""

import json
import random
from pathlib import Path

from jamdict import Jamdict
from tatoeba_search import get_example

VOCAB_PATH = Path(__file__).parent / "jlpt_vocab.json"

_vocab: dict[str, str] = {}   # word → level
_loaded = False


def _load() -> None:
    global _loaded
    if _loaded:
        return
    with open(VOCAB_PATH, encoding="utf-8") as f:
        _vocab.update(json.load(f))
    _loaded = True


def jlpt_level(word: str) -> str | None:
    """Return JLPT level for a word, or None if not in the list."""
    _load()
    return _vocab.get(word)


def words_for_level(level: str) -> list[str]:
    """Return all words for a given level e.g. 'N3'."""
    _load()
    return [w for w, lv in _vocab.items() if lv == level]


def already_saved(notes_dir: Path) -> set[str]:
    """
    Scan saved note filenames and frontmatter titles to build
    a set of words the user has already studied.
    """
    saved = set()
    for md_file in notes_dir.rglob("*.md"):
        # title is in the filename after the timestamp: 20260522_153000_食べる.md
        parts = md_file.stem.split("_", 2)
        if len(parts) == 3:
            saved.add(parts[2])
        # Also read frontmatter title for accuracy
        try:
            text = md_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"')
                    saved.add(title)
                    break
        except Exception:
            pass
    return saved


def wordbank(level: str, jam: Jamdict, notes_dir: Path, n: int = 20) -> list[dict]:
    """
    Return n random words for `level` that haven't been saved yet.
    Each entry: { word, reading, meaning, example_jp, example_en }

    Falls back to already-seen words if unseen pool is exhausted.
    """
    _load()
    all_words  = words_for_level(level)
    saved      = already_saved(notes_dir)
    unseen     = [w for w in all_words if w not in saved]

    # fall back to full list if not enough unseen
    pool = unseen if len(unseen) >= n else all_words
    selection = random.sample(pool, min(n, len(pool)))

    results = []
    for word in selection:
        # reading + meaning from JMdict
        reading = ""
        meaning = ""
        result  = jam.lookup(word)
        if result.entries:
            entry   = result.entries[0]
            kana    = entry.kana_forms
            reading = kana[0].text if kana else word
            glosses = entry.senses[0].gloss if entry.senses else []
            meaning = ", ".join(str(g) for g in glosses[:3])  # max 3 glosses

        # example from Tatoeba
        jp_ex, en_ex, _ = get_example(word)
        if jp_ex == "（自動查詢無結果）":
            jp_ex = ""
            en_ex = ""

        results.append({
            "word":       word,
            "reading":    reading,
            "meaning":    meaning,
            "example_jp": jp_ex,
            "example_en": en_ex,
        })

    return results


def format_wordbank_message(entries: list[dict], level: str) -> str:
    """Format wordbank entries as a Telegram message."""
    lines = [f"📚 Word Bank — {level} ({len(entries)} words)\n"]
    for i, e in enumerate(entries, 1):
        lines.append(f"{i}. {e['word']}（{e['reading']}）")
        if e["meaning"]:
            lines.append(f"   💬 {e['meaning']}")
        if e["example_jp"]:
            lines.append(f"   📝 {e['example_jp']}")
            if e["example_en"]:
                lines.append(f"      {e['example_en']}")
        lines.append("")
    return "\n".join(lines)
