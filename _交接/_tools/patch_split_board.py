"""把 index.js 的待办板落盘层搬到 boardStore.js（体检体积判据报红，这是真该拆的地方）。

幂等：每处都先判「已打过 / 未打过」，未命中抛错且不写任何文件。
"""
import io
import sys

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
IDX = WB + r'\dsh\index.js'
HEALTH = WB + r'\dsh\health.js'
TH = WB + r'\_evidence\test-health.mjs'

FACTORY = (
    '  // ---------- 交接层：私有层（§〇 覆盖写）+ 共享层（待办板） ----------\n'
    '\n'
    '  // 待办板的落盘层在 boardStore.js（规则在 board.js），index.js 只留路由。\n'
    '  // 为什么拆：体检的体积判据已经报红（860 行 / 33 KB），再往里加东西就是雪崩前的最后一块石头。\n'
    '  const boardStore = createBoard({ projectRoot, hubRoot, displayPath, readLegacy: readStore })\n'
    '  const readBoard = boardStore.read\n'
    '  const saveBoard = boardStore.save\n'
)

def patch_index(src):
    if 'from \'./boardStore.js\'' not in src:
        anchor = "import { readScenes, scenesSummary } from './scenes.js'\n"
        if anchor not in src:
            raise SystemExit('import anchor miss')
        src = src.replace(anchor, anchor + "import { createBoard } from './boardStore.js'\n", 1)

    for gone in ("const BOARD_REL = join('_交接', '待办板.md')\n", "const HUB_BOARD_REL = join('boards', '待办板.md')\n"):
        if gone in src:
            src = src.replace(gone, '', 1)

    start = '  // 待办板落在哪：总工作台有 boards/待办板.md 就用它（全机唯一落点），否则退回项目内的。\n'
    pid_start = '  // 归档落在总工作台：先按 projects.json 的 root 反查场景 id，查不到就用目录名。\n'
    pid_end = '  async function archiveSummary() {\n'
    if start in src:
        head, rest = src.split(start, 1)
        if pid_start not in rest:
            raise SystemExit('待办板块结束锚点缺失')
        _, tail = rest.split(pid_start, 1)
        src = head + FACTORY + pid_start + tail
    elif FACTORY not in src:
        raise SystemExit('待办板块起始锚点缺失')

    # projectIdOf 只剩一份，在 boardStore.js 里（两处各写一遍 = 两份结论，早晚打架）。
    if pid_start in src:
        head, rest = src.split(pid_start, 1)
        if pid_end not in rest:
            raise SystemExit('projectIdOf 结束锚点缺失')
        _, tail = rest.split(pid_end, 1)
        src = head + pid_end + tail

    src = src.replace('await projectIdOf()', 'await boardStore.projectIdOf()')
    if 'function projectIdOf' in src.replace('boardStore.projectIdOf', ''):
        raise SystemExit('index.js 里还有本地 projectIdOf 定义')
    return src

def patch_health(src):
    anchor = "  { rel: vector('dsh', 'scenes.js'), lines: 340, bytes: 18 * 1024 },\n"
    line = "  { rel: vector('dsh', 'boardStore.js'), lines: 260, bytes: 20 * 1024 },\n"
    if line in src:
        return src
    if anchor not in src:
        raise SystemExit('health SIZE_TARGETS anchor miss')
    return src.replace(anchor, anchor + line, 1)

def patch_th(src):
    anchor = "    'dsh/scenes.js': '// fixture\\n',\n"
    line = "    'dsh/boardStore.js': '// fixture\\n',\n"
    if line in src:
        return src
    if anchor not in src:
        raise SystemExit('test-health fixture anchor miss')
    return src.replace(anchor, anchor + line, 1)

def main():
    files = {}
    for path, fn in ((IDX, patch_index), (HEALTH, patch_health), (TH, patch_th)):
        src = io.open(path, encoding='utf-8', newline='').read()
        out = fn(src)
        if out != src:
            files[path] = out
    if not files:
        print('nothing to do')
        return
    for path, out in files.items():
        io.open(path, 'w', encoding='utf-8', newline='').write(out)
        print('written', path.split('\\')[-1], len(out), 'chars')

if __name__ == '__main__':
    main()
