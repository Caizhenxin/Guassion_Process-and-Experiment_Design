"""D99 补记：把 `check_run_pipeline.py`（7/7）写进三份文档。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
S8 = ROOT / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"

SELFTEST = (ROOT / "1_Code" / "Experiment" / "exp_Check" / "check_run_pipeline.py")
N_LINES = len(SELFTEST.read_text(encoding="utf-8").split("\n"))


def sub_one(path: Path, old: str, new: str, what: str) -> str:
    txt = path.read_text(encoding="utf-8")
    n = txt.count(old)
    if n != 1:
        raise AssertionError(f"{what}：命中 {n} 次（期望 1）")
    path.write_text(txt.replace(old, new), encoding="utf-8", newline="\n")
    return f"{what}：ok"


def main() -> None:
    p_main = MAIN.read_text(encoding="utf-8")
    if "check_run_pipeline.py" not in p_main:
        print(sub_one(
            MAIN,
            "⑥ 代价：这次 3.2 h 的拟合**一个可引用数字都没换来**，但换到了「闸门必须自动跑」这条硬约束。 |",
            "⑥ 代价：这次 3.2 h 的拟合**一个可引用数字都没换来**，但换到了「闸门必须自动跑」这条硬约束。"
            f"⑦ 自测：新增 `check_run_pipeline.py`（{N_LINES} 行，**7/7**）—— P2 用一份"
            "`n_flipped`=2/16、而 `k_max`=0.000 与 `p_loo`=10 都「好看」的假 JSON，钉死"
            "「只有 D74 会判死它」；P4/P5 钉死健康组放行（退出码 0）与病组拦截（退出码 1）。 |",
            "主计划 D99 加自测"))
        print(sub_one(
            MAIN,
            "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_pipeline/results_skeleton.md`（实测 0/4 可引用） |",
            "`2_Data/Real_Data/_SYNTHETIC_DEMO_v1/_pipeline/results_skeleton.md`（实测 0/4 可引用）"
            f" + `1_Code/Experiment/exp_Check/check_run_pipeline.py`（**新建**，{N_LINES} 行，7/7） |",
            "主计划 D99 落地件加自测"))
    else:
        print("主计划：已含 check_run_pipeline.py，跳过")

    if "D99 补" in README.read_text(encoding="utf-8"):
        print("README：§9 第 82 项已补 D99，跳过")
    else:
        print(sub_one(
            README,
            "| 82 | ✅ **全流程一键跑通（D98）**：`run_pipeline.py` 串起 intake → stage6 → stage8 → "
        "出图 → 结果节骨架；合成数据 8/8 KEEP；三图 + 骨架已产出 | **尚未做**：`run_pipeline.py` "
        "没有 `check_run_pipeline.py` 自测、也没进 `run_selftest.bat`；Stage 8 的 8 人全量"
        "（quick 配置约 5 h）尚未跑完，当前只有组 1（2 人）落盘 |",
        "| 82 | ✅ **全流程一键跑通（D98）**：`run_pipeline.py` 串起 intake → stage6 → stage8 → "
        "出图 → 结果节骨架；合成数据 8/8 KEEP；三图 + 骨架已产出。**D99 补**：LOO 闸门进流水线"
        "（3.5 步）、骨架四列 + 不可引用横幅、`fig3` 斜线，并有 `check_run_pipeline.py` **7/7** | "
        "**尚未做**：没进 `run_selftest.bat`（那是实验室机的 MATLAB 自测，故意不掺分析代码）；"
        "Stage 8 的 8 人 quick 全量已跑完但**四组全不可引用**（D99），formal 全量未跑 |",
        "README §9 第 82 项"))

    s8 = S8.read_text(encoding="utf-8").split("\n")
    if not any("check_run_pipeline.py" in x for x in s8):
        idx = max(k for k, x in enumerate(s8) if "run_pipeline.py`（D98）" in x)
        s8.insert(idx + 1,
                  f"| `1_Code/Experiment/exp_Check/check_run_pipeline.py`（**新建**，D99，"
                  f"{N_LINES} 行，7/7） | 证明「LOO 闸门真的接进流水线」：健康组放行（退出码 0）、"
                  "`n_flipped`=2/16 而 `k_max`/`p_loo` 都好看的病组被拦（退出码 1） |")
        S8.write_text("\n".join(s8), encoding="utf-8", newline="\n")
        print(f"Stage8 方案：已插入自测行（{len(s8)} 行）")
    else:
        print("Stage8 方案：已含，跳过")


if __name__ == "__main__":
    main()
