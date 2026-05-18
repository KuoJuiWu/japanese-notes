# Japanese Vocabulary Bot — Project Notes

---

## 📋 Changelog

---

### v2.0 — 2026-05-18
**Grammar Analysis Pipeline (Step 1–3)**

#### 新增檔案
| 檔案 | 說明 |
|---|---|
| `morphology.py` | Step 1：形態素解析，抽出 pos / base_form / conj_type / conj_form |
| `aux_verbs.py` | Step 2：助動詞辨識，支援單一助動詞＋複合語尾 |
| `grammar_patterns.py` | Step 3：50 個文法模板比對（N5–N1） |

#### 改動
- `japan_bot.py`：引入 morphology / aux_verbs / grammar_patterns
- `jmdict_lookup()`：改為依詞性篩選 JMdict sense，修正「は: feather」類錯誤
- `analyze_japanese()`：新增回傳 MorphToken 列表（含 conj_type / conj_form）
- `build_note()`：新增 `## 文法` 和 `## 文法模板` 區塊，新增免責聲明 footer
- Telegram preview：顯示活用型和活用形

#### 新增指令
- `/debug <句子>`：印出 UniDic 原始 token 資料，用於驗證 pattern 的 base_form

#### Pipeline（v2.0）
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
   助動詞辨識               ない／た／ている 等（回傳 used_indices）
        ↓
   match_patterns()        grammar_patterns.py
   文法模板比對             たことがある／なければならない 等
        ↓
   get_example_smart()     Massif API
   查例句
        ↓
   build_note()
   組合 Markdown 筆記（含文法區塊＋免責聲明）
        ↓
   git push + mkdocs gh-deploy
   上傳到 GitHub Pages
```

---

### v1.0 — 初始版本

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

## Pipeline（v1.0）
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

## Key Files（v1.0）
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
- [ ] Bot runs locally — consider hosting on a server for 24/7 or at least running in backend
- [ ] Could add /list command to browse saved notes from Telegram
- [ ] Could add /edit command to update existing notes
- [ ] Task Scheduler set up for auto-start on Windows boot

## Website
https://kuojuiwu.github.io/japanese-notes/

## GitHub Repo
https://github.com/KuoJuiWu/japanese-notes