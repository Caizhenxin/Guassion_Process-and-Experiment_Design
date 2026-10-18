"""修 D102 落纸后两处列数：主计划证据行（2 列）、README §9 行（3 列）。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"

# 主计划：证据表是 2 列（表头 3 竖线）⇒ 补第二格
L = PLAN.read_text(encoding="utf-8").split("\n")
hit = [i for i, x in enumerate(L) if x.startswith("| `1_Code/Experiment/scan_min_n.py`（**新建**，D102")]
assert len(hit) == 1, hit
line = L[hit[0]]
assert line.rstrip().endswith("|"), line[-80:]
body = line.rstrip()[:-1].rstrip()          # 去掉末竖线
L[hit[0]] = body + " | D102 证据：阶梯在后台跑（`pwsh-577`），结果回填 `scan_min_n.md`；判词来源固定为 `stage8_health.assess_group` |"
PLAN.write_text("\n".join(L), encoding="utf-8", newline="\n")

# README §9：3 列（表头 4 竖线）⇒ 拆成 编号 / 状态 / 说明
R = README.read_text(encoding="utf-8").split("\n")
hit = [i for i, x in enumerate(R) if x.startswith("| 85 | 🟡 **进行中**：D102")]
assert len(hit) == 1, hit
R[hit[0]] = ("| 85 | 🟡 **进行中** | D102 的 N=4/8/12 扫描（后台 `pwsh-577`）——结果回填 "
             "`2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md`；「首次转 OK 的 N」写进 D102 ⑥ 与 §8.73 |")
README.write_text("\n".join(R), encoding="utf-8", newline="\n")
print("fixed")
