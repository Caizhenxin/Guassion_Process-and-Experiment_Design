"""D102 落纸：scan_min_n.py + 机制更正说明（主计划四张表 + README §8.73 + §9 第 85 项）。"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"

DEC = (
    "| **D102** | 2026-10-18 | **「多少人/组才让 LOO 闸门转绿」从猜测变成可重跑扫描**。"
    "① 新工具 `1_Code/Experiment/scan_min_n.py`：对每个 N 依次「生成 N 名合成被试 → "
    "`stage8_run` 单组拟合 → `stage8_health.assess_group` 取判词 → 追加写 "
    "`scan_min_n.json` / `scan_min_n.md`」，同一 N 重跑覆盖、`--reuse` 跳过已拟合；"
    "② **只扫组 1 是合法的**：逐组拟合参数集 = `WITHIN_FREE_LIN`(7) + `rho`，`beta_P` 不参与"
    "（见 D100 机制更正），所以单组就能回答「16 维组层超参数（`mu`/`log_sigma` 各 8）需要多少名被试」；"
    "③ 配置固定 quick（`n_em`=3、`n_draws`=12、`n_x`=21、PPC 1、`--hyper-method analytic`、"
    "`--loo-level trial`），阶梯 **N = 4 / 8 / 12**；按 8 人 quick 实测 11594.3 s 线性摊"
    "（≈ 24 min/人）⇒ 全阶梯 ≈ 9.6 h；④ 判词一律从 `stage8_health` 取，不复制判据（D94/D98 教训）；"
    "⑤ 冒烟已过：1 人 txt = **581 行 / 25 列**、Markdown 表与 JSON 追加语义 OK（同 N 覆盖不增行）；"
    "⑥ **扫描结果待填**（后台作业 `pwsh-577`，产物 `2_Data/Real_Data/_SYNTHETIC_SCAN/`）"
    "——N 增大仍 BAD ⇒ 查判据；首次转 OK 的 N 就是可辨识下限的粗估 "
    "| `1_Code/Experiment/scan_min_n.py`（**新建**，145 行）+ "
    "`1_Code/DDM_Core/_scratch/_smoke_scan_min_n.py`（冒烟，51 行）+ "
    "`2_Data/Real_Data/_SYNTHETIC_SCAN/`（`scan_min_n.md` / `scan_min_n.json` / `_scan_run.log`） "
    "| 无（扫描跑完把拐点填进 D102 ⑥ 与 README §8.73） |"
)

PROG = (
    "| 2026-10-18 | **D100 后续（最小可辨识样本量扫描）** | 新增 `scan_min_n.py`"
    "（N=4/8/12 阶梯、判词取 `stage8_health`、追加式报告）并在后台起跑"
    "（`pwsh-577`，≈9.6 h）；同时纠正 D100 的机制句：`beta_P` 不参与逐组拟合，"
    "真因是 16 维组层超参数 vs 被试数 "
    "| `1_Code/Experiment/scan_min_n.py`（145 行）+ `2_Data/Real_Data/_SYNTHETIC_SCAN/`（产物：`scan_min_n.md`/`.json`/日志） "
    "| 无（结果回来填 D102 ⑥） |"
)

CHG = (
    "| 2026-10-18 | **新增 D102（最小可辨识样本量扫描）**：`scan_min_n.py` 把「4/8/12 人/组各判什么」"
    "做成一条可重跑命令（生成 → 单组拟合 → `stage8_health` 判词 → 追加报告），后台作业 `pwsh-577` 起跑；"
    "同时更正 D100 的机制解释：`beta_P` 不在逐组拟合参数集里（见失败记录"
    "「文档把未参与拟合的参数写成机制原因」） |"
)

EV = (
    "| `1_Code/Experiment/scan_min_n.py`（**新建**，D102，145 行）：`gen_data`（包一层 "
    "`_make_ddm_pilot.py`，只写 txt）+ `run_stage8`（`--hyper-method analytic`、`--loo-level trial`）"
    "+ `one`（判词取 `stage8_health.assess_group`）+ `write_reports`（JSON 合并 + Markdown 表，"
    "同 N 覆盖）；`2_Data/Real_Data/_SYNTHETIC_SCAN/`（D102 产物） |"
)

R873 = [
    "## 8.73 「多少人/组才让 LOO 转绿」的扫描（D102）",
    "",
    "**问题**：D100 只证明「2 人/组必红、加抽样不救」，没有回答「多少人/组能绿」。",
    "",
    "**工具**：`1_Code/Experiment/scan_min_n.py`",
    "",
    "```bash",
    "python -X utf8 1_Code/Experiment/scan_min_n.py --n-list 4 8 12     # 全阶梯 ≈ 9.6 h",
    "python -X utf8 1_Code/Experiment/scan_min_n.py --n-list 4 --reuse  # 只补缺的 N",
    "```",
    "",
    "对每个 N：`_make_ddm_pilot.py` 生成 N 名合成被试（组 1、`--rho 0.8`、`--anticipation 0.03`）→ "
    "`stage8_run.py` 单组 quick 拟合 → `stage8_health.assess_group` 取判词 → 追加进 "
    "`scan_min_n.json` / `scan_min_n.md`（同一 N 重跑覆盖，不新增行）。",
    "",
    "**为什么单组就够**：逐组拟合的参数集是 `WITHIN_FREE_LIN`（7 个）+ `rho`，"
    "`k = nw + (1 if rho_free else 0)`，超参数 Hessian 维数 **2K = 16**（`mu`、`log_sigma` 各 8）。"
    "`beta_P` **不参与**逐组拟合（`BETWEEN_FREE` 只在 `mapping.py:70` 声明、层级拟合没用它）"
    "——所以瓶颈是「16 维组层超参数 vs 被试数」，与 P 的组间回归无关。",
    "",
    "**判词只从 `stage8_health` 取**（D94/D98 的教训：判据一旦复制就会分叉）。",
    "",
    "**读法**：N 增大仍 `BAD` ⇒ 查判据（不是样本量问题）；首次 `OK` 的 N = 可辨识下限的粗估，"
    "再乘真实数据的噪声余量才是 Stage 7 的处方人数。",
    "",
    "**成本**：8 人 quick 实测 11594.3 s ⇒ ≈ 24 min/人（两模型），N=4/8/12 合计 ≈ 9.6 h。",
    "",
]

S9 = (
    "| 85 | 🟡 **进行中**：D102 的 N=4/8/12 扫描（后台 `pwsh-577`）——结果回填 "
    "`2_Data/Real_Data/_SYNTHETIC_SCAN/scan_min_n.md`；「首次转 OK 的 N」写进 D102 ⑥ 与 §8.73 |"
)


def edit(path: Path, fn):
    L = path.read_text(encoding="utf-8").split("\n")
    L = fn(L)
    path.write_text("\n".join(L), encoding="utf-8", newline="\n")


def plan_fn(L):
    def ins_after(prefix, row):
        idxs = [i for i, x in enumerate(L) if x.startswith(prefix)]
        assert len(idxs) == 1, (prefix, len(idxs))
        L.insert(idxs[0], row)

    ins_after("| **D101** |", DEC)
    ins_after("| 2026-10-18 | **6.5（结果进论文）**", PROG)
    ins_after("| 2026-10-18 | **新增 D101（结果章模板 + 自动填表）**", CHG)
    last = max(i for i, x in enumerate(L) if x.startswith("| `5_Reference/03_论文写作/论文_结果章_模板.md`"))
    L.insert(last + 1, EV)
    return L


def readme_fn(L):
    i = L.index("## 9. 尚未做")
    L[i:i] = R873
    last = max(i for i, x in enumerate(L) if x.startswith("| 84 |"))
    L.insert(last + 1, S9)
    return L


edit(PLAN, plan_fn)
edit(README, readme_fn)
for p in (PLAN, README):
    L = p.read_text(encoding="utf-8").split("\n")
    print(p.name, "→", len(L), "行")
