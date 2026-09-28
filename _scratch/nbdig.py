import json,re
p='1_Code/Python_for_Generate/S2_gen_data_optimized_cp.ipynb'
nb=json.load(open(p,encoding='utf-8'))
src=[]
for c in nb['cells']:
    if c['cell_type']=='code':
        src.append(''.join(c['source']))
code='\n'.join(src)
print("total code chars:",len(code))
# print key function bodies
for key in ['def k_P','def v_P_Func','def compute_v','def compute_a','def simulate','def generate','ALAPH','alaph','bounds','differential_evolution','GP','gp_','target','deadline','max_time','omission','TARGET']:
    for m in re.finditer(re.escape(key), code):
        s=max(0,m.start()-80); print("-"*50); print(code[s:m.start()+320].replace('\n','\n  ')); break
