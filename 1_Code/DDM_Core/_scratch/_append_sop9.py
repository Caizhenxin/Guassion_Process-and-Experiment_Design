from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\数据快速筛查SOP.md")
s = p.read_text(encoding="utf-8")
if "## 九、把筛查结果交接给下游（Stage 8）" in s:
    print("already")
else:
    add = """
## 九、把筛查结果交接给下游（Stage 8）

`stage8_run.py` **只吃"同一目录下 N 个 `exp_group<g>_subject<s>.txt`"** 的扁平布局；而正式数据是
`Condition 1..4/` 分层布局（每人一份 csv + 一份同内容 txt）。直接把它指到数据根目录会得到：

```
没有任何可用的 v4.1 逐被试 txt 输入，共 1 项被拒：
  ⛔ New_Design：目录里没有 *.txt（有 1 个其它文件，例如 README.md）⇒ 本运行器只吃 v4.1 逐被试 txt
```

转接方式（不改数据、不复制字节）：

```powershell
python -X utf8 1_Code/DDM_Core/_scratch/_stage8_stage_in.py   # 按筛查快照的 KEEP 做硬链接
python -X utf8 -u 1_Code/DDM_Core/stage8_run.py `
    --data 2_Data\\Real_Data\\New_Design\\_stage8_in `
    --out  2_Data\\Real_Data\\New_Design\\_pipeline\\stage8 `
    --n-em 3 --n-draws 12 --n-x 21 --n-ppc 1 `
    --hyper-method analytic --loo-level trial --allow-large
```

**已知口径不一致（待决策，2026-10-25）**：`read_formal_data` 的读取器对"单行 `stimulus_dur_actual`
超 T + 1 帧"是**整份拒收被试**；而本 SOP 的口径（D120）把同一现象记为**信息项、被试照收**。
20 人批上两者的差是 17 人 vs 15 人。在改成"丢坏试次、留被试"之前，**报告人数时必须写清是哪一层的人数**。
"""
    p.write_text(s.rstrip("\n") + "\n" + add, encoding="utf-8", newline="\n")
    print("appended")
