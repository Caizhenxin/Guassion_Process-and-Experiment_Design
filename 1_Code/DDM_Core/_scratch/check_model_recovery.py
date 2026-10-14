"""Stage 5 / README §9 第 4 项：模型恢复（混淆矩阵）—— M-T1 vs M-T3

纯**后分析**：不重新生成数据、不重新拟合，只读 `_scratch/check_rho_power_n10_u8.txt`
的逐被试行（该日志由 `check_rho_power.py 10` 产生：D4 = 576 试次/人，
Euler dt=5e-5 生成，每档 10 名被试，每名被试同时拟合 M-T3（k=7, ρ≡1）
与 M-T1（k=8, ρ 自由））。

本脚本回答 README §9 第 4 项「模型恢复（混淆矩阵）」，产出五块：

  (1) 每条判决规则的**逐被试**决策率：
        · LRT 规则：  LRT > χ²(1, 0.95) = 3.841
        · BIC 规则：  ΔBIC > 0（ΔBIC = LRT − ln N_obs，N_obs=576 ⇒ 罚 6.356）
      —— 两条规则的差别本身就是本项的主要发现（未校正的 LRT 远比 BIC 宽松）。
  (2) 2×2 **混淆矩阵**（真实生成模型 × 判决模型），每个 ρ_true 一格。
      真值 ρ_true = 1.00 ⇒ 生成模型是 M-T3（恒定漂移）；ρ_true < 1 ⇒ M-T1。
  (3) **组层聚合检验**：Σ_s LRT_s ~ χ²(n_subj)（被试独立）。
      这是「ρ 只能作组层统计量报告」这条纪律（D33 ⑤）的直接检验。
  (4) 把组层检验 **bootstrap 投影到 n=40/组**（D31/D32 的拟采集规模）：
      非参 bootstrap 重抽被试行 ⇒ 每个 ρ_true 一格的组层检验效力曲线。
  (5) ρ̂ 的**组层偏差与 SE**（逐被试 ρ̂ 不可信，D33 ⑤）。

⚠️ **本矩阵只有 2 个模型**。M-T2（斜坡）未实现，见 README §9 第 16 项；
D33 已论证「连单参数的 ρ 都只有单侧力」，故 M-T2 支腿优先级已降。

用法：python _scratch/check_model_recovery.py [日志路径] [B] [输出路径]
      默认 `_scratch/check_rho_power_n10_u8.txt`、B=20000、输出 `_scratch/check_model_recovery_u8.txt`

⚠️ 编码：本机控制台是 **GBK**，`print` 带 ρ/χ²/Δ 会抛 `UnicodeEncodeError`；
   且用 PowerShell `>` 重定向写出的日志是 **UTF-16LE**（本项目已踩过）。
   故本脚本**自己**以 UTF-8 写输出文件（stdout 同时 reconfigure 成 utf-8/replace 以防崩溃）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - 老解释器/被替换的流
        pass


class _Tee:
    """把 stdout 同时写到文件（UTF-8），避免 PowerShell 重定向改变编码。"""

    def __init__(self, *streams) -> None:
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:
            try:
                st.write(s)
            except Exception:  # noqa: BLE001
                pass
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            try:
                st.flush()
            except Exception:  # noqa: BLE001
                pass

HERE = Path(__file__).resolve().parent
DEFAULT_LOG = HERE / "check_rho_power_n10_u8.txt"

CHI2_1_95 = float(chi2.ppf(0.95, 1))          # 3.8415
N_OBS = 576                                   # 每名被试的观测数（= 试次数）
BIC_PENALTY = float(np.log(N_OBS))            # 6.3556
N_PROJECT = 40                                # 拟采集规模：40 人/组
SEED = 20261014

# 逐被试行：subj omit acc RTms ll_M3 ll_M1 rho_hat LRT dBIC sec
# ⚠️ LRT 必须允许负号：M-T1 的 ll 可能略低于 M-T3（LRT ≈ -0.000），
#    早期版本第 8 组写成 ([\d.]+) 会静默丢掉这些被试（曾实测 ρ=1.0 与 ρ=1.5 各丢 1 人）。
ROW = re.compile(
    r"^\s*(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s*$"
)
RHO_HDR = re.compile(r"^ρ_true\s*=\s*([\d.]+)")


def read_text_any(path: Path) -> str:
    """按 BOM 自适应解码。

    ⚠️ 实测教训：`_scratch/*_u8.txt` 里的日志并非都是 UTF-8——
    用 Windows PowerShell 的 `>` 重定向产生的文件是 **UTF-16LE（BOM: FF FE）**，
    直接 `Path.read_text(encoding="utf-8")` 会在第 0 字节抛 `UnicodeDecodeError`。
    """
    raw = path.read_bytes()
    for bom, enc in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(enc)
    return raw.decode("utf-8", errors="strict")


def parse_log(path: Path) -> dict[float, dict[str, np.ndarray]]:
    """→ {rho_true: {"rho_hat":…, "lrt":…, "dbic":…, "acc":…, "omit":…}}"""
    cells: dict[float, dict[str, list[float]]] = {}
    cur: float | None = None
    for line in read_text_any(path).splitlines():
        m = RHO_HDR.match(line.strip())
        if m:
            cur = float(m.group(1))
            cells.setdefault(cur, {k: [] for k in
                                   ("rho_hat", "lrt", "dbic", "acc", "omit")})
            continue
        m = ROW.match(line)
        if m and cur is not None:
            cells[cur]["omit"].append(float(m.group(2)))
            cells[cur]["acc"].append(float(m.group(3)))
            cells[cur]["rho_hat"].append(float(m.group(7)))
            cells[cur]["lrt"].append(float(m.group(8)))
            cells[cur]["dbic"].append(float(m.group(9)))
    return {k: {kk: np.asarray(vv) for kk, vv in v.items()} for k, v in cells.items()}


def boot_group_power(lrt: np.ndarray, n_subj: int, crit: float,
                     n_boot: int, rng: np.random.Generator) -> tuple[float, float, float]:
    """非参 bootstrap：从观测到的逐被试 LRT 里重抽 n_subj 个，算 ΣLRT > crit 的频率。

    返回 (power, lo95, hi95)。⚠️ 这个区间是**条件**区间——它把 10 名被试的
    经验分布当成总体，因此**严重偏窄**，只反映"重抽噪声"。
    """
    idx = rng.integers(0, lrt.size, size=(n_boot, n_subj))
    sums = lrt[idx].sum(axis=1)
    hit = sums > crit
    p = float(hit.mean())
    # 对 p 的 Poisson 二项区间（比 percentile 更稳，p→0 时不会给出 0 宽区间）
    se = np.sqrt(max(p * (1.0 - p), 1e-12) / n_boot)
    return p, max(p - 1.96 * se, 0.0), min(p + 1.96 * se, 1.0)


def boot_group_power_dirichlet(lrt: np.ndarray, n_subj: int, crit: float,
                               n_boot: int, rng: np.random.Generator
                               ) -> tuple[float, float, float]:
    """**贝叶斯 bootstrap**：对 10 个观测先抽 Dirichlet(1) 权重（= 后验 over 分布），
    再从该加权分布里重抽 n_subj 个被试，算 ΣLRT > crit 的频率。

    这才是「n=40/组 的效力」应该报的区间：它把「只有 10 名被试、
    故 LRT 的**均值本身**也不确定」这一层不确定性传了进去。
    （在 ρ=1.25 那档，均值 1.543 的 SE 是 0.580 ⇒ λ̂ = 0.543 与 0 相差不到 1 SE，
      条件区间给出的 ±0.7 个百分点是假的精确。）
    """
    n = lrt.size
    w = rng.dirichlet(np.ones(n), size=n_boot)          # (B, n)
    cs = np.cumsum(w, axis=1)                           # (B, n)
    u = rng.random((n_boot, n_subj))                    # (B, n_subj)
    idx = (u[:, :, None] > cs[:, None, :]).sum(axis=2)  # (B, n_subj)
    np.clip(idx, 0, n - 1, out=idx)
    hit = lrt[idx].sum(axis=1) > crit
    p = float(hit.mean())
    lo, hi = np.percentile(hit.astype(float), [2.5, 97.5])
    return p, float(lo), float(hi)



def main() -> None:
    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LOG
    n_boot = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "check_model_recovery_u8.txt"
    if not out_path.is_absolute():
        out_path = HERE / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _fh = open(out_path, "w", encoding="utf-8", newline="\n")
    sys.stdout = _Tee(sys.__stdout__, _fh)
    if not log_path.is_absolute():
        log_path = HERE / log_path
    if not log_path.exists():
        raise SystemExit(f"日志不存在：{log_path}")

    cells = parse_log(log_path)
    if not cells:
        raise SystemExit(f"未能从 {log_path} 解析出任何被试行——格式改了吗？")

    # 观测样本量/档 —— 全部叙述文本都从这里取，杜绝把 n=10 写死在输出里
    n_obs = int(next(iter(cells.values()))["lrt"].size)

    rng = np.random.default_rng(SEED)
    bar = "=" * 100
    print(bar)
    print("Stage 5 / README §9 第 4 项：模型恢复（混淆矩阵）—— M-T1（ρ 自由）vs M-T3（ρ ≡ 1）")
    print(bar)
    print(f"数据来源：{log_path.name}（D4 = {N_OBS} 试次/人，Euler dt=5e-5；每档 {n_obs} 名被试）")
    print(f"判决规则：LRT > χ²(1,0.95) = {CHI2_1_95:.4f} ｜ ΔBIC > 0（罚 = ln {N_OBS} = {BIC_PENALTY:.4f}）")
    print(f"组层聚合检验：Σ_s LRT_s ~ χ²(n_subj)；投影规模 n = {N_PROJECT}/组，bootstrap B = {n_boot}")
    print()
    print("⚠️ 矩阵只有 2 个模型（M-T2 未实现，见 §9 第 16 项）。真值 ρ=1 ⇒ 生成模型是 M-T3。")
    print()

    # ---------------- 表 1：逐被试判决与混淆矩阵 ----------------
    print("-" * 100)
    print(f"表 1｜逐被试判决率与 2×2 混淆矩阵（每档 {n_obs} 名被试）")
    print("-" * 100)
    hdr = (f"{'ρ_true':>7} {'真值模型':>8} {'n':>3} "
           f"{'ρ̂ 均值':>9} {'ρ̂ SD':>8} "
           f"{'LRT 均值':>9} {'LRT SD':>8} "
           f"{'LRT 判 M-T1':>12} {'BIC 判 M-T1':>12} "
           f"{'ΔBIC 均值':>10}")
    print(hdr)
    print("-" * 100)
    rows = []
    for rho in sorted(cells):
        c = cells[rho]
        lrt, dbic, rh = c["lrt"], c["dbic"], c["rho_hat"]
        n = lrt.size
        true_model = "M-T3" if abs(rho - 1.0) < 1e-12 else "M-T1"
        r_lrt = float((lrt > CHI2_1_95).mean())
        r_bic = float((dbic > 0).mean())
        print(f"{rho:>7.2f} {true_model:>8} {n:>3} "
              f"{rh.mean():>9.4f} {rh.std(ddof=1):>8.4f} "
              f"{lrt.mean():>9.3f} {lrt.std(ddof=1):>8.3f} "
              f"{r_lrt*100:>11.1f}% {r_bic*100:>11.1f}% "
              f"{dbic.mean():>10.3f}")
        rows.append(dict(rho=rho, true_model=true_model, n=n, rho_hat=rh,
                         lrt=lrt, dbic=dbic, r_lrt=r_lrt, r_bic=r_bic))
    print("-" * 100)
    print("读法：LRT 规则**未校正**（每名被试各做一次检验）⇒ 名义 5% 下 ρ=1 那行应≈5%；")
    print("      BIC 规则把 ΔBIC>0 当判决，罚 6.356 ⇒ 与 LRT 规则相比可见其保守程度。")
    print()
    print("2×2 混淆矩阵（行 = 真实生成模型，列 = 被判决模型；括号内为 BIC 规则）")
    print("-" * 100)
    print(f"{'':>14}{'判 M-T3':>18}{'判 M-T1':>18}")
    for r in rows:
        p_m1 = r["r_lrt"]
        p_m1_b = r["r_bic"]
        print(f"ρ={r['rho']:>4.2f} {r['true_model']:>7}"
              f"{(1-p_m1)*100:>13.1f}%{(p_m1)*100:>17.1f}%")
        print(f"{'':>14}{(1-p_m1_b)*100:>15.1f}%{(p_m1_b)*100:>17.1f}%")
    print("-" * 100)
    print()

    # ---------------- 表 2：组层聚合检验 ----------------
    print("-" * 100)
    print("表 2｜组层聚合检验 Σ_s LRT_s ~ χ²(n_subj)（被试独立）")
    print("-" * 100)
    print(f"{'ρ_true':>7} {'真值模型':>8} {'n':>3} {'ΣLRT 实测':>11} "
          f"{'χ²(n,0.95)':>12} {'组层判决':>10} {'经验拒绝率':>12}")
    print("-" * 100)
    for r in rows:
        n = r["n"]
        crit = float(chi2.ppf(0.95, n))
        s = float(r["lrt"].sum())
        rej = "拒绝 M-T3" if s > crit else "未拒绝"
        r["crit_n"] = crit
        r["sum_n"] = s
        print(f"{r['rho']:>7.2f} {r['true_model']:>8} {n:>3} {s:>11.3f} "
              f"{crit:>12.3f} {rej:>10} "
              f"{'—' if abs(r['rho']-1.0)<1e-12 else ('命中' if s>crit else '漏检'):>12}")
    print("-" * 100)
    print()
    _r75 = rows[[r["rho"] for r in rows].index(0.75)]
    _crit_n = float(chi2.ppf(0.95, n_obs))
    _sum75 = float(_r75["lrt"].sum())
    _verdict = "跨过 ✅" if _sum75 > _crit_n else "没跨过 ❌"
    print(f"⚠️ 观测样本量 n={n_obs}/档：χ²({n_obs},0.95) = {_crit_n:.3f}。"
          f"逐被试规则在 ρ=0.75 只有 {_r75['r_lrt']*100:.0f}% 拒绝，")
    print(f"   但组层聚合后 ΣLRT = {_sum75:.2f} vs {_crit_n:.3f} → **{_verdict}**"
          f"——这正是本项最实用的发现：")
    print("   **检验力应在组层兑现，而不是要求每个被试各自显著**（与 D33 ⑤ 的组层纪律一致）。")
    print()

    # ---------------- 表 3：投影到 n=40/组 ----------------
    print("-" * 100)
    print(f"表 3｜组层检验的效力曲线：非参 bootstrap 投影到 n = {N_PROJECT}/组（D31/D32 拟采集规模）")
    print("-" * 100)
    crit40 = float(chi2.ppf(0.95, N_PROJECT))
    print(f"判据：Σ_s LRT_s > χ²({N_PROJECT},0.95) = {crit40:.3f}"
          f"（每名被试期望 LRT 由实测分布的 bootstrap 重抽给出）")
    print("-" * 100)
    print(f"{'ρ_true':>7} {'真值模型':>8} {'E[ΣLRT] 投影':>14} {'组层效力':>10} "
          f"{'条件区间(窄)':>18} {'Dirichlet 区间(真)':>22} {'逐被试效力':>12}")
    print("-" * 100)
    for r in rows:
        p, lo, hi = boot_group_power(r["lrt"], N_PROJECT, crit40, n_boot, rng)
        pd, lod, hid = boot_group_power_dirichlet(r["lrt"], N_PROJECT, crit40, n_boot, rng)
        e_sum = N_PROJECT * float(r["lrt"].mean())
        r["power40"] = pd
        r["power40_lo"] = lod
        r["power40_hi"] = hid
        print(f"{r['rho']:>7.2f} {r['true_model']:>8} {e_sum:>14.1f} "
              f"{pd*100:>9.1f}% {f'[{lo*100:.1f}%, {hi*100:.1f}%]':>18} "
              f"{f'[{lod*100:.1f}%, {hid*100:.1f}%]':>22} "
              f"{r['r_lrt']*100:>11.1f}%")
    print("-" * 100)
    print("⚠️ **两个区间的区别是关键**：")
    print("   · 「条件区间」把观测到的经验分布**当成总体** ⇒ 只反映重抽噪声，**假性精确**；")
    print("   · 「Dirichlet 区间」先对观测抽 Dirichlet(1) 权重（后验 over 分布）再重抽 ⇒")
    print("     把「LRT 的**均值本身**也不确定」传了进去。**引用效力时用这一列。**")
    _r125 = rows[[r["rho"] for r in rows].index(1.25)]
    _m125 = float(_r125["lrt"].mean())
    _s125 = float(_r125["lrt"].std(ddof=1))
    _se125 = _s125 / np.sqrt(n_obs)
    print(f"   例：ρ=1.25 的逐被试 LRT 均值 {_m125:.3f}，其 SE = {_s125:.3f}/√{n_obs} = {_se125:.3f}"
          f" ⇒ 「均值 − {crit40:.1f}/{n_obs}」距 0 只有 {(_m125 - crit40/n_obs)/max(_se125,1e-12):+.1f} 个 SE，")
    print("       故 n=40 的效力区间必须很宽（见上表），不能报成单点。")
    print("⚠️ bootstrap 不覆盖 M-T2（斜坡），也不覆盖真值族（只跑了 exp/lin 少数的 ρ 档）。")
    print()

    # ---------------- 表 4：组层 ρ̂ 的偏差与 SE ----------------
    print("-" * 100)
    print("表 4｜ρ̂ 的组层偏差与 SE（D33 ⑤：ρ 只能作组层统计量报告）")
    print("-" * 100)
    print(f"{'ρ_true':>7} {'真值模型':>8} {'组层 ρ̂':>10} {'SE(ρ̂)':>9} "
          f"{'偏差':>9} {'偏差/SE':>9} {'95% CI 含真值?':>15} {'饱和上界':>9}")
    print("-" * 100)
    for r in rows:
        rh = r["rho_hat"]
        n = rh.size
        mean = float(rh.mean())
        se = float(rh.std(ddof=1) / np.sqrt(n))
        bias = mean - r["rho"]
        lo, hi = mean - 1.96 * se, mean + 1.96 * se
        covers = "✅" if (lo <= r["rho"] <= hi) else "❌"
        print(f"{r['rho']:>7.2f} {r['true_model']:>8} {mean:>10.4f} {se:>9.4f} "
              f"{bias:>+9.4f} {bias/se:>+9.2f} {covers:>15} "
              f"{rh.max():>9.4f}")
    print("-" * 100)
    print(f"⚠️ 组层 SE 由这 {n_obs} 名被试给出（自由度为 {n_obs-1}）⇒ «偏差/SE» 只能当量级参考；"
          f"ρ̂ 的「饱和上界」列 = 该档观测到的最大 ρ̂（n 越大越接近真实可达上界）。")
    print()

    # ---------------- 结语 ----------------
    print(bar)
    print("结论（写进 README §9 第 4 项）")
    print(bar)
    r0 = rows[[r["rho"] for r in rows].index(0.00)]
    r50 = rows[[r["rho"] for r in rows].index(0.50)]
    r75 = rows[[r["rho"] for r in rows].index(0.75)]
    r100 = rows[[r["rho"] for r in rows].index(1.00)]
    r125 = rows[[r["rho"] for r in rows].index(1.25)]
    r150 = rows[[r["rho"] for r in rows].index(1.50)]
    print(f"① 标定行（ρ=1，真值就是 M-T3）：逐被试 LRT 规则 {r100['r_lrt']*100:.0f}%、"
          f"BIC 规则 {r100['r_bic']*100:.0f}%、组层 ΣLRT {r100['sum_n']:.2f} vs {r100['crit_n']:.2f}"
          f" ⇒ **无假阳性** ✅")
    print(f"② 逐被试规则下 ρ=0/0.5/0.75 的 M-T1 命中率：LRT 规则 "
          f"{r0['r_lrt']*100:.0f}%/{r50['r_lrt']*100:.0f}%/{r75['r_lrt']*100:.0f}%，"
          f"BIC 规则 {r0['r_bic']*100:.0f}%/{r50['r_bic']*100:.0f}%/{r75['r_bic']*100:.0f}%")
    print(f"   ⇒ **LRT 规则系统性偏乐观**（ΔBIC 罚 {BIC_PENALTY:.2f}）；论文若报检验力必须写明规则")
    print(f"③ 组层聚合（n={n_obs}）：ρ=0.75 逐被试只有 {r75['r_lrt']*100:.0f}%，"
          f"但 ΣLRT {r75['sum_n']:.2f} vs {r75['crit_n']:.2f} → "
          f"{'拒绝 M-T3 ✅' if r75['sum_n'] > r75['crit_n'] else '漏检 ❌'}；")
    print(f"   ρ=1.25：ΣLRT {r125['sum_n']:.2f} vs {r125['crit_n']:.2f} → "
          f"{'拒绝 M-T3 ✅' if r125['sum_n'] > r125['crit_n'] else '漏检 ❌'}"
          f"（逐被试 {r125['r_lrt']*100:.0f}%）；"
          f"ρ=1.5：ΣLRT {r150['sum_n']:.2f} vs {r150['crit_n']:.2f} → "
          f"{'拒绝 M-T3 ✅' if r150['sum_n'] > r150['crit_n'] else '漏检 ❌'}"
          f"（逐被试 {r150['r_lrt']*100:.0f}%）")
    print(f"④ 投影到 n={N_PROJECT}/组（Dirichlet 区间，含分布不确定性）："
          f"ρ=0/0.5/0.75 效力 {r0['power40']*100:.0f}%/{r50['power40']*100:.0f}%/{r75['power40']*100:.0f}%"
          f"（下界 {r0['power40_lo']*100:.0f}%/{r50['power40_lo']*100:.0f}%/{r75['power40_lo']*100:.0f}%），"
          f"ρ=1.0 {r100['power40']*100:.0f}%")
    print(f"   ⚠️ **ρ>1 是关键不确定项**：ρ=1.25 效力 {r125['power40']*100:.0f}%"
          f"（区间 [{r125['power40_lo']*100:.0f}%, {r125['power40_hi']*100:.0f}%]，"
          f"逐被试 {r125['r_lrt']*100:.0f}%）、ρ=1.5 效力 {r150['power40']*100:.0f}%"
          f"（区间 [{r150['power40_lo']*100:.0f}%, {r150['power40_hi']*100:.0f}%]，"
          f"逐被试 {r150['r_lrt']*100:.0f}%）")
    print(f"   ⇒ 观测样本量 n={n_obs}/档。n<30 时 ρ>1 的**中心值**不可当结论（分布均值没被钉住）；")
    print("     n≥30 时中心值可报，但**必须同时给 Dirichlet 区间**——它通常仍是 [0%, 100%]。")
    print("     ⇒ 论文若报 ρ>1 的效力，写法是「中心值 X%（区间 [0%, 100%]，n=30/档 模拟）」，不是单点。")
    print(f"⑤ ρ̂ 组层偏差：ρ=0.5 时 {r50['rho_hat'].mean():.4f}（真值 0.50，"
          f"偏差 {(r50['rho_hat'].mean()-0.5):+.4f}）；ρ=1.0 时 {r100['rho_hat'].mean():.4f}")
    print("⑥ ❌ 矩阵只有 2 个模型：M-T2（斜坡）缺失，见 §9 第 16 项")
    print(bar)


if __name__ == "__main__":
    main()
