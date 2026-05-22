"""
generate_grammar_pages.py
─────────────────────────
Reads all N5–N1 grammar JSON files and generates one MkDocs .md page
per grammar pattern under docs/grammar/.

Run once (or whenever the JSON files change):
    python generate_grammar_pages.py

Output structure:
    docs/grammar/
    ├── index.md          ← full overview table by level
    ├── N5/
    │   ├── index.md      ← N5 pattern list
    │   ├── N5-01.md
    │   ├── N5-02.md
    │   └── ...
    ├── N4/
    ├── N3/
    ├── N2/
    └── N1/
"""

import json
from pathlib import Path

BASE_DIR    = Path(__file__).parent
DATA_DIR    = BASE_DIR / "data"
GRAMMAR_DIR = BASE_DIR / "docs" / "grammar"

JSON_FILES = [
    (DATA_DIR / "N5_grammar.json",      "N5"),
    (DATA_DIR / "N4_grammar.json",      "N4"),
    (DATA_DIR / "N3_grammar.json",      "N3"),
    (DATA_DIR / "N2_grammar.json",      "N2"),
    (DATA_DIR / "N1_grammar_01.json",   "N1"),
    (DATA_DIR / "N1_grammar_02.json",   "N1"),
]

LEVEL_LABELS = {
    "N5": "N5 — Beginner",
    "N4": "N4 — Elementary",
    "N3": "N3 — Intermediate",
    "N2": "N2 — Upper Intermediate",
    "N1": "N1 — Advanced",
}


def load_all() -> dict[str, list[dict]]:
    """Load all JSON files, grouped by level."""
    by_level: dict[str, list[dict]] = {lv: [] for lv in ["N5","N4","N3","N2","N1"]}
    for path, level in JSON_FILES:
        if not path.exists():
            print(f"  ⚠️  Not found: {path}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        by_level[level].extend(data)
    return by_level


def make_pattern_page(entry: dict) -> str:
    """Generate a single grammar pattern .md page."""
    pid     = entry.get("id", "")
    level   = entry.get("level", "")
    pattern = entry.get("pattern", "")
    meaning = entry.get("meaning", "")
    ex_ja   = entry.get("example_ja", "")
    ex_en   = entry.get("example_en", "")

    return f"""---
title: "{pattern}"
tags:
  - grammar
  - {level}
---
# {pattern}

| | |
|---|---|
| **Level** | {level} |
| **Meaning** | {meaning} |

## Example

{ex_ja}

> {ex_en}

## Notes

<!-- Add your personal notes here -->
"""


def make_level_index(level: str, entries: list[dict]) -> str:
    """Generate the index page for one JLPT level."""
    label = LEVEL_LABELS.get(level, level)
    rows  = "\n".join(
        f"| [{e['pattern']}]({e['id']}.md) | {e['meaning']} |"
        for e in entries
    )
    return f"""---
title: "{label} Grammar"
---
# {label} Grammar Patterns

| Pattern | Meaning |
|---|---|
{rows}
"""


def make_main_index(by_level: dict[str, list[dict]]) -> str:
    """Generate the top-level grammar index page."""
    sections = []
    total = sum(len(v) for v in by_level.values())

    sections.append(f"""---
title: "Grammar Reference"
---
# Grammar Reference

{total} patterns across N5–N1, compiled from TUFS Language Modules and JLPT handbooks.

| Level | Patterns | Description |
|---|---|---|
""")
    for level, label in LEVEL_LABELS.items():
        count = len(by_level.get(level, []))
        sections.append(f"| [{level}]({level}/index.md) | {count} | {label} |")

    return "\n".join(sections) + "\n"


def generate():
    by_level = load_all()

    # Create dirs
    GRAMMAR_DIR.mkdir(parents=True, exist_ok=True)
    for level in by_level:
        (GRAMMAR_DIR / level).mkdir(exist_ok=True)

    # Main index
    (GRAMMAR_DIR / "index.md").write_text(make_main_index(by_level), encoding="utf-8")
    print(f"  ✅ docs/grammar/index.md")

    # Per-level pages
    for level, entries in by_level.items():
        if not entries:
            continue

        # Level index
        idx_path = GRAMMAR_DIR / level / "index.md"
        idx_path.write_text(make_level_index(level, entries), encoding="utf-8")
        print(f"  ✅ docs/grammar/{level}/index.md  ({len(entries)} patterns)")

        # Individual pattern pages
        for entry in entries:
            pid  = entry.get("id", "")
            path = GRAMMAR_DIR / level / f"{pid}.md"
            path.write_text(make_pattern_page(entry), encoding="utf-8")

        print(f"     → {len(entries)} pattern pages generated")

    total = sum(len(v) for v in by_level.values())
    print(f"\n✅ Done — {total} pattern pages + {len(by_level)+1} index pages")


if __name__ == "__main__":
    generate()
