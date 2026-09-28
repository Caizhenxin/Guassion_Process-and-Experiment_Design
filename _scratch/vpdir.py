import json,re,glob,os
files=sorted(glob.glob('1_Code/Python_for_Generate/**/*.ipynb',recursive=True))+sorted(glob.glob('1_Code/Python_for_Generate/**/*.py',recursive=True))
pat_call=re.compile(r'v_P_Function\([^)]*\)|v_P_func\([^)]*\)')
pat_alaph=re.compile(r'alaph[12]\s*=\s*[-0-9.]+')
rows=[]
for f in files:
    if '.ipynb_checkpoints' in f: continue
    try:
        if f.endswith('.ipynb'):
            nb=json.load(open(f,encoding='utf-8'))
            code='\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
        else:
            code=open(f,encoding='utf-8',errors='ignore').read()
    except Exception as e:
        continue
    calls=set(m.group(0).replace('\n',' ') for m in pat_call.finditer(code))
    km=[m.group(0) for m in re.finditer(r'k_min\s*=\s*[0-9.]+',code)][:2]
    alph=sorted(set(m.group(0).replace(' ','') for m in pat_alaph.finditer(code)))
    if calls or ('v_P' in code):
        rows.append((os.path.basename(f), ' | '.join(sorted(calls))[:90], ','.join(km), ','.join(alph)))
print(f"{'file':<44} {'v_P calls':<92} {'k_min/k_max':<22} alaph")
for r in rows: print(f"{r[0]:<44} {r[1]:<92} {r[2]:<22} {r[3]}")
