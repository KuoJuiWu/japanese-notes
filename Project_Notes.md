# Japanese Vocabulary Bot — Project Notes

---

## 📋 Changelog

---

### v3.1 — 2026-05-23
**MkDocs Navigation + Notes Index System**

#### 新增檔案
| 檔案 | 說明 |
|---|---|
| `docs/notes/index.md` | 詞彙筆記總覽頁（自動更新） |
| `docs/notes/{category}/index.md` | 各分類筆記列表（自動更新） |

#### 改動
- `japan_bot.py`：新增 `update_notes_index()` — 每次儲存筆記時自動更新分類 index
- `japan_bot.py`：新增 `update_mkdocs_nav()` — 新建自訂分類時自動更新 mkdocs.yml nav
- `japan_bot.py`：`git_push()` 改為同時 stage 筆記、notes/ 資料夾、mkdocs.yml
- `japan_bot.py`：`deploy()` 新增 `--dirty` flag，只重建有變動的頁面（加快部署速度）
- `mkdocs.yml`：新增 `nav` 區塊，含 Vocabulary Notes（按分類）和 Grammar Reference（按等級）
- `mkdocs.yml`：新增 `navigation.tabs` 和 `navigation.indexes` theme features

#### Notes Index 結構
```
docs/notes/
├── index.md              ← 所有筆記總覽表（自動 append）
├── song/
│   └── index.md          ← Song 分類筆記列表（自動 append）
├── anime/
│   └── index.md
├── textbook/
│   └── index.md
├── daily/
│   └── index.md
├── other/
│   └── index.md
└── {custom}/             ← 自訂分類（bot 建立時自動產生）
    └── index.md
```

#### 自訂分類自動化流程
```
使用者透過 bot 新建分類（如 📁 music）
        ↓
update_notes_index() → 建立 docs/notes/music/index.md
        ↓
update_mkdocs_nav() → 在 mkdocs.yml nav 加入 "📁 music: notes/music/index.md"
        ↓
git_push() → stage 筆記 + notes/ + mkdocs.yml
        ↓
deploy --dirty → 只重建變動頁面
```

---

### v3.0 — 2026-05-23
**Offline Upgrade + JLPT Vocabulary Bank + Grammar Reference System**

#### 新增檔案
| 檔案 | 說明 |
|---|---|
| `tatoeba_search.py` | 取代 Massif API，從本地 wwwjdic.csv 查例句（完全離線） |
| `jlpt_lookup.py` | JLPT 詞彙等級查詢 + `/wordbank` 指令 |
| `data/jlpt_vocab.json` | JLPT N5–N1 詞彙表（8,138 個詞，來源：Jonathan Waller） |
| `generate_grammar_pages.py` | 從文法 JSON 產生 MkDocs 文法參考頁面 |
| `PROJECT_SOURCES.md` | 所有資料來源的說明與授權記錄 |

#### 移除檔案
| 檔案 | 說明 |
|---|---|
| `grammar_patterns.py` | 移除：50 個硬編碼文法模板，與 JSON 文法系統無法整合 |

#### 改動
- `japan_bot.py`：移除 Massif / grammar_patterns，引入 tatoeba_search / jlpt_lookup
- `build_note()`：新增英文例句翻譯（blockquote 格式）
- `get_example_smart()`：改為同步函式（移除 async/await）
- 例句來源標示由 Massif 改為 Tatoeba
- 資料檔案移至 `data/` 資料夾統一管理

#### 新增指令
- `/wordbank N3`：隨機取得 20 個未儲存的指定等級詞彙（含讀音、意思、例句）

#### 系統架構調整
本版本將系統拆分為兩個獨立部分：

**System 1 — 詞彙 Bot（Telegram）**
- 專注於詞彙分析、意思查詢、例句儲存
- 保留 `aux_verbs.py`（助動詞分析，token-based）
- 移除文法模板比對（與 JSON 格式不相容）

**System 2 — 文法參考網站（MkDocs）**
- 從 N5–N1 文法 JSON 產生靜態頁面（636 個模板）
- 每個文法模板獨立一頁，含結構、意思、例句
- 執行 `python generate_grammar_pages.py` 產生 `docs/grammar/`
- 類似 TUFS 語言模組的結構

**分離原因**：JSON 文法模板為人類可讀格式（如 `~によって`），
無法直接對應 fugashi token 序列，強行整合維護成本過高。

#### Pipeline（v3.0）
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
   從 wwwjdic.csv 查例句    base form → surface form fallback
        ↓
   build_note()
   組合 Markdown 筆記（含英文例句翻譯）
        ↓
   git push + mkdocs gh-deploy --dirty
   上傳到 GitHub Pages
```

#### Tatoeba 例句查詢策略
```
對每個內容詞（名詞、動詞、形容詞）：
  1. 嘗試 fugashi base form（如 朝御飯）→ 索引查詢
  2. 嘗試 surface form fallback（如 朝ご飯）→ 處理 UniDic/Tatoeba 格式差異
  → 首個命中即回傳，隨機從所有匹配句子中選一句
  → 找不到 → 留空（不顯示警告）
```

**重要發現**：UniDic 將 base form 正規化為完整漢字（如 御飯），
Tatoeba 保留日常混合寫法（如 ご飯），需要 surface form fallback 處理。

#### Key Files（v3.0）
```
Japanese/
├── japan_bot.py                ← 主程式
├── morphology.py               ← 形態素解析
├── aux_verbs.py                ← 助動詞分析
├── tatoeba_search.py           ← 離線例句查詢
├── jlpt_lookup.py              ← JLPT 等級查詢 + /wordbank
├── generate_grammar_pages.py   ← 文法頁面產生器
├── PROJECT_SOURCES.md          ← 資料來源說明
├── categories.json             ← 自訂分類（自動產生）
├── data/
│   ├── wwwjdic.csv             ← Tatoeba 語料庫
│   ├── jlpt_vocab.json         ← JLPT N5–N1 詞彙表
│   ├── N5_grammar.json
│   ├── N4_grammar.json
│   ├── N3_grammar.json
│   ├── N2_grammar.json
│   ├── N1_grammar_01.json
│   └── N1_grammar_02.json
├── docs/
│   ├── index.md
│   ├── notes/
│   ├── grammar/                ← 產生的文法頁面
│   └── stylesheets/
│       └── extra.css
├── mkdocs.yml
├── jamdictdb/
│   └── jamdict.db
└── .env
```

#### 資料來源
| 來源 | 檔案 | 用途 | 授權 |
|---|---|---|---|
| JMdict | `jamdict.db` | 詞義查詢（191k 詞條） | CC BY-SA 4.0 |
| Tatoeba/WWWJDIC | `wwwjdic.csv` | 例句（147k 句） | CC BY 2.0 |
| JLPT 文法 | `N5–N1_grammar.json` | 文法參考（636 個模板） | 個人使用 |
| JLPT 詞彙 | `jlpt_vocab.json` | JLPT 等級標記（8,138 詞） | CC BY |
| UniDic | fugashi 內建 | 形態素解析 + 詞性標記 | BSD / CC BY-SA 4.0 |

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
- [ ] NHK Easy News integration — feed real articles, flag unknown vocab + grammar

## Website
https://kuojuiwu.github.io/japanese-notes/

## GitHub Repo
https://github.com/KuoJuiWu/japanese-notes