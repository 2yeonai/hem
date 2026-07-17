#!/usr/bin/env python3
"""
handoff_check.py — 공장별 HANDOFF 신선도 검사기

배경: `0. Docs/기록체계_재설계_2026-07-17.md` 원칙 3 — "규칙은 기억이 아니라
스크립트로 검사한다". HANDOFF.md의 "현재 상태" 갱신은 사람이 기억해서 지키는
규칙이었는데, 실제로 ai공장짓기 HANDOFF가 약 9일, 정부지원 HANDOFF가 약 5일
밀린 채 방치된 적이 있었다(정부지원은 최근 작업 T7~T11이 HANDOFF에 한 줄도
없어 "이미 만든 기능을 재설계"하는 사고까지 발생). 이 스크립트는 그 지연을
사람이 알아채기 전에 기계가 먼저 경고한다.

검사 대상 (하드코딩, 설계 근거 문서 §3):
  (a) 클로드 꽃집 ai       ↔ 같은 폴더 HANDOFF.md
  (b) 클로드 정부지원사업 ai ↔ 같은 폴더 HANDOFF.md
  (c) 클로드 콘텐츠 ai      ↔ 같은 폴더 HANDOFF.md
  (d) 클로드 방역 ai        ↔ ai공장짓기/HANDOFF.md (방역은 자체 HANDOFF가 없고 공용을 씀)

판정 방식:
  ① 폴더의 최근 작업일 = `git log -1 --format=%cs -- "<폴더>"`
     (git 실패/빈 결과 시 폴더 내 파일 mtime 최댓값으로 폴백)
  ② HANDOFF의 상태 날짜 = 본문에서 YYYY-MM-DD 패턴을 전부 찾아 그중 최댓값
     (frontmatter의 updated 필드도 본문 스캔에 포함되므로 자동으로 잡힘)
  ② 가 ① 보다 2일 이상 뒤처지면 [WARN], 아니면 [OK].

추가로 `ai공장짓기/현재작업현황.md`에 1일(24시간) 넘은 선언이 남아있으면
[STALE-DECL] 경고를 출력한다 — "끝나면 지운다"는 규칙이 실제로 지켜지고
있는지 확인하는 용도.

사용법:
  python3 handoff_check.py

종료 코드: WARN(또는 STALE-DECL)이 하나라도 있으면 1, 전부 정상이면 0.

알려진 한계 (2026-07-17 실측 확인): 폴더 이동/정리성 커밋(예: 파일 리오르그)도
"최근 작업"으로 집계된다. 콘텐츠 공장이 실제로는 2026-07-12 이후 진짜 작업이
없었는데도, 2026-07-14 리오르그 커밋 때문에 HANDOFF가 2일 밀린 것으로 오탐된
사례가 있었다. WARN이 뜨면 먼저 `git log -- <폴더>`로 실제 작업 커밋인지
확인할 것 — 파일 이동만 있었다면 HANDOFF를 억지로 갱신하지 말 것(할 얘기가
없는데 새 섹션을 추가하면 그 자체가 또 다른 형태의 부정확한 기록이 된다).
"""
import sys
import os
import re
import subprocess
import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 이 스크립트는 <vault>/1. Projects/ai공장짓기/scripts/handoff_check.py 에 위치.
# scripts -> ai공장짓기 -> "1. Projects" -> <vault root>
VAULT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
)

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DECL_RE = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2})\s+\[([^\]]+)\]\s+(.*)$")

# (표시용 이름, 폴더 상대경로, HANDOFF 상대경로)
PAIRS = [
    ("꽃집", "1. Projects/클로드 꽃집 ai", "1. Projects/클로드 꽃집 ai/HANDOFF.md"),
    ("정부지원사업", "1. Projects/클로드 정부지원사업 ai", "1. Projects/클로드 정부지원사업 ai/HANDOFF.md"),
    ("콘텐츠", "1. Projects/클로드 콘텐츠 ai", "1. Projects/클로드 콘텐츠 ai/HANDOFF.md"),
    ("방역", "1. Projects/클로드 방역 ai", "1. Projects/ai공장짓기/HANDOFF.md"),
]

CURRENT_WORK_DECL = "1. Projects/ai공장짓기/현재작업현황.md"

WARN_THRESHOLD_DAYS = 2
STALE_DECL_THRESHOLD_DAYS = 1


def git_last_commit_date(rel_folder_path):
    """git log -1 --format=%cs -- <폴더> 로 마지막 커밋 날짜(date)를 구한다.
    git 실패/빈 결과면 None을 반환 (호출자가 mtime 폴백을 시도)."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel_folder_path],
            cwd=VAULT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    if not out:
        return None
    try:
        return datetime.date.fromisoformat(out)
    except ValueError:
        return None


def mtime_fallback_date(abs_folder_path):
    """폴더 내 파일 mtime 최댓값을 date로 반환. 파일이 없으면 None."""
    latest = None
    if not os.path.isdir(abs_folder_path):
        return None
    for dirpath, dirnames, filenames in os.walk(abs_folder_path):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                continue
            d = datetime.date.fromtimestamp(mtime)
            if latest is None or d > latest:
                latest = d
    return latest


def folder_last_work_date(rel_folder_path):
    abs_path = os.path.join(VAULT_ROOT, rel_folder_path)
    d = git_last_commit_date(rel_folder_path)
    if d is not None:
        return d, "git"
    d = mtime_fallback_date(abs_path)
    if d is not None:
        return d, "mtime폴백"
    return None, "없음"


def handoff_latest_date(rel_handoff_path):
    abs_path = os.path.join(VAULT_ROOT, rel_handoff_path)
    if not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    dates = []
    for m in DATE_RE.findall(text):
        try:
            dates.append(datetime.date.fromisoformat(m))
        except ValueError:
            continue
    if not dates:
        return None
    return max(dates)


def check_pairs():
    any_warn = False
    print("== HANDOFF 신선도 검사 ==")
    for label, rel_folder, rel_handoff in PAIRS:
        folder_date, source = folder_last_work_date(rel_folder)
        handoff_date = handoff_latest_date(rel_handoff)

        if folder_date is None:
            print(f"[ERROR] {label}: 폴더의 최근 작업일을 확인할 수 없음 ({rel_folder})")
            any_warn = True
            continue
        if handoff_date is None:
            print(
                f"[WARN] {label}: HANDOFF에서 날짜 표기를 찾을 수 없음 "
                f"({rel_handoff}) — 폴더 최근 작업 {folder_date.isoformat()}({source})"
            )
            any_warn = True
            continue

        lag_days = (folder_date - handoff_date).days
        if lag_days >= WARN_THRESHOLD_DAYS:
            print(
                f"[WARN] {label}: 폴더 최근 작업 {folder_date.isoformat()}({source}) "
                f"vs HANDOFF 최신 표기 {handoff_date.isoformat()} ({lag_days}일 밀림)"
            )
            any_warn = True
        else:
            print(f"[OK] {label}")
    return any_warn


def check_current_work_declarations():
    any_stale = False
    abs_path = os.path.join(VAULT_ROOT, CURRENT_WORK_DECL)
    print("\n== 현재작업현황.md 선언 잔류 검사 ==")
    if not os.path.isfile(abs_path):
        print(f"[ERROR] 현재작업현황.md를 찾을 수 없음: {CURRENT_WORK_DECL}")
        return True

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        print(f"[ERROR] 현재작업현황.md를 읽을 수 없음: {CURRENT_WORK_DECL}")
        return True

    today = datetime.date.today()
    found_any = False
    for line in lines:
        m = DECL_RE.match(line.strip())
        if not m:
            continue
        found_any = True
        decl_date_str, tag, rest = m.groups()
        try:
            decl_date = datetime.date.fromisoformat(decl_date_str)
        except ValueError:
            continue
        age_days = (today - decl_date).days
        if age_days >= STALE_DECL_THRESHOLD_DAYS:
            print(
                f"[STALE-DECL] [{tag}] {decl_date_str} 선언이 아직 남아있음 "
                f"({age_days}일 경과): {rest[:60]}"
            )
            any_stale = True

    if not found_any:
        print("[OK] 남아있는 선언 없음")
    elif not any_stale:
        print("[OK] 선언은 있으나 아직 24시간 이내")

    return any_stale


def main():
    warn1 = check_pairs()
    warn2 = check_current_work_declarations()
    sys.exit(1 if (warn1 or warn2) else 0)


if __name__ == "__main__":
    main()
