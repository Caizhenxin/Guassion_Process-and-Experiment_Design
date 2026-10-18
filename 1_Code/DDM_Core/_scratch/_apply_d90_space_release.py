# -*- coding: utf-8 -*-
"""D90：给 8 处「按空格继续」加上「先等松键」的门槛，挡住上一屏确认键穿透下一屏。

症状（用户 2026-10-18 实机报告）：第一次出现的块首指导语（C6 屏）「好像没按空格就进入
正式实验了」。根因：两处相邻的等待都用 KbCheck 忙等「此刻空格是否按着」，没有按下沿/
松开沿的概念；上一屏（练习结束休息屏）确认用的空格若还按着（≥50 ms 即够），下一屏的
while 立刻被这个残留按下穿透 ⇒ 指导语一闪而过。

修法（v4.7）：新增局部函数 waitForSpaceRelease()（最多等 5 s 见到「所有键松开」），
在每个 `waitForSpace = true;` / `waitingForSpace = true;` 之后、进入 while 之前调用一次。
幂等：已存在则不重复插入；newline="\\n" 写回。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "Exp_Design_Formal.m"

HEADER = """%
% ★★ v4.7 本次修正（2026-10-18，主试实机报告"块首指导语一闪而过"；D90）★★
%   (#1) 8 处「按空格继续」缺"松键门槛"：这些等待都用 KbCheck 忙等"此刻空格是否按着"，
%        没有按下沿的概念。相邻两屏（练习结束休息屏 → 块首 C6 指导语）之间只隔一次
%        Screen('Flip') 与几十毫秒建表时间；上一屏确认用的空格若还按着（≥50 ms 即够），
%        下一屏的 while 会立刻被这个"残留按下"穿透 ⇒ 指导语一闪而过、被试还没读完就进了
%        正式试次（该块首个试次被白白消耗，且被试不知道本组反应窗口是多少）。
%        修法：新增局部函数 waitForSpaceRelease()，在每个 while 空格等待之前先等一次
%        "所有键都松开"（最多 5 s，防键卡住时死结），再等一次新的按下。
%        只改等待方式，不动试次时序、不动数据列。
%
"""

FUNC = """
function waitForSpaceRelease()
% v4.7（D90）：直到所有键都松开才返回（最多等 5 s，防止键卡住时死结）。
%   目的：挡住"上一屏的确认键还没松开"穿透下一屏的空格等待——症状是指导语一闪而过。
%   用法：放在每个 `while waitForSpace` / `while waitingForSpace` 之前。
    t0 = GetSecs();
    while GetSecs() - t0 < 5
        [keyIsDown, ~, ~] = KbCheck;
        if ~keyIsDown
            return
        end
        WaitSecs(0.005);
        checkEscape();
    end
end
"""

FLAGS = ("waitForSpace = true;", "waitingForSpace = true;")
CALL = "waitForSpaceRelease();"


def main():
    text = TARGET.read_text(encoding="utf-8")
    lines = text.split("\n")

    # (1) 头注：插在 `%% 被试基础信息` 之前（放在所有 ★★ 版本段之后）
    if "★★ v4.7 本次修正" in text:
        print("header: already present, skip")
    else:
        idx = None
        for i, ln in enumerate(lines):
            if ln.strip() == "%% 被试基础信息":
                idx = i
                break
        assert idx is not None, "找不到 `%% 被试基础信息` 锚点"
        lines[idx:idx] = HEADER.rstrip("\n").split("\n") + [""]
        print("header: inserted before line %d" % (idx + 1))

    # (2) 8 处 flag 行后插入调用
    out = []
    inserted = 0
    for i, ln in enumerate(lines):
        out.append(ln)
        if ln.strip() in FLAGS:
            # 下一行已经是调用就跳过（幂等）
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt.strip() == CALL:
                continue
            indent = ln[: len(ln) - len(ln.lstrip())]
            out.append(indent + CALL)
            inserted += 1
    lines = out
    print("calls: inserted %d" % inserted)

    # (3) 局部函数追加到文件末尾
    text2 = "\n".join(lines)
    if "\nfunction waitForSpaceRelease()" in text2:
        print("function: already present, skip")
    else:
        text2 = text2.rstrip("\n") + "\n" + FUNC
        print("function: appended")

    TARGET.write_text(text2, encoding="utf-8", newline="\n")

    # 自检
    now = TARGET.read_text(encoding="utf-8")
    n_flag = sum(1 for ln in now.split("\n") if ln.strip() in FLAGS)
    n_call = sum(1 for ln in now.split("\n") if ln.strip() == CALL)
    print("verify flags=%d calls=%d func=%d" % (
        n_flag, n_call, now.count("function waitForSpaceRelease()")))
    assert n_flag == 8, "应有 8 处空格等待，实际 %d" % n_flag
    assert n_call == 8, "应有 8 处调用，实际 %d" % n_call
    print("OK")


if __name__ == "__main__":
    main()
