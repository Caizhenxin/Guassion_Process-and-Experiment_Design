# -*- coding: utf-8 -*-
"""把 `项目全景预览_v1.md` 转成自包含的 HTML（无外部依赖、无 CDN）。

不追求通用 Markdown 兼容，只覆盖本文档用到的子集：标题 / 段落 / 表格 / 代码块 /
列表 / 引用 / 分隔线 / 行内 code 与 **粗体**；三个显示公式换成手写 HTML（带上标
下标与分数），其余公式块原样保留 LaTeX 源码。
"""
import html
import re
from pathlib import Path

ROOT = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
SRC = ROOT / "5_Reference/06_进展与汇报/项目全景预览_v1.md"
DST = ROOT / "5_Reference/06_进展与汇报/项目全景预览_v1.html"

# ---------------------------------------------------------------- 公式（手写 HTML）
EQ_PIECEWISE = """<div class="eq"><span class="eq-name">式 1 · 两阶段漂移</span>
<div class="fml">d(t) =
<span class="cases">{</span><span class="casebody">
<span class="caserow">d<sub>stim</sub>,&nbsp;&nbsp;0 ≤ t ≤ T</span>
<span class="caserow">ρ · d<sub>stim</sub>,&nbsp;&nbsp;t &gt; T</span>
</span></div>
<div class="eqnote">ρ ∈ [0, 3]：掩蔽后证据保留率。ρ = 1 时退化为单阶段模型 M-T3。</div></div>"""

EQ_DRIFT = """<div class="eq"><span class="eq-name">式 2 · 设计变量 → 漂移</span>
<div class="fml">d<sub>stim</sub> = d<sub>ref</sub>
+ β<sub>P</sub> [ f<sub>P</sub>(P; τ<sub>P</sub>) − f<sub>P</sub>(P<sub>ref</sub>; τ<sub>P</sub>) ]
+ β<sub>T</sub> [ Q<sub>T</sub>(T; τ<sub>T</sub>) − Q<sub>T</sub>(T<sub>ref</sub>; τ<sub>T</sub>) ]
+ 𝟙<sub>self</sub> ( β<sub>S</sub> + β<sub>SP</sub> Δf<sub>P</sub> + β<sub>ST</sub> ΔQ<sub>T</sub> )</div>
<div class="eqnote">三项分别是：练习 / 呈现时长 / 自我（他人条件时 𝟙 = 0）。</div></div>"""

EQ_SAT = """<div class="eq"><span class="eq-name">式 3 · 两个饱和函数</span>
<div class="fml">f<sub>P</sub>(P; τ<sub>P</sub>) = 1 − e<sup>−P/τ<sub>P</sub></sup>
&nbsp;&nbsp;&nbsp;&nbsp; Q<sub>T</sub>(X; τ) = 1 − e<sup>−X/τ</sup></div>
<div class="eqnote">练习量与呈现时长都按指数饱和：收益递减，τ 越大饱和越慢。</div></div>"""

EQ_BOUND = """<div class="eq"><span class="eq-name">式 4 · 边界与起点</span>
<div class="fml">a(W) = a<sub>ref</sub> + Δa [ Q<sub>T</sub>(W; τ<sub>a</sub>) − Q<sub>T</sub>(W<sub>ref</sub>; τ<sub>a</sub>) ]
&nbsp;&nbsp;&nbsp;&nbsp; z = z<sub>ratio</sub> · a</div>
<div class="eqnote">期限越长边界越宽（更保守）；起点居中（z_ratio = 0.5）。</div></div>"""

EQ_MAP = {}


def pick_eq(latex: str) -> str:
    s = latex.replace(" ", "")
    if "d(t)=" in s:
        return EQ_PIECEWISE
    if "d_{\\text{stim}}=" in s:
        return EQ_DRIFT
    if "a(W)" in s:
        return EQ_BOUND
    if "f_P(P;\\tau_P)" in s:
        return EQ_SAT
    return '<pre class="latex">' + html.escape(latex.strip()) + "</pre>"


# ---------------------------------------------------------------- 行内标记
def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", t)
    t = re.sub(r"~~([^~]+)~~", lambda m: f"<del>{m.group(1)}</del>", t)
    return t


def slug(t: str, n: int) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", t).strip("-").lower()
    return f"s{n}-{s[:40]}"


def convert(md: str):
    lines = md.split("\n")
    out, toc = [], []
    i, h2, h3 = 0, 0, 0
    in_code = False
    code_buf = []
    in_eq = False
    eq_buf = []
    in_table = False

    def flush_table(rows):
        if not rows:
            return ""
        head = rows[0]
        is_sep = len(rows) > 1 and all(set(c.replace("|", "").strip()) <= set("-: ")
                                       for c in rows[1] if c.strip())
        body = rows[2:] if is_sep else rows[1:]
        th = "".join(f"<th>{inline(c.strip())}</th>" for c in head)
        trs = []
        for r in body:
            tds = "".join(f"<td>{inline(c.strip())}</td>" for c in r)
            trs.append(f"<tr>{tds}</tr>")
        return f'<div class="tblwrap"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'

    table_rows = []
    while i < len(lines):
        ln = lines[i]
        # 代码块
        if ln.startswith("```"):
            if in_code:
                out.append('<pre class="code">' + html.escape("\n".join(code_buf)) + "</pre>")
                code_buf, in_code = [], False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue
        # 显示公式
        if ln.strip() == "$$":
            in_eq = not in_eq
            if not in_eq:
                out.append(pick_eq("\n".join(eq_buf)))
                eq_buf = []
            i += 1
            continue
        if in_eq:
            eq_buf.append(ln)
            i += 1
            continue
        # 表格
        if ln.startswith("|"):
            table_rows.append([c for c in ln.strip().strip("|").split("|")])
            i += 1
            nxt = lines[i] if i < len(lines) else ""
            if not nxt.startswith("|"):
                out.append(flush_table(table_rows))
                table_rows = []
            continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            if lvl == 1:
                # 文档自身的 H1 与页头重复，跳过（页头已经写了标题）
                i += 1
                continue
            if lvl == 2:
                h2 += 1
                sid = slug(txt, h2)
                toc.append((2, txt, sid))
                out.append(f'<h2 id="{sid}"><span class="sn">{h2:02d}</span>{inline(txt)}</h2>')
            elif lvl == 3:
                h3 += 1
                sid = slug(txt, 100 + h3)
                toc.append((3, txt, sid))
                out.append(f'<h3 id="{sid}">{inline(txt)}</h3>')
            else:
                out.append(f"<h{lvl}>{inline(txt)}</h{lvl}>")
            i += 1
            continue
        if re.match(r"^---+$", ln.strip()):
            out.append('<hr class="sep">')
            i += 1
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(inline(lines[i].lstrip("> ")))
                i += 1
            out.append('<blockquote>' + "<br>".join(buf) + "</blockquote>")
            continue
        if re.match(r"^[-*]\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"^[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+\.\s+", ln):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"^\d+\.\s+", "", lines[i])) + "</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        if ln.strip():
            out.append("<p>" + inline(ln.strip()) + "</p>")
        i += 1
    return out, toc


CSS = """
:root{--ink:#1a1d21;--dim:#5b6470;--line:#e3e7ee;--bg:#fbfcfe;--accent:#1f5fd6;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.75 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:0 28px 80px}
header.hero{background:linear-gradient(135deg,#12213f,#1f5fd6 70%,#3f8cff);color:#fff;
 padding:52px 28px 40px;margin-bottom:26px}
header.hero .inner{max-width:1000px;margin:0 auto}
header.hero h1{margin:0 0 10px;font-size:30px;letter-spacing:.5px}
header.hero p{margin:4px 0;color:#dbe6ff;font-size:14.5px}
.badges{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.16);border:1px solid rgba(255,255,255,.3);
 padding:4px 11px;border-radius:999px;font-size:12.5px}
nav.toc{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:16px 22px;margin:0 0 26px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
nav.toc b{display:block;font-size:13px;color:var(--dim);letter-spacing:1px;margin-bottom:8px}
nav.toc a{color:var(--ink);text-decoration:none;font-size:14px;margin-right:14px;line-height:2}
nav.toc a:hover{color:var(--accent);text-decoration:underline}
h2{font-size:22px;margin:44px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--line)}
h2 .sn{color:var(--accent);font-size:14px;margin-right:10px;font-variant-numeric:tabular-nums}
h3{font-size:17px;margin:28px 0 10px;color:#12213f}
p{margin:10px 0}
code{background:#eef2f9;border:1px solid #e0e7f3;border-radius:5px;padding:1px 5px;
 font:13px/1.5 "Cascadia Mono",Consolas,monospace;color:#123}
pre.code{background:#0f172a;color:#e2e8f0;padding:16px 18px;border-radius:12px;overflow:auto;
 font:13px/1.6 "Cascadia Mono",Consolas,monospace}
pre.latex{background:#f4f6fb;border:1px dashed #c9d4e8;border-radius:10px;padding:12px 16px;
 font:12.5px/1.6 Consolas,monospace;color:#405;overflow:auto}
.tblwrap{overflow:auto;margin:14px 0;border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14.2px}
th,td{padding:9px 13px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f2f5fb;font-weight:600;color:#2b3a55;white-space:nowrap}
tbody tr:hover{background:#fafcff}
tr:last-child td{border-bottom:none}
blockquote{margin:14px 0;padding:12px 18px;background:#f3f7ff;border-left:4px solid var(--accent);
 border-radius:0 10px 10px 0;color:#2c3b57;font-size:14.6px}
ul,ol{margin:10px 0 10px 22px}
li{margin:4px 0}
hr.sep{border:none;border-top:1px dashed var(--line);margin:34px 0}
.eq{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:18px 22px;margin:22px 0;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.eq-name{display:inline-block;font-size:11.5px;letter-spacing:.6px;color:#fff;background:var(--accent);
 padding:2px 9px;border-radius:999px;margin-bottom:12px}
.fml{font:15.5px/2.1 "Cambria Math",Cambria,"Times New Roman",serif;text-align:center;color:#101a2e}
.eqnote{margin-top:10px;font-size:13.2px;color:var(--dim);text-align:center}
.cases{font-size:2.6em;line-height:.7;vertical-align:-.32em;margin-right:4px}
.casebody{display:inline-block;text-align:left;vertical-align:middle}
.caserow{display:block;padding:2px 0}
figure{margin:22px 0;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
figure img{width:100%;display:block;border-radius:8px}
figcaption{margin-top:10px;font-size:13px;color:var(--dim);text-align:center}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.pill{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;
 background:#e8f2ff;color:#12509b;border:1px solid #cfe2ff}
.ok{background:#e8f7ee;color:#146c3a;border-color:#c8ecd6}
.warn{background:#fff6e5;color:#8a5a00;border-color:#ffe3b0}
.bad{background:#fdeaea;color:#a12626;border-color:#f6cccc}
footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);
 color:var(--dim);font-size:13px}
"""

GALLERY = """
<h3 id="s4-figs">4.5 三张论文级图（模拟/解析，可直接进论文）</h3>
<div class="grid2">
<figure><img src="../03_论文写作/figures_sim/fig_sim_crlb.png" alt="CRLB">
<figcaption>图 1 · 参数精度的 Cramér–Rao 下界：每组多少人才能把参数压到 10%<br>
<span class="pill ok">d_ref 3 人</span> <span class="pill ok">β_T 41 人</span> <span class="pill bad">β_ST 2248 人</span></figcaption></figure>
<figure><img src="../03_论文写作/figures_sim/fig_sim_p_design.png" alt="P 方案识别力">
<figcaption>图 2 · P 水平设计的纯识别力（oracle）：40 人/组稳、20 人/组是下限</figcaption></figure>
</div>
<figure><img src="../03_论文写作/figures_sim/fig_sim_trials.png" alt="试次级模拟">
<figcaption>图 3 · 模型生成的试次级数据：RT 分位数随 T 单调、正确率 0.58→0.75、遗漏率随 W 单调下降</figcaption></figure>
<figure><img src="../../2_Data/Real_Data/_SYNTHETIC_NOTEBOOK/fig_trial_sim_check.png" alt="S3 notebook 自检图">
<figcaption>图 4 · <code>S3</code> notebook 的自检图（8 名被试 × 576 试次，含个体差异）</figcaption></figure>
"""

DIAGRAM = """
<h3 id="s3-diagram">3.0 一张图看懂模型</h3>
<figure><svg viewBox="0 0 900 300" width="100%" role="img" aria-label="三层结构示意图">
<style>text{font-family:"Microsoft YaHei",system-ui,sans-serif}</style>
<rect x="0" y="0" width="900" height="300" fill="#fbfcfe"/>
<rect x="20" y="26" width="250" height="88" rx="12" fill="#eaf1ff" stroke="#b9cdf5"/>
<text x="145" y="54" text-anchor="middle" font-size="14" fill="#1f5fd6" font-weight="700">任务层</text>
<text x="145" y="78" text-anchor="middle" font-size="12.5" fill="#2c3b57">P · T · W · 自我/他人 · 匹配</text>
<text x="145" y="98" text-anchor="middle" font-size="12.5" fill="#2c3b57">→ f_P 与 Q_T 两个饱和函数</text>
<rect x="20" y="150" width="250" height="104" rx="12" fill="#f0fbf3" stroke="#bfe6cd"/>
<text x="145" y="178" text-anchor="middle" font-size="14" fill="#146c3a" font-weight="700">被试层</text>
<text x="145" y="202" text-anchor="middle" font-size="12.5" fill="#2c3b57">v 漂移 · a 边界 · z 起点</text>
<text x="145" y="222" text-anchor="middle" font-size="12.5" fill="#2c3b57">t0 非决策 · ρ 掩蔽后保留率</text>
<text x="145" y="242" text-anchor="middle" font-size="12.5" fill="#2c3b57">每被一套，来自 N(mu, sigma²)</text>
<rect x="330" y="26" width="250" height="88" rx="12" fill="#fff7ea" stroke="#f2d9ab"/>
<text x="455" y="54" text-anchor="middle" font-size="14" fill="#8a5a00" font-weight="700">组层</text>
<text x="455" y="78" text-anchor="middle" font-size="12.5" fill="#2c3b57">β_P 练习效应 · τ_P 饱和</text>
<text x="455" y="98" text-anchor="middle" font-size="12.5" fill="#2c3b57">β_S 自我效应（组间回归）</text>
<rect x="330" y="150" width="250" height="104" rx="12" fill="#fdeef1" stroke="#f3c6d0"/>
<text x="455" y="178" text-anchor="middle" font-size="14" fill="#a12626" font-weight="700">观测层</text>
<text x="455" y="202" text-anchor="middle" font-size="12.5" fill="#2c3b57">RT · 选择 · 遗漏</text>
<text x="455" y="222" text-anchor="middle" font-size="12.5" fill="#2c3b57">首次通过时间 + t0</text>
<text x="455" y="242" text-anchor="middle" font-size="12.5" fill="#2c3b57">共同产生 576 试次/人</text>
<rect x="640" y="26" width="240" height="228" rx="12" fill="#f5f7fb" stroke="#d5dceb"/>
<text x="760" y="54" text-anchor="middle" font-size="14" fill="#2b3a55" font-weight="700">证据积累（两阶段）</text>
<line x1="676" y1="150" x2="844" y2="150" stroke="#8894a8" stroke-dasharray="4 3"/>
<line x1="676" y1="86" x2="844" y2="86" stroke="#8894a8"/>
<line x1="676" y1="214" x2="844" y2="214" stroke="#8894a8"/>
<text x="760" y="80" text-anchor="middle" font-size="11.5" fill="#5b6470">上边界 a</text>
<text x="760" y="230" text-anchor="middle" font-size="11.5" fill="#5b6470">下边界 0</text>
<path d="M700,150 L724,150 L742,124 L758,138 L774,104 L790,118 L806,96 L820,104"
      fill="none" stroke="#1f5fd6" stroke-width="2.2"/>
<circle cx="820" cy="104" r="4" fill="#1f5fd6"/>
<text x="826" y="100" font-size="11.5" fill="#1f5fd6">反应</text>
<line x1="742" y1="60" x2="742" y2="240" stroke="#e08a00" stroke-width="1.6" stroke-dasharray="5 3"/>
<text x="746" y="250" font-size="11" fill="#8a5a00">掩蔽出现 → ρ·d</text>
<path d="M145,114 L145,150" stroke="#9aa7bd" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M270,80 L330,60" stroke="#9aa7bd" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M270,190 L330,200" stroke="#9aa7bd" stroke-width="1.6" marker-end="url(#ar)"/>
<path d="M580,200 L640,160" stroke="#9aa7bd" stroke-width="1.6" marker-end="url(#ar)"/>
<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
<path d="M0,0 L10,5 L0,10 z" fill="#9aa7bd"/></marker></defs>
</svg>
<figcaption>图 0 · 三层结构：任务变量经映射方程进入被试层机制，机制产生观测；右侧是单个试次的两阶段证据积累。</figcaption>
</figure>
"""


def main():
    md = SRC.read_text(encoding="utf-8")
    body, toc = convert(md)
    # 图库插在 §4 末尾（即 §5 标题之前）；示意图插在 §3.1 之前
    joined = "\n".join(body)
    idx = joined.find('<h2 id="s6-')
    if idx > 0:
        joined = joined[:idx] + GALLERY + joined[idx:]
    idx3 = joined.find('<h3 id="s103-')
    if idx3 > 0:
        joined = joined[:idx3] + DIAGRAM + joined[idx3:]

    nav = "".join(
        f'<a href="#{sid}" class="{"lv2" if lvl == 2 else "lv3"}">{html.escape(txt)}</a>'
        for lvl, txt, sid in toc
    )
    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>项目全景预览 v1 · 自我匹配任务的证据积累建模</title>
<style>{CSS}</style></head>
<body>
<header class="hero"><div class="inner">
<h1>自我匹配任务中的证据积累：项目全景预览</h1>
<p>2026-10-21 ｜ pipeline-v1.13 ｜ 全部数字可复现（脚本见 §10）</p>
<div class="badges">
<span class="badge">4 组 × 4 T × 3 W × 自我/匹配 × 12 = 576 试次/人</span>
<span class="badge">两阶段 DDM（M-T1）</span>
<span class="badge">β_T 需 37–43 人/组</span>
<span class="badge">τ_P / β_ST 不可估</span>
</div>
</div></header>
<div class="wrap">
<nav class="toc"><b>目录</b>{nav}</nav>
{joined}
<footer>由 <code>1_Code/DDM_Core/_scratch/build_preview_html.py</code> 从同名 Markdown 生成；
图片相对路径指向 <code>5_Reference/03_论文写作/figures_sim/</code> 与 <code>2_Data/Real_Data/_SYNTHETIC_NOTEBOOK/</code>。</footer>
</div></body></html>
"""
    DST.write_text(page, encoding="utf-8", newline="\n")
    print("written", DST, len(page), "chars,", len(toc), "toc entries")


if __name__ == "__main__":
    main()
