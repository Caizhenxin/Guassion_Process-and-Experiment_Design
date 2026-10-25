"""逐模型检查点（D125）的最小自测：不拟合，桩掉 `hier.fit_and_loo`。

验的是三条：
1. 第一次跑到某模型 ⇒ 立刻写出 `stage8_model_g<组>_<模型>.json`；
2. `--resume` 再跑 ⇒ 该模型命中检查点、**不调用**拟合函数；
3. 从检查点读回的 `log_lik` 必须是 ndarray（裸 list 会让 `compare_models` 静默算错）。
"""
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(REPO / "1_Code" / "DDM_Core"))
import stage8_run as S  # noqa: E402

CALLS = []


def _fake_fit(subs, n_draws, seed, n_em, do_bruteforce, hyper_method, loo_level):
    CALLS.append(len(subs))
    n = max(len(subs), 1)
    return {
        "loo": {"elpd_loo": -100.0, "se": 5.0, "p_loo": 3.0, "k_max": 0.0,
                "n_k_gt_bad": 0, "n_obs": 10 * n},
        "log_lik": np.full((n, 10), -1.5),
        "fit": {"mu": np.zeros(3), "sigma": np.ones(3), "modes": np.zeros((n, 3))},
        "loo_stats": {}, "n_fallback_fit": 0, "n_nonfinite_g_fit": 0,
    }


S.hier.fit_and_loo = _fake_fit
S._subjects = lambda people, rho_free, n_x: [{"subject": i} for i in range(len(people))]
people = [{"subject": 1, "group": 9}, {"subject": 2, "group": 9}]
cfg = {"n_em": 1}
tf = Path(tempfile.mkdtemp(prefix="ckpt_"))

# —— 第一次：两个模型都该落盘 ——
r1 = S.fit_group(people, 1, 11, 2, 0, False, ckpt={"dir": tf, "tag": "9",
                                                   "config": cfg, "resume": False})
files = sorted(p.name for p in tf.glob("stage8_model_*.json"))
assert files == ["stage8_model_g9_M-T1.json", "stage8_model_g9_M-T3.json"], files
assert len(CALLS) == 2, CALLS
print(f"[ok] 首次拟合写盘 {len(files)} 个检查点、拟合调用 {len(CALLS)} 次")

# —— 第二次：两个模型都该命中，拟合函数一次都不调 ——
CALLS.clear()
r2 = S.fit_group(people, 1, 11, 2, 0, False, ckpt={"dir": tf, "tag": "9",
                                                   "config": cfg, "resume": True})
assert CALLS == [], f"命中检查点时不该再拟合，实际调用 {CALLS}"
assert isinstance(r2["M-T1"]["log_lik"], np.ndarray), type(r2["M-T1"]["log_lik"])
assert r2["M-T1"]["log_lik"].shape == r1["M-T1"]["log_lik"].shape
print(f"[ok] 二次命中 {len(r2)} 个模型、拟合调用 0 次、log_lik 已还原为 ndarray "
      f"{r2['M-T1']['log_lik'].shape}")

# —— 配置不一致必须大声失败（不许静默复用） ——
try:
    S.fit_group(people, 1, 11, 2, 0, False, ckpt={"dir": tf, "tag": "9",
                                                  "config": {"n_em": 99}, "resume": True})
except ValueError as exc:
    print(f"[ok] 配置不一致时报错：{str(exc)[:60]}…")
else:
    raise SystemExit("[fail] 配置不一致却静默复用了检查点")

# —— 半截文件必须大声失败 ——
bad = tf / "stage8_model_g9_M-T1.json"
bad.write_text("{not json", encoding="utf-8")
try:
    S.fit_group(people, 1, 11, 2, 0, False, ckpt={"dir": tf, "tag": "9",
                                                  "config": cfg, "resume": True})
except ValueError as exc:
    print(f"[ok] 残片报错：{str(exc)[:60]}…")
else:
    raise SystemExit("[fail] 残片被当成有效缓存")

print("\n全部通过：逐模型检查点的写 / 命中 / 配置校验 / 残片校验四条都成立")
