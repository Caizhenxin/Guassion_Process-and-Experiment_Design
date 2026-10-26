from pathlib import Path

idx = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\INDEX.md")
text = idx.read_text(encoding="utf-8")
row = ("| 2026-10-26 | 预判「加污染项（λ 混合）能修好 PPC」，实现后剖面几乎处处 Δℓ<0，被数据证否 | "
       "`#预判未验证` `#污染项` `#lambda混合` `#PPC` `#RT过散` `#双峰` `#Stage8` "
       "`#似然下降` `#窄窗` `#lapse不建模` `#先剖面后写计划` | "
       "[2026-10-26_预判污染项能修好PPC实测被证否.md]"
       "(./2026-10-26_预判污染项能修好PPC实测被证否.md) |")
if "预判污染项能修好PPC" in text:
    print("已存在，跳过")
else:
    if not text.endswith("\n"):
        text += "\n"
    text += row + "\n"
    idx.write_text(text, encoding="utf-8", newline="\n")
    print(f"已追加；现 {len(text.splitlines())} 行")
