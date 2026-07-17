#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카드 md 파일들(1. Projects/클로드 RTS AI/카드/*.md)을 app/data.json 스키마로 변환.
HANDOFF_카드재작성_2026-07-17.md에 기술된 로직 재현:
- 카드 폴더의 모든 *.md 프론트매터(YAML) + '## 헤딩' 단위 섹션 파싱
- 검사카드/테크닉카드로 분류해 {assessments:[...], techniques:[...]} 구조의 data.json 생성
- json.dump(..., default=str) 필수 (created 필드가 date 객체일 수 있음)
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(r"C:\Users\82106\Desktop\hem\1. Projects\클로드 RTS AI")
CARD_DIR = ROOT / "카드"
OUT_PATH = ROOT / "app" / "data.json"

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)
TITLE_RE = re.compile(r"^# (.+)$", re.MULTILINE)
SECTION_SPLIT_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def normalize_section_text(text):
    text = text.strip("\n")
    if not text.strip():
        return ""
    paragraphs = re.split(r"\n[ \t]*\n+", text)
    lines = [p.strip() for p in paragraphs if p.strip()]
    return "\n".join(lines)


def parse_card(path: Path):
    raw = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(raw)
    if not m:
        raise ValueError(f"frontmatter not found: {path}")
    fm_text, body = m.group(1), m.group(2)

    try:
        frontmatter = yaml.safe_load(fm_text)
        if not isinstance(frontmatter, dict):
            raise ValueError("frontmatter did not parse to dict")
    except Exception as e:
        # 줄 단위 fallback: key: value 형태만 문자열로 저장
        frontmatter = {}
        for line in fm_text.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                frontmatter[k.strip()] = v.strip()
        print(f"  [WARN] YAML parse failed for {path.name}, used line fallback: {e}", file=sys.stderr)

    title_m = TITLE_RE.search(body)
    title = title_m.group(1).strip() if title_m else path.stem

    # 섹션 파싱: '## ' 헤딩 기준으로 분리 (본문에서 타이틀 라인 이후부터)
    sections = {}
    matches = list(SECTION_SPLIT_RE.finditer(body))
    for i, mm in enumerate(matches):
        heading = mm.group(1).strip()
        start = mm.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end]
        # sentinel(<!-- ok -->)이 마지막 섹션 뒤에 붙는 경우 제거
        content = content.replace("<!-- ok -->", "")
        sections[heading] = normalize_section_text(content)

    card_id = frontmatter.get("id", path.stem)
    card_type = frontmatter.get("type", "")

    return {
        "id": card_id,
        "type": card_type,
        "title": title,
        "frontmatter": frontmatter,
        "sections": sections,
    }


def main():
    assessments = []
    techniques = []
    errors = []

    for path in sorted(CARD_DIR.glob("*.md")):
        try:
            card = parse_card(path)
        except Exception as e:
            errors.append((path.name, str(e)))
            continue
        if card["type"] == "검사카드":
            assessments.append(card)
        elif card["type"] == "테크닉카드":
            techniques.append(card)
        else:
            errors.append((path.name, f"unknown type: {card['type']!r}"))

    if errors:
        print("=== 파싱 실패/미분류 파일 ===", file=sys.stderr)
        for name, msg in errors:
            print(f"  {name}: {msg}", file=sys.stderr)

    data = {"assessments": assessments, "techniques": techniques}

    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"검사카드 {len(assessments)}장, 테크닉카드 {len(techniques)}장 -> {OUT_PATH}")
    print(f"총 {len(assessments) + len(techniques)}장 / 실패 {len(errors)}건")


if __name__ == "__main__":
    main()
