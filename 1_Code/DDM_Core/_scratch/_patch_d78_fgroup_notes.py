# -*- coding: utf-8 -*-
"""_patch_d78_fgroup_notes.py —— 把 F 组（按行号写入）写进三条说明 + 自测头注"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RD = ROOT / "1_Code/DDM_Core/README.md"
S7 = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
CHK = ROOT / "1_Code/Experiment/exp_matlab/test/check_data_accum.m"

pairs = [
    (RD, "A 容器类型与列数、B 崩溃复现（`f` 之后写 `NA` 必须不报错且 `Response` 保留 `NA`）、C 不等长标签无补齐空格、D 静态守卫（主程序不得再出现 `data = table()` / `data.Properties`）、E 写 CSV 再 `readtable` 读回逐列核对。",
     "A 容器类型与列数、B 崩溃复现（`f` 之后写 `NA` 必须不报错且 `Response` 保留 `NA`）、C 不等长标签无补齐空格、D 静态守卫（主程序不得再出现 `data = table()` / `data.Properties`）、E 写 CSV 再 `readtable` 读回逐列核对、**F 主程序实际写法**（`data{trialIndex, c}` 按行号写入：自动扩行不留空洞、`size(data,1) == trialIndex-1` 成立、cell2table 与写读回环 5 行混合响应）。"),
    (S7, "含「先 f 后 NA」崩溃复现、不等长标签、静态守卫、写读回环",
     "含「先 f 后 NA」崩溃复现、不等长标签、静态守卫、写读回环、按行号写入（F 组）"),
    (CHK, "%   E 端到端：3 行混合响应 → 写 CSV → readtable 读回，逐列核对。",
     "%   E 端到端：3 行混合响应 → 写 CSV → readtable 读回，逐列核对；\n%   F 主程序实际写法 `data{trialIndex, c}`（按行号写，不是 end+1）：自动扩行不留空洞、\n%     行数自检成立、cell2table 与写读回环。"),
]
for p, old, new in pairs:
    t = p.read_text(encoding="utf-8")
    if new in t:
        print("[跳过]", p.name)
        continue
    if t.count(old) != 1:
        raise SystemExit(f"❌ {p.name}：命中 {t.count(old)} 次")
    p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
    print("[替换]", p.name)
