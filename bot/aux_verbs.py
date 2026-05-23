# aux_verbs.py
# Step 2 — 助動詞辨識模組
# 負責辨識單一助動詞和複合語尾，並回傳對應的文法說明
# 供 japan_bot.py 的 handle_japanese() 和 build_note() 使用

from morphology import MorphToken

# ── 單一助動詞硬規則表 ────────────────────────────────────────────────────────
# key   = 助動詞的原形（base_form），依照 UniDic 實際輸出
# value = 文法說明（中文）
AUX_SINGLE: dict[str, str] = {
    # 否定
    "ない":     "否定（不～／沒有～）",
    "ぬ":       "否定（文語・古語）",

    # 過去／完了
    "た":       "過去／完了（～了）",

    # 禮貌體
    "ます":     "禮貌體（正式場合使用）",

    # 推量／意志
    "う":       "意志／推量（～吧／打算～）",
    "よう":     "意志／推量（～吧／打算～）",
    "だろう":   "推量（大概是～）",
    "でしょう": "推量・禮貌體（大概是～）",

    # 可能／被動／使役／尊敬
    "れる":     "被動／可能／自發／尊敬",
    "られる":   "被動／可能／自發／尊敬",
    "せる":     "使役（讓～做）",
    "させる":   "使役（讓～做）",

    # 希望
    "たい":     "希望（自己想要～）",
    "たがる":   "希望（第三者想要～）",

    # 樣態／傳聞
    "そうだ":   "樣態（看起來～）／傳聞（據說～）",
    "らしい":   "推量／傳聞（好像～／聽說～）",
    "ようだ":   "比況／推量（好像～）",
    "みたいだ": "比況／推量（好像～，口語）",

    # 義務／當然
    "べきだ":   "義務／當然（應該～）",

    # 否定推量
    "まい":     "否定意志／否定推量（不打算～／應該不～）",
}

# ── 複合語尾規則表 ────────────────────────────────────────────────────────────
# ⚠️ 所有 base_form 已根據 /debug 實際輸出修正：
#   いる  → 居る
#   ある  → 有る
#   する  → 為る
#   なる  → 成る
#   いける → 行く（いけない 的 base）
#   こと  → 事
#
# 比對順序：較長的 pattern 排在前面，避免被短的先匹配

COMPOUND_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # ── 三詞以上（優先比對）──────────────────────────────────────────────────
    (("て", "居る", "ない"),   "進行否定（還沒在做／不在做）"),
    (("て", "居る", "た"),     "過去進行（之前一直在～）"),
    (("て", "仕舞う", "た"),   "完了／遺憾（已經～了，帶有後悔語氣）"),
    (("て", "も", "良い"),     "許可（可以～）"),
    (("て", "は", "行く"),     "禁止（不可以～）"),       # いけない の base = 行く
    (("て", "は", "成る"),     "禁止（不可以～，較正式）"), # ならない の base = 成る

    # ── 兩詞複合語尾 ──────────────────────────────────────────────────────
    (("て", "居る"),   "進行／狀態（正在～／～著）"),
    (("て", "有る"),   "結果狀態（已經～了，強調結果）"),
    (("て", "置く"),   "事先準備（事先～）"),
    (("て", "見る"),   "嘗試（試著～看看）"),
    (("て", "仕舞う"), "完了／遺憾（～完了／不小心～）"),
    (("て", "来る"),   "動作由遠至近／漸進變化（～過來／漸漸～）"),
    (("て", "行く"),   "動作由近至遠／持續變化（～下去／漸漸～）"),
    (("て", "欲しい"), "希望他人（希望你～）"),
    (("て", "下さる"), "請求（請～）"),
    (("て", "も"),     "逆接條件（即使～也）"),
    (("ない", "で"),   "否定連接（不～而）"),
]


# ── 主要辨識函式 ──────────────────────────────────────────────────────────────

def explain_aux(
    tokens: list[MorphToken],
    used_indices: set[int] | None = None,
) -> tuple[list[str], set[int]]:
    """
    從詞素列表中辨識助動詞和複合語尾，回傳文法說明列表。

    ⚠️ 介面更新（解決 Step 2/3 重複匹配問題）：
    - 接受外部傳入的 used_indices（已被其他模組用掉的位置）
    - 回傳 (explanations, used_indices)，讓 match_patterns() 知道哪些已用

    參數：
        tokens       — morphology.analyze() 回傳的 MorphToken 列表
        used_indices — 已被使用的詞素位置集合（預設為空集合）

    回傳：
        (explanations, used_indices)
        explanations  — 文法說明字串列表
        used_indices  — 更新後的已用位置集合（傳給 match_patterns 用）
    """
    if used_indices is None:
        used_indices = set()

    explanations = []
    base_forms   = [t.base_form for t in tokens]

    # ── Step 1：掃描複合語尾 ──────────────────────────────────────────────
    for pattern, explanation in COMPOUND_PATTERNS:
        search_keys = list(pattern)
        if not search_keys:
            continue

        for i in range(len(base_forms) - len(search_keys) + 1):
            if base_forms[i:i + len(search_keys)] == search_keys:
                indices = set(range(i, i + len(search_keys)))
                if indices & used_indices:
                    continue
                used_indices |= indices
                surface = "〜" + "".join(tokens[j].surface for j in range(i, i + len(search_keys)))
                explanations.append(f"{surface} → {explanation}")
                break

    # ── Step 2：單一助動詞 ────────────────────────────────────────────────
    for i, token in enumerate(tokens):
        if i in used_indices:
            continue
        if token.pos != "助動詞":
            continue

        explanation = AUX_SINGLE.get(token.base_form)
        if explanation:
            explanations.append(f"{token.surface} → {explanation}")
        else:
            # Fallback：助動詞存在但不在 AUX_SINGLE 裡
            explanations.append(f"{token.surface} → ⚠️ 未收錄（{token.base_form}）")

        used_indices.add(i)

    return explanations, used_indices


def format_aux_for_telegram(explanations: list[str]) -> str:
    """格式化成 Telegram 訊息字串。沒有內容時回傳空字串。"""
    if not explanations:
        return ""
    lines = "\n".join(explanations)
    return f"📐 文法：\n{lines}"


def format_aux_for_note(explanations: list[str]) -> str:
    """格式化成筆記 Markdown 區塊。沒有內容時回傳空字串。"""
    if not explanations:
        return ""
    lines = "\n".join(explanations)
    return f"## 文法 (Grammar)\n{lines}\n"