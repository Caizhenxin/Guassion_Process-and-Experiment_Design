from pathlib import Path
p = Path(r"1_Code/Tools/running.py")
s = p.read_text(encoding="utf-8")

old_t = '''    lines.append("== 最近的 DSH 窗口（按最后活动） ==")
    for w in data["windows"][:6]:
        lines.append(f"  {w['last']}（{human_age(w['ago_s'])}前）  {w['path']}")'''
new_t = '''    lines.append("== 最近的 DSH 窗口（按最后活动） ==")
    for w in data["windows"][:6]:
        lines.append(f"  {w['last']}（{human_age(w['ago_s'])}前）  {w['title']}")
        lines.append(f"        {w['cwd']}  [{w['sid']}]")'''
assert s.count(old_t) == 1
s = s.replace(old_t, new_t)

old_h = '''    parts.append('<h2 style="font-size:14px;margin:18px 0 0">DSH 窗口（按最后活动）</h2><table>'
                 '<tr><th>最后活动</th><th>工作目录</th></tr>')
    for w in data["windows"][:8]:
        parts.append(f'<tr><td class="age">{w["last"]} <span class="muted">（{human_age(w["ago_s"])}前）</span></td>'
                     f'<td><code>{w["path"]}</code></td></tr>')'''
new_h = '''    parts.append('<h2 style="font-size:14px;margin:18px 0 0">DSH 窗口（按最后活动）</h2><table>'
                 '<tr><th>最后活动</th><th>窗口标题</th><th>工作目录</th></tr>')
    for w in data["windows"][:8]:
        parts.append(f'<tr><td class="age">{w["last"]} <span class="muted">（{human_age(w["ago_s"])}前）</span></td>'
                     f'<td>{w["title"]} <span class="muted">[{w["sid"]}]</span></td>'
                     f'<td><code>{w["cwd"]}</code></td></tr>')'''
assert s.count(old_h) == 1
s = s.replace(old_h, new_h)
p.write_text(s, encoding="utf-8", newline="\n")
print("patched renderers")
