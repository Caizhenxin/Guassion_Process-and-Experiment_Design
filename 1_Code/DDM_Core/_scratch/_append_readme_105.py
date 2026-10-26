"""在 1_Code/DDM_Core/README.md §9 末尾追加第 105/106 项（D125/D126）。"""
from pathlib import Path

README = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\README.md")

ROWS = [
    "| 105 | ✅ **逐模型检查点 + `schtasks` 托管（D125）** | `stage8_run.py`：新增 `_model_file(outdir, g, name)` → "
    "`stage8_model_g<组>_<模型>.json`、`_load_model(mf, name, config)`，`fit_group(..., ckpt=None)` 命中即跳过拟合并把 "
    "`r[\"log_lik\"]` 用 `np.asarray(..., float)` 还原，`run_group(..., ckpt=None)` 透传，`main()` 传 "
    "`{\"dir\": outdir, \"tag\": str(g), \"config\": run_config, \"resume\": bool(args.resume)}`。**为什么**："
    "组级缓存让组 3 的 M-T1 白跑 1.8 h ×3；`run_in_background` 与 WMI 拉起的进程都会被同一控制台的 `^C` 打死，"
    "只有 `schtasks` 能活过会话。自测 `_scratch/check_model_ckpt.py` 四条。 |",
    "| 106 | ✅ **Stage 8 二轮读数 + λ 通道（默认关）（D126）** | `likelihood.py` 的 "
    "`trials_from_arrays(..., lambda_guess=0.0)` 新增 `lambda_guess` 键：`per_trial_loglik` 在 `lam>0` 时 responded 用 "
    "`np.logaddexp(np.log1p(-lam)+log_f, np.log(lam)-np.log(w_ref)-np.log(2.0))`、omission 用 "
    "`p_omit = (1-lam)*s + lam*(1 - W/w_ref)`（`w_ref = float(np.max(tr[\"W\"]))`，污染项也允许超时）；"
    "**`lam == 0` 走原分支、与改动前逐位等价**，Stage 3/5/9 不受影响。**本轮被数据证否**：9 人剖面几乎处处 "
    "Δℓ<0（若要用，必须把污染分量从 `[0, W]` 收窄到 `[t0, 0.45]` 再试）。二轮读数（17 人 quick）：M-T1 四组 "
    "`n_flipped`=1 ⇒ ELPD 不可引用，M-T3 四组可报；PPC 为「过散」而非「偏短」。详见 "
    "`5_Reference/03_论文写作/Stage8_真实数据二轮_20261026.md`。 |",
]


def main():
    text = README.read_text(encoding="utf-8")
    lines = text.splitlines()
    if any(ln.startswith("| 106 |") for ln in lines):
        print("已存在，跳过")
        return
    last = lines[-1]
    if not last.startswith("| 104 |"):
        raise SystemExit(f"最后一行不是第 104 项：{last[:80]}")
    lines.extend(ROWS)
    README.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"已追加两行；现 {len(lines)} 行")


if __name__ == "__main__":
    main()
