"""把结果节骨架的同一批块填进论文结果章模板（D101）。

单一来源原则：表格与横幅一律来自 `run_pipeline.build_blocks`，本模块只做
「模板 → 成品」的替换与几处文字化，**不重写任何判据、不另起一套渲染**。
理由见 README §8.70/§8.71：同一张报告里的同一个量，必须由同一个函数产出。

用法（数据目录里已有 `_pipeline/stage6_report.md` 与拟合结果时）：

    python -X utf8 1_Code/Experiment/manuscript.py 2_Data/Real_Data/<目录> [--out ...]

或由 `run_pipeline.py` 作为第 5 步调用（推荐，避免重复读盘）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEMPLATE = ROOT / "5_Reference" / "03_论文写作" / "论文_结果章_模板.md"
MARK_RE = re.compile(r"\{\{([a-z0-9_]+)\}\}")


def load_template(path: Path | None = None) -> str:
    p = Path(path) if path else TEMPLATE
    if not p.exists():
        raise FileNotFoundError(f"找不到结果章模板：{p}")
    return p.read_text(encoding="utf-8")


def table_under(text: str, heading_prefix: str) -> list[str]:
    """取某个 `## ` 小节里的第一段连续表格行（表格行以 `|` 开头）。"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(heading_prefix)), None)
    if start is None:
        return []
    out: list[str] = []
    seen = False
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        if l.strip().startswith("|"):
            out.append(l)
            seen = True
        elif seen:
            break
    return out


def render(template: str, blocks: dict[str, list[str]]) -> str:
    """把 `{{name}}` 换成对应行块；模板里有而块里没有的占位必须报错（不许静默留空）。"""
    used = MARK_RE.findall(template)
    missing = sorted({m for m in used if m not in blocks})
    if missing:
        raise KeyError(f"模板占位没有对应数据块：{', '.join(missing)}")
    return MARK_RE.sub(lambda m: "\n".join(blocks[m.group(1)]), template)


def synth_banner(data: Path) -> str:
    p = Path(data) / "synth_truth.json"
    if not p.exists():
        return ""
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        meta = {}
    gen = meta.get("generator", "未知生成器")
    n = len(meta.get("sessions") or []) or meta.get("n_sessions", "?")
    return ("> ⚠️ **本文件由合成数据生成**（`synth_truth.json`，生成器 "
            f"`{gen}`，{n} 场）：只用于验证流程是否跑通，"
            "**任何数字都不得写进论文正文**（主计划 D98/D100）。\n")


def write_draft(data: Path, out: Path, rows: list[dict], groups: dict,
                truth: dict | None, health: dict[int, dict] | None = None) -> Path:
    """生成 `<out>/manuscript_draft.md`；返回路径。"""
    import run_pipeline as RP

    blocks = RP.build_blocks(rows, groups, truth, health)
    s6 = Path(out) / "stage6_report.md"
    if s6.exists():
        blocks["s6_table"] = table_under(s6.read_text(encoding="utf-8"), "## 2.")
    else:
        blocks["s6_table"] = ["（本目录没有 `stage6_report.md`：先跑流水线第 2 步）"]

    text = render(load_template(), blocks)

    banner = synth_banner(data)
    if banner:
        lines = text.split("\n")
        idx = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        lines.insert(idx, banner)
        text = "\n".join(lines)

    p = Path(out) / "manuscript_draft.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def load_truth(data: Path) -> dict | None:
    """从 `<data>/synth_truth.json` 取组真值（只有合成数据才有；真数据返回 None）。"""
    p = Path(data) / "synth_truth.json"
    if not p.exists():
        return None
    try:
        meta = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    gt = meta.get("group_truth") or {}
    return next(iter(gt.values()), None)


def main() -> int:
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import intake as INTAKE
    import run_pipeline as RP

    ap = argparse.ArgumentParser(description="把结果章模板填成草稿（数据须已跑过流水线）")
    ap.add_argument("data")
    ap.add_argument("--out", default=None, help="默认 <数据目录>/_pipeline")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()

    data = Path(args.data).resolve()
    out = Path(args.out).resolve() if args.out else data / "_pipeline"
    sessions = INTAKE.find_sessions([data])
    if not sessions:
        print(f"[错误] 没有找到场次：{data}", file=sys.stderr)
        return 2
    rows = [INTAKE.audit_one(s["gid"], s["sid"], s.get("csv"), s.get("txt"),
                             s.get("shadowed")) for s in sessions]
    s8 = out / "stage8"
    groups = RP.load_groups(s8) if s8.exists() else {}
    health = RP.assess_health(s8) if s8.exists() else {}
    truth = load_truth(data)
    global TEMPLATE
    if args.template:
        TEMPLATE = Path(args.template).resolve()
    p = write_draft(data, out, rows, groups, truth, health)
    text = p.read_text(encoding="utf-8")
    n_pending = text.count("【待写】")
    print(f"[manuscript] {p}")
    print(f"[manuscript] 行数 {len(text.splitlines())}、表格块 4、待写处 {n_pending}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
