import pathlib

p = pathlib.Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\INDEX.md")
s = p.read_text(encoding="utf-8")
old = "`#监控盲区` `#Stage8` `#流程问题` |"
new = ("`#监控盲区` `#Stage8` `#流程问题` `#控制台信号` `#WMI不隔离控制台` "
       "`#schtasks` `#逐模型检查点` `#落盘粒度` |")
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("[ok] INDEX 行标签已扩写；行数", len(p.read_text(encoding="utf-8").splitlines()))
