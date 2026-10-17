# -*- coding: utf-8 -*-
"""**语法错定位器**：专治"中文字符串里混进 ASCII 双引号 ⇒ 字符串提前闭合"。

**为什么需要它**（本会话的真实教训，出现两次）：在中文长字符串里手写 `"某某"` 时若用的是
**ASCII** 双引号而不是全角引号，字符串会提前闭合；Python 报出的是
`invalid syntax. Perhaps you forgot a comma?`，而且**指向整条语句的开头**
（实测：`_apply_d54.py` 的真凶在第 57 行，报错说第 33 行）。

**为什么不做"按行统计引号个数"**：那段内容有 4 个 ASCII 引号（偶数），奇偶性判据抓不住；
而 `tokenize` 也**不会报错**（`"a"b"c"` 是合法的 token 序列 STRING NAME STRING），
所以它只在 **parser** 层失败。实测过的教训。

**真正的判据**：看 token 流里有没有
**「STRING → 换行 → NAME/NUMBER」** 这种组合 —— 那正是"字符串提前闭合、后面的中文变成了裸标识符"。
本工具只在 `ast.parse` **失败**时才去定位真凶行，因此**零误报**。

用法：
    python 1_Code/DDM_Core/_scratch/check_code_quotes.py <文件…>          # 有失败才输出
    python 1_Code/DDM_Core/_scratch/check_code_quotes.py --all <目录…>     # 连能解析的文件也报统计
"""
import ast
import io
import sys
import tokenize
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INTERESTING = {tokenize.NAME, tokenize.NUMBER}


def locate(text: str) -> list[str]:
    """在**已知解析失败**的源码里定位"字符串提前闭合"的行。

    判据：token 流里出现 **`STRING` 紧跟 `NAME`/`NUMBER`**（可以同行、也可以隔一个换行）。
    合法的 Python 里字符串后面**永远**不会直接跟一个裸标识符或数字 ——
    `"a"b`、`"a"` 换行 `b` 都是"引号提前闭合、后面的中文变成了裸标识符"。
    """
    out: list[str] = []
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    for i in range(1, len(toks)):
        cur, prev = toks[i], toks[i - 1]
        if cur.type not in INTERESTING:
            continue
        if prev.type == tokenize.STRING:
            out.append(f"L{cur.start[0]} C{cur.start[1]}：字符串之后直接跟了一个裸 "
                       f"{tokenize.tok_name[cur.type]} {cur.string[:24]!r}"
                       f"（上一个字符串结束在 L{prev.end[0]} C{prev.end[1]}）"
                       f" ⇒ 那个字符串**提前闭合**了")
        elif prev.type == tokenize.NL and i >= 2 and toks[i - 2].type == tokenize.STRING:
            out.append(f"L{cur.start[0]} C{cur.start[1]}：上一行是字符串、本行却出现裸 "
                       f"{tokenize.tok_name[cur.type]} {cur.string[:24]!r}"
                       f" ⇒ 上一行的字符串很可能**提前闭合**了")
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--all"]
    show_all = "--all" in sys.argv
    targets: list[Path] = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            targets.extend(sorted(p.rglob("*.py")))
        else:
            targets.append(p)
    if not targets:
        print("用法：python check_code_quotes.py <文件或目录…>（**必须显式传参**）")
        return 2

    n_syntax, n_located, n_ok = 0, 0, 0
    for p in targets:
        text = p.read_text(encoding="utf-8")
        try:
            ast.parse(text)
        except SyntaxError as e:
            n_syntax += 1
            print(f"❌ {p}：`ast.parse` 失败 —— 第 {e.lineno} 行：{e.msg}")
            hits = locate(text)
            if hits:
                n_located += 1
                for h in hits:
                    print(f"    🎯 {h}")
                print(f"    ⇒ 修法：把该行里的 ASCII 双引号改成全角引号「」或 \" \"")
            else:
                print("    （未定位到'字符串提前闭合'，需人工看）")
        else:
            n_ok += 1
            if show_all:
                print(f"✅ {p}")
    print(f"\n检查 {len(targets)} 个文件：可解析 {n_ok}、有语法错 {n_syntax}"
          f"（其中 {n_located} 个已定位到真凶行）")
    return 1 if n_syntax else 0


if __name__ == "__main__":
    raise SystemExit(main())
