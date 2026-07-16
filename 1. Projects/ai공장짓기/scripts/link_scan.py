#!/usr/bin/env python3
"""
link_scan.py — 옵시디언 위키링크([[...]]) 무결성 스캔 스크립트

배경 (2026-07-13, U3): 볼트 내 원본 바이너리(hwp/pdf/pptx/docx/hwpx/mp4/m4a/lnk 등)
파일은 의도적으로 볼트 밖(원래 위치)에 보관한다 — md 변환본이 전부 존재해 정보
손실은 없고, 바이너리를 볼트에 넣으면 sync·스캔 비용만 늘어난다. 이 설계 때문에
"[[...파일명.hwp|원본]]" 류 링크는 볼트 안에서 절대 못 찾는 게 정상이고, 링크
스캔이 이걸 매번 "깨진 링크"로 오탐하면 매 스캔마다 ~250건의 노이즈가 발생한다.

규칙: 링크 타깃의 확장자가 .md 가 아니면(확장자가 아예 없으면 암묵적 .md로 간주)
검사 대상에서 제외한다. .md(또는 확장자 없음) 링크만 실제로 깨졌는지 검사한다.

사용법:
  python3 link_scan.py <루트 디렉토리>
"""
import sys
import os
import re

WIKILINK = re.compile(r'\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]*)?\]\]')

NON_MD_EXT_NOTE = "비-md 확장자 — 원본 바이너리, 볼트 밖 보관 설계(U3) → 스캔 제외"


def find_md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


def build_basename_index(root):
    """루트 하위 모든 파일의 basename(확장자 포함) -> 상대경로 리스트."""
    index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            index.setdefault(fn, []).append(rel)
    return index


def has_non_md_extension(target):
    base = os.path.basename(target)
    _, ext = os.path.splitext(base)
    return bool(ext) and ext.lower() != ".md"


def resolve(target, root, basename_index):
    """target(확장자 없으면 .md 암묵) 이 루트 안에 실제로 존재하는지 확인."""
    candidate = target if target.endswith(".md") else target + ".md"
    # 1) 루트 기준 상대경로로 바로 존재
    if os.path.isfile(os.path.join(root, candidate)):
        return True
    # 2) 옵시디언처럼 basename 만으로도 어디든 매칭되면 존재로 간주
    base = os.path.basename(candidate)
    return base in basename_index


def scan(root):
    basename_index = build_basename_index(root)
    broken = []
    excluded_non_md = 0
    total_links = 0
    for md_path in find_md_files(root):
        with open(md_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        for m in WIKILINK.finditer(text):
            target = m.group(1).strip()
            total_links += 1
            if has_non_md_extension(target):
                excluded_non_md += 1
                continue
            if not resolve(target, root, basename_index):
                broken.append((md_path, target))
    return total_links, excluded_non_md, broken


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    total, excluded, broken = scan(root)
    for md_path, target in broken:
        print(f"[BROKEN] {md_path} -> [[{target}]]")
    print(f"[SUMMARY] 전체 위키링크 {total}개 / 비-md 제외 {excluded}개({NON_MD_EXT_NOTE}) / 깨짐 {len(broken)}개")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
