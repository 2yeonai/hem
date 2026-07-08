#!/usr/bin/env python3
"""docx_writer.py — 표준 라이브러리만으로 .docx 생성 (사업계획서 초안 Export용).

DOCX = Open XML zip. 제목/부제/본문/표를 지원하는 최소 구성.
사용: write_docx(path, title, blocks)
  blocks: [("h1"|"h2"|"p"|"hint", text) | ("table", {"head": [...], "rows": [[...]]})]
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _p(text: str, size=22, bold=False, color="000000") -> str:
    runs = ""
    for i, line in enumerate(text.split("\n")):
        br = "<w:br/>" if i else ""
        runs += (f'{br}<w:r><w:rPr><w:rFonts w:eastAsia="Malgun Gothic"/>'
                 f'{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/>'
                 f'<w:color w:val="{color}"/></w:rPr><w:t xml:space="preserve">{escape(line)}</w:t></w:r>')
    return f"<w:p>{runs}</w:p>"


def _table(head: list, rows: list) -> str:
    def row(cells, bold=False):
        tcs = "".join(
            f'<w:tc><w:tcPr><w:tcBorders>'
            f'<w:top w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/>'
            f'<w:left w:val="single" w:sz="4"/><w:right w:val="single" w:sz="4"/></w:tcBorders></w:tcPr>'
            + _p(str(c), 20, bold) + "</w:tc>"
            for c in cells)
        return f"<w:tr>{tcs}</w:tr>"
    body = row(head, True) + "".join(row(r) for r in rows)
    return f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>{body}</w:tbl><w:p/>'


def write_docx(path: Path, title: str, blocks: list) -> Path:
    parts = [_p(title, 32, True), _p("")]
    for kind, content in blocks:
        if kind == "h1":
            parts.append(_p(content, 28, True, "1A1A2E"))
        elif kind == "h2":
            parts.append(_p(content, 24, True, "2455D6"))
        elif kind == "hint":
            parts.append(_p(content, 18, False, "777777"))
        elif kind == "table":
            parts.append(_table(content["head"], content["rows"]))
        else:
            parts.append(_p(content))
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {W}><w:body>{"".join(parts)}'
           f'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def draft_to_docx(project: str, res: dict, out_dir: Path) -> Path | None:
    """사업계획서 초안(document.draft) → application_draft.docx. 초안 없으면 None."""
    doc = res.get("document", {})
    draft = doc.get("draft", {})
    if not draft.get("ready"):
        return None
    blocks = [("hint", f"상태: DRAFT — [확인 필요] 해소·사람 검수 전 제출 금지 / 생성 {res.get('generated_at', '')}"),
              ("h2", "과제명(초안): " + draft.get("title", "")),
              ("p", "한 줄 요약: " + draft.get("summary", ""))]
    for s in draft["sections"]:
        blocks.append(("h1", f"{s['no']}. {s['title']}"))
        blocks.append(("p", s["body"]))
        if s.get("table"):
            blocks.append(("table", {"head": s["table"]["head"],
                                     "rows": [[str(c) for c in r] for r in s["table"]["rows"]]}))
        blocks.append(("hint", "가이드: " + " / ".join(s.get("guide", []))))
    bt = doc.get("budget_table", {})
    if bt.get("ready"):
        blocks.append(("h1", "연결형 예산표"))
        blocks.append(("table", {"head": ["항목", "금액", "목적", "산출물", "산정 근거", "연결 평가항목", "기대성과"],
                                 "rows": [[r["item"], r["amount"], r["purpose"], r["output"],
                                           r["basis"], r["linked_item"], r["expected"]] for r in bt["rows"]]}))
    return write_docx(out_dir / "application_draft.docx", f"사업계획서 초안 — {project}", blocks)
