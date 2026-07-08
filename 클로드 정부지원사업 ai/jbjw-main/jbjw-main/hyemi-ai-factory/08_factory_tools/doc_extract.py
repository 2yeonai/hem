#!/usr/bin/env python3
"""doc_extract.py — 공고문 파일(PDF/DOCX/HWPX/HWP/TXT/MD) 텍스트 추출.

원칙: 표준 라이브러리 우선. DOCX/HWPX는 zip+XML이라 의존성 0.
PDF는 pypdf, HWP(구형 OLE)는 olefile이 있으면 사용 — 없으면 설치 안내와 함께
'텍스트 붙여넣기' 폴백을 권한다. 이미지(OCR)는 로컬 불가 → AI 모드 안내.
어떤 실패도 예외로 앱을 멈추지 않는다: 항상 {text, kind, warnings} 반환.
"""
from __future__ import annotations

import re
import zipfile
import zlib
from io import BytesIO


def _clean(text: str) -> str:
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _xml_text(xml: bytes, para_tags: tuple) -> str:
    """XML에서 문단 태그 기준으로 줄바꿈을 살리며 텍스트만 추출."""
    s = xml.decode("utf-8", "ignore")
    for t in para_tags:
        s = s.replace(f"</{t}>", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    return s


def _docx(data: bytes) -> str:
    with zipfile.ZipFile(BytesIO(data)) as z:
        xml = z.read("word/document.xml")
    # 표 셀은 탭으로 구분해 배점표 파싱이 가능하게
    s = xml.decode("utf-8", "ignore").replace("</w:tc>", "\t")
    s = s.replace("</w:p>", "\n")
    return re.sub(r"<[^>]+>", "", s)


def _hwpx(data: bytes) -> str:
    out = []
    with zipfile.ZipFile(BytesIO(data)) as z:
        for name in sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml", n)):
            out.append(_xml_text(z.read(name), ("hp:p", "hp:tc")))
    return "\n".join(out)


def _hwp(data: bytes) -> str:
    """구형 HWP 5.x (OLE) — olefile 필요. BodyText 스트림 zlib 해제 후 UTF-16 텍스트 복원."""
    import olefile  # 선택적 의존성 (호출부에서 ImportError 처리)

    ole = olefile.OleFileIO(BytesIO(data))
    compressed = True
    if ole.exists("FileHeader"):
        compressed = bool(ole.openstream("FileHeader").read()[36] & 1)
    out = []
    for entry in ole.listdir():
        if entry[0] != "BodyText":
            continue
        raw = ole.openstream(entry).read()
        if compressed:
            try:
                raw = zlib.decompress(raw, -15)
            except zlib.error:
                continue
        # 레코드 순회: 태그 67(HWPTAG_PARA_TEXT)만 UTF-16LE로 해석
        i, n = 0, len(raw)
        while i + 4 <= n:
            hdr = int.from_bytes(raw[i:i + 4], "little")
            tag, size = hdr & 0x3FF, (hdr >> 20) & 0xFFF
            i += 4
            if size == 0xFFF:  # 확장 크기
                size = int.from_bytes(raw[i:i + 4], "little")
                i += 4
            if tag == 67 and i + size <= n:
                chars = []
                for j in range(0, size - 1, 2):
                    c = int.from_bytes(raw[i + j:i + j + 2], "little")
                    if c in (10, 13):
                        chars.append("\n")
                    elif c >= 32:
                        chars.append(chr(c))
                    # 0~31: HWP 제어문자 — 무시 (텍스트 우선 근사 추출)
                out.append("".join(chars))
            i += size
    ole.close()
    return "\n".join(out)


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader  # 선택적 의존성

    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_text(filename: str, data: bytes) -> dict:
    """반환: {"text": str, "kind": str, "warnings": [str]} — 절대 예외를 올리지 않는다."""
    name = (filename or "").lower()
    warnings: list = []
    kind, text = "unknown", ""
    try:
        if name.endswith((".txt", ".md")):
            kind, text = "txt", data.decode("utf-8", "ignore")
        elif name.endswith(".docx"):
            kind, text = "docx", _docx(data)
        elif name.endswith(".hwpx"):
            kind, text = "hwpx", _hwpx(data)
        elif name.endswith(".hwp"):
            kind = "hwp"
            try:
                text = _hwp(data)
                warnings.append("HWP 추출은 근사치 — 표·서식 유실 가능. 원문 대조 필수 [확인 필요]")
            except ImportError:
                warnings.append("HWP(구형) 추출에는 `pip install olefile` 필요 — 또는 한글에서 '다른 이름으로 저장 → HWPX/PDF' 후 재업로드")
        elif name.endswith(".pdf"):
            kind = "pdf"
            try:
                text = _pdf(data)
                if len(text.strip()) < 50:
                    warnings.append("PDF에서 텍스트가 거의 없음 — 스캔 이미지 PDF일 가능성. AI 모드(비전) 또는 원문 텍스트 붙여넣기 필요")
            except ImportError:
                warnings.append("PDF 추출에는 `pip install pypdf` 필요 (1회) — 설치 후 재업로드하거나 텍스트를 붙여넣어라")
        elif name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
            kind = "image"
            warnings.append("이미지 OCR은 로컬 모드에서 불가 — AI 모드(API·비전) 사용 또는 공고 텍스트를 직접 붙여넣기")
        else:
            warnings.append(f"미지원 형식({name.rsplit('.', 1)[-1] if '.' in name else '?'}) — PDF/HWP/HWPX/DOCX/TXT 지원")
    except Exception as e:  # 어떤 파일이 와도 앱은 멈추지 않는다
        warnings.append(f"추출 실패: {type(e).__name__}: {e} — 텍스트 붙여넣기로 진행 가능")
    text = _clean(text)
    if text and len(text) < 200:
        warnings.append("추출 텍스트가 짧음 — 원문 전체가 맞는지 확인 필요")
    return {"text": text, "kind": kind, "warnings": warnings}
