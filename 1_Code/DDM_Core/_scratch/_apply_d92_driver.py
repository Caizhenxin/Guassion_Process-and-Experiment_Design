# -*- coding: utf-8 -*-
"""D92 回归：给 run_full_session.m 加第 4 参数 runInProgramDir（默认 true）。

为什么要加：v4.8 改变了「掩蔽纹理从哪解析」（改用程序目录），必须有一条**可执行**的
回归证明「即使当前目录不是程序目录，整场也能跑通、且数据落进当前目录」。原来的驱动
函数第一件事就是 cd(expDir)，天生拓不到这个场景。

幂等；逐处断言命中 1 次。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "1_Code/Experiment/exp_matlab/test/run_full_session.m"

OLD_SIG = "function res = run_full_session(groupID, subjectID, outDir)"
NEW_SIG = "function res = run_full_session(groupID, subjectID, outDir, runInProgramDir)"

OLD_USAGE = "%   res = run_full_session(groupID, subjectID[, outDir])"
NEW_USAGE = (
    "%   res = run_full_session(groupID, subjectID[, outDir[, runInProgramDir]])\n"
    "%\n"
    "%   runInProgramDir（★ v4.8 / D92）：默认 true = 先 cd 到程序目录再跑（D79 起的原行为）。\n"
    "%     false = 就在【当前目录】跑（脚本按名调用，不改变当前目录），用来验证路径可移植性：\n"
    "%     掩蔽纹理仍从程序目录解析（v4.8 的 progDir），而 CSV/txt 落进当前目录。"
)

OLD_DEF = "if nargin < 3 || isempty(outDir), outDir = fullfile(here, '_full_session_out'); end"
NEW_DEF = (
    "if nargin < 3 || isempty(outDir), outDir = fullfile(here, '_full_session_out'); end\n"
    "if nargin < 4 || isempty(runInProgramDir), runInProgramDir = true; end"
)

OLD_RUN = "oldDir = cd(expDir);\nt0 = tic;\ntry\n    s = evalc(\"run('Exp_Design_Formal.m')\");"
NEW_RUN = (
    "if runInProgramDir\n"
    "    oldDir = cd(expDir);\n"
    "    runCall = \"run('Exp_Design_Formal.m')\";\n"
    "else\n"
    "    % 按名调用脚本：MATLAB 不会因此改当前目录（run() 会改），这正是要测的场景\n"
    "    addpath(expDir, '-begin');\n"
    "    oldDir = cd(pwd);\n"
    "    runCall = 'Exp_Design_Formal';\n"
    "end\n"
    "runDir = pwd;          % 数据落点 = 运行时的当前目录\n"
    "t0 = tic;\n"
    "try\n"
    "    s = evalc(runCall);"
)

OLD_PATHS = (
    "csvFile = fullfile(expDir, sprintf('EXP_data_group%d_%d.csv', groupID, subjectID));\n"
    "txtFile = fullfile(expDir, sprintf('exp_group%d_subject%d.txt', groupID, subjectID));"
)
NEW_PATHS = (
    "csvFile = fullfile(runDir, sprintf('EXP_data_group%d_%d.csv', groupID, subjectID));\n"
    "txtFile = fullfile(runDir, sprintf('exp_group%d_subject%d.txt', groupID, subjectID));"
)

src = F.read_text(encoding="utf-8")
assert "runInProgramDir" not in src, "已打过 D92 补丁"
for old, new, tag in [
    (OLD_SIG, NEW_SIG, "签名"),
    (OLD_USAGE, NEW_USAGE, "用法注释"),
    (OLD_DEF, NEW_DEF, "默认值"),
    (OLD_RUN, NEW_RUN, "运行段"),
    (OLD_PATHS, NEW_PATHS, "产物路径"),
]:
    n = src.count(old)
    assert n == 1, f"{tag}: 命中 {n} 次"
    src = src.replace(old, new)

F.write_text(src, encoding="utf-8", newline="\n")
print(f"D92 补丁完成：{F.name} {len(src.splitlines())} 行")
