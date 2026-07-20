#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""정부지원 매칭 리포트 생성기 — 고객에게 보낼 리포트 1장을 만든다.

수집기가 만든 candidates_*.json을 읽어, 사업체 하나에 맞는 후보만 골라
비개발자 사장님이 읽을 수 있는 md 리포트로 출력한다.

실행 예:
  python generate_report.py --business oncheon_flower \
      --input ../scripts/inbox/candidates_2026-07-17.json \
      --out 샘플리포트_온천꽃식물원.md

설계 원칙(중요):
  - 없는 정보를 지어내지 않는다. 미검수 후보는 "확인 전"이라고 그대로 쓴다.
  - 마감일을 못 읽은 건은 숨기지 않고 별도 섹션으로 뺀다(놓치면 손해라서).
  - 전문용어를 쓰지 않는다. 읽는 사람은 개발자가 아니다.
"""
import argparse
import io
import json
import os
from datetime import datetime, date

# 사업체 코드 → 사람이 읽는 이름
BUSINESS_NAMES = {
    "oncheon_flower": "온천꽃식물원",
    "daeryuk": "대륙창업",
    "moon": "모온(mo,on)",
}


def parse_deadline(v):
    """마감일 문자열을 날짜로. 못 읽으면 None."""
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return None


def days_left(d, today):
    return (d - today).days if d else None


def load_candidates(path, business):
    with io.open(path, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("candidates", data if isinstance(data, list) else [])
    out = []
    for c in rows:
        if business and business not in (c.get("matched_profiles") or []):
            continue
        out.append(c)
    return data, out


def why_matched(c, business):
    detail = c.get("match_detail") or {}
    reasons = detail.get(business) or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return ", ".join(reasons) if reasons else "사업 정보와 겹치는 항목이 있어 후보로 올림"


def esc(s):
    return str(s or "").replace("|", "／").replace("\n", " ").strip()


def build(data, rows, business, today):
    name = BUSINESS_NAMES.get(business, business or "전체")
    reviewed = [c for c in rows if c.get("reviewed")]
    unreviewed = [c for c in rows if not c.get("reviewed")]

    dated, undated = [], []
    for c in rows:
        d = parse_deadline(c.get("deadline"))
        (dated if d else undated).append((d, c))
    # 마감 지난 건 제외, 임박 순
    live = sorted([(d, c) for d, c in dated if d and d >= today], key=lambda x: x[0])
    expired = [(d, c) for d, c in dated if d and d < today]

    L = []
    A = L.append
    A("---")
    A("type: reference")
    A("status: active")
    A("tags: [정부지원]")
    A("---")
    A("")
    A(f"# {name} — 지원사업 후보 리포트")
    A("")
    A(f"**기준일**: {today.isoformat()}  |  **찾은 후보**: 총 {len(rows)}건")
    A("")
    A("> 정부·지자체가 올린 지원사업 공고 중에서, 사업자등록 정보(업종·지역·업력 등)와")
    A("> 겹치는 것만 자동으로 골라낸 목록입니다. **아직 신청서가 아니라 '후보'입니다** —")
    A("> 아래 목록에서 관심 가는 것을 알려주시면 자격 조건과 필요 서류를 자세히 확인해 드립니다.")
    A("")

    # --- 마감 임박 TOP 5 ---
    A("## ⏰ 먼저 볼 것 — 마감이 가까운 순서 TOP 5")
    A("")
    if live:
        A("| 공고 이름 | 주관 기관 | 마감일 | 남은 날 | 왜 골랐나 |")
        A("|---|---|---|---|---|")
        for d, c in live[:5]:
            n = days_left(d, today)
            urgent = "🔴" if n <= 7 else ("🟡" if n <= 14 else "")
            A(f"| {esc(c.get('program_name'))} | {esc(c.get('agency'))} | {d.isoformat()} "
              f"| {urgent} {n}일 | {esc(why_matched(c, business))} |")
    else:
        A("마감일이 확인된 진행 중인 공고가 이번 목록에는 없습니다.")
        A("(아래 '마감일을 못 읽은 공고'에 실제로 열려 있는 건이 섞여 있을 수 있어 확인이 필요합니다.)")
    A("")

    # --- 마감일 미확인 ---
    A("## ❓ 마감일을 못 읽은 공고 (직접 확인 필요)")
    A("")
    A(f"공고 페이지에서 마감일이 자동으로 읽히지 않은 건이 **{len(undated)}건** 있습니다.")
    A("숨기지 않고 그대로 보여드립니다 — 이 중에 아직 접수 중인 것이 있을 수 있습니다.")
    A("")
    if undated:
        A("| 공고 이름 | 주관 기관 | 공고일 | 원문 보기 |")
        A("|---|---|---|---|")
        for _, c in undated[:10]:
            A(f"| {esc(c.get('program_name'))} | {esc(c.get('agency'))} "
              f"| {esc(c.get('announcement_date')) or '-'} | [공고 원문]({c.get('source_url','')}) |")
        if len(undated) > 10:
            A("")
            A(f"…외 {len(undated)-10}건. 전체 목록이 필요하면 말씀해 주세요.")
    else:
        A("해당 없음.")
    A("")

    # --- 전체 목록 ---
    A("## 📋 전체 후보 목록")
    A("")
    A("| # | 공고 이름 | 기관 | 마감일 | 상태 |")
    A("|---|---|---|---|---|")
    ordered = [c for _, c in live] + [c for _, c in undated] + [c for _, c in expired]
    for i, c in enumerate(ordered, 1):
        d = parse_deadline(c.get("deadline"))
        if d and d < today:
            dl, st = d.isoformat(), "마감됨"
        elif d:
            dl, st = d.isoformat(), "접수 중"
        else:
            dl, st = "확인 필요", "마감일 미확인"
        A(f"| {i} | {esc(c.get('program_name'))} | {esc(c.get('agency'))} | {dl} | {st} |")
    A("")

    # --- 정직한 한계 ---
    A("## 📌 이 리포트에 대해 꼭 알아두실 것")
    A("")
    A(f"- **아직 사람이 확인하지 않은 후보가 {len(unreviewed)}건**입니다"
      f"{f' (확인 완료 {len(reviewed)}건)' if reviewed else ''}. "
      "기계가 공고 제목·기관·업종만 보고 골라낸 상태라, 실제로 신청 자격이 되는지는 "
      "공고 본문을 열어 봐야 알 수 있습니다.")
    A("- **자격 조건·필요 서류·지원금 액수는 아직 비어 있습니다.** 공고 본문(첨부 파일 포함)을 "
      "읽어야 채워지는 항목이라, 관심 있는 공고를 골라 주시면 그 건만 자세히 확인해 드립니다.")
    A("- 마감일이 자동으로 안 읽히는 공고가 있습니다(위 ❓ 섹션). 시스템의 한계이지 "
      "공고가 없다는 뜻이 아닙니다.")
    A("")
    A("## 다음에 하실 일")
    A("")
    A("1. 위 목록에서 관심 가는 공고 번호를 알려주세요.")
    A("2. 그 공고의 **자격 조건·필요 서류·지원금**을 확인해 정리해 드립니다.")
    A("3. 신청하기로 하시면 사업계획서 초안까지 만들어 드립니다. "
      "(제출은 반드시 사장님이 직접 하십니다 — 대신 접수하지 않습니다.)")
    A("")
    A(f"<!-- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
      f"원본: {os.path.basename(data.get('_src','')) or 'candidates json'} -->")
    A("")
    A("<!-- ok -->")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--business", required=True, help="사업체 코드 (oncheon_flower/daeryuk/moon)")
    ap.add_argument("--input", required=True, help="candidates_*.json 경로")
    ap.add_argument("--out", required=True, help="출력 md 경로")
    ap.add_argument("--today", default=None, help="기준일 YYYY-MM-DD (생략 시 오늘)")
    a = ap.parse_args()

    today = datetime.strptime(a.today, "%Y-%m-%d").date() if a.today else date.today()
    data, rows = load_candidates(a.input, a.business)
    data["_src"] = a.input
    if not rows:
        print(f"[경고] '{a.business}'에 해당하는 후보가 0건입니다. 사업체 코드를 확인하세요.")
    md = build(data, rows, a.business, today)
    with io.open(a.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"리포트 생성: {a.out}  (후보 {len(rows)}건)")


if __name__ == "__main__":
    main()
