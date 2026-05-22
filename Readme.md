# 🇯🇵 Japanese Notes Bot

A personal Japanese learning system with two components:
- **Telegram Bot** — analyzes Japanese text and saves structured vocabulary notes to MkDocs
- **Grammar Reference** — 636 N5–N1 grammar patterns as a static MkDocs site

## 📦 Tech Stack

| Tool | Purpose |
|---|---|
| python-telegram-bot | Telegram bot framework |
| fugashi + UniDic | Japanese morphological analysis |
| jaconv | Katakana → Hiragana conversion |
| jamdict + JMdict | Offline Japanese dictionary |
| Tatoeba / wwwjdic.csv | Offline example sentence lookup |
| MkDocs + Material | Markdown → website |
| GitHub Pages | Free hosting |

## 🗂 File Structure

```
japanese-notes/
├── japan_bot.py                ← Main bot script
├── morphology.py               ← Morphological analysis
├── aux_verbs.py                ← Auxiliary verb recognition
├── tatoeba_search.py           ← Offline example sentence lookup
├── jlpt_lookup.py              ← JLPT level tagging + /wordbank
├── generate_grammar_pages.py   ← Grammar site generator
├── PROJECT_SOURCES.md          ← Data source documentation
├── categories.json             ← Custom categories (auto-generated)
├── data/
│   ├── wwwjdic.csv             ← Tatoeba sentence corpus
│   ├── jlpt_vocab.json         ← JLPT N5–N1 vocabulary list
│   ├── N5_grammar.json
│   ├── N4_grammar.json
│   ├── N3_grammar.json
│   ├── N2_grammar.json
│   ├── N1_grammar_01.json
│   └── N1_grammar_02.json
├── docs/
│   ├── index.md                ← MkDocs homepage
│   ├── notes/                  ← Auto-generated vocabulary notes
│   │   ├── index.md            ← Notes overview (auto-updated)
│   │   ├── song/
│   │   ├── anime/
│   │   ├── textbook/
│   │   ├── daily/
│   │   └── other/
│   ├── grammar/                ← Generated grammar reference pages
│   └── stylesheets/
│       └── extra.css
├── mkdocs.yml                  ← MkDocs configuration
├── jamdictdb/
│   └── jamdict.db              ← Local dictionary (not on GitHub)
└── .env                        ← Tokens (not on GitHub)
```

## ⚙️ Pipeline

```
Telegram 輸入日文句子
        ↓
   analyze()              morphology.py
   MorphToken 列表         pos / base_form / conj_type / conj_form
        ↓
   lookup_meaning()        morphology.py
   依詞性查 JMdict          名詞／動詞／形容詞
        ↓
   explain_aux()           aux_verbs.py
   助動詞辨識               ない／た／ている 等
        ↓
   get_example_smart()     tatoeba_search.py（離線）
   從 wwwjdic.csv 查例句
        ↓
   build_note()
   組合 Markdown 筆記（含英文例句翻譯）
        ↓
   update_notes_index()    自動更新分類 index
   update_mkdocs_nav()     自動更新 nav（自訂分類）
        ↓
   git push + mkdocs gh-deploy --dirty
   上傳到 GitHub Pages
```

## 🚀 Setup

1. Clone the repo
```bash
git clone https://github.com/KuoJuiWu/japanese-notes.git
cd japanese-notes
```

2. Install dependencies
```bash
pip install python-telegram-bot fugashi unidic-lite jaconv jamdict jamdict-data python-dotenv mkdocs mkdocs-material
```

3. Download UniDic
```bash
python -m unidic download
```

4. Set up `.env`
```
TELEGRAM_TOKEN=your_token_here
ALLOWED_USER_ID=your_telegram_user_id
```

5. Place `jamdict.db` in `jamdictdb/jamdict.db`

6. Generate grammar pages (first time only)
```bash
python generate_grammar_pages.py
```

7. Run the bot
```bash
python japan_bot.py
```

## 💬 Bot Commands

| Command | Description |
|---|---|
| Send Japanese text | Start the note creation flow |
| `/auto` | Use JMdict meaning or Tatoeba example automatically |
| `/skip` | Skip meaning or example input |
| `/wordbank <level>` | Get 20 random unseen words at a JLPT level e.g. `/wordbank N4` |
| `/debug <sentence>` | Inspect raw UniDic token output for debugging |

## 🌐 Website

https://kuojuiwu.github.io/japanese-notes/

## ⚠️ Disclaimer

Meanings are sourced from JMdict (offline dictionary). Grammar analysis is rule-based and auto-generated. Example sentences are from the Tatoeba corpus. Content is for personal learning purposes only.