# -*- coding: utf-8 -*-
"""把闸门的「下一次切换」改成解析求解（只在 00:00/09:00/12:00/14:00/18:00 上找边界）。

原实现按 15 分钟步进，会把 09:00 的边界报成 09:15，看着像 bug。
"""
from pathlib import Path

p = Path(r"C:\Users\蔡振辛\AppData\Roaming\dsh-desktop\harness\offpeak_gate.py")
s = p.read_text(encoding="utf-8")

start = s.index("def _peak_now(")
end = s.index("def status(")
new = '''BOUNDS = [dtime(0, 0), dtime(9, 0), dtime(12, 0), dtime(14, 0), dtime(18, 0)]


def _peak_now(t: dtime) -> bool:
    return any(a <= t < b for a, b in PEAK_WINDOWS)


def _is_peak_at(moment: datetime, holidays: set[str]) -> bool:
    """某一时刻是否落在高峰（周末与法定节假日全天不算）。"""
    if moment.weekday() >= 5 or moment.strftime("%Y-%m-%d") in holidays:
        return False
    return _peak_now(moment.time())


def _next_boundary(now: datetime, want_peak: bool, holidays: set[str],
                   limit_days: int = 14) -> datetime:
    """往后找第一个「峰谷状态 = want_peak」的边界时刻（精确到窗口开闭点）。"""
    for k in range(limit_days + 1):
        day = (now + timedelta(days=k)).date()
        for b in BOUNDS:
            cand = datetime.combine(day, b, tzinfo=TZ)
            if cand <= now:
                continue
            if _is_peak_at(cand, holidays) == want_peak:
                return cand
    return now + timedelta(days=limit_days)          # pragma: no cover


'''
s = s[:start] + new + s[end:]
s = s.replace('switch = next_offpeak(now, holidays) if peak else next_peak(now, holidays)',
              'switch = _next_boundary(now, want_peak=not peak, holidays=holidays)')
p.write_text(s, encoding="utf-8", newline="\n")
print("analytic switch patched")
