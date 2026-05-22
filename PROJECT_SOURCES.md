# Project Data Sources

All data used in this system is offline, open-source, and free for personal use.

---

## 1. JMdict (Japanese–Multilingual Dictionary)
- **Used for**: Word meaning lookup (`jmdict_lookup` in `japan_bot.py`)
- **File**: `jamdictdb/jamdict.db` (SQLite, built from JMdict XML)
- **Access**: via [jamdict](https://github.com/neocl/jamdict) Python library
- **Source**: [JMdict Project](https://www.edrdg.org/jmdict/j_jmdict.html) by Jim Breen
- **Raw XML**: `JMdict_b` (upstream source, not used directly)
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
- **Used for**: Grammar pattern matching (`grammar_patterns.py`)
- **Files**: `N5_grammar.json`, `N4_grammar.json`, `N3_grammar.json`,
  `N2_grammar.json`, `N1_grammar_01.json`, `N1_grammar_02.json`
- **Format**: JSON array with fields: `id`, `level`, `pattern`, `meaning`,
  `example_ja`, `example_en`
- **Source**: Compiled manually from TUFS Language Modules and JLPT handbook
- **License**: Personal use

---

## 4. JLPT Vocabulary List (N5–N1)  ← NEW
- **Used for**: JLPT level tagging of words in bot analysis
- **File**: `jlpt_vocab.json` (built from source below)
- **Format**: `{ "word": "N3", ... }` — expression → JLPT level
- **Source**: [Bluskyo/JLPT_Vocabulary](https://github.com/Bluskyo/JLPT_Vocabulary)
  on GitHub, which parses the original word lists by
  [Jonathan Waller](http://www.tanos.co.uk/jlpt/) (same source as Jisho.org)
- **License**: Creative Commons BY (Jonathan Waller's original data)
- **Coverage**: ~8,500 words across N5–N1
- **Counts**: N5: 700 | N4: 649 | N3: 1,835 | N2: 1,846 | N1: 3,475
- **Note**: No official JLPT vocab list exists. This is the most widely used
  unofficial reference. Levels are approximate — words may appear on a
  different level's exam than listed.

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

## Summary Table

| Source | File | Words/Entries | License |
|---|---|---|---|
| JMdict | `jamdict.db` | 191,541 entries | CC BY-SA 4.0 |
| Tatoeba/WWWJDIC | `wwwjdic.csv` | ~147k sentences | CC BY 2.0 |
| JLPT Grammar | `N5–N1_grammar.json` | N5–N1 patterns | Personal |
| JLPT Vocabulary | `jlpt_vocab.json` | ~8,500 words | CC BY |
| UniDic | (bundled) | — | BSD / CC BY-SA 4.0 |
