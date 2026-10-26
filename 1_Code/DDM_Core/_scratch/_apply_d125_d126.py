"""把 D125/D126 写进主计划的四处（决策表 / 进度行 / 变更日志 / 证据行）。"""
from pathlib import Path

PLAN = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
            r"\5_Reference\08_工作流\工作流_主计划.md")

D126 = (
    "| **D126** | 2026-10-26 | **Stage 8 二轮（17 人 quick 档，8/8）收口：模型比较仍无结论，但 PPC 的失配形态从"
    "「偏短」改判为「过散」，并把 λ 污染项与 T 通道两条假设都排除掉**。M-T1 四组超参数 Hessian 全非正定"
    "（`n_flipped` = 1/1/1/1）⇒ ELPD 一律不可引用，**ΔELPD 本轮不报**（D121 的「组3/4 高 62/50」随之作废）；"
    "M-T3 四组 `k_max` 全 0、越界 0、`p_loo`/`n_obs` ≤ 0.00173 ⇒ 参数可报。PPC 分位（17 人平均「预测−观测」）："
    "**p10 −99.3、p25 −97.1、p50 −48.3、p75 +62.6、p90 +184.5 ms**，`(p90−p10)/p50` 预测是观测的 1.7–2.2 倍 ⇒ "
    "论文只能写「预测 RT 分布过散」，不能写「系统性偏快」；且 `t0`≈0.19–0.29 使模拟 RT 无一例 <0.20，"
    "故「预测端也该剔 RT<0.20」这条辩护不成立（两种口径分位逐位相同）。**λ 污染项已实现但被证否**："
    "`likelihood.py` 加 `lambda_guess`（λ=0 走原分支、逐位等价），9 人剖面几乎处处 Δℓ<0"
    "（2-3 −85.9、2-1 −104.1、1-2 −5.6…），只有 1-3 在 λ=0.05 时 +11.3 ⇒ 抢按通道不是这批数据缺失的成分；"
    "代码保留但默认关、不进论文。**T 通道也排除**：`_probe_T_channel.py` 扫 `d_ref` 显示 acc 0.654→0.770 "
    "只需 `d_ref` 0.35→0.69、RT 中位 679→661（ΔRT −18 ms），实测 +12 ms、缺口仅 30 ms ⇒ 不必给 T 加边界通道。"
    "**下一轮**：把污染分量从「铺满 [0,W]」改成「窄窗 [t0, 0.45]」再判一次（半天，不重跑 Stage 8）；"
    "若仍 Δℓ<0 则判定为模型族局限，把 PPC 结论写进第 9 章。 | "
    "用户 2026-10-25「优先把当前运行的跑完吧，之后就专注Stage 8」＋ 2026-10-26 08:0x「请继续」 | "
    "`5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md`（**新建**）+ "
    "`2_Data/Real_Data/New_Design/_pipeline/stage8_d123/stage8_report.md`（1837 行）+ "
    "`_scratch/{_ppc_parse,_ppc_quantiles,_probe_ppc_filter,_probe_bimodal,_probe_lambda_profile,"
    "_probe_lambda_low,_probe_T_channel}.py` + "
    "`Self-Repo/AI_Self_Improvement/2026-10-26_预判污染项能修好PPC实测被证否.md`（**新建**） |"
)

D125 = (
    "| **D125** | 2026-10-26 | **Stage 8 的产物粒度从「整组」降到「逐模型」，托管从「会话内后台」换到 `schtasks`**。"
    "一天内四次中断：`run_in_background` 随会话重开被回收；`.cmd` 写成 LF 换行使 `cmd.exe` 静默退出并烧光 5 次"
    "重启额度；19:39 一次原因不明（日志停在组 3 M-T1 开始后一行 `RuntimeWarning: invalid value encountered in "
    "subtract`）；**19:57 一次是我自己造成的**——`job_kill` 一个无关冒烟作业，日志立刻出现 `^C`，"
    "证明 `Invoke-CimMethod Win32_Process.Create` 拉起的进程仍继承同一控制台。定案：**只有 `schtasks` 彻底脱离**"
    "（任务 `DSH_stage8` 跑 `_stage8_launch.cmd`，内含失败睡 120 s 后 `--resume` 的重试环，最多 8 次；"
    "`DSH_stage8_watch` 刷面板）。同时把缓存降到逐模型：`stage8_run.py` 在 `_group_file` 之外新增 "
    "`_model_file`/`_load_model`，`fit_group(..., ckpt=None)` 命中时把 `r[\"log_lik\"]` 用 "
    "`np.asarray(..., float)` 还原（否则 `compare_models` 静默算错），每模型跑完 `_write_json_atomic` ⇒ "
    "组 3 的 M-T1 不再因组内另一个模型失败而重跑 1.8 h（此前已作废三次）。面板同步三修："
    "`stage8_watch.progress_from_disk()` 改从磁盘数进度（换日志文件后不再归零）、"
    "`jobstatus._resolve_root()` 四级回落（任务计划拉起的进程没有 `DSH_HOME`）、插件 `STALE_SECONDS = 600`。"
    "`check_model_ckpt.py` 四条自测全过。 | 用户 2026-10-25「Stage 8的进程停了」＋"
    "「记得把踩过的坑记录下来……你的『作业』这个插件……没有能监督到现在正在运行的后台任务」 | "
    "`1_Code/DDM_Core/stage8_run.py`（`_model_file`/`_load_model`/`ckpt`）+ "
    "`1_Code/Experiment/stage8_watch.py`（`progress_from_disk`）+ `1_Code/Tools/jobstatus.py`（`_resolve_root`）+ "
    "`1_Code/Tools/dsh-jobboard/lib/index.mjs` + `_scratch/_stage8_launch.cmd`（CRLF）+ 提交 `a67ab44`；"
    "失败记录追加两节、INDEX 36 行 |"
)

PROG = [
    "| 2026-10-25 | **22（逐模型检查点 + 任务计划托管 → D125）** | **把「跑不完的作业」从根上解决**：产物粒度整组 → 逐模型"
    "（组 3 的 M-T1 不再被组内另一个模型拖死，此前白跑 1.8 h ×3）；托管从会话内后台 → `schtasks`"
    "（实测 `job_kill` 一个无关作业就把 Stage 8 打死，`^C` 留在日志里）；面板进度改从磁盘数、`jobstatus` 四级回落路径。"
    "未做：把 4 组拆成 4 个并行进程（`--out` 已支持，但要先确认内存与 GPU/CPU 竞争）。 | "
    "`check_model_ckpt.py` 四条自测；提交 `a67ab44` | `stage8_run.py`；`stage8_watch.py`；`jobstatus.py` |",
    "| 2026-10-26 | **23（Stage 8 二轮读数 → D126）** | 17 人 quick 档 8/8 跑完（组耗时 2112/4965/3202/4041 s）。"
    "M-T1 四组超参 Hessian 全非正定 ⇒ ΔELPD 不报；M-T3 四组干净。PPC 由「偏短 60–90 ms」改判为**过散**"
    "（p10 −99 / p90 +185 ms、相对离散度 1.7–2.2×）。λ 污染项与 T 通道两条假设被逐一排除。"
    "未做：窄窗污染项、formal 档 PPC 复核、组层 P 效应（需 ≥10 人/组）。 | "
    "用户 2026-10-25「之后就专注Stage 8」 | `Stage8_真实数据二轮_20261026.md` |",
]

CHANGE = [
    "| 2026-10-25 | **新增 D125（逐模型检查点 + `schtasks` 托管）**：`stage8_run.py` 加 "
    "`_model_file`/`_load_model`/`fit_group(ckpt=)`，每模型落盘 `stage8_model_g<组>_<模型>.json`；"
    "`_stage8_launch.cmd` 改 CRLF 并自带重试环；注册任务 `DSH_stage8`/`DSH_stage8_watch`；"
    "`stage8_watch.progress_from_disk` 与 `jobstatus._resolve_root` 修面板不显示/进度归零。 |",
    "| 2026-10-26 | **新增 D126（Stage 8 二轮读数与两条阴性结果）**：17 人 8/8；M-T1 ELPD 不可引用、"
    "M-T3 可报；PPC 改判「过散」；λ 污染项剖面几乎处处 Δℓ<0 ⇒ 默认关；T 通道经模拟排除。"
    "新建二轮报告与失败记录 `2026-10-26_预判污染项能修好PPC实测被证否.md`。 |",
]

EVID = [
    "| `1_Code/DDM_Core/stage8_run.py`（`_model_file`/`_load_model`/`ckpt`）+ `_scratch/_stage8_launch.cmd` + "
    "`1_Code/Experiment/stage8_watch.py`（`progress_from_disk`）+ `1_Code/Tools/jobstatus.py`（`_resolve_root`） | "
    "D125 证据：① 四次中断的时间线与证据（`job_kill` 后日志里的 `^C`；LF 换行的 `.cmd` 让 `cmd.exe` 静默退出）；"
    "② `check_model_ckpt.py` 四自测（写盘/命中/`log_lik` 还原/配置不一致报错）；③ 面板实读 "
    "`[running ] Stage 8 真实数据（17 人） 4/8 组 3 · M-T1 拟合中`；④ 产物 "
    "`stage8_model_g{3,4}_M-T{1,3}.json`。 |",
    "| `5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md` + `_pipeline/stage8_d123/stage8_report.md` + "
    "`_scratch/_probe_{ppc_filter,lambda_profile,lambda_low,T_channel,bimodal}.py` | "
    "D126 证据：① 四组两模型的 ELPD/`n_flipped`/`p_loo`（2 表合一）；② 17 人 PPC 分位差（−99/−97/−48/+63/+185 ms）"
    "与三个代表被试的分位对照；③ 8,355 试次的 RT 带正确率表（≤400 ms 占 11.1%、acc 0.544）；"
    "④ λ 剖面 9 人 3–4 档 Δℓ；⑤ `d_ref` 扫描（acc 0.522→0.809、RT 中位 678→470）与两端插值（ΔRT −18 ms）。 |",
]


def main():
    text = PLAN.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    hit = {"dec": 0, "prog": 0, "chg": 0, "evd": 0}
    for ln in lines:
        if ln.startswith("| **D124** | 2026-10-25 |"):
            out.extend([D126, D125])
            hit["dec"] += 1
        out.append(ln)
        if "**21（通用作业面板 → D124）**" in ln:
            out.extend(PROG)
            hit["prog"] += 1
        if "**新增 D124（DSH 侧边栏作业面板）**" in ln:
            out.extend(CHANGE)
            hit["chg"] += 1
        if ln.startswith("| `1_Code/Tools/dsh-jobboard/`（`lib/index.mjs`"):
            out.extend(EVID)
            hit["evd"] += 1
    if any(v != 1 for v in hit.values()):
        raise SystemExit(f"锚点数量不对：{hit}")
    PLAN.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"已写入；{len(lines)} → {len(out)} 行；锚点 {hit}")


if __name__ == "__main__":
    main()
