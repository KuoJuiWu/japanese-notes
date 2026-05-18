# 🇯🇵 Japanese Notes Bot

A personal Telegram bot that receives Japanese text, analyzes it linguistically, and saves structured Markdown vocabulary notes to a MkDocs website hosted on GitHub Pages.

## 📦 Tech Stack

| Tool | Purpose |
|---|---|
| python-telegram-bot | Telegram bot framework |
| fugashi + UniDic | Japanese morphological analysis |
| jaconv | Katakana → Hiragana conversion |
| jamdict + JMdict | Offline Japanese dictionary |
| Massif API | Example sentence lookup |
| MkDocs + Material | Markdown → website |
| GitHub Pages | Free hosting |

## 🗂 File Structure

```
japanese-notes/
├── japan_bot.py          ← Main bot script
├── morphology.py         ← Step 1: morphological analysis
├── aux_verbs.py          ← Step 2: auxiliary verb recognition
├── grammar_patterns.py   ← Step 3: grammar pattern matching
├── docs/
│   ├── index.md          ← MkDocs homepage
│   ├── about.md          ← System explanation
│   ├── notes/            ← Auto-generated vocabulary notes
│   └── stylesheets/
│       └── extra.css     ← Custom MkDocs styling
├── mkdocs.yml            ← MkDocs configuration
├── jamdictdb/
│   └── jamdict.db        ← Local dictionary (not on GitHub)
└── .env                  ← Tokens (not on GitHub)
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
   match_patterns()        grammar_patterns.py
   文法模板比對             たことがある／なければならない 等
        ↓
   get_example_smart()     Massif API
   查例句
        ↓
   build_note()
   組合 Markdown 筆記
        ↓
   git push + mkdocs gh-deploy
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
pip install python-telegram-bot fugashi unidic-lite jaconv jamdict jamdict-data httpx python-dotenv mkdocs mkdocs-material
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

6. Run the bot
```bash
python japan_bot.py
```

## 💬 Bot Commands

| Command | Description |
|---|---|
| Send Japanese text | Start the note creation flow |
| `/auto` | Use JMdict meaning or Massif example automatically |
| `/skip` | Skip meaning or example input |
| `/debug <sentence>` | Inspect raw UniDic token output for debugging |

## 🌐 Website

https://kuojuiwu.github.io/japanese-notes/

## ⚠️ Disclaimer

Meanings are sourced from JMdict (offline dictionary). Grammar analysis is rule-based and auto-generated. Example sentences are from the Massif corpus. Content is for personal learning purposes only.