#!/usr/bin/env python3
"""pptx_writer.py — 표준 라이브러리만으로 .pptx 생성 (외부 패키지 불필요).

PPTX = Open XML 파일들의 zip. 최소 구성(마스터·레이아웃·테마·슬라이드)을 직접 만든다.
슬라이드: 16:9, 제목 + 본문 불릿 + 하단 노트(핵심 메시지·시간).

사용: write_pptx(path, title, slides)  # slides = deck["slides"] (present_engine)
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

EMU_W, EMU_H = 12192000, 6858000  # 16:9

NS_P = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'


def _content_types(n_slides: int) -> str:
    slides = "".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n_slides + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
{slides}</Types>"""


ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""


def _presentation(n_slides: int) -> str:
    ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>' for i in range(1, n_slides + 1))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation {NS_P}>
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst>{ids}</p:sldIdLst>
<p:sldSz cx="{EMU_W}" cy="{EMU_H}"/><p:notesSz cx="{EMU_H}" cy="{EMU_W}"/>
</p:presentation>"""


def _presentation_rels(n_slides: int) -> str:
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    for i in range(1, n_slides + 1):
        rels.append(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')
    rels.append(f'<Relationship Id="rId{n_slides + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels) + "</Relationships>")


THEME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Hyemi">
<a:themeElements>
<a:clrScheme name="Hyemi"><a:dk1><a:srgbClr val="1A1A2E"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="16213E"/></a:dk2><a:lt2><a:srgbClr val="F5F5F2"/></a:lt2>
<a:accent1><a:srgbClr val="FFD166"/></a:accent1><a:accent2><a:srgbClr val="27AE60"/></a:accent2>
<a:accent3><a:srgbClr val="C0392B"/></a:accent3><a:accent4><a:srgbClr val="2980B9"/></a:accent4>
<a:accent5><a:srgbClr val="8E44AD"/></a:accent5><a:accent6><a:srgbClr val="E67E22"/></a:accent6>
<a:hlink><a:srgbClr val="2980B9"/></a:hlink><a:folHlink><a:srgbClr val="8E44AD"/></a:folHlink></a:clrScheme>
<a:fontScheme name="Hyemi"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Arial"/><a:ea typeface="Malgun Gothic"/><a:cs typeface=""/></a:minorFont></a:fontScheme>
<a:fmtScheme name="Office">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme></a:themeElements></a:theme>"""


SLIDE_MASTER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster {NS_P}>
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>"""

SLIDE_MASTER_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""

SLIDE_LAYOUT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout {NS_P} type="blank">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""

LAYOUT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""

SLIDE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""


def _textbox(sp_id: int, name: str, x: int, y: int, w: int, h: int, paras: str) -> str:
    return f"""<p:sp><p:nvSpPr><p:cNvPr id="{sp_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
<p:txBody><a:bodyPr wrap="square" rtlCol="0"><a:normAutofit fontScale="90000"/></a:bodyPr><a:lstStyle/>{paras}</p:txBody></p:sp>"""


def _para(text: str, size: int, bold=False, color="1A1A2E", bullet=False) -> str:
    b = ' b="1"' if bold else ""
    bu = '<a:buChar char="•"/>' if bullet else "<a:buNone/>"
    return (f'<a:p><a:pPr marL="{285750 if bullet else 0}" indent="{-285750 if bullet else 0}">{bu}</a:pPr>'
            f'<a:r><a:rPr lang="ko-KR" sz="{size * 100}"{b} dirty="0">'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:rPr>'
            f'<a:t>{escape(text)}</a:t></a:r></a:p>')


def _slide_xml(s: dict, footer: str) -> str:
    """s: {no,title,key_message,bullets,evidence,seconds}"""
    title_paras = _para(f"{s['no']}. {s['title']}", 28, bold=True)
    key = _para(s["key_message"], 20, bold=True, color="C0392B")
    bullets = "".join(_para(b, 16, bullet=True) for b in s["bullets"] if b)
    if s.get("evidence"):
        bullets += _para(f"증빙: {s['evidence']}", 14, color="2980B9", bullet=True)
    meta = _para(f"{footer} · 권장 {s['seconds']}초", 11, color="7F8C8D")
    shapes = (
        _textbox(2, "Title", 457200, 274638, EMU_W - 914400, 800000, title_paras)
        + _textbox(3, "Key", 457200, 1200000, EMU_W - 914400, 700000, key)
        + _textbox(4, "Body", 457200, 2000000, EMU_W - 914400, 3800000, bullets or _para("", 16))
        + _textbox(5, "Meta", 457200, EMU_H - 550000, EMU_W - 914400, 400000, meta)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld {NS_P}>
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
{shapes}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""


def write_pptx(path: Path, project: str, slides: list) -> Path:
    """slides = present_engine deck["slides"]. 반환: 생성 파일 경로."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(slides)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _content_types(n))
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("ppt/presentation.xml", _presentation(n))
        z.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels(n))
        z.writestr("ppt/theme/theme1.xml", THEME)
        z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", SLIDE_MASTER_RELS)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", LAYOUT_RELS)
        for i, s in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(s, f"{project} — DRAFT"))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", SLIDE_RELS)
    return path
