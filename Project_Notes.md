# Japanese Vocabulary Bot — Project Notes

## Overview
A Telegram bot that receives Japanese text, analyzes it linguistically,
and saves structured Markdown vocabulary notes automatically.

## Tech Stack
| Tool | Purpose |
|---|---|
| python-telegram-bot | Telegram bot framework |
| fugashi + UniDic | Japanese morphological analysis |
| jaconv | Katakana → Hiragana conversion |
| jamdict + JMdict | Offline Japanese dictionary |
| Massif API | Example sentence lookup |
| MkDocs + Material | Markdown → website |
| GitHub Pages | Free hosting |

## Pipeline
```
Telegram message (Japanese text)
↓
fugashi → tokenize → POS, reading, lemma
↓
jamdict → auto meaning lookup
↓
Massif → auto example sentence lookup
↓
Conversation: confirm/edit meaning and example
↓
Save .md to docs/notes/
↓
git push → GitHub repo
↓
mkdocs gh-deploy → GitHub Pages website
```

## Note Structure
Each saved note contains:
- YAML frontmatter (title, created, tags)
- 原句 (original sentence)
- 分詞解析 (word breakdown table)
- 意思 (meaning — manual or JMdict auto)
- 例句 (example — manual or Massif auto)
- 出典 (source citation)
- 参考 (Kotobank + Weblio reference links)
- Example Search Attempts + Warning (if Massif was used)

## Conversation Flow
```
Send Japanese text
↓
Bot shows: analysis preview + JMdict meaning
↓
意思は？
  → type own    → uses your text
  → /auto       → uses JMdict
  → /skip       → 待填入
↓
例句は？
  → type own    → uses your text + source: 手動入力
  → /auto       → uses Massif result
  → /skip       → 待填入
↓
Note saved → git push → deploy
```

## Massif Example Search Strategy
```
1. Search full sentence (top 10)
   → exact match found? → pick shortest ✅
2. Expand to 50
   → exact match found? → pick shortest ✅
3. Search each content word lemma (名詞, 動詞, 形容詞)
   → exact match found? → pick shortest ✅
4. All failed → （自動查詢無結果） + warning message
```

## Key Files
```
Japanese/
├── japan_bot.py          ← main bot script
├── docs/
│   ├── index.md          ← MkDocs homepage
│   ├── notes/            ← saved vocabulary notes
│   └── stylesheets/
│       └── extra.css     ← custom MkDocs styling
├── mkdocs.yml            ← MkDocs configuration
├── jamdictdb/
│   └── jamdict.db        ← local dictionary (not on GitHub)
└── .env                  ← tokens (not on GitHub)
```

## Known Issues / Future Ideas
- [ ] Kotobank URL uses search instead of direct link (no stable ID)
- [ ] Bot runs locally — consider hosting on a server for 24/7
- [ ] Could add /list command to browse saved notes from Telegram
- [ ] Could add /edit command to update existing notes
- [ ] Task Scheduler set up for auto-start on Windows boot

## Website
https://kuojuiwu.github.io/japanese-notes/

## GitHub Repo
https://github.com/KuoJuiWu/japanese-notes