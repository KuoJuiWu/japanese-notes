# Project Data Sources

All data used in this system is offline, open-source, and free for personal use.

---

## 1. JMdict (Japanese–Multilingual Dictionary)
- **Used for**: Word meaning lookup (`jmdict_lookup` in `japan_bot.py`)
- **File**: `jamdictdb/jamdict.db` (SQLite, built from JMdict XML)
- **Access**: via [jamdict](https://github.com/neocl/jamdict) Python library
- **Source**: [JMdict Project](https://www.edrdg.org/jmdict/j_jmdict.html) by Jim Breen
- **License**: Creative Commons Attribution-ShareAlike 4.0
- **Note**: Does NOT include JLPT level data (JLPT vocab lists are not officially published)

---

## 2. Tatoeba / WWWJDIC Sentence Corpus
- **Used for**: Example sentence lookup (`tatoeba_search.py`)
- **File**: `wwwjdic.csv` (tab-separated, ~147k sentences)
- **Format**: `sentence_id | pair_id | japanese | english | word_tags`
- **Source**: [Tatoeba Project](https://tatoeba.org) via WWWJDIC
- **License**: Creative Commons Attribution 2.0
- **Note**: Word tags use base-form notation (e.g. `帰る[01]{帰り}`).
  fugashi/UniDic normalizes to full kanji (e.g. `御飯`), while Tatoeba
  uses everyday mixed writing (e.g. `ご飯`). Surface-form fallback handles this.

---

## 3. JLPT Grammar Patterns (N5–N1)
- **Used for**: Static grammar reference pages on MkDocs site (`docs/grammar/`)
- **Files**: `N5_grammar.json`, `N4_grammar.json`, `N3_grammar.json`,
  `N2_grammar.json`, `N1_grammar_01.json`, `N1_grammar_02.json`
- **Format**: JSON array with fields: `id`, `level`, `pattern`, `meaning`,
  `example_ja`, `example_en`
- **Source**: Compiled manually from TUFS Language Modules and JLPT handbook
- **License**: Personal use
- **Note**: Previously used for pattern matching (`grammar_patterns.py`, removed in v3.0).
  Now used exclusively to generate 636 static MkDocs pages via `scripts/generate_grammar_pages.py`.

---

## 4. JLPT Vocabulary List (N5–N1)
- **Used for**: JLPT level tagging of words in bot analysis
- **File**: `jlpt_vocab.json`
- **Format**: `{ "word": "N3", ... }` — expression → JLPT level
- **Source**: [Bluskyo/JLPT_Vocabulary](https://github.com/Bluskyo/JLPT_Vocabulary),
  which parses the original word lists by
  [Jonathan Waller](http://www.tanos.co.uk/jlpt/) (same source as Jisho.org)
- **License**: Creative Commons BY (Jonathan Waller's original data)
- **Coverage**: ~8,500 words across N5–N1
- **Counts**: N5: 700 | N4: 649 | N3: 1,835 | N2: 1,846 | N1: 3,475
- **Note**: No official JLPT vocab list exists. Levels are approximate.

---

## 5. UniDic (Japanese Morphological Dictionary)
- **Used for**: Tokenization and POS tagging via fugashi
- **Access**: Bundled with [fugashi](https://github.com/polm/fugashi) +
  [unidic-lite](https://github.com/polm/unidic-lite)
- **Source**: [National Institute for Japanese Language and Linguistics](https://unidic.ninjal.ac.jp/)
- **License**: BSD / CC BY-SA 4.0
- **Note**: Normalizes base forms to full kanji (linguistic canonical form),
  which differs from everyday writing conventions used in Tatoeba.

---

## 6. MATCHA やさしい日本語 (Easy Japanese Articles)
- **Used for**: Easy Japanese reading practice via RSS reader (`docs/matcha/index.html`)
- **Access**: Public RSS feed at `https://matcha-jp.com/easy/feed`
- **Source**: [MATCHA](https://matcha-jp.com/easy) — Japan travel and culture articles at N4 level
- **License**: All rights reserved by MATCHA — content displayed via RSS feed for personal use only
- **Note**: Fetched via Cloudflare Workers CORS proxy (`learnjapanese-from-matcha.kuojuiw.workers.dev`).
  RSS feed only includes articles from 2024 and earlier. Newer articles require MATCHA account login.

---

## Summary Table

| Source | File | Words/Entries | License |
|---|---|---|---|
| JMdict | `jamdict.db` | 191,541 entries | CC BY-SA 4.0 |
| Tatoeba/WWWJDIC | `wwwjdic.csv` | ~147k sentences | CC BY 2.0 |
| JLPT Grammar | `N5–N1_grammar.json` | 636 patterns | Personal |
| JLPT Vocabulary | `jlpt_vocab.json` | ~8,500 words | CC BY |
| UniDic | (bundled) | — | BSD / CC BY-SA 4.0 |
| MATCHA RSS | (live feed) | 30 articles | All rights reserved |