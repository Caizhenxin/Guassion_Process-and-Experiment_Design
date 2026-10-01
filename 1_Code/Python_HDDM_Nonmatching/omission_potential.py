# -*- coding: utf-8 -*-
"""阶段 1 · 步骤 2+3：把遗漏似然项挂到 HDDM 的 pymc2 模型上

    logL = Σ_观测试次 log f_Wiener(rt_i | θ_格子)  +  Σ_格子 n_遗漏(格子) · log P_遗漏(θ_格子, deadline)

接口契约（规格文档 §4.5.6，C1–C8）
=================================
* **C1 逐格**：每 `(被试 × 身份 × 条件)` 单元格各算一个 `P_遗漏`，乘各自的遗漏数
* **C2 口径**：`a` = 分离度；`z` 用 Φ 从 `z_trans` 还原；`t0` 即 HDDM 的 `t`
* **C3**：`deadline = T + W`，与 `t0` 同一时间原点（刺激起点）
* **C4**：取 log 前 clip
* **C5**：遗漏判定不受 `T+200` 窗口门控影响（门控只改 RT 似然，不改遗漏）
* **C7**：`p_outlier` 必须为 0（否则与遗漏项双重计入）
* **C8**：在 HDDM 上加 `Potential`，而不是用 PyMC 重写 Wiener 似然

实现要点（都是踩过的坑）
=====================
1. **父节点不用自己拼**：HDDM 的观测节点名就是 `wfpt(cell.identity).subj`，其 `parents`
   里**恰好**是该格的 `(v, a, z, t)`——
       v → `v_subj(identity).s`（Normal）
       a → `a_subj.s`（Gamma，同理 t）
       z → `z_subj(cell).s`（Deterministic = Φ(z_subj_trans(cell).s)）
   直接复用这些节点即同时满足 C1 与 C2，不必还原层级先验，也不会写错标度。

2. **一个 Potential 挂全部格子**，而不是每格一个。pymc2 的 logp 是纯 Python 调用，
   逐格建会调用次数放大 O(格子数) 倍，采样直接被拖死。

3. **势函数必须与节点一起交给 `pm.MCMC`**（2026-10-01 spike 实测）：
   HDDM 的 `mc` 在 `model.mcmc()` 里创建，`pre_sample()` 会**就地**给每个随机节点
   分配 `SliceStep`。事后追加势函数拿不到正确的计算集，所以这里自己建 MCMC 再 `pre_sample()`。
   `SliceStep` 无梯度 → 兼容不可导的解析式（C6）。

4. **不要交给 kabuki 的多链路径**：`kabuki.sample(chains>1)` 会对每个链 `deepcopy(self)`
   再 `hddm.mcmc(...)`，那会用 `nodes_db` 重建 mc，**把势函数丢掉**。多链要自己在外层循环建。
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pymc as pm

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from omission_likelihood import omission_logp, p_omission  # noqa: E402

# HDDM 观测节点名：wfpt(cell.identity).subj
_WFPT_RE = re.compile(r"^wfpt\((\d+)\.(\d+)\)\.(\d+)$")


def build_omission_terms(model, omission_df, verbose=True):
    """按模型的观测格子，收集逐格的父节点 / 遗漏数。

    参数
    ----
    model : hddm.HDDM —— 已构建（`nodes_db` 可用）但尚未 `mcmc()` 的模型
    omission_df : DataFrame —— `hddm_omission_*.csv`，需含 subj_idx / cell 两列

    返回 (parents, plan, n_omission, info)
      parents : {安全键名: pymc 节点}
      plan    : [(cell, subj, key_v, key_a, key_z, key_t), ...]
      n_omission : np.ndarray，与 plan 等长
      info    : 覆盖情况与告警
    """
    obs = model.nodes_db[model.nodes_db["observed"]]
    counts = {}
    for (cell, subj), n in omission_df.groupby(["cell", "subj_idx"]).size().items():
        counts[(int(cell), int(subj))] = int(n)

    model_cells, parents, plan, n_om, uncovered = set(), {}, [], [], []
    for key, row in obs.iterrows():
        m = _WFPT_RE.match(str(key))
        if not m:
            continue
        cell, ident, subj = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        model_cells.add((cell, subj))
        n_cs = counts.get((cell, subj), 0)
        if n_cs == 0:                      # 该格没有遗漏 → 不进入似然，省掉父节点
            continue
        par = row["node"].parents
        k_v, k_a = f"v_i{ident}_s{subj}", f"a_s{subj}"
        k_z, k_t = f"z_c{cell}_s{subj}", f"t_s{subj}"
        parents[k_v], parents[k_a] = par["v"], par["a"]
        parents[k_z], parents[k_t] = par["z"], par["t"]
        plan.append((cell, subj, k_v, k_a, k_z, k_t))
        n_om.append(n_cs)

    for (cell, subj), n in counts.items():
        if (cell, subj) not in model_cells:
            uncovered.append(((cell, subj), n))

    info = {"n_cells_in_likelihood": len(plan), "n_omission_used": int(np.sum(n_om)),
            "n_omission_file": int(len(omission_df)),
            "n_omission_uncovered": int(sum(n for _, n in uncovered)),
            "uncovered_cells": uncovered, "n_parents": len(parents),
            "n_model_cells": len(model_cells),
            "plan": plan, "n_omission": n_om}
    if verbose:
        print(f"  遗漏项：进入似然 {len(plan)} 个格子、{info['n_omission_used']} 个遗漏试次"
              f"（文件共 {info['n_omission_file']}）| 父节点 {len(parents)} 个")
        if uncovered:
            print(f"  ⚠️ 有 {len(uncovered)} 个格子在遗漏文件里、但模型没有对应观测节点"
                  f"（共 {info['n_omission_uncovered']} 试次），未计入似然：{uncovered[:5]}")
    return parents, plan, np.asarray(n_om, dtype=float), info


def make_omission_logp(plan, n_omission, deadline):
    """构造 pymc2 的 logp 函数（`**kwargs` 接全部父节点值）。"""
    idx_v = [p[2] for p in plan]
    idx_a = [p[3] for p in plan]
    idx_z = [p[4] for p in plan]
    idx_t = [p[5] for p in plan]

    def _logp(**kw):
        if not idx_v:
            return 0.0
        v = np.fromiter((kw[k] for k in idx_v), dtype=float, count=len(idx_v))
        a = np.fromiter((kw[k] for k in idx_a), dtype=float, count=len(idx_a))
        z = np.fromiter((kw[k] for k in idx_z), dtype=float, count=len(idx_z))
        t = np.fromiter((kw[k] for k in idx_t), dtype=float, count=len(idx_t))
        return omission_logp(n_omission, p_omission(v, a, z, t, deadline))

    return _logp


def attach_omission_potential(model, omission_df, deadline, name="omission_logp",
                              db="ram", dbname="tmp.db", verbose=True):
    """在 HDDM 模型上挂遗漏势函数，并把 `model.mc` 建好（含步进器）。

    返回 info dict（含 potential 对象，便于事后自检）。
    """
    parents, plan, n_om, info = build_omission_terms(model, omission_df, verbose=verbose)
    logp = make_omission_logp(plan, n_om, deadline)
    pot = pm.Potential(logp=logp,
                       doc="遗漏项 Σ_格子 n_遗漏·log P(遗漏|θ_格子)，deadline=%.3f" % deadline,
                       name=name, parents=parents, cache_depth=2, verbose=0)

    nodes = list(model.nodes_db.node.values) + [pot]
    model.mc = pm.MCMC(nodes, db=db, dbname=dbname)
    model.pre_sample()

    if verbose:
        print(f"  已挂势函数 '{name}'：mc.nodes = {len(model.mc.nodes)}"
              f"（HDDM 节点 {len(nodes) - 1} + 势函数 1）| 初值 logp = {pot.logp:.4f}")
    info.update({"potential": pot, "logp_initial": float(pot.logp),
                 "deadline": float(deadline), "name": name,
                 "parents": parents, "plan": plan})
    return info


def validate_wiring(model, omission_df, info, deadline, verbose=True):
    """自检：独立重算每格 (v, a, z, t) 与 P(遗漏)，与势函数的父节点取值逐格对账。

    这不是重复劳动——它专门抓"父节点接错格子/接错标度"这类**静默错误**：
    p_omission 本身已由 `omission_likelihood.py` 的自检单独验证过，
    这里只验证"接线"。
    """
    obs = model.nodes_db[model.nodes_db["observed"]]
    node_by_key = {}
    for key, row in obs.iterrows():
        m = _WFPT_RE.match(str(key))
        if m:
            node_by_key[(int(m.group(1)), int(m.group(3)))] = row["node"]

    parents = info["parents"]
    bad = []
    rows = []
    for (cell, subj, k_v, k_a, k_z, k_t), n in zip(info["plan"], info["n_omission"]):
        node = node_by_key.get((cell, subj))
        if node is None:
            bad.append(f"格子({cell},{subj}) 无观测节点")
            continue
        par = node.parents
        pairs = [(k_v, par["v"], "v"), (k_a, par["a"], "a"),
                 (k_z, par["z"], "z"), (k_t, par["t"], "t")]
        for k, expected, kind in pairs:
            got = parents.get(k)
            if got is not expected:
                bad.append(f"格子({cell},{subj}) 的 {kind}: 势函数接了 "
                           f"{getattr(got, '__name__', got)}，观测节点用的是 {expected.__name__}")
        v = float(par["v"].value)
        a = float(par["a"].value)
        z = float(par["z"].value)
        t = float(par["t"].value)
        rows.append({"cell": cell, "subj": subj, "n_omission": n, "v": v, "a": a, "z": z,
                     "t": t, "p_omission": float(p_omission(v, a, z, t, deadline))})

    df = pd.DataFrame(rows)
    n_ok = len(df) and bool(np.all((df["a"] > 0) & (df["z"] > 0) & (df["z"] < 1) & (df["t"] >= 0)))
    # 端到端对账：pymc 走的 logp vs 用节点取值独立重算的 logp（抓父节点值接错/漏接）
    logp_direct = (omission_logp(df["n_omission"].to_numpy(float),
                                 df["p_omission"].to_numpy(float)) if len(df) else 0.0)
    logp_pymc = float(info["logp_initial"])
    gap = abs(logp_direct - logp_pymc)
    if verbose:
        print(f"  接线自检：对账 {len(df)} 个格子 | 结构错误 {len(bad)} 条 | "
              f"取值域正常（a>0, 0<z<1, t≥0）: {n_ok}")
        print(f"    logp 对账：pymc = {logp_pymc:.6f} | 直接重算 = {logp_direct:.6f} "
              f"| 差 = {gap:.2e}")
        if len(df):
            print(f"    起始参数下 P(遗漏) 区间 = [{df['p_omission'].min():.4f}, "
                  f"{df['p_omission'].max():.4f}]，均值 {df['p_omission'].mean():.4f}")
        for b in bad[:5]:
            print("    ❌", b)
    return (len(bad) == 0) and (gap < 1e-6), df


# ------------------------------------------------------------------
# CLI：接线自检（默认不采样）
# ------------------------------------------------------------------
def _load_group(gid):
    base = _THIS_DIR.parents[1] / "2_Data" / "Real_Data" / "HDDM_Ready_Nonmatching"
    main_f = next(base.glob(f"hddm_data_group{gid}_*.csv"), None)
    omit_f = next(base.glob(f"hddm_omission_group{gid}_*.csv"), None)
    if main_f is None or omit_f is None:
        raise SystemExit(f"未找到 group{gid} 的数据：{base}")
    return pd.read_csv(main_f), pd.read_csv(omit_f), main_f


def main():
    import argparse
    import warnings

    import hddm

    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description="遗漏势函数接线自检")
    ap.add_argument("--group", type=int, default=1)
    ap.add_argument("--draws", type=int, default=0, help=">0 时额外微采样，验证采样器可用")
    args = ap.parse_args()

    data, omit, path = _load_group(args.group)
    print(f"数据：{path.name} | 有效试次 {len(data)} | 遗漏试次 {len(omit)}")
    print("观测到的遗漏率（按格）：")
    tot = data.groupby("cell").size().rename("有效")
    om = omit.groupby("cell").size().rename("遗漏")
    grid = pd.concat([tot, om], axis=1).fillna(0)
    grid["遗漏率"] = grid["遗漏"] / (grid["有效"] + grid["遗漏"])
    print(grid.T.to_string())

    model = hddm.HDDM(data, depends_on={"v": "identity", "z": "cell"},
                      include=["v", "a", "t", "z"], bias=False, p_outlier=0.0)
    deadline = float(data["deadline"].iloc[0])
    info = attach_omission_potential(model, omit, deadline)
    ok, df = validate_wiring(model, omit, info, deadline)
    print(f"接线自检：{'✅ 通过' if ok else '❌ 未通过'}")

    if args.draws > 0:
        t0 = info["potential"].logp
        model.sample(args.draws, burn=max(1, args.draws // 3))
        t1 = info["potential"].logp
        print(f"微采样 {args.draws} 步完成：势函数 logp {t0:.4f} → {t1:.4f}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
