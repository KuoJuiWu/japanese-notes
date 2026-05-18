# morphology.py
# 形態素解析模組 — 負責將日文句子拆成詞素，並提取詞性、原形、活用型等資訊
# 供 japan_bot.py 的 analyze_japanese() 和 jmdict_lookup() 呼叫使用

from fugashi import Tagger
import jaconv
from dataclasses import dataclass

# ── 初始化 ────────────────────────────────────────────────────────────────────

# 初始化 MeCab tagger（使用 UniDic 字典）
# UniDic 比 IPAdic 更現代，對動詞活用型的辨識更精確
# 這裡只初始化一次，避免每次呼叫 analyze() 都重新載入
tagger = Tagger()

# ── 解析時跳過的品詞 ──────────────────────────────────────────────────────────
# 補助記号 = 句號、逗號、括號等標點符號
# 空白     = 空格
# 這些詞素對意思查詢和文法分析沒有幫助，直接跳過
SKIP_POS: set[str] = {"補助記号", "空白"}

# ── 詞素資料結構 ──────────────────────────────────────────────────────────────

@dataclass
class MorphToken:
    """
    單一詞素的完整資訊。
    每個欄位對應 UniDic 的一個特徴欄位。

    原有欄位（japan_bot.py 原本就在用的）：
        surface, reading, pos, base_form

    新增欄位（供 Step 2 助動詞辨識、Step 3 文法模板使用）：
        pos_detail, conj_type, conj_form
    """
    surface:    str  # 表層形：文字中實際出現的字串，例如「食べ」「ない」「ます」
    reading:    str  # 讀音（平假名），例如「たべ」「ない」「ます」
    pos:        str  # 品詞（第一層）：名詞／動詞／助動詞／助詞／形容詞 等
    pos_detail: str  # 品詞細分類：「非自立可能」「固有名詞」等，Step 2 辨識補助動詞時需要
    base_form:  str  # 原形／辭書形：例如「食べる」「ない」「する」
    conj_type:  str  # 活用型：例如「五段-カ行」「下一段-バ行」「助動詞-ナイ」
    conj_form:  str  # 活用形：例如「連用形-一般」「終止形-一般」「仮定形-一般」


# ── 品詞對應表（UniDic 中文品詞名稱 → JMdict 英文標籤前綴）─────────────────
# 用途：lookup_meaning() 依照詞性篩選 JMdict 的 sense，避免查錯意思
# JMdict sense.pos 的值像 "v5u"、"v1"、"n"、"adj-i" 這樣，用前綴比對即可
POS_MAP: dict[str, list[str]] = {
    "動詞":    ["v"],       # 包含 v5u（五段）、v1（一段）、vs-i（する）、vk（くる）等
    "形容詞":  ["adj-i"],   # い形容詞，例如「高い」「美しい」
    "形容動詞": ["adj-na"], # な形容詞，例如「静かな」「便利な」
    "名詞":    ["n"],       # 一般名詞、固有名詞、數詞、形式名詞 等
    "副詞":    ["adv"],     # 副詞，例如「もっと」「やはり」
    "助詞":    ["prt"],     # 助詞，例如「を」「は」「が」「に」
    "助動詞":  ["aux"],     # 助動詞，例如「ない」「た」「ます」「れる」
}

# ── 查詞典時跳過的品詞 ────────────────────────────────────────────────────────
# 助詞、接頭辭等沒有獨立詞彙意思，不需要查 JMdict
# 助動詞由 Step 2 的 aux_verbs.py 處理，也不走 JMdict
SKIP_LOOKUP_POS: set[str] = {"助詞", "補助記号", "空白", "接頭辞", "助動詞"}

# ── 主要解析函式 ──────────────────────────────────────────────────────────────

def analyze(text: str) -> list[MorphToken]:
    """
    將日文字串拆解為詞素列表。

    參數：
        text — 要解析的日文字串，例如「毎日日本語を勉強しています」

    回傳：
        MorphToken 的列表，每個元素代表一個詞素
        補助記号（句號、逗號等）和空白會被跳過

    使用範例：
        tokens = analyze("食べています")
        for t in tokens:
            print(t.surface, t.pos, t.base_form, t.conj_type, t.conj_form)
    """
    tokens = []

    for word in tagger(text):
        # 跳過標點和空白
        if word.feature.pos1 in SKIP_POS:
            continue

        # 讀音：UniDic 提供片假名，轉換成平假名比較直觀
        # 若讀音欄位為空（部分外來語或符號），直接用表層形代替
        kana    = word.feature.kana
        reading = jaconv.kata2hira(kana) if kana else word.surface

        # 原形：優先用 lemma（辭書形），若為「*」（未知）則退回用表層形
        # 例如「食べ」的 lemma 是「食べる」，「東京」的 lemma 是「東京」
        lemma     = word.feature.lemma
        base_form = lemma if lemma and lemma != "*" else word.surface

        tokens.append(MorphToken(
            surface    = word.surface,
            reading    = reading,
            pos        = word.feature.pos1 or "",   # 品詞（第一層）
            pos_detail = word.feature.pos2 or "",   # 品詞細分類，Step 2 需要
            base_form  = base_form,
            conj_type  = word.feature.cType or "",  # 活用型，Step 2/3 需要
            conj_form  = word.feature.cForm or "",  # 活用形，Step 2/3 需要
        ))

    return tokens


# ── 詞性分類函式 ──────────────────────────────────────────────────────────────

def classify_tokens(tokens: list[MorphToken]) -> dict[str, list[MorphToken]]:
    """
    將詞素列表依詞性分類，方便後續分開處理不同詞類的意思查詢。

    回傳格式：
    {
        "名詞":   [MorphToken, ...],
        "動詞":   [MorphToken, ...],
        "助動詞": [MorphToken, ...],
        "形容詞": [MorphToken, ...],
        "副詞":   [MorphToken, ...],
        "其他":   [MorphToken, ...],
    }
    """
    classified: dict[str, list[MorphToken]] = {
        "名詞":   [],
        "動詞":   [],
        "助動詞": [],
        "形容詞": [],
        "副詞":   [],
        "其他":   [],
    }

    for token in tokens:
        if token.pos in classified:
            classified[token.pos].append(token)
        else:
            classified["其他"].append(token)

    return classified


# ── Markdown 表格產生函式 ─────────────────────────────────────────────────────

def tokens_to_table_md(tokens: list[MorphToken]) -> str:
    """
    將詞素列表轉成 Markdown 表格字串。
    格式與現有筆記完全一致：表面形 | 讀音 | 詞性 | 原形
    """
    rows = [
        f"| {t.surface} | {t.reading} | {t.pos} | {t.base_form} |"
        for t in tokens
    ]
    table = "\n".join(rows)
    return (
        "## 分詞解析\n"
        "| 表面形 | 讀音 | 詞性 | 原形 |\n"
        "|---|---|---|---|\n"
        f"{table}\n"
    )


# ── JMdict 意思查詢函式 ───────────────────────────────────────────────────────

def lookup_meaning(tokens: list[MorphToken], jam) -> str:
    """
    根據詞素列表查詢 JMdict 意思，並依詞性篩選最相關的 sense。
    助動詞由 aux_verbs.py 的 explain_aux() 處理，這裡跳過。

    參數：
        tokens — analyze() 回傳的詞素列表
        jam    — Jamdict 實例（從 japan_bot.py 傳入，避免重複初始化資料庫）
    """
    classified = classify_tokens(tokens)

    # 只查有詞彙意思的詞類，助動詞交給 aux_verbs.py
    lookup_targets = (
        classified["名詞"]
        + classified["動詞"]
        + classified["形容詞"]
        + classified["副詞"]
    )

    seen    = set()
    results = []

    for token in lookup_targets:
        base = token.base_form
        if base in seen:
            continue
        seen.add(base)

        result = jam.lookup(base)
        if not result.entries:
            continue

        entry        = result.entries[0]
        pos_prefixes = POS_MAP.get(token.pos, [])

        if pos_prefixes:
            matched_senses = [
                s for s in entry.senses
                if any(
                    str(p).startswith(prefix)
                    for p in s.pos
                    for prefix in pos_prefixes
                )
            ]
        else:
            matched_senses = []

        senses_to_use = matched_senses if matched_senses else entry.senses[:1]
        glosses = [str(g) for s in senses_to_use for g in s.gloss]
        if glosses:
            results.append(f"{base}: {', '.join(glosses)}")

    return "\n".join(results) if results else "（自動查詢無結果）"