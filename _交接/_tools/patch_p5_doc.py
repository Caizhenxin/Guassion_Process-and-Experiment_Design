"""P5 补丁 2：doc 自测改用自建夹具（不再依赖真实产物）。"""
import io

P = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-server.mjs'
old = """// 8) doc：archify 架构图这类自包含 HTML 要整篇原样返回，交给 iframe 自己解析
const archPath = '1_Code/Animation_Manim/Architecture_Visualization/spe-runtime.html'
const docRes = await route('doc').fetch(
  new Request('http://local/api/my-project-workbench/doc?path=' + encodeURIComponent(archPath) + '&embed=1'),
)
const docType = docRes.headers.get('content-type') || ''
const docBody = await docRes.text()
console.log('[doc]', docType, docBody.length, 'B')
assert.ok(docType.indexOf('text/html') >= 0, 'doc 必须返回 text/html')
assert.ok(docBody.startsWith('<!DOCTYPE html') || docBody.startsWith('<html'), 'doc 返回的必须是整篇 HTML')
assert.ok(docBody.indexOf('<svg') >= 0, '架构图 HTML 里应该有内联 SVG')
assert.ok(docBody.length > 500000, 'spe-runtime.html 应该有 70 万字符量级')"""

new = """// 8) doc：自包含 HTML 要整篇原样返回，交给 iframe 自己解析。
//    夹具自建 —— 上一版指着项目里的 spe-runtime.html，那个产物一改名就假红，
//    而且顺带把「70 万字符」这种产物属性写进了接口契约。
const docProj = join(dataRoot, 'docproj')
await mkdir(join(docProj, 'sub'), { recursive: true })
const DOC_HTML = '<!DOCTYPE html>\\n<html><body><svg width="1" height="1"></svg>PROBE</body></html>'
await writeFile(join(docProj, 'chart.html'), DOC_HTML, 'utf8')
const routes2 = []
const ctx2 = { connection: { fetch: { register: (def) => routes2.push(def) } } }
mod.apply(ctx2, { root: dataRoot, projectRoot: docProj, hubRoot })
const docRes = await routes2
  .find((def) => def.path.endsWith('/doc'))
  .fetch(new Request('http://local/api/my-project-workbench/doc?path=chart.html'))
const docType = docRes.headers.get('content-type') || ''
const docBody = await docRes.text()
console.log('[doc]', docType, docBody.length, 'B')
assert.ok(docType.indexOf('text/html') >= 0, 'doc 必须返回 text/html')
assert.equal(docBody, DOC_HTML, 'doc 必须逐字返回原文（不许改写或转义）')"""

src = io.open(P, encoding='utf-8').read()
if old in src:
    src = src.replace(old, new, 1)
    print('patched doc fixture')
elif new in src:
    print('skip (already)')
else:
    raise SystemExit('ANCHOR MISS')
io.open(P, 'w', encoding='utf-8', newline='\n').write(src.replace('\r\n', '\n'))
print('written')
