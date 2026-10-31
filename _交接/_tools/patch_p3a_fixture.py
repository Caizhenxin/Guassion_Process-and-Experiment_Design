import io, os

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-health.mjs'
s = io.open(p, encoding='utf-8').read()

old = "    'dsh/health.js': '// fixture\\n',\n"
new = "    'dsh/health.js': '// fixture\\n',\n    'dsh/scenes.js': '// fixture\\n',\n"
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new)

# 夹具里的体检只该看「这份夹具」，不该顺带去看插件自身的 scenes.json —— 明确写进注释。
old2 = "    '_evidence/test-one.mjs': '// fixture\\n',\n"
new2 = ("    // scenes.json 故意不给：夹具走「没有配置 → 用内置默认」这条 warn 路径，不引入文件侧失败。\n"
        "    '_evidence/test-one.mjs': '// fixture\\n',\n")
assert s.count(old2) == 1
s = s.replace(old2, new2)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
