"""给「静默健康读数」失败记录追加第三次实例：流水线骨架不接闸门。"""
from __future__ import annotations

from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement"
         r"\2026-10-18_工具在能力不足时静默输出健康读数.md")

BLOCK = """
## 再次触发记录（2026-10-18，流水线骨架绕过 LOO 闸门）

- **新发现的原因**：`1_Code/Experiment/run_pipeline.py` 生成「结果节骨架」时，只把
  `elpd_loo / Δelpd / SE / k_diag_ok` 四列摆进「模型比较」表，**从不调用
  `stage8_health.assess_group`**。而 `stage8_health.py` 里早有 D74（超参数 Hessian 正定）与
  `p_loo ∈ [0, n_obs]` 两条硬判据。结果是：四组实测 `n_flipped` = 1/16、2/16、3/16、3/16、
  `p_loo/n_obs` = 0.009、2.16、3.22、2.33，**全部不可引用**，骨架却照样印出
  `Δelpd = +0.7 / −454.7 / −497.6 / −218.0`，看上去就是一组正常的模型比较结果。
- **与 D52 同源**：判据存在、工具存在、唯独「报告生成路径」没连上去 —— 判据成了摆设。
  这次是我自己写的新工具重演了旧错：`k_diag_ok` 是我新加的判据，我把它接上了，
  却把早已存在的 Hessian / `p_loo` 判据漏在外面，**只接了自己记得的那一条**。
- **是否换方案**：不换，改为「闸门自动跑」：新增 `assess_health()` 复用 `assess_group`
  （不重写判据），流水线加「3.5 LOO 健康」步骤，任一组 `BAD` ⇒ 该步 `ok=False`、退出码 1；
  骨架 §2 增 `p_loo÷n_obs`、`n_flipped`、判定、原因四列与段首「本段数值不可引用」横幅；
  `fig3` 给不可引用组加斜线并标注「N/M 组未过闸门」。
- **新增教训**：
  1. 报告生成器必须**从判据模块取结论**，不许自己拼字段 —— 拼字段时只会记得自己刚加的那一条。
  2. 新工具上线时问一句「这个领域里已经有几条闸门？」，把全部闸门接上，而不是只接新闸门。
  3. `k_max = 0` + `p_loo` 健康仍可能被判死（组 1 就是），**单看任一指标都会误判可报**。
"""

if __name__ == "__main__":
    txt = P.read_text(encoding="utf-8")
    if "流水线骨架绕过 LOO 闸门" in txt:
        print("已存在，跳过")
    else:
        P.write_text(txt.rstrip() + "\n" + BLOCK, encoding="utf-8", newline="\n")
        print(f"已追加：{len(P.read_text(encoding='utf-8').split(chr(10)))} 行")
