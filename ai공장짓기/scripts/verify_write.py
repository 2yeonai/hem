#!/usr/bin/env python3
"""
verify_write.py — 파일 동기화 truncation 버그 자동 점검/복구 스크립트

배경: 2026-07-07 방역 스킬 작업 중 Edit/Write 도구로 파일을 고친 직후, 그
파일이 mid-byte/mid-statement에서 잘려있는 현상이 네 번(manifest.schema.v2.yaml,
클로드 방역 ai/manifest.yaml, validate_manifest.py, HANDOFF.md) 재현됐다.
지금까지는 매번 사람이 wc -l/yaml parse로 눈으로 확인하고 rename+재작성으로
고쳤는데, 이 스크립트는 그 확인+복구 과정을 자동화한다.

사용법:
  python3 verify_write.py <검사할 파일 경로> <의도한 내용이 담긴 임시파일 경로> [--handoff <HANDOFF.md 경로>]

동작:
  1. 대상 파일(디스크에서 실제로 읽히는 내용 — bash/파일시스템 레벨 read)과
     "의도한 내용" 임시파일을 바이트 단위로 비교한다.
  2. 다르면(= truncation 등 손상) 발생:
     - 손상된 파일을 <파일명>.stale-<타임스탬프>로 rename
     - 의도한 내용을 원래 경로에 새로 쓴다
     - HANDOFF.md(기본: 이 스크립트와 같은 저장소의 ai공장짓기/HANDOFF.md,
       --handoff로 다른 경로 지정 가능)에 자동 복구 사실을 한 줄 append한다.
     - exit code 1 (문제 발견 + 복구 완료)
  3. 같으면: 문제 없음 — exit code 0

이 스크립트가 서있는 워크플로우: Claude가 Write/Edit 도구로 파일을 고칠 때마다
그 직후 "의도한 최종 내용"을 임시파일에 저장해두고 이 스크립트를 호출해
검증한다. 사람이 매번 눈으로 wc -l을 세어보는 습관을, 스크립트 호출 습관으로
대체하는 것이 목적 — 진짜 의미의 자동 후크(hook)는 아니고, 매번 호출하는
"루틴"으로 동일한 효과를 낸다(알려진 한계: 호출 자체를 잊으면 소용없음 —
SKILL.md/CLAUDE.md류 문서에 이 루틴을 명시해두는 것으로 보완).
"""
import sys
import os
import argparse
import datetime


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def append_handoff_log(handoff_path, message):
    if not handoff_path or not os.path.isfile(handoff_path):
        return False
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(handoff_path, "a", encoding="utf-8") as f:
        f.write(f"\n- [자동복구 로그 {ts}] {message}\n")
    return True


def find_diverge_point(actual, expected):
    n = min(len(actual), len(expected))
    for i in range(n):
        if actual[i] != expected[i]:
            return i
    return n  # 공통 구간까지는 동일, 길이만 다름


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target_path", help="검사할 실제 파일 경로")
    parser.add_argument("expected_path", help="의도한 최종 내용이 담긴 임시 파일 경로")
    parser.add_argument("--handoff", dest="handoff_path", default=None,
                         help="자동 복구 시 한 줄 기록할 HANDOFF.md 경로 (생략 시 기록 안 함)")
    args = parser.parse_args()

    if not os.path.isfile(args.target_path):
        print(f"[ERROR] 대상 파일이 없음: {args.target_path}")
        sys.exit(2)
    if not os.path.isfile(args.expected_path):
        print(f"[ERROR] 의도한 내용 파일이 없음: {args.expected_path}")
        sys.exit(2)

    actual = read_bytes(args.target_path)
    expected = read_bytes(args.expected_path)

    if actual == expected:
        print(f"[OK] {args.target_path} — 손상 없음 ({len(actual)} bytes)")
        sys.exit(0)

    # 불일치 발견 — truncation으로 간주하고 자동 복구
    diverge_at = find_diverge_point(actual, expected)
    print(f"[MISMATCH] {args.target_path} — 실제 {len(actual)} bytes vs 의도 {len(expected)} bytes, {diverge_at}바이트 지점부터 다름")
    print("[ACTION] 자동 복구 시작: 기존 파일 rename 후 의도한 내용으로 재작성")

    ts_suffix = str(int(datetime.datetime.now().timestamp()))
    stale_path = f"{args.target_path}.stale-{ts_suffix}"
    os.rename(args.target_path, stale_path)
    with open(args.target_path, "wb") as f:
        f.write(expected)

    print(f"[FIXED] {args.target_path} 복구 완료 (기존 손상본은 {stale_path}로 보존)")

    logged = append_handoff_log(
        args.handoff_path,
        f"`{args.target_path}` 파일 동기화 버그(truncation) 자동 감지·복구됨 "
        f"(실제 {len(actual)}B vs 의도 {len(expected)}B, {diverge_at}B 지점부터 손상). "
        f"손상본: `{stale_path}`"
    )
    if args.handoff_path and not logged:
        print(f"[WARN] HANDOFF.md 경로가 없거나 못 찾음 — 기록 생략: {args.handoff_path}")

    sys.exit(1)


if __name__ == "__main__":
    main()
