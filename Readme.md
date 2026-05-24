# 🇯🇵 Japanese Notes

A personal Japanese learning system with two components:

- **System 1 — Telegram Bot**: analyzes Japanese text and saves structured vocabulary notes
- **System 2 — MkDocs Site**: grammar reference (N5–N1), vocabulary notes, and MATCHA easy Japanese reader

🌐 **Site**: https://kuojuiwu.github.io/japanese-notes/

---

## 📦 Tech Stack

| Tool | Purpose |
|---|---|
| python-telegram-bot | Telegram bot framework |
| fugashi + UniDic | Japanese morphological analysis |
| jaconv | Katakana → Hiragana conversion |
| jamdict + JMdict | Offline Japanese dictionary |
| Tatoeba / wwwjdic.csv | Offline example sentence lookup |
| MkDocs + Material | Markdown → website |
| GitHub Pages | Free static hosting |
| Google Cloud VM (e2-micro) | 24/7 bot hosting (free tier) |
| Cloudflare Workers | CORS proxy for MATCHA RSS feed |
| rclone | Google Drive mount for jamdict.db backup |

---

## 🗂 File Structure

```
japanese-notes/
├── bot/
│   ├── __init__.py
│   ├── japan_bot.py            ← Main bot script
│   ├── morphology.py           ← Morphological analysis
│   ├── aux_verbs.py            ← Auxiliary verb recognition
│   ├── tatoeba_search.py       ← Offline example sentence lookup
│   ├── jlpt_lookup.py          ← JLPT level tagging + /wordbank
│   └── nhk.py                  ← (placeholder)
├── scripts/
│   └── generate_grammar_pages.py  ← Grammar site generator (run once)
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
│   ├── matcha/
│   │   └── index.html          ← MATCHA easy Japanese RSS reader
│   ├── notes/                  ← Auto-generated vocabulary notes
│   │   ├── index.md
│   │   ├── song/
│   │   ├── anime/
│   │   ├── textbook/
│   │   ├── daily/
│   │   └── other/
│   ├── grammar/                ← Generated grammar reference pages
│   └── stylesheets/
│       └── extra.css
├── mkdocs.yml
├── PROJECT_SOURCES.md
├── jamdictdb/
│   └── jamdict.db              ← Not on GitHub (backed up on Google Drive)
└── .env                        ← Not on GitHub
```

---

## ⚙️ Pipeline

```
Telegram 輸入日文句子
        ↓
   analyze()              morphology.py — MeCab/UniDic tokenization
        ↓
   lookup_meaning()        morphology.py — JMdict lookup
        ↓
   explain_aux()           aux_verbs.py — auxiliary verb recognition
        ↓
   get_example_smart()     tatoeba_search.py — offline example sentence
        ↓
   build_note()            assemble Markdown note
        ↓
   update_notes_index()    auto-update category index
   update_mkdocs_nav()     auto-update mkdocs.yml nav
        ↓
   git push → GitHub (master)
   mkdocs gh-deploy → GitHub Pages (gh-pages)
```

---

## 🚀 Infrastructure

The bot runs 24/7 on a **Google Cloud VM** (e2-micro, free tier):

- **Region**: `us-west1`
- **OS**: Debian GNU/Linux 12
- **Python venv**: `~/venv/`
- **Project**: `~/japanese-notes/`
- **jamdict.db**: `~/japanese-notes/jamdictdb/jamdict.db` (backed up on Google Drive via rclone)
- **Process manager**: systemd (`/etc/systemd/system/japanese-bot.service`)
- **GitHub auth**: SSH key (ed25519)

### Manage the bot service
```bash
sudo systemctl status japanese-bot   # check status
sudo systemctl restart japanese-bot  # restart
sudo journalctl -u japanese-bot -f   # live logs
```

---

## 💻 Local Setup (development only)

1. Clone the repo
```bash
git clone https://github.com/KuoJuiWu/japanese-notes.git
cd japanese-notes
```

2. Create virtual environment
```bash
python3 -m venv venv && source venv/bin/activate  # Linux/Mac
python -m venv venv && venv\Scripts\activate       # Windows
```

3. Install dependencies
```bash
pip install python-telegram-bot fugashi unidic-lite jaconv jamdict python-dotenv mkdocs mkdocs-material
```

4. Set up `.env`
```
TELEGRAM_TOKEN=your_token_here
ALLOWED_USER_ID=your_telegram_user_id
```

5. Place `jamdict.db` in `jamdictdb/jamdict.db`

6. Generate grammar pages (first time only)
```bash
python scripts/generate_grammar_pages.py
```

7. Run the bot
```bash
python bot/japan_bot.py
```

---

## 💬 Bot Commands

| Command | Description |
|---|---|
| Send Japanese text | Start the note creation flow |
| `/auto` | Use JMdict meaning or Tatoeba example automatically |
| `/skip` | Skip meaning or example input |
| `/wordbank <level>` | Get 20 random unseen words at a JLPT level e.g. `/wordbank N4` |
| `/debug <sentence>` | Inspect raw UniDic token output |

---

## ⚠️ Disclaimer

Meanings are sourced from JMdict (offline dictionary). Grammar analysis is rule-based and auto-generated. Example sentences are from the Tatoeba corpus. Content is for personal learning purposes only.

---

## 🙏 Acknowledgements

### Data & Dictionaries
- **Jim Breen** — JMdict/EDICT project, the foundation of Japanese electronic dictionaries
- **Tatoeba Project** — community-built sentence corpus used for example sentences
- **Jonathan Waller** — JLPT vocabulary lists widely used by the Japanese learning community
- **NINJAL** — National Institute for Japanese Language and Linguistics, creators of UniDic

### Tools & Libraries
- **fugashi + unidic-lite** — Japanese morphological analysis
- **jamdict** — Python interface to JMdict
- **MkDocs + Material theme** — static site generation
- **python-telegram-bot** — Telegram bot framework

### Platforms
- **GitHub Pages** — free static site hosting
- **Google Cloud** — free e2-micro VM for 24/7 bot hosting
- **Cloudflare Workers** — free CORS proxy for MATCHA RSS feed

### Content
- **MATCHA やさしい日本語** — easy Japanese articles for reading practice
- **TUFS Language Modules** — reference for JLPT grammar patterns