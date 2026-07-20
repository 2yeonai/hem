#!/usr/bin/env python3
"""카드 96장 frontmatter에서 전사문 인용 필드(날짜/출처/검증상태) 제거.

혜미 지시(2026-07-19): "전사문 3.20이런거 빼" — 카드가 강의 전사문에서
만들어진 티가 나는 raw 파일명/날짜 인용(예: "3.20.md 강의 전사 원본",
"날짜: 4/9", "검증상태: 전사원문확인")을 제거해 전문 레퍼런스 톤으로 정리.
"""
import re
import sys
from pathlib import Path

CARD_DIR = Path(__file__).resolve().parent.parent / "카드"
FIELDS_TO_STRIP = {"날짜", "출처", "검증상태"}

def strip_frontmatter_fields(text: str) -> tuple[str, list[str]]:
    if not text.startswith("---\n"):
        raise ValueError("frontmatter가 --- 로 시작하지 않음")
    end = text.index("\n---\n", 4)
    fm_block = text[4:end]
    rest = text[end + 5:]

    lines = fm_block.split("\n")
    removed = []
    kept = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([^\s:][^:]*):", line)
        if m and m.group(1) in FIELDS_TO_STRIP:
            removed.append(line)
            i += 1
            # 값이 다음 줄로 이어지는 경우(들여쓰기)까지 같이 제거
            while i < len(lines) and lines[i].startswith(("  ", "\t")):
                removed.append(lines[i])
                i += 1
            continue
        kept.append(line)
        i += 1

    new_fm = "\n".join(kept)
    new_text = "---\n" + new_fm + "\n---\n" + rest
    return new_text, removed


def main():
    files = sorted(CARD_DIR.glob("*.md"))
    if not files:
        print("카드 파일을 찾지 못함:", CARD_DIR)
        sys.exit(1)

    changed = 0
    no_sentinel = []
    for f in files:
        original = f.read_text(encoding="utf-8")
        new_text, removed = strip_frontmatter_fields(original)
        if not removed:
            continue
        if "<!-- ok -->" not in new_text.rstrip().splitlines()[-1:]:
            # sentinel이 마지막 비어있지 않은 줄이 아니면 기록만 하고 계속 진행
            last_nonempty = [l for l in new_text.rstrip().splitlines() if l.strip()][-1] if new_text.strip() else ""
            if last_nonempty.strip() != "<!-- ok -->":
                no_sentinel.append(f.name)
        f.write_text(new_text, encoding="utf-8", newline="\n")
        changed += 1

    print(f"총 파일: {len(files)}, 수정됨: {changed}")
    if no_sentinel:
        print("⚠️ sentinel 누락 의심 파일:", no_sentinel)
    else:
        print("sentinel 전수 확인 완료")


if __name__ == "__main__":
    main()
