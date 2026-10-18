# 多少人/组才让 LOO 闸门转绿（D100 后续）

> **数据是合成的**（`_make_ddm_pilot.py`，组 1，`--anticipation 0.03`）。
> 配置：quick（`n_em`=3、`n_draws`=12、`n_x`=21、PPC=1）、`--hyper-method analytic`、`--loo-level trial`。判词来自 `stage8_health.assess_group`（D73/D74/D75）。

| N（人/组） | 判词 | `n_flipped` | `p_loo`÷`n_obs` | `k_max` | `max_abs_theta` | 拟合耗时 | 主因 |
|---|---|---|---|---|---|---|---|

读法：**N 增大但判词仍 BAD** ⇒ 不是样本量问题，要查判据；**N 增大后转 OK 的那个 N** 就是「可辨识下限」的粗估。
