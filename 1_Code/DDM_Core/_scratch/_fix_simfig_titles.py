"""试次图面板标题：把「同一被试」改成「N 名被试合并」。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\make_sim_figures.py")
s = p.read_text(encoding="utf-8")
old = '    ax.set_title("RT 分布（同一被试、同一真值）" if lang == "zh" else "RT distributions (one simulated subject)")'
new = ('    ax.set_title(f"RT 分布（{td[\'n_subjects\']} 名被试合并、同一真值）" if lang == "zh"\n'
       '                 else f"RT distributions ({td[\'n_subjects\']} subjects pooled, same truth)")')
assert s.count(old) == 1, (old, s.count(old))
s = s.replace(old, new)
p.write_text(s, encoding="utf-8", newline="\n")
print("ok, lines", len(s.split("\n")))
