# -*- coding: utf-8 -*-
"""临时：在 §6.3.3 标注参数恢复的口径更新，并重建 v3.1。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"
BODY = DOC / "_v3_正文.md"

s = BODY.read_text(encoding="utf-8")
note = ("⏳【口径更新】本节表 6-2、表 6-3 与图 6-3~6-5 的数值以**历史配置（配置 A）**的参数为真值。"
        "以修正配置（配置 C）参数为真值的参数恢复重跑已启动（8 个条件 × 3 重复 × 2 方案 + 遗漏率曲线 32 次，共 80 次拟合；"
        "脚本 `rerun_recovery_with_refit_truth.py`，产物 `param_recovery_refit/`）；完成后需替换本节相应表图。"
        "预期定性结论不变（绝对漂移率不可恢复、SPE_v 可恢复），但具体偏倚数值会随真值口径调整。")
anchor = "参数恢复的真值—恢复值对照见图 6-3。"
if anchor in s and "【口径更新】" not in s:
    s = s.replace(anchor, note + "\n\n" + anchor)
    BODY.write_text(s, encoding="utf-8")
    print("[body] 已加入口径更新说明")
else:
    print("[body] 跳过（锚点缺失或已存在）")

r = subprocess.run([sys.executable, "-u", str(DOC / "_build_docx_v3.py")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
print("[build] exit:", r.returncode)
print((r.stdout or "").strip().splitlines()[-1] if r.stdout else "")
