from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, MessageHandler,
    filters, ContextTypes, ConversationHandler,
    CommandHandler, CallbackQueryHandler
)
from morphology import analyze, tokens_to_table_md, lookup_meaning, classify_tokens, MorphToken
from aux_verbs import explain_aux, format_aux_for_telegram, format_aux_for_note
from grammar_patterns import match_patterns, format_patterns_for_telegram, format_patterns_for_note

from jamdict import Jamdict
import httpx
import json
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

BASE_DIR  = Path(__file__).parent
jam       = Jamdict(db_file=str(BASE_DIR / "jamdictdb" / "jamdict.db"))

NOTES_DIR = BASE_DIR / "docs" / "notes"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# ── 對話狀態 ──────────────────────────────────────────────────────────────────
WAIT_MEANING, WAIT_EXAMPLE, WAIT_CATEGORY, WAIT_NEW_CATEGORY = range(4)

user_state: dict = {}

GIT    = r"C:\Program Files\Git\cmd\git.exe"
MKDOCS = shutil.which("mkdocs")

# ── 預設分類 ──────────────────────────────────────────────────────────────────
DEFAULT_CATEGORIES: list[dict] = [
    {"emoji": "🎵", "name": "Song",      "folder": "song"},
    {"emoji": "🎌", "name": "Anime",     "folder": "anime"},
    {"emoji": "📚", "name": "Textbook",  "folder": "textbook"},
    {"emoji": "💬", "name": "Daily",     "folder": "daily"},
    {"emoji": "📦", "name": "Other",     "folder": "other"},
]

# ── 自建分類持久化 ────────────────────────────────────────────────────────────
# categories.json 存在 repo 根目錄
# 格式：[{"emoji": "📁", "name": "music", "folder": "music"}, ...]
CATEGORIES_FILE = BASE_DIR / "categories.json"


def load_custom_categories() -> list[dict]:
    """
    從 categories.json 讀取自建分類。
    Bot 啟動時呼叫一次，之後存在記憶體裡。
    若檔案不存在，回傳空列表。
    """
    if not CATEGORIES_FILE.exists():
        return []
    try:
        with open(CATEGORIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Failed to load categories.json: {e}")
        return []


def save_custom_categories(categories: list[dict]) -> None:
    """
    把自建分類寫進 categories.json（硬碟）。
    每次新增分類時呼叫，確保重啟後還在。
    """
    try:
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.error(f"Failed to save categories.json: {e}")


# Bot 啟動時從硬碟讀取自建分類
custom_categories: list[dict] = load_custom_categories()


def get_all_categories() -> list[dict]:
    """回傳預設分類＋自建分類的完整列表"""
    return DEFAULT_CATEGORIES + custom_categories


def build_category_keyboard() -> InlineKeyboardMarkup:
    """
    建立分類選擇的 Inline Keyboard。
    每排兩個按鈕，最後一排加上「✏️ 新建分類」。
    callback_data 格式：cat:<folder>
    """
    all_cats = get_all_categories()
    buttons  = []

    row = []
    for cat in all_cats:
        row.append(InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat:{cat['folder']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("✏️ 新建分類", callback_data="cat:__new__")
    ])

    return InlineKeyboardMarkup(buttons)


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
    category:    str,
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
  - {category}
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
{debug_section}
---
> ⚠️ **注意**：本筆記的意思說明來自 JMdict 離線字典，文法分析（助動詞、文法模板）由規則程式自動產生，例句來自 Massif 語料庫。內容僅供學習參考，建議重要詞彙以 Kotobank 或 Weblio 等權威來源進行確認。"""


def git_push(filepath: str) -> None:
    try:
        repo = str(BASE_DIR)
        subprocess.run([GIT, "add", filepath], check=True, cwd=repo)
        subprocess.run([GIT, "commit", "-m", f"add: {Path(filepath).name}"], check=True, cwd=repo)
        subprocess.run([GIT, "push", "origin", "master"], check=True, cwd=repo)
    except subprocess.CalledProcessError as e:
        logging.error(f"Git error: {e}")


def deploy() -> None:
    try:
        subprocess.run([MKDOCS, "gh-deploy", "--quiet"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Deploy error: {e}")


def save_note(path: Path, note: str, filepath: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note, encoding="utf-8")
    git_push(filepath)
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

    aux_explanations, used_indices = explain_aux(tokens)
    grammar_telegram = format_aux_for_telegram(aux_explanations)
    grammar_md       = format_aux_for_note(aux_explanations)

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
        "category":     None,
    }

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
    state["example"] = example
    state["source"]  = "手動入力"

    await update.message.reply_text(
        "📁 分類は？",
        reply_markup=build_category_keyboard()
    )
    return WAIT_CATEGORY


async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ALLOWED_USER_ID:
        return ConversationHandler.END

    data = query.data

    if data == "cat:__new__":
        await query.edit_message_text("✏️ 新しい分類名を入力してください（英数字推奨）：")
        return WAIT_NEW_CATEGORY

    folder = data.replace("cat:", "")
    await _save_with_category(query, folder)
    return ConversationHandler.END


async def handle_new_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    使用者輸入新分類名稱後：
    1. 加進 custom_categories（記憶體）
    2. 寫進 categories.json（硬碟）← 這樣重啟後還在
    3. 儲存筆記
    """
    raw    = update.message.text.strip()
    folder = re.sub(r'[^\w]', '_', raw).lower()

    if not folder:
        await update.message.reply_text("❌ 分類名稱無效，請重新輸入。")
        return WAIT_NEW_CATEGORY

    # 若不重複才加入
    existing_folders = [c["folder"] for c in get_all_categories()]
    if folder not in existing_folders:
        new_cat = {"emoji": "📁", "name": raw, "folder": folder}
        custom_categories.append(new_cat)

        # 寫進硬碟，重啟後還在
        save_custom_categories(custom_categories)
        logging.info(f"New category saved to disk: {folder}")

    await _save_with_category(update, folder)
    return ConversationHandler.END


async def _save_with_category(update_or_query, folder: str) -> None:
    state    = user_state[ALLOWED_USER_ID]
    filename = state["filename"]

    note_dir  = NOTES_DIR / folder
    note_path = note_dir / filename
    filepath  = f"docs/notes/{folder}/{filename}"

    note = build_note(
        text        = state["text"],
        analysis_md = state["analysis_md"],
        meaning     = state["meaning"],
        grammar_md  = state["grammar_md"],
        pattern_md  = state["pattern_md"],
        example     = state.get("example", "（待填入）"),
        source      = state.get("source", "（待填入）"),
        attempts    = state["attempts"],
        warning     = state["warning"],
        category    = folder,
    )

    save_note(note_path, note, filepath)

    reply_text = f"🎉 Saved：`{filename}`\n📁 Category：{folder}"
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(reply_text, parse_mode="Markdown")
    else:
        await update_or_query.reply_text(reply_text, parse_mode="Markdown")

    user_state.pop(ALLOWED_USER_ID, None)


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

    state["example"] = state["auto_example"]
    state["source"]  = state["auto_source"]

    await update.message.reply_text(
        f"✅ Massif 例句を使用。\n\n📁 分類は？",
        reply_markup=build_category_keyboard()
    )
    return WAIT_CATEGORY


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

    state["example"] = "（待填入）"
    state["source"]  = "（待填入）"

    await update.message.reply_text(
        "⏭️ 例句をスキップ。\n\n📁 分類は？",
        reply_markup=build_category_keyboard()
    )
    return WAIT_CATEGORY


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
        WAIT_CATEGORY: [
            CallbackQueryHandler(handle_category_callback, pattern="^cat:"),
        ],
        WAIT_NEW_CATEGORY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_category),
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