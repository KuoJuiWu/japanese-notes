# grammar_patterns.py
# Step 3 — 文法模板辨識模組
# 負責在詞素列表中比對高頻文法結構，並回傳對應的說明
#
# ⚠️ 所有 base_form 已根據 /debug 實際輸出修正：
#   いる  → 居る       ある  → 有る
#   する  → 為る       なる  → 成る
#   こと  → 事         いける → 行く
#   できる → 出来る    もらう → 貰う

from morphology import MorphToken
from dataclasses import dataclass

# ── 文法模板資料結構 ──────────────────────────────────────────────────────────

@dataclass
class GrammarPattern:
    """
    單一文法模板的完整定義。
    pattern 裡的空字串 "" 代表萬用字元（匹配任意一個詞素）
    """
    pattern: tuple[str, ...]
    name:    str
    meaning: str
    example: str


# ── 文法模板庫 ────────────────────────────────────────────────────────────────
# 排列原則：較長的 pattern 排在前面，避免被短的先匹配

GRAMMAR_PATTERNS: list[GrammarPattern] = [

    # ── 經驗／回憶 ────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("た", "事", "有る"),
        name    = "Vたことがある",
        meaning = "表示曾經有過某種經驗（曾經～過）",
        example = "富士山に登ったことがある。",
    ),
    GrammarPattern(
        pattern = ("た", "事", "ない"),
        name    = "Vたことがない",
        meaning = "表示從未有過某種經驗（從來沒有～過）",
        example = "刺身を食べたことがない。",
    ),

    # ── 義務／禁止 ────────────────────────────────────────────────────────────
    GrammarPattern(
        # なければ + ならない：なけれ(base=ない) + ば + なら(base=成る) + ない
        pattern = ("ない", "ば", "成る", "ない"),
        name    = "Vなければならない",
        meaning = "表示義務（必須～／不得不～）",
        example = "宿題をしなければならない。",
    ),
    GrammarPattern(
        # なければ + いけない：なけれ(base=ない) + ば + いけ(base=行く) + ない
        pattern = ("ない", "ば", "行く", "ない"),
        name    = "Vなければいけない",
        meaning = "表示義務（必須～，口語較常用）",
        example = "もう寝なければいけない。",
    ),
    GrammarPattern(
        # てはいけない：て + は + いけ(base=行く) + ない
        pattern = ("て", "は", "行く", "ない"),
        name    = "Vてはいけない",
        meaning = "表示禁止（不可以～）",
        example = "ここで写真を撮ってはいけない。",
    ),
    GrammarPattern(
        # てはならない：て + は + なら(base=成る) + ない
        pattern = ("て", "は", "成る", "ない"),
        name    = "Vてはならない",
        meaning = "表示禁止（不可以～，較正式／書面語）",
        example = "法律を破ってはならない。",
    ),

    # ── 許可 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("て", "も", "良い"),
        name    = "Vてもいい",
        meaning = "表示許可（可以～／～也沒關係）",
        example = "ここに座ってもいいですか。",
    ),
    GrammarPattern(
        pattern = ("て", "も", "構う"),
        name    = "Vても構わない",
        meaning = "表示許可（～也無妨／不介意～）",
        example = "遅くなっても構わない。",
    ),

    # ── 可能 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        # ことができる：事 + が + 出来る
        pattern = ("事", "が", "出来る"),
        name    = "VことができるV",
        meaning = "表示能力或可能性（能夠～／可以～）",
        example = "日本語を話すことができる。",
    ),

    # ── 決定 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("事", "に", "為る"),
        name    = "VことにするV",
        meaning = "表示個人決定（決定～）",
        example = "毎日走ることにした。",
    ),
    GrammarPattern(
        pattern = ("事", "に", "成る"),
        name    = "VことになるV",
        meaning = "表示自然結果或外部決定（結果變成～／決定要～）",
        example = "来月転勤することになった。",
    ),

    # ── 同時進行 ──────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("ながら", ""),
        name    = "Vながら",
        meaning = "表示兩個動作同時進行（一邊～一邊～）",
        example = "音楽を聴きながら勉強する。",
    ),

    # ── 目的 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("ため", "に"),
        name    = "Vために",
        meaning = "表示目的（為了～）",
        example = "合格するために毎日勉強する。",
    ),

    # ── 時間關係 ──────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("て", "から"),
        name    = "Vてから",
        meaning = "表示先後順序（做完～之後，再～）",
        example = "宿題をしてから遊ぶ。",
    ),
    GrammarPattern(
        pattern = ("前", "に"),
        name    = "Vまえに",
        meaning = "表示之前（在～之前）",
        example = "寝る前に歯を磨く。",
    ),
    GrammarPattern(
        pattern = ("後", "で"),
        name    = "Vあとで",
        meaning = "表示之後（在～之後）",
        example = "食べた後で薬を飲む。",
    ),
    GrammarPattern(
        pattern = ("間", "に"),
        name    = "Vあいだに",
        meaning = "表示在某段期間內發生（在～的時候／趁～）",
        example = "子供が寝ている間に家事をする。",
    ),

    # ── 變化 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("に", "成る"),
        name    = "〜になる",
        meaning = "表示變化結果（變成～／成為～）",
        example = "医者になりたい。",
    ),
    GrammarPattern(
        pattern = ("に", "為る"),
        name    = "〜にする",
        meaning = "表示決定或使之變成（決定～／把～變成～）",
        example = "コーヒーにする。",
    ),

    # ── 原因／理由 ────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("所為", "で"),
        name    = "Nせいで",
        meaning = "表示負面原因（都是因為～的緣故）",
        example = "雨のせいで試合が中止になった。",
    ),
    GrammarPattern(
        pattern = ("御蔭", "で"),
        name    = "Nおかげで",
        meaning = "表示正面原因（托～的福／多虧了～）",
        example = "君のおかげで助かった。",
    ),

    # ── 說明／定義 ────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("と", "言う", "事"),
        name    = "ということ",
        meaning = "表示事實的說明或歸納（也就是說～／意思是～）",
        example = "合格したということは努力が実った。",
    ),
    GrammarPattern(
        pattern = ("と", "言う"),
        name    = "～という",
        meaning = "表示引用或傳聞（說～／據說～）",
        example = "明日雨が降るという。",
    ),

    # ── 比較／程度 ────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("より", ""),
        name    = "AよりB",
        meaning = "表示比較（B比A更～）",
        example = "電車よりバスの方が安い。",
    ),
    GrammarPattern(
        pattern = ("程", ""),
        name    = "Aほど",
        meaning = "表示程度（～到～的程度／越～越～）",
        example = "死ぬほど疲れた。",
    ),
    GrammarPattern(
        pattern = ("過ぎる", ""),
        name    = "Vすぎる",
        meaning = "表示過度（太～了／過於～）",
        example = "食べすぎた。",
    ),

    # ── 程度限定 ──────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("だけ", "で", "なく"),
        name    = "AだけでなくB",
        meaning = "表示附加（不只是A，連B也～）",
        example = "英語だけでなく日本語も話せる。",
    ),
    GrammarPattern(
        pattern = ("許り", "で", "なく"),
        name    = "AばかりでなくB",
        meaning = "表示附加（不只是A，B也～）",
        example = "勉強ばかりでなく運動も大切だ。",
    ),
    GrammarPattern(
        pattern = ("しか", "ない"),
        name    = "NしかVない",
        meaning = "表示限定（只有～／除了～別無其他）",
        example = "これしか方法がない。",
    ),
    GrammarPattern(
        pattern = ("さえ", ""),
        name    = "Nさえ",
        meaning = "表示極端例子（連～都～／只要～就～）",
        example = "子供さえ知っている。",
    ),
    GrammarPattern(
        pattern = ("だけ", ""),
        name    = "Nだけ",
        meaning = "表示限定（只～／僅～）",
        example = "一人だけ残った。",
    ),

    # ── 形式名詞 ──────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("物", "だ"),
        name    = "Vものだ",
        meaning = "表示一般常識或感慨（本來就是～／真是～啊）",
        example = "人間は必ず死ぬものだ。",
    ),
    GrammarPattern(
        pattern = ("訳", "だ"),
        name    = "Vわけだ",
        meaning = "表示理所當然的結論（難怪～／也就是說～）",
        example = "毎日練習したんだから上手になるわけだ。",
    ),
    GrammarPattern(
        pattern = ("訳", "が", "ない"),
        name    = "Vわけがない",
        meaning = "表示不可能（不可能～／沒道理～）",
        example = "彼が嘘をつくわけがない。",
    ),
    GrammarPattern(
        pattern = ("筈", "だ"),
        name    = "Vはずだ",
        meaning = "表示根據推測的確信（應該是～／按理說～）",
        example = "もう着いているはずだ。",
    ),
    GrammarPattern(
        pattern = ("筈", "が", "ない"),
        name    = "Vはずがない",
        meaning = "表示根據推測的否定（不可能～／按理說不會～）",
        example = "彼が来るはずがない。",
    ),

    # ── 被動／使役進階 ────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("させ", "られる"),
        name    = "V使役被動",
        meaning = "表示被迫做某事（被強迫～／不得不～）",
        example = "残業させられた。",
    ),

    # ── 強調 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("こそ", ""),
        name    = "Nこそ",
        meaning = "表示強調（正是～／才是～）",
        example = "今こそ行動するべきだ。",
    ),

    # ── 逆接 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("のに", ""),
        name    = "Vのに",
        meaning = "表示逆接（明明～卻～／雖然～但～）",
        example = "頑張ったのに失敗した。",
    ),

    # ── 讓步 ──────────────────────────────────────────────────────────────────
    GrammarPattern(
        pattern = ("と", "為る", "も"),
        name    = "Vとしても",
        meaning = "表示讓步假設（即使假設～也～）",
        example = "行けるとしても遅くなる。",
    ),
]


# ── 主要比對函式 ──────────────────────────────────────────────────────────────

def match_patterns(
    tokens: list[MorphToken],
    used_indices: set[int] | None = None,
) -> tuple[list[str], set[int]]:
    """
    在詞素列表中比對文法模板，回傳說明字串列表。

    ⚠️ 介面更新（解決 Step 2/3 重複匹配問題）：
    - 接受外部傳入的 used_indices（Step 2 已用掉的位置）
    - 回傳 (results, used_indices)

    參數：
        tokens       — morphology.analyze() 回傳的 MorphToken 列表
        used_indices — Step 2 已使用的詞素位置集合（預設為空集合）

    回傳：
        (results, used_indices)
        results      — 模板說明字串列表
        used_indices — 更新後的已用位置集合
    """
    if used_indices is None:
        used_indices = set()

    results    = []
    base_forms = [t.base_form for t in tokens]

    for gp in GRAMMAR_PATTERNS:
        # 萬用字元 "" 不參與比對，只用來標記「這個位置可以是任意詞素」
        search_keys = [k for k in gp.pattern if k != ""]
        if not search_keys:
            continue

        for i in range(len(base_forms) - len(search_keys) + 1):
            window = base_forms[i:i + len(search_keys)]
            match  = all(pk == bk for pk, bk in zip(search_keys, window))

            if not match:
                continue

            indices = set(range(i, i + len(search_keys)))
            if indices & used_indices:
                continue

            used_indices |= indices
            surface = "〜" + "".join(tokens[j].surface for j in range(i, i + len(search_keys)))
            results.append(
                f"{gp.name}（{surface}）\n"
                f"  → {gp.meaning}\n"
                f"  例：{gp.example}"
            )
            break

    return results, used_indices


def format_patterns_for_telegram(results: list[str]) -> str:
    """格式化成 Telegram 訊息字串。沒有內容時回傳空字串。"""
    if not results:
        return ""
    lines = "\n\n".join(results)
    return f"📋 文法模板：\n{lines}"


def format_patterns_for_note(results: list[str]) -> str:
    """格式化成筆記 Markdown 區塊。沒有內容時回傳空字串。"""
    if not results:
        return ""
    lines = "\n\n".join(results)
    return f"## 文法模板 (Grammar Pattern)\n{lines}\n"