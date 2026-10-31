"""恢复被误认领的三行：〔总工作台·M*〕本来属于 workbench，不该被 GP 项目改写。"""
import io

P = r'D:\GitHub_programe\GitHub\DSH_Workbench\boards\待办板.md'
src = io.open(P, encoding='utf-8').read()
before = src.count('【gp-experiment】〔总工作台·')
src = src.replace('【gp-experiment】〔总工作台·', '【workbench】〔总工作台·')
io.open(P, 'w', encoding='utf-8', newline='\n').write(src)
print('恢复行数', before)
