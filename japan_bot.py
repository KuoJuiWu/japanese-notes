from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    filters, ContextTypes, ConversationHandler,
    CommandHandler
)
from fugashi import Tagger
from jamdict import Jamdict
import jaconv
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import re
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN in .env")

ALLOWED_USER_ID_RAW = os.getenv("ALLOWED_USER_ID")
if not ALLOWED_USER_ID_RAW:
    raise ValueError("Missing ALLOWED_USER_ID in .env")

ALLOWED_USER_ID = int(ALLOWED_USER_ID_RAW)

tagger   = Tagger()
BASE_DIR = Path(__file__).parent
jam      = Jamdict(db_file=str(BASE_DIR / "jamdictdb" / "jamdict.db"))

NOTES_DIR = BASE_DIR / "docs" / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

SKIP_POS = {"補助記号", "空白"}

WAIT_MEANING, WAIT_EXAMPLE = range(2)

user_state: dict = {}


def safe_filename(text: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]', "_", text).strip()
    clean = clean[:30] if clean else "untitled"
    date  = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{date}_{clean}.md"


def analyze_japanese(text: str) -> tuple[str, list[dict]]:
    rows  = []
    words = []

    for word in tagger(text):
        pos = word.feature.pos1
        if pos in SKIP_POS:
            continue

        surface = word.surface
        kana    = word.feature.kana
        lemma   = word.feature.lemma
        reading = jaconv.kata2hira(kana) if kana else surface
        base    = lemma if lemma and lemma != "*" else surface

        rows.append(f"| {surface} | {reading} | {pos} | {base} |")
        words.append({"surface": surface, "reading": reading, "pos": pos, "base": base})

    table    = "\n".join(rows)
    markdown = f"""## 分詞解析
| 表面形 | 讀音 | 詞性 | 原形 |
|---|---|---|---|
{table}
"""
    return markdown, words


def jmdict_lookup(words: list[dict]) -> str:
    seen    = set()
    results = []

    for w in words:
        base = w["base"]
        if base in seen:
            continue
        seen.add(base)

        result = jam.lookup(base)
        if not result.entries:
            continue

        entry    = result.entries[0]
        meanings = [str(g) for g in entry.senses[0].gloss]
        results.append(f"{base}: {', '.join(meanings)}")

    return "\n".join(results) if results else "（自動查詢無結果）"


async def get_example(word: str) -> tuple[str, str]:
    async with httpx.AsyncClient() as client:
        # first try top 10
        r = await client.get(f"https://massif.la/ja/search?q={word}&fmt=json")
        results = r.json().get("results", [])
        matches = [s for s in results if word in s["text"]]

        # no exact match in 10, expand to 50
        if not matches:
            r = await client.get(f"https://massif.la/ja/search?q={word}&fmt=json&hits=50")
            results = r.json().get("results", [])
            matches = [s for s in results if word in s["text"]]

    if not matches:
        return "（自動查詢無結果）", ""

    best     = min(matches, key=lambda s: len(s["text"]))
    sentence = best["text"]
    source   = best.get("info_json", {}).get("title") or "Massif"

    return sentence, source


async def get_example_smart(text: str, words: list[dict]) -> tuple[str, str, list[str], str]:
    attempts = []

    # 1. search full sentence
    attempts.append(text)
    example, source = await get_example(text)
    if example != "（自動查詢無結果）":
        return example, source, attempts, ""

    # 2. search content words: noun, verb, adjective
    candidates = [
        w["base"]
        for w in words
        if w["pos"] in ("名詞", "動詞", "形容詞")
    ]

    # remove duplicates
    seen = set()
    candidates = [x for x in candidates if not (x in seen or seen.add(x))]

    for word in candidates:
        attempts.append(word)
        example, source = await get_example(word)
        if example != "（自動查詢無結果）":
            return example, source, attempts, ""

    # 3. all failed
    warning = (
        "⚠️ Massif could not find a matching example.\n"
        "Possible causes:\n"
        "- typo\n"
        "- uncommon phrasing\n"
        "- corpus limitation\n"
        "- conjugation mismatch"
    )

    return "（自動查詢無結果）", "", attempts, warning


def build_note(
    text:        str,
    analysis_md: str,
    meaning:     str,
    example:     str,
    source:      str,
    attempts:    list[str],
    warning:     str,
) -> str:
    source_line = f"*{source} (via Massif)*" if source and source != "Massif" else "*Massif*"
    if source in ("手動入力", "（待填入）"):
        source_line = source

    encoded = text.replace(" ", "%20")

    # only show debug sections if Massif was involved
    if source not in ("手動入力", "（待填入）"):
        attempt_lines = "\n".join([f"- {a}" for a in attempts])
        debug_section = f"""
## Example Search Attempts
{attempt_lines}

## Warning
{warning if warning else "None"}
"""
    else:
        debug_section = ""

    return f"""---
title: "{text}"
created: "{datetime.now().isoformat(timespec='seconds')}"
tags:
  - japanese
---
# {text}

## 原句 (Original)
{text}

{analysis_md}
## 意思 (Meaning)
{meaning}

## 例句 (Example)
{example}

## 出典 (Source)
{source_line}

## 参考 (Reference)
- [Kotobank](https://kotobank.jp/word/{encoded})
- [Weblio](https://www.weblio.jp/content/{encoded})
{debug_section}"""


async def handle_japanese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Unauthorized。")
        return ConversationHandler.END

    text               = update.message.text.strip()
    analysis_md, words = analyze_japanese(text)
    auto_meaning       = jmdict_lookup(words)
    auto_example, auto_source, attempts, warning = await get_example_smart(text, words)

    user_state[ALLOWED_USER_ID] = {
        "text":         text,
        "analysis_md":  analysis_md,
        "filename":     safe_filename(text),
        "auto_meaning": auto_meaning,
        "auto_example": auto_example,
        "auto_source":  auto_source,
        "attempts":     attempts,
        "warning":      warning,
    }

    preview_lines = [f"{w['surface']}（{w['reading']}）{w['pos']}" for w in words]
    preview       = "\n".join(preview_lines)

    await update.message.reply_text(
        f"✅ 分析完成：\n\n{preview}\n\n"
        f"📖 JMdict 自動意思：\n{auto_meaning}\n\n"
        f"📝 意思は？\n"
        f"（自分で入力 / /auto でJMdict使用 / /skip でスキップ）"
    )
    return WAIT_MEANING


async def handle_meaning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meaning = update.message.text.strip()
    user_state[ALLOWED_USER_ID]["meaning"] = meaning

    state = user_state[ALLOWED_USER_ID]
    await update.message.reply_text(
        f"✏️ 例句は？\n"
        f"Massif 自動例句：\n{state['auto_example']}\n\n"
        f"（自分で入力 / /auto でMassif使用 / /skip でスキップ）"
    )
    return WAIT_EXAMPLE


async def handle_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    example = update.message.text.strip()
    state   = user_state[ALLOWED_USER_ID]

    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        example     = example,
        source      = "手動入力",
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    path.write_text(note, encoding="utf-8")
    git_push(state["filename"])
    deploy()
    await update.message.reply_text(
        f"🎉 Saved：`{path.name}`",
        parse_mode="Markdown"
    )

    user_state.pop(ALLOWED_USER_ID, None)
    return ConversationHandler.END


async def cmd_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = user_state.get(ALLOWED_USER_ID)
    if not state:
        await update.message.reply_text("No active note.")
        return ConversationHandler.END

    # /auto during WAIT_MEANING
    if "meaning" not in state:
        state["meaning"] = state["auto_meaning"]
        await update.message.reply_text(
            f"✅ JMdict 意思を使用：\n{state['meaning']}\n\n"
            f"✏️ 例句は？\n"
            f"Massif 自動例句：\n{state['auto_example']}\n\n"
            f"（自分で入力 / /auto でMassif使用 / /skip でスキップ）"
        )
        return WAIT_EXAMPLE

    # /auto during WAIT_EXAMPLE
    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        example     = state["auto_example"],
        source      = state["auto_source"],
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    path.write_text(note, encoding="utf-8")
    git_push(state["filename"])
    deploy()

    await update.message.reply_text(
        f"✅ Massif 例句を使用、保存：`{path.name}`",
        parse_mode="Markdown"
    )

    user_state.pop(ALLOWED_USER_ID, None)
    return ConversationHandler.END


async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = user_state.get(ALLOWED_USER_ID)
    if not state:
        await update.message.reply_text("No active note.")
        return ConversationHandler.END

    # /skip during WAIT_MEANING
    if "meaning" not in state:
        state["meaning"] = "（待填入）"
        await update.message.reply_text(
            "⏭️ 意思をスキップ\n\n"
            f"✏️ 例句は？\n"
            f"Massif 自動例句：\n{state['auto_example']}\n\n"
            f"（自分で入力 / /auto でMassif使用 / /skip でスキップ）"
        )
        return WAIT_EXAMPLE

    # /skip during WAIT_EXAMPLE
    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        example     = "（待填入）",
        source      = "（待填入）",
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    path.write_text(note, encoding="utf-8")
    git_push(state["filename"])
    deploy()
    
    await update.message.reply_text(
        f"⏭️ 例句をスキップ、保存：`{path.name}`",
        parse_mode="Markdown"
    )

    user_state.pop(ALLOWED_USER_ID, None)
    return ConversationHandler.END

################### For Github and MkDocs ######################
import subprocess

def git_push(filename: str) -> None:
    try:
        subprocess.run(["git", "add", f"docs/notes/{filename}"], check=True)
        subprocess.run(["git", "commit", "-m", f"add: {filename}"], check=True)
        subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

def deploy() -> None:
    try:
        subprocess.run(["mkdocs", "gh-deploy", "--quiet"], check=True)
        print("Deployed to GitHub Pages")
    except subprocess.CalledProcessError as e:
        print(f"Deploy error: {e}")

##################################################################

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_japanese)],
    states={
        WAIT_MEANING: [
            CommandHandler("auto", cmd_auto),
            CommandHandler("skip", cmd_skip),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_meaning),
        ],
        WAIT_EXAMPLE: [
            CommandHandler("auto", cmd_auto),
            CommandHandler("skip", cmd_skip),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_example),
        ],
    },
    fallbacks=[],
)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(conv_handler)
app.run_polling()