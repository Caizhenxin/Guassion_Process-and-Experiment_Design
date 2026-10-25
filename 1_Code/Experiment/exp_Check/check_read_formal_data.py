"""`read_formal_data.py` 的自测 —— 正向要放行、负向要报错。

为什么值得单独测
================
`read_formal_data.py` 干的事是**把按键/标签翻译成因子**。这类映射最危险的地方
在于：写错了不会抛异常，只会把 `is_match` 悄悄反过来，于是整条 Stage 8 的
模型比较都建在错的签上，而且每一份下游报告都自洽。所以这里既要测"对的能过"，
也要逐条测"错的会被抓住"——**每一条守卫都必须有它自己的触发样例**。

跑法
====
    python 1_Code/Experiment/exp_Check/check_read_formal_data.py
    python ... --keep            # 保留临时目录，便于人工翻看

退出码：0 = 全部通过；1 = 有未通过项。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # 1_Code/Experiment/exp_Check
EXP_DIR = HERE.parent                            # 1_Code/Experiment
REPO = EXP_DIR.parent.parent                     # 仓库根
MAKER = REPO / "1_Code" / "DDM_Core" / "_scratch" / "make_fake_pilot.py"

sys.path.insert(0, str(EXP_DIR))
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
import read_formal_data as R  # noqa: E402
import mapping as M  # noqa: E402
import wfpt as W  # noqa: E402

#: 密度"远未下溢"的门槛。双精度最小次正规数 ≈ 5e−324，取 1e−300 留 24 个数量级。
#:
#: ⚠️ 2026-10-14 起，`wfpt.flux` 的**抵消地板**（≈ kmax·eps ≈ 8.7e−15，来源
#: `1_Code/DDM_Core/_scratch/_probe_flux_floor.py`）**不再是** `t0` 余量的依据：
#: `flux` 现在按 t 在正弦级数与**镜像级数**之间派发，小 t 一侧给出正确的小正数
#: （`1_Code/DDM_Core/_scratch/check_flux_smallt.py` 6/6：V3 与闭式吸收概率差
#: 1.3e−15、V4 数值积分差 8.8e−16、V5 测出**旧实现在小 t 侧最差偏 2.2e+34 倍**）。
#: 剩下唯一会触发 `np.any(f <= 0)` 的机制是 exp 的**下溢**。
UNDERFLOW_FLOOR = 1e-300

_N_PASS = 0
_N_FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _N_PASS, _N_FAIL
    if ok:
        _N_PASS += 1
        print(f"  ✅ {name}" + (f"：{detail}" if detail else ""))
    else:
        _N_FAIL += 1
        print(f"  ❌ {name}" + (f"：{detail}" if detail else ""))


def gen(outdir: Path, *extra: str, n_subjects: int = 1) -> None:
    """调合成数据生成器造一份 v4.1 格式的输出。"""
    cmd = [sys.executable, str(MAKER), str(outdir),
           "--n-subjects", str(n_subjects), "--group", "1", "--seed", "7", *extra]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"生成失败：{r.stdout}\n{r.stderr}")


def load_one(outdir: Path, subject: int = 1):
    p = outdir / f"exp_group1_subject{subject}.txt"
    rec, _ = R.load_file(p)
    return rec, R.to_trials(rec)


# ------------------------------------------------------------------
# A 组：正向 —— 一致的数据必须一路放行，且翻译结果就是模型要的那张表
# ------------------------------------------------------------------
def case_a(tmp: Path) -> None:
    print("\n[A] 正向：一致的 v4.1 数据必须通过，且翻译成模型能吃的表")
    out = tmp / "a"
    gen(out, n_subjects=2)
    rec1, tr1 = load_one(out, 1)

    # A1 主判据：validate 必须返回空清单
    bad = R.validate(rec1, tr1)
    check("A1 一致数据的 validate 返回空清单", bad == [], str(bad))

    # A2 因子结构：576 试次，4 T × 3 W，每 (T,W,Self,Match) 格 12 次、(Self,Match) 格 144 次
    n = tr1["rt"].size
    n_t = np.unique(np.round(tr1["T"], 5)).size
    n_w = np.unique(np.round(tr1["W"], 5)).size
    cells = {}
    for s in (0.0, 1.0):
        for m in (0, 1):
            cells[(s, m)] = int(np.sum((tr1["is_self"] == s) & (tr1["is_match"] == m)))
    check("A2 正式段取到 576 试次、T 4 档、W 3 档",
          n == 576 and n_t == 4 and n_w == 3, f"n={n}, T={n_t} 档, W={n_w} 档")
    # ⚠️ 最细格是 (T,W,Self,Match)=12，不是 48：W 按 block 变，(T,W) 才是 48
    finer = len({(round(float(t), 5), round(float(w), 5), int(s), int(m))
                 for t, w, s, m in zip(tr1["T"], tr1["W"], tr1["is_self"], tr1["is_match"])})
    check("A3 (T,W,Self,Match) 恰 48 个格子、每格 12 次",
          finer == 48 and n == 48 * 12, f"{finer} 格 × {n / finer:g} 次")
    check("A4 四个 (Self,Match) 单元各 144 次",
          set(cells.values()) == {144}, str(cells))

    # A5 最强自检：程序记的 Correct == (side == is_match)，且由此能反推出侧别
    resp = ~tr1["omission"].astype(bool)
    ok_correct = np.all(rec1["Correct"][resp] == (tr1["side"][resp] == tr1["is_match"][resp]))
    check("A5 Correct == (side == is_match)（已响应试次）", bool(ok_correct))

    # A6 未响应试次：rt 必须是 NaN，且 omission 与 Response=='NA' 一致
    om = tr1["omission"].astype(bool)
    check("A6 未响应试次的 rt 全为 NaN、omission 一致",
          bool(np.all(~np.isfinite(tr1["rt"][om])) and np.array_equal(om, rec1["Response"] == "")),
          f"未响应 {int(om.sum())} 次")

    # A7 跨模块接口：翻译结果必须与 DDM_Core 的 trials_from_arrays 逐键逐 dtype 相等
    sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
    try:
        import likelihood as L  # noqa: E402
        ref = L.trials_from_arrays(
            tr1["rt"], tr1["side"], tr1["omission"], tr1["P"], tr1["T"], tr1["W"],
            tr1["is_self"], tr1["is_match"])
        diffs = [k for k in ref
                 if ref[k].dtype != tr1[k].dtype or not np.array_equal(
                     ref[k], tr1[k], equal_nan=True)]
        check("A7 to_trials 与 likelihood.trials_from_arrays 逐键逐 dtype 相等",
              not diffs, f"不一致的键：{diffs}" if diffs else "8 个键全等")
    except ImportError as e:  # pragma: no cover
        check("A7 跨模块接口可比", False, f"导入 likelihood 失败：{e}")

    # A8 似然真的能算。⚠️ 这里必须分两侧测，因为合起来测会掩盖一条硬约束：
    #    `likelihood.per_trial_loglik` 里 `t = rt − t0` 之后紧跟
    #    `if np.any(t <= 0): return None` —— **一条** rt ≤ t0 的已响应试次
    #    就让**整份**数据返回 None。而合成数据里本来就有 ~3% 的预期性抢按
    #    （RT 低到 ~16 ms），所以原表必然算不出来，必须先剔除。
    try:
        import likelihood as L  # noqa: E402
        p = L.MappingParams(shape_model="lin")

        # A8a 原表：必须返回 None（约束存在，不是我们以为它能算）
        raw = L.per_trial_loglik(p, tr1)
        n_below = int(np.sum((~tr1["omission"].astype(bool))
                             & (tr1["rt"] < p.t0)))
        check("A8a 未剔除抢按的原表：per_trial_loglik 返回 None（约束为真）",
              raw is None and n_below > 0,
              f"rt < t0(={p.t0}) 的已响应试次 {n_below} 条 ⇒ 整份数据 None")

        # A8b fit_ready 之后再算：必须逐条有限
        tr_fit, rep_fit = R.fit_ready(tr1)
        ll = L.per_trial_loglik(p, tr_fit)
        finite = (ll is not None) and bool(np.all(np.isfinite(np.asarray(ll, dtype=float))))
        check("A8b 剔除抢按后 per_trial_loglik 逐条有限",
              bool(finite), f"保留 {tr_fit['rt'].size} 试次、"
              f"最小 RT {np.nanmin(tr_fit['rt']) * 1000:.1f} ms")
        check("A8c fit_ready 剔掉的抢按数 = 已响应且 rt < RT_FLOOR 的条数",
              rep_fit["n_dropped_slow"] == int(np.sum((~tr1["omission"].astype(bool))
                                                      & (tr1["rt"] < R.RT_FLOOR))),
              f"fit_ready 剔抢按 {rep_fit['n_dropped_slow']}、"
              f"直接数 {int(np.sum((~tr1['omission'].astype(bool)) & (tr1['rt'] < R.RT_FLOOR)))}")
        # D123 新增：不传 rec 时「刺激期内按键」这条必须完全不生效（向后兼容）
        check("A8c2 不传 rec ⇒ 刺激期内按键剔除数为 0（向后兼容）",
              rep_fit["n_dropped_dev"] == 0,
              f"n_dropped_dev = {rep_fit['n_dropped_dev']}")
        check("A8d fit_ready 保留全部未响应试次（它们走 survival 不受 t>0 约束）",
              int(np.sum(tr_fit["omission"].astype(bool)))
              == int(np.sum(tr1["omission"].astype(bool))),
              f"未响应 {int(np.sum(tr_fit['omission'].astype(bool)))} 条不变")

        # A12–A15 「可行域内没有 cliff」——这道守卫的**前提在 2026-10-14 变了**。
        #     旧前提：`wfpt.flux` 只有正弦级数一条分支，t 小时真值落进相消地板、
        #             符号是噪声，`np.any(f <= 0)` 于是把**整份**数据判成 None，
        #             所以 t0 的上界必须停在"真值离开噪声地板"处。
        #     新前提：`flux` 按 t 在正弦级数与**镜像级数**之间派发，小 t 一侧是
        #             正确的小正数（`_scratch/check_flux_smallt.py`：V3 差 1.3e-15、
        #             V4 差 8.8e-16、V5 旧实现最差偏 2.2e+34）。于是 t0 余量只剩
        #             两条依据：闸门 1 要求 t > 0 **严格**成立；密度不能下溢成 0。
        tb = R.t0_bounds(tr_fit)
        hi = float(tb["t0"][1])
        p_hi = L.MappingParams(shape_model="lin", t0=hi)
        ll_hi = L.per_trial_loglik(p_hi, tr_fit)
        finite_hi = (ll_hi is not None) and bool(
            np.all(np.isfinite(np.asarray(ll_hi, dtype=float))))
        check("A12 用 t0_bounds 的上界取 t0 时似然仍有限（可行域内无 cliff）",
              finite_hi,
              f"t0 上界 = {hi:.4f}（= 最小 RT − {R.T0_SAFE_MARGIN}）")

        resp_m = ~tr_fit["omission"].astype(bool)
        f_used = (np.exp(np.asarray(ll_hi, dtype=float))[resp_m]
                  if finite_hi else np.array([np.nan]))
        f_min = float(np.min(f_used)) if f_used.size else float("nan")

        # A13 闸门 2 现在只剩**下溢**一种触发方式 ⇒ 上界处**实际被用到**的最小密度
        #     必须是**正的、可表示的**。注意不是"大于某个抵消地板"：`np.any(f <= 0)`
        #     对**恰好 0** 也触发，而下溢正是给出恰好 0，所以门槛按表示范围定。
        check("A13 上界处最小「被用到的密度」为正且远离下溢（> 1e-300）",
              finite_hi and np.isfinite(f_min) and f_min > UNDERFLOW_FLOOR,
              f"min f = {f_min:.3e}（已响应 {int(resp_m.sum())} 条）；"
              f"门槛 {UNDERFLOW_FLOOR:.1e}；双精度最小次正规数 ≈ 5e-324")

        # A14 **断言方向与 2026-10-14 之前相反，这是本组最重要的一处变更**。
        #     以前 5 ms 余量必须"已经失效"（t0 = min(RT) − 5 ms ⇒ 整份 None，
        #     因为真值落进相消地板）；现在同一取值必须**有限**——这正是
        #     "cliff 已修掉"的直接证据。保留同一条取值、只把断言反过来，回归可比。
        rt_resp = np.asarray(tr_fit["rt"], dtype=float)[resp_m]
        p_tight = L.MappingParams(shape_model="lin", t0=float(np.nanmin(rt_resp)) - 0.005)
        ll_t = L.per_trial_loglik(p_tight, tr_fit)
        ok_t = (ll_t is not None) and bool(
            np.all(np.isfinite(np.asarray(ll_t, dtype=float))))
        check("A14 【断言已反向】t0 = min(RT) − 5 ms 现在必须有限（旧实现在此必然 None）",
              ok_t,
              f"t0 = min(RT) − 5 ms = {p_tight.t0:.4f} ⇒ "
              + ("有限（cliff 已修掉）" if ok_t
                 else "None（cliff 回来了，须复查 1_Code/DDM_Core/wfpt.py 的 flux）"))

        # A15 这组分量：真实数据的可行域内**确实**有试次走到镜像分支。
        #     否则 A12–A14 只在测大 t 分支，flux 修不修都过。
        #     判据**不复述交叉点公式**，而是直接比 `flux`（派发后）与
        #     `wfpt._flux_series`（旧实现）：只要有一个点不同，镜像分支就被走到了；
        #     再数出旧实现有多少条试次的密度 ≤ 0 —— 那正是它被判死的地方。
        tp = M.trial_params(tr_fit, p_hi)
        # ⚠️ 必须先按**已响应**掩掉：未响应试次的 rt 是 NaN，而 `_flux_series` 内部
        # 用 `np.min(t)` 定截断项数 ⇒ NaN 会直接抛
        # `ValueError: cannot convert float NaN to integer`。
        # （`flux` 本身是容 NaN 的：`pos = t > 0` 对 NaN 为 False、返回 0，
        #   所以这里出错是**测试直接调私有分支**造成的，不是库的缺陷。）
        a_v = np.asarray(tp["a"], dtype=float)[resp_m]
        z_v = np.asarray(tp["z"], dtype=float)[resp_m]
        v_v = np.asarray(tp["v"], dtype=float)[resp_m]
        t_v = np.asarray(tr_fit["rt"], dtype=float)[resp_m] - float(p_hi.t0)
        d_up, d_lo = a_v - z_v, z_v
        new_up, new_lo = W.flux(d_up, v_v, a_v, t_v), W.flux(d_lo, -v_v, a_v, t_v)
        old_up = W._flux_series(d_up, v_v, a_v, t_v)
        old_lo = W._flux_series(d_lo, -v_v, a_v, t_v)
        n_div = int(np.sum((new_up != old_up) | (new_lo != old_lo)))
        n_old_bad = int(np.sum((old_up <= 0) | (old_lo <= 0)))
        n_new_bad = int(np.sum((new_up <= 0) | (new_lo <= 0)))
        # 旧实现在这些点上的**量级**误差（相对新实现）。
        # ⚠️ 实测结论与直觉相反，值得写死在这里：在 0.02 s 余量下，旧实现（纯正弦
        # 级数）与修复后的派发结果最差只差 **7.85e−09** —— 也就是说**既有验收结果
        # 不受这次修复影响**（Stage 2 的 `validate_wfpt.py` 也逐位复现）。旧的失败
        # （None）只在余量被收到 5 ms 时出现（A14）。所以 A15 同时是一条**回归**守卫：
        # 若哪天这个数字变大，"修复改变了旧结论"就必须重新评估。
        old_rel = np.concatenate([
            np.abs(old_up - new_up) / np.maximum(new_up, 1e-300),
            np.abs(old_lo - new_lo) / np.maximum(new_lo, 1e-300)])
        worst_rel = float(np.max(old_rel)) if old_rel.size else float("nan")
        check("A15 上界处确有试次走镜像分支，且旧实现在该余量下仍准确（无回归）",
              n_div >= 1 and n_new_bad == 0 and worst_rel < 1e-6,
              f"上界处已响应 {int(resp_m.sum())} 条：派发路径与旧实现不同的 {n_div} 条"
              f"（= {100.0 * n_div / max(int(resp_m.sum()), 1):.0f}%）；"
              f"新实现 ≤0 的 {n_new_bad} 条；旧实现 ≤0 的 {n_old_bad} 条"
              f"（0.02 余量下符号未翻 —— 那是余量的功劳，不是旧实现的功劳）；"
              f"旧实现最差相对误差 {worst_rel:.3e}（门槛 1e-6）")
    except Exception as e:  # noqa: BLE001
        # ⚠️ 这里**必须**带 traceback：不带的话异常来自 A8–A15 里的哪一条都看不出来，
        # 只剩一句 "ValueError: cannot convert float NaN to integer" —— 守卫就成了
        # 又一个"没有牙齿"的例子（真发生过：A15 抛异常，报出来的却是 A8 的名字）。
        import traceback
        tb_txt = "".join(traceback.format_exc(limit=6)).strip().splitlines()
        check("A8–A15 组内未捕获异常（traceback 见下）", False,
              f"{type(e).__name__}: {e}\n         " + "\n         ".join(tb_txt[-5:]))

    # A9/A10 BOM 陷阱：真实 v4.1 由 MATLAB 写出、**带 BOM**（合成生成器不带），
    #    所以这里自己造一份带 BOM 的副本来测读取端，而不是断言生成器的字节。
    path = out / "exp_group1_subject1.txt"
    raw = path.read_bytes()
    check("A9 合成生成器写的是无 BOM 的 UTF-8（真实 MATLAB 文件带 BOM）",
          raw[:3] != b"\xef\xbb\xbf", f"首三字节 = {raw[:3]!r}")
    bom_path = out / "exp_group1_subject1_bom.txt"
    bom_path.write_bytes(b"\xef\xbb\xbf" + raw)
    rec_bom, rep_bom = R.load_file(bom_path)
    ok_bom = bool(rec_bom) and rec_bom["subjectID"] == rec1["subjectID"]
    check("A10 带 BOM 的文件仍能正确解析（靠 utf-8-sig）", ok_bom,
          f"subjectID = {rec_bom.get('subjectID') if rec_bom else None}")
    first_col_sig = b"\xef\xbb\xbf".decode("utf-8-sig") + ""
    bad_col = bom_path.read_bytes().decode("utf-8").split("\n", 1)[0].split("\t")[0]
    check("A11 若误用 utf-8 读带 BOM 文件，首列名会变成 '\\ufeffgroupID'",
          bad_col != "groupID", f"utf-8 → {bad_col!r}")


# ------------------------------------------------------------------
# B 组：负向 —— 每一条守卫都必须能被它自己的坏样例触发
# ------------------------------------------------------------------
def case_b(tmp: Path) -> None:
    print("\n[B] 负向：坏数据必须被对应守卫抓住（守卫没有牙齿就等于没有）")

    # B1 定向破坏一名被试的 `CorrectKey` 整列（f↔j 互换）⇒ 两条独立路径必须打架。
    #    ⚠️ 旧版是靠"生成器对所有被试写同一张规则表"的缺陷来触发的，但那是
    #    **生成器的 bug**（已修：现在按 `getPairingRules` 逐被试写）——负向测试必须
    #    **自己制造坏样例**，不能借用另一个部件的缺陷当负样例，否则修好那个部件就把
    #    测试一起弄坏了（这正是修生成器时发生的事）。
    out = tmp / "b1"
    gen(out, n_subjects=2)
    orig = out / "exp_group1_subject1.txt"
    rows = orig.read_text(encoding="utf-8").splitlines()
    fixed = [rows[0]]
    for ln in rows[1:]:
        c = ln.split("\t")
        if len(c) >= 13:
            c[12] = "j" if c[12] == "f" else "f"
        fixed.append("\t".join(c))
    bad_path = out / "exp_group1_subject1_keyflip.txt"
    bad_path.write_text("\n".join(fixed) + "\n", encoding="utf-8")
    for tag, path, should_flag in (("原样", orig, False),
                                   ("CorrectKey 整列 f↔j", bad_path, True)):
        rec, _ = R.load_file(path)
        bad = R.validate(rec, R.to_trials(rec))
        hit = any("两条推导路径不一致" in b for b in bad)
        check(f"B1 被试 1（{tag}）两条 is_match 路径"
              f"{'必须报错' if should_flag else '必须一致'}",
              hit == should_flag, f"报错项 {len(bad)} 个、命中 {hit}")
    # 同时确认：**正常生成的多被试数据现在全部通过**（生成器逐被试配对规则已修）
    gen(out, n_subjects=4)
    for s in (1, 2, 3, 4):
        rec, _ = R.load_file(out / f"exp_group1_subject{s}.txt")
        bad4 = R.validate(rec, R.to_trials(rec))
        check(f"B1 被试 {s}（%4={s % 4}）配对规则现已逐被试正确",
              bad4 == [], f"报错项 {len(bad4)} 个" + (f"：{bad4[0]}" if bad4 else ""))

    # B2 v4.1 的 %.1f 精度损失：T/W 只剩粗档 ⇒ 因子结构必须报错
    out = tmp / "b2"
    gen(out, "--defect-1f")
    rec, tr = load_one(out)
    bad = R.validate(rec, tr)
    check("B2 `--defect-1f`（T/W 精度塌陷）被因子档数判据抓住",
          any("只出现" in b for b in bad), (bad or ["（无报错！）"])[0])

    # B3 Response 与 RT 自相矛盾 ⇒ 缺值一致性必须报错
    out = tmp / "b3"
    gen(out, "--defect-mismatch")
    rec, tr = load_one(out)
    bad = R.validate(rec, tr)
    check("B3 `--defect-mismatch`（有按键无 RT）被缺值一致性判据抓住",
          any("不一致" in b and "Response" in b for b in bad),
          next((b for b in bad if "Response" in b), "（无报错！）"))

    # B4 只跑了 2 档 T ⇒ 档数判据必须报错
    out = tmp / "b4"
    gen(out, "--defect-missing-t")
    rec, tr = load_one(out)
    bad = R.validate(rec, tr)
    check("B4 `--defect-missing-t`（只 2 档 T）被档数判据抓住",
          any("T 只出现" in b for b in bad),
          next((b for b in bad if "T 只出现" in b), "（无报错！）"))

    # B5 把某一行的 Response 改成"按对了但记错"的键：Correct 与 side==is_match 必须对不上
    out = tmp / "b5"
    gen(out)
    rec, tr = load_one(out)
    mk = rec["matchKey"]
    other = "j" if mk == "f" else "f"
    i = int(np.argmax(~tr["omission"].astype(bool)))       # 第一个已响应试次
    rec2 = dict(rec)
    rec2["Response"] = rec["Response"].copy()
    rec2["Response"][i] = other                            # 侧别翻转，Correct 不动
    _, tr2 = R.load_file(out / "exp_group1_subject1.txt")
    tr2 = R.to_trials(rec2)
    bad = R.validate(rec2, tr2)
    check("B5 单行侧别被翻转后 `Correct` 判据报错",
          any("Correct" in b and "side == is_match" in b for b in bad),
          next((b for b in bad if "side == is_match" in b), "（无报错！）"))

    # B6 刺激期内按键却把 dur 记成整段 T：技术列判据必须报错
    #    ⚠️ 必须挑一个「截断真的缩短了刺激」的试次：若 rt 落在 T 的前一帧之内，
    #       `min(T, ⌈rt⌉)` 本就等于 T，改不改都看不出来 —— 那样测的是空气。
    out = tmp / "b6"
    gen(out)
    rec, tr = load_one(out)
    frame = 1.0 / 60.0
    exp_early = np.minimum(tr["T"], (np.floor(tr["rt"] / frame) + 1.0) * frame)
    shortened = np.where((~tr["omission"].astype(bool)) & (tr["rt"] < tr["T"])
                         & ((tr["T"] - exp_early) >= frame + 1e-9))[0]
    if shortened.size == 0:
        check("B6 提前截断判据（本样例无「真被缩短」的试次，跳过）", True,
              "该批数据无有效 early 试次")
    else:
        i = int(shortened[0])
        rec2 = dict(rec)
        rec2["stimulus_dur_actual"] = rec["stimulus_dur_actual"].copy()
        rec2["stimulus_dur_actual"][i] = tr["T"][i]        # 抹平截断
        bad = R.validate(rec2, R.to_trials(rec2))
        check("B6 提前截断被抹平后技术列判据报错",
              any("下一帧" in b for b in bad),
              next((b for b in bad if "下一帧" in b),
                   f"（无报错！第 {i} 行 T={tr['T'][i] * 1000:.1f}ms "
                   f"rt={tr['rt'][i] * 1000:.1f}ms dur={exp_early[i] * 1000:.1f}ms）"))

    # B7 表头列数不对 ⇒ 必须在读表阶段就失败（不能读成一张歪表继续跑）
    out = tmp / "b7"
    gen(out)
    p = out / "exp_group1_subject1.txt"
    lines = p.read_text(encoding="utf-8-sig").split("\n")
    lines[0] = "\t".join(lines[0].split("\t")[:20])        # 砍成 20 列
    p.write_text("\n".join(lines), encoding="utf-8-sig")
    rec3, rep3 = R.load_file(p)
    check("B7 20 列的表头被拒绝（不读成歪表）",
          (rec3 == {} or bool(rep3.get("error"))),
          f"rec 空 = {rec3 == {}}、error = {rep3.get('error')!r}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="保留临时目录")
    args = ap.parse_args()
    if not MAKER.exists():
        print(f"❌ 找不到合成数据生成器：{MAKER}")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="ck_rfd_"))
    print(f"临时目录：{tmp}")
    try:
        case_a(tmp)
        case_b(tmp)
    finally:
        if args.keep:
            print(f"（--keep）保留：{tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'=' * 64}\n通过 {_N_PASS} 项、未通过 {_N_FAIL} 项")
    if _N_FAIL:
        print(f"❌ {_N_FAIL} 项判据未通过")
    return 1 if _N_FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
