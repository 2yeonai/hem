#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_viz_data.py — 3D 시각화용 파생 데이터 추출기 (1단계)

app/data.json(파싱된 96장 카드: frontmatter + sections)을 읽어,
각 카드에서 시각화에 필요한 파생 필드만 뽑아 app/viz_data.json 으로 저장한다.
원본 data.json/parse_cards.py 는 건드리지 않는다(뷰어는 두 파일을 함께 로드).

추출 항목:
- 근육명(신/구용어 슬래시 병기 보존) + 근육명_영문 + 약어(SCM 등)
- 각 ART/MET/운동/촉진 섹션의 "자세:" 텍스트(대상자/검사자) + 자세태그 분류
  (앉기/누움/엎드림/옆누움/서기 중 가장 가까운 것, 애매하면 태그 비움)
- 손의 접촉/방법에서 스트로크·압박 방향 문장을 화살표 힌트로 추출(원문 보존, 지어내지 않음)
- 체인 필드(의심근육→/테크닉→/재검사→/연관검사→) 파싱
- 검사카드: 자세(대상자/검사자), 양성 판단 요약, 의심근육
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\82106\Desktop\hem\1. Projects\클로드 RTS AI")
DATA_PATH = ROOT / "app" / "data.json"
OUT_PATH = ROOT / "app" / "viz_data.json"

# ---------- 자세태그 분류 규칙 ----------
# 순서 중요: '옆으로 누'/'엎드리'를 '누'보다 먼저 매칭해야 오분류 방지
POSE_RULES = [
    ("엎드림", ["엎드리", "엎드려", "엎드린", "복와위", "prone"]),
    ("옆누움", ["옆으로 누", "옆으로 눕", "측와위", "side-lying", "sidelying", "옆누움"]),
    ("누움", ["바로 누", "누운", "누워", "누우", "앙와위", "후킹", "후크", "hook-lying", "hooklying", "supine", "반듯이 누", "눕힌", "눕는"]),
    ("앉기", ["앉은", "앉아", "앉힌", "앉힘", "앉게", "좌위", "seated", "sitting"]),
    ("서기", ["선 자세", "서서", "서 있", "기립", "standing", "까치발", "벽에 서", "벽을 보고 서", "일어서", "서기"]),
]


def clean_label(s):
    """마크다운(**·-··)·'대상자:/검사자:' 접두어 제거해 라벨용 텍스트로 정리."""
    s = str(s or "")
    s = re.sub(r"^\s*[-*·]+\s*", "", s)
    s = s.replace("**", "")
    s = re.sub(r"^\s*(대상자|검사자)\s*[:：]\s*", "", s)
    return s.strip(" *:：.")

# 스트로크/압박 방향을 담은 문장을 뽑기 위한 동사·방향 키워드
ARROW_VERBS = ["쓸어올린", "쓸어내린", "쓸어", "쓸기", "밀어", "밀기", "눌러", "누르며", "당겨", "당기며",
               "올린다", "내린다", "긁", "훑", "쓸어주", "쓸어 올", "짜올린", "짜 올린"]
ARROW_DIRS = ["위로", "아래로", "위쪽", "아래쪽", "안쪽", "바깥쪽", "머리 쪽", "목 쪽", "목걸이",
              "쇄골", "흉골", "심장 쪽", "원위", "근위", "상방", "하방", "외측", "내측",
              "몸쪽", "발쪽", "종골", "부착부", "정지부", "기시부", "→"]


def classify_pose(text):
    """자세 텍스트 → 자세태그(앉기/누움/엎드림/옆누움/서기) 또는 '' (애매)."""
    if not text:
        return ""
    low = text.lower()
    for tag, kws in POSE_RULES:
        for kw in kws:
            if kw.lower() in low:
                return tag
    return ""


def parse_pose_line(raw):
    """'대상자 앉은 자세 / 검사자 대상자 후방' → (subject, operator)."""
    s = str(raw).replace("**", "").strip()
    # '검사자' 표지를 기준으로 대상자/검사자 분리(설명 내부의 '/'에 영향받지 않도록)
    parts = re.split(r"\s*/?\s*검사자\s*[:：]?\s*", s, maxsplit=1)
    subj = re.sub(r"^\s*대상자\s*[:：]?\s*", "", parts[0])
    oper = parts[1] if len(parts) > 1 else ""
    return clean_label(subj), clean_label(oper)


def extract_poses(sections):
    """ART/MET/운동/촉진 섹션에서 자세 텍스트 추출.
    반환: [{section, subject_raw, operator_raw, pose_tag}]"""
    poses = []
    sec_re = re.compile(r"^(ART|MET|운동|테크닉|셀프|평가|촉진)", re.IGNORECASE)
    for heading, body in sections.items():
        if not sec_re.search(heading):
            continue
        # '**자세:** ...' 또는 '자세: ...' 또는 '대상자 자세: ...'
        found = None
        for line in body.split("\n"):
            l = line.strip()
            m = re.match(r"^\*{0,2}(?:자세|대상자 자세)\*{0,2}\s*[:：]\s*(.+)$", l)
            if m:
                found = m.group(1).strip()
                break
        if not found:
            continue
        subj, oper = parse_pose_line(found)
        poses.append({
            "section": heading,
            "subject_raw": subj,
            "operator_raw": oper,
            "pose_tag": classify_pose(subj) or classify_pose(found),
        })
    return poses


def infer_pose_from_body(sections):
    """명시적 '자세:' 줄이 없을 때, 촉진/ART/MET/운동 본문 산문에서 자세를 보수적으로 추론.
    정확히 한 가지 자세 범주만 등장할 때에만 그 태그를 반환(여럿/없음이면 '')."""
    sec_re = re.compile(r"^(ART|MET|운동|테크닉|셀프|촉진|이완|스트레칭)", re.IGNORECASE)
    blob = " ".join(b for h, b in sections.items() if sec_re.search(h))
    if not blob:
        return ""
    low = blob.lower()
    found = []
    for tag, kws in POSE_RULES:
        if any(kw.lower() in low for kw in kws):
            found.append(tag)
    return found[0] if len(found) == 1 else ""


def split_sentences(text):
    return re.split(r"[\n。.]|(?<=다)\s+(?=[①-⑨])", text)


def extract_arrow_hints(sections):
    """촉진/ART/MET/운동 섹션에서 방향성 문장을 화살표 힌트로 추출(원문 보존)."""
    hints = []
    seen = set()
    sec_re = re.compile(r"^(ART|MET|운동|테크닉|촉진)", re.IGNORECASE)
    for heading, body in sections.items():
        if not sec_re.search(heading):
            continue
        for sent in split_sentences(body):
            s = sent.strip(" -*①②③④⑤⑥⑦⑧⑨\t")
            if len(s) < 4 or len(s) > 90:
                continue
            has_verb = any(v in s for v in ARROW_VERBS)
            has_dir = any(d in s for d in ARROW_DIRS)
            if has_verb and has_dir:
                key = s[:40]
                if key in seen:
                    continue
                seen.add(key)
                hints.append({"section": heading, "text": s})
            if len(hints) >= 6:
                return hints
    return hints


def split_respecting_parens(s):
    out, depth, cur = [], 0, ""
    for c in s:
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        if c == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        out.append(cur)
    return out


def parse_arrow_field(raw):
    """app.js parseArrowField 재현: 괄호 설명 제거, 콤마 분리, 미기재/위키링크 정리."""
    if raw is None:
        return []
    if isinstance(raw, list):
        vals = raw
    else:
        s = str(raw)
        m = re.search(r"\[([\s\S]*)\]", s)
        inner = m.group(1) if m else s
        if inner.strip().startswith("미기재"):
            return []
        vals = split_respecting_parens(inner)
    out = []
    for x in vals:
        x = str(x)
        x = re.sub(r"\(.*?\)", "", x)          # 괄호 설명 제거
        x = re.sub(r"[\[\]]", "", x)           # 위키링크·대괄호 전부 제거
        x = x.replace("테크닉_", "").replace("검사_", "")
        x = re.sub(r"^[\"']|[\"']$", "", x).strip(" .·—-")
        # '통합 카드 참조' 같은 설명 꼬리 제거
        x = re.split(r"\s{2,}|\s*—\s*|\s+참조|\s+통합", x)[0].strip()
        if x and x != "미기재" and not x.startswith("본 검사"):
            out.append(x)
    return out


ABBR_RE = re.compile(r"\(([A-Z][A-Za-z]{1,4}(?:/[A-Z][A-Za-z]{1,4})?)\)")


def extract_abbr(en, ko):
    for src in (en, ko):
        m = ABBR_RE.search(src or "")
        if m:
            return m.group(1)
    return ""


def muscle_label(ko, en, abbr):
    """'구용어(이명) / 영어·약자' 라벨 구성요소."""
    parts = [p.strip() for p in str(ko).split("/") if p.strip()]
    new = parts[0] if parts else str(ko)
    old = parts[1] if len(parts) > 1 else ""
    en_short = ""
    if en:
        # 괄호 앞 첫 표제 영문만
        en_short = re.split(r"\(", str(en))[0].strip()
    sci = abbr if abbr else en_short
    return {"full": ko, "new": new, "old": old, "en": en, "en_short": en_short,
            "abbr": abbr, "sci": sci}


def first_lines(text, n=2):
    if not text:
        return ""
    lines = [re.sub(r"^[-*①②③④⑤⑥⑦⑧⑨\s]+", "", l).strip()
             for l in text.split("\n")]
    lines = [l for l in lines if l]
    return " / ".join(lines[:n])


def build_card(card):
    fm = card["frontmatter"]
    sec = card["sections"]
    out = {
        "id": card["id"],
        "type": card["type"],
        "title": card["title"],
        "part": fm.get("파트", ""),
        "date": fm.get("날짜", ""),
    }
    poses = extract_poses(sec)
    out["poses"] = poses
    tags = [p["pose_tag"] for p in poses if p["pose_tag"]]
    if tags:
        out["primary_pose_tag"] = tags[0]
        out["pose_source"] = "explicit"
    else:
        inferred = infer_pose_from_body(sec)
        out["primary_pose_tag"] = inferred
        out["pose_source"] = "inferred" if inferred else ""
    out["arrow_hints"] = extract_arrow_hints(sec)
    out["chain"] = {
        "suspect_muscles": parse_arrow_field(fm.get("의심근육→")),
        "techniques": parse_arrow_field(fm.get("테크닉→")),
        "retests": parse_arrow_field(fm.get("재검사→")),
        "related_assessments": parse_arrow_field(fm.get("연관검사→")),
    }

    if card["type"] == "테크닉카드":
        abbr = extract_abbr(fm.get("근육명_영문", ""), fm.get("근육명", ""))
        out["muscle"] = muscle_label(fm.get("근육명", ""), fm.get("근육명_영문", ""), abbr)
        out["technique_types"] = fm.get("테크닉_유형", "")
        out["palpation"] = sec.get("촉진 (Palpation)", "")
        out["one_liner"] = first_lines(sec.get("핵심 한 줄", ""), 1)
    else:  # 검사카드
        out["assessment_name"] = fm.get("검사명", "")
        out["joint"] = fm.get("관절", "")
        out["level"] = fm.get("레벨", "")
        # 자세 섹션(대상자/검사자) 파싱
        pose_sec = sec.get("자세", "")
        subj = oper = ""
        for line in pose_sec.split("\n"):
            l = re.sub(r"^\s*[-*·]+\s*", "", line.strip()).replace("**", "")
            ms = re.match(r"^대상자\s*[:：]\s*(.+)$", l)
            mo = re.match(r"^검사자\s*[:：]\s*(.+)$", l)
            if ms:
                subj = clean_label(ms.group(1))
            if mo:
                oper = clean_label(mo.group(1))
        if not subj and pose_sec:
            subj = clean_label(first_lines(pose_sec, 1))
        out["assess_pose"] = {"subject_raw": subj, "operator_raw": oper,
                              "pose_tag": classify_pose(subj) or classify_pose(pose_sec)}
        if not out["primary_pose_tag"]:
            out["primary_pose_tag"] = out["assess_pose"]["pose_tag"]
        out["positive"] = first_lines(sec.get("양성 판단", ""), 2)
    return out


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    cards = {}
    no_pose = []
    for grp in ("assessments", "techniques"):
        for c in data[grp]:
            vc = build_card(c)
            cards[vc["id"]] = vc
            if not vc["primary_pose_tag"]:
                no_pose.append(vc["id"])

    result = {
        "generated_from": "app/data.json",
        "counts": {
            "assessments": len(data["assessments"]),
            "techniques": len(data["techniques"]),
            "total": len(cards),
        },
        "cards": cards,
    }
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8")

    # 요약(콘솔 안전: 숫자 위주)
    tagged = sum(1 for v in cards.values() if v["primary_pose_tag"])
    print(f"[build_viz_data] cards={len(cards)} pose_tagged={tagged} no_pose={len(no_pose)}")
    print(f"  -> {OUT_PATH}")
    if no_pose:
        (ROOT / "app" / "viz_no_pose.txt").write_text(
            "\n".join(no_pose), encoding="utf-8")
        print(f"  자세태그 미분류 {len(no_pose)}건 목록 -> app/viz_no_pose.txt")


if __name__ == "__main__":
    main()
