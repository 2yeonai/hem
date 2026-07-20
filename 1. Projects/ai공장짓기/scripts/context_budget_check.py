#!/usr/bin/env python3
# 시작 문맥 길이 실측 — 경고 전용(WARN only). 길이로 커밋을 막지 않는다.
# 배경: 2026-07-20 토큰 감사 [hyemi]. 하드 상한은 2~4주 실측 후 사람이 결정.
import subprocess, sys, os
FILES = [
    "CLAUDE.md",
    "2. Areas/핵심맥락.md",
    "1. Projects/클로드 정부지원사업 ai/HANDOFF.md",
    "1. Projects/ai공장짓기/HANDOFF.md",
    "1. Projects/클로드 꽃집 ai/HANDOFF.md",
]
def head_size(path):
    try:
        out = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True)
        if out.returncode == 0:
            return len(out.stdout)
    except Exception:
        pass
    return None
total = 0; warn = 0
print("[context-budget] 시작 문맥 길이 실측 (경고 전용 — 커밋을 막지 않음)")
for f in FILES:
    if not os.path.exists(f):
        print(f"  - {f}: 파일 없음"); continue
    data = open(f, "rb").read(); b = len(data)
    c = len(data.decode("utf-8", errors="replace")); total += b
    prev = head_size(f)
    if prev:
        delta = (b - prev) / prev * 100
        mark = " ⚠ WARN: 이전 커밋 대비 10% 이상 증가" if delta > 10 else ""
        if mark: warn += 1
        print(f"  - {f}: {c:,}자 / {b:,}바이트 / HEAD 대비 {delta:+.1f}%{mark}")
    else:
        print(f"  - {f}: {c:,}자 / {b:,}바이트 / HEAD 비교 불가")
print(f"[context-budget] 합계 {total:,}바이트 / WARN {warn}건 / 하드 상한 없음(실측 후 결정)")
sys.exit(0)
