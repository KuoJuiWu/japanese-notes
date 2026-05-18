from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    filters, ContextTypes, ConversationHandler,
    CommandHandler
)
from morphology import analyze, tokens_to_table_md, lookup_meaning, classify_tokens, MorphToken
from aux_verbs import explain_aux, format_aux_for_telegram, format_aux_for_note
from grammar_patterns import match_patterns, format_patterns_for_telegram, format_patterns_for_note

from jamdict import Jamdict
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import re
import os
import subprocess
import shutil
import logging
import time

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN in .env")

ALLOWED_USER_ID_RAW = os.getenv("ALLOWED_USER_ID")
if not ALLOWED_USER_ID_RAW:
    raise ValueError("Missing ALLOWED_USER_ID in .env")

ALLOWED_USER_ID = int(ALLOWED_USER_ID_RAW)

BASE_DIR = Path(__file__).parent
jam      = Jamdict(db_file=str(BASE_DIR / "jamdictdb" / "jamdict.db"))

NOTES_DIR = BASE_DIR / "docs" / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

WAIT_MEANING, WAIT_EXAMPLE = range(2)

user_state: dict = {}

GIT    = r"C:\Program Files\Git\cmd\git.exe"
MKDOCS = shutil.which("mkdocs")


def safe_filename(text: str) -> str:
    clean = re.sub(r'[\\/:*?"<>|]', "_", text).strip()
    clean = clean[:30] if clean else "untitled"
    date  = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{date}_{clean}.md"


def analyze_japanese(text: str) -> tuple[str, list[dict], list[MorphToken]]:
    tokens      = analyze(text)
    analysis_md = tokens_to_table_md(tokens)
    words = [
        {
            "surface":   t.surface,
            "reading":   t.reading,
            "pos":       t.pos,
            "base":      t.base_form,
            "conj_type": t.conj_type,
            "conj_form": t.conj_form,
        }
        for t in tokens
    ]
    return analysis_md, words, tokens


def jmdict_lookup(words: list[dict]) -> str:
    tokens = [
        MorphToken(
            surface    = w["surface"],
            reading    = w["reading"],
            pos        = w["pos"],
            pos_detail = "",
            base_form  = w["base"],
            conj_type  = w.get("conj_type", ""),
            conj_form  = w.get("conj_form", ""),
        )
        for w in words
    ]
    return lookup_meaning(tokens, jam)


async def get_example(word: str) -> tuple[str, str]:
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://massif.la/ja/search?q={word}&fmt=json")
        results = r.json().get("results", [])
        matches = [s for s in results if word in s["text"]]

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

    attempts.append(text)
    example, source = await get_example(text)
    if example != "（自動查詢無結果）":
        return example, source, attempts, ""

    candidates = [
        w["base"]
        for w in words
        if w["pos"] in ("名詞", "動詞", "形容詞")
    ]

    seen = set()
    candidates = [x for x in candidates if not (x in seen or seen.add(x))]

    for word in candidates:
        attempts.append(word)
        example, source = await get_example(word)
        if example != "（自動查詢無結果）":
            return example, source, attempts, ""

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
    grammar_md:  str,
    pattern_md:  str,
    example:     str,
    source:      str,
    attempts:    list[str],
    warning:     str,
) -> str:
    source_line = f"*{source} (via Massif)*" if source and source != "Massif" else "*Massif*"
    if source in ("手動入力", "（待填入）"):
        source_line = source

    encoded = text.replace(" ", "%20")

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

    grammar_section = f"\n{grammar_md}" if grammar_md else ""
    pattern_section = f"\n{pattern_md}" if pattern_md else ""

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
{grammar_section}{pattern_section}
## 例句 (Example)
{example}

## 出典 (Source)
{source_line}


## 参考 (Reference)
- [Kotobank](https://kotobank.jp/search/{encoded})
- [Weblio](https://www.weblio.jp/content/{encoded})

---
> ⚠️ **注意**：本筆記的意思說明來自 JMdict 離線字典，文法分析（助動詞、文法模板）
> 由規則程式自動產生，例句來自 Massif 語料庫。內容僅供學習參考，建議重要詞彙
> 以 Kotobank 或 Weblio 等權威來源進行確認{debug_section}

"""


def git_push(filename: str) -> None:
    try:
        repo = str(BASE_DIR)
        subprocess.run([GIT, "add", f"docs/notes/{filename}"], check=True, cwd=repo)
        subprocess.run([GIT, "commit", "-m", f"add: {filename}"], check=True, cwd=repo)
        subprocess.run([GIT, "push", "origin", "master"], check=True, cwd=repo)
    except subprocess.CalledProcessError as e:
        logging.error(f"Git error: {e}")


def deploy() -> None:
    try:
        subprocess.run([MKDOCS, "gh-deploy", "--quiet"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Deploy error: {e}")


def save_note(path: Path, note: str, filename: str) -> None:
    path.write_text(note, encoding="utf-8")
    git_push(filename)
    deploy()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Exception while handling update: {context.error}")


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Unauthorized。")
        return

    if not context.args:
        await update.message.reply_text("用法：/debug 食べています")
        return

    text   = " ".join(context.args)
    tokens = analyze(text)

    if not tokens:
        await update.message.reply_text("解析結果為空，請確認輸入是否為日文。")
        return

    lines = ["🔍 UniDic 原始資料：\n"]
    for t in tokens:
        lines.append(
            f"surface={t.surface}\n"
            f"  pos={t.pos} / {t.pos_detail}\n"
            f"  base={t.base_form}\n"
            f"  cType={t.conj_type}\n"
            f"  cForm={t.conj_form}\n"
        )

    await update.message.reply_text("\n".join(lines))


async def handle_japanese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Unauthorized。")
        return ConversationHandler.END

    text                       = update.message.text.strip()
    analysis_md, words, tokens = analyze_japanese(text)
    auto_meaning               = jmdict_lookup(words)
    auto_example, auto_source, attempts, warning = await get_example_smart(text, words)

    # Step 2：助動詞辨識
    # used_indices 從空集合開始，explain_aux() 會把用掉的位置填進去
    aux_explanations, used_indices = explain_aux(tokens)
    grammar_telegram = format_aux_for_telegram(aux_explanations)
    grammar_md       = format_aux_for_note(aux_explanations)

    # Step 3：文法模板辨識
    # 把 Step 2 的 used_indices 傳進來，避免重複匹配同一個詞素
    pattern_results, _ = match_patterns(tokens, used_indices)
    pattern_telegram   = format_patterns_for_telegram(pattern_results)
    pattern_md         = format_patterns_for_note(pattern_results)

    user_state[ALLOWED_USER_ID] = {
        "text":         text,
        "analysis_md":  analysis_md,
        "filename":     safe_filename(text),
        "auto_meaning": auto_meaning,
        "grammar_md":   grammar_md,
        "pattern_md":   pattern_md,
        "auto_example": auto_example,
        "auto_source":  auto_source,
        "attempts":     attempts,
        "warning":      warning,
    }

    # Telegram preview
    preview_lines = []
    for w in words:
        line = f"{w['surface']}（{w['reading']}）{w['pos']}"
        if w['conj_type']:
            line += f" | {w['conj_type']}"
        if w['conj_form']:
            line += f" | {w['conj_form']}"
        preview_lines.append(line)

    preview = "\n".join(preview_lines)

    msg = (
        f"✅ 分析完成：\n\n{preview}\n\n"
        f"📖 JMdict 自動意思：\n{auto_meaning}\n"
    )
    if grammar_telegram:
        msg += f"\n{grammar_telegram}\n"
    if pattern_telegram:
        msg += f"\n{pattern_telegram}\n"
    msg += (
        f"\n📝 意思は？\n"
        f"（自分で入力 / /auto でJMdict使用 / /skip でスキップ）"
    )

    await update.message.reply_text(msg)
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
        grammar_md  = state["grammar_md"],
        pattern_md  = state["pattern_md"],
        example     = example,
        source      = "手動入力",
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    save_note(path, note, state["filename"])

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

    if "meaning" not in state:
        state["meaning"] = state["auto_meaning"]
        await update.message.reply_text(
            f"✅ JMdict 意思を使用：\n{state['meaning']}\n\n"
            f"✏️ 例句は？\n"
            f"Massif 自動例句：\n{state['auto_example']}\n\n"
            f"（自分で入力 / /auto でMassif使用 / /skip でスキップ）"
        )
        return WAIT_EXAMPLE

    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        grammar_md  = state["grammar_md"],
        pattern_md  = state["pattern_md"],
        example     = state["auto_example"],
        source      = state["auto_source"],
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    save_note(path, note, state["filename"])

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

    if "meaning" not in state:
        state["meaning"] = "（待填入）"
        await update.message.reply_text(
            "⏭️ 意思をスキップ\n\n"
            f"✏️ 例句は？\n"
            f"Massif 自動例句：\n{state['auto_example']}\n\n"
            f"（自分で入力 / /auto でMassif使用 / /skip でスキップ）"
        )
        return WAIT_EXAMPLE

    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        grammar_md  = state["grammar_md"],
        pattern_md  = state["pattern_md"],
        example     = "（待填入）",
        source      = "（待填入）",
        attempts    = state["attempts"],
        warning     = state["warning"],
    )

    path = NOTES_DIR / state["filename"]
    save_note(path, note, state["filename"])

    await update.message.reply_text(
        f"⏭️ 例句をスキップ、保存：`{path.name}`",
        parse_mode="Markdown"
    )

    user_state.pop(ALLOWED_USER_ID, None)
    return ConversationHandler.END


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


def main():
    while True:
        try:
            logging.info("Bot starting...")
            app = (
                ApplicationBuilder()
                .token(TOKEN)
                .read_timeout(30)
                .write_timeout(30)
                .connect_timeout(30)
                .pool_timeout(30)
                .build()
            )
            app.add_handler(conv_handler)
            app.add_error_handler(error_handler)
            app.add_handler(CommandHandler("debug", cmd_debug))
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            logging.info("Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()