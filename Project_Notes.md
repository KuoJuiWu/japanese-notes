# Japanese Vocabulary Bot — Project Notes

---

## 📋 Changelog

---

### v4.0 — 2026-05-25
**Cloud Deployment + Infrastructure + Site Expansion**

#### 動機
Bot 原本需要在本機電腦持續執行。目標是改為僅使用手機（Telegram）操作，不依賴電腦。

#### 嘗試過的方案（失敗）
| 方案 | 失敗原因 |
|---|---|
| Cloudflare Workers | 僅支援 JavaScript，無法執行 Python |
| PythonAnywhere 免費方案 | 512MB 磁碟限制，`unidic-lite` 約 400MB，安裝即超額 |
| Google Drive 串流 | MeCab 仍需本地檔案路徑，無法解決磁碟限制 |

#### 最終方案：Google Cloud VM
- 機器類型：`e2-micro`，區域：`us-west1`（永久免費方案）
- 儲存空間：30GB，足以安裝完整 NLP 套件
- systemd 管理 bot 程序，開機自動啟動、當機自動重啟
- SSH 金鑰（ed25519）認證 GitHub
- rclone 掛載 Google Drive，備份 `jamdict.db`

#### 重要路徑（VM）
| 路徑 | 說明 |
|---|---|
| `~/japanese-notes/` | 專案目錄 |
| `~/venv/` | Python 虛擬環境 |
| `~/japanese-notes/jamdictdb/jamdict.db` | 本地字典（Google Drive 備份） |
| `~/gdrive_japanbot/` | Google Drive 掛載點 |
| `/etc/systemd/system/japanese-bot.service` | systemd 服務設定 |

#### 新增檔案
| 檔案 | 說明 |
|---|---|
| `docs/matcha/index.html` | MATCHA やさしい日本語 RSS 閱讀器 |
| `bot/__init__.py` | Python package 初始化 |

#### 專案結構重組
- 所有 Python 模組移入 `bot/` 資料夾
- `generate_grammar_pages.py` 移入 `scripts/`
- 根目錄改為只含設定檔與資料夾

#### 改動（`bot/japan_bot.py`）
```python
GIT   = "git"                                          # Windows 路徑 → Linux
MKDOCS = "/home/kuojuiw/venv/bin/mkdocs"              # 使用完整路徑（systemd 不啟動 venv）
BASE_DIR = Path(__file__).parent.parent                # 調整為新的資料夾結構
```

#### MATCHA やさしい日本語 RSS 閱讀器
- Cloudflare Workers CORS Proxy：`https://learnjapanese-from-matcha.kuojuiw.workers.dev/`
- 從 RSS feed 取得文章列表，inline 顯示全文（含振り仮名）
- 限制：RSS feed 僅包含 2025 年以前的文章（新文章需登入）
- 保留作為學習 RSS / CORS 概念的參考實作

#### 遇到的問題
| 問題 | 解法 |
|---|---|
| 首次開機 dpkg lock | 等待背景自動更新完成，再執行安裝 |
| rclone 認證（`y` 失敗） | 遠端伺服器無瀏覽器，改用 `n`（手動 token） |
| systemd 找不到模組 | 使用完整絕對路徑，不依賴 venv 啟動 |
| Telegram 409 衝突 | `ps aux | grep japan_bot` 找出重複程序並 kill |
| git 分支分歧 | `git config pull.rebase false` + `git pull --allow-unrelated-histories` |
| RSS 標題顯示原始 HTML | 使用 `innerHTML` + `decodeHTML()` 解碼 |

#### Bot 現在的工作流程
```
手機 Telegram
      ↓
Google Cloud VM（24/7 運行）
      ↓ 分析、儲存筆記
GitHub（master branch）← Markdown 原始檔
      ↓ mkdocs gh-deploy
GitHub Pages（gh-pages）← 建置完成的網站
```

#### 刪除筆記流程
```bash
rm docs/notes/{category}/filename.md
git add . && git commit -m "remove: filename" && git push origin master
~/venv/bin/mkdocs gh-deploy --dirty
```

#### Known Issues（已知待修）
- `expected str, bytes or os.PathLike object, not NoneType`：`deploy()` 後的小錯誤，不影響主要功能

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
│   └── index.md
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
- 保留 `aux_verbs.py`（助動詞分析）
- 移除文法模板比對

**System 2 — 文法參考網站（MkDocs）**
- 從 N5–N1 文法 JSON 產生靜態頁面（636 個模板）
- 執行 `python generate_grammar_pages.py` 產生 `docs/grammar/`

---

### v2.0 — 2026-05-18
**Grammar Analysis Pipeline (Step 1–3)**

#### 新增檔案
| 檔案 | 說明 |
|---|---|
| `morphology.py` | 形態素解析，抽出 pos / base_form / conj_type / conj_form |
| `aux_verbs.py` | 助動詞辨識，支援單一助動詞＋複合語尾 |
| `grammar_patterns.py` | 50 個文法模板比對（N5–N1） |

#### 改動
- `japan_bot.py`：引入 morphology / aux_verbs / grammar_patterns
- `jmdict_lookup()`：改為依詞性篩選 JMdict sense
- `build_note()`：新增文法區塊＋免責聲明 footer

---

### v1.0 — 初始版本
**基礎 Telegram Bot**

#### Pipeline（v1.0）
```
Telegram 輸入日文句子
        ↓
fugashi → tokenize → POS / reading / lemma
        ↓
jamdict → 自動查詢意思
        ↓
Massif API → 自動查詢例句
        ↓
儲存 .md → git push → mkdocs gh-deploy → GitHub Pages
```

#### Known Issues（v1.0，已在後續版本解決）
- Bot 需本機執行 → v4.0 移至 Google Cloud VM
- NHK Easy News 整合（計畫中）→ NHK 已改為付費登入牆，改用 MATCHA