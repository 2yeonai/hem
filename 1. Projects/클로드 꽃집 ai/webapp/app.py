#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webapp/app.py - 꽃집(온천꽃식물원) 파이프라인을 휴대폰 브라우저에서 실시간으로 쓸 수
있게 만든 최소 웹앱(2026-07-17 신설, 혜미 요청: "모바일에서 확인/승인").

원칙: 이 폴더 밖(../code)의 봇 파일은 한 글자도 수정하지 않는다. run_pipeline.py와
flower_adapter.py가 이미 만들어둔 "code/를 sys.path에 추가하고 평범하게 import" 방식을
그대로 재사용해서, 12봇_kind분류표.yaml의 실제 stage 함수를 그대로 호출만 한다.

이 웹앱이 하는 일 (run_pipeline.py의 흐름을 그대로 웹 화면으로 노출):
  1. 새 문의 입력(/new) -> collection_bot ~ review_manager_bot까지 실행 -> 사람 승인
     대기 목록(pending_orders.json)에 저장. human_reviewer 이전에서 멈춘다(자동승인 없음
     - run_pipeline.py의 _mock_human_stage와 다르게, 여기서는 진짜로 사람이 눌러야 함).
  2. 대기 목록(/) -> review_priority(빨강/노랑/파랑/초록) 순으로 정렬해서 보여줌.
  3. 상세 화면(/order/<id>)에서 값을 확인/수정 후 승인(-> storage_bot ~ sms_ledger_bot까지
     실행) 또는 반려(대기 목록에서만 제거 - "반려 시 되돌아갈 단계(return_to)"는 원래
     설계 문서에도 없는 미정 항목이라는 걸 승인화면_프로토타입_v1.html README와 동일하게
     화면에도 그대로 밝힌다).

알려진 한계(숨기지 않고 명시):
  - order_split_bot이 여러 세그먼트(다중 주문)를 감지해도 이 웹앱은 첫 번째 세그먼트만
    처리한다(flower_adapter.py 발견사항 3과 동일한 한계 - 부분 fan-out은 미지원).
  - 승인화면_프로토타입_v1.html이 설계한 3단계(검수저장/주문확정/출력준비) 대신, 이
    웹앱은 "승인" 한 번으로 저장+인쇄준비+배차+배송사진+문자발송까지 한번에 처리한다
    (실사용 검증 전까지의 단순화 - 나중에 3단계로 쪼갤 수 있음).
  - 여러 사람이 동시에 승인 버튼을 누르는 경우의 충돌 처리는 없다(작은 가게 1인 운영
    기준으로 설계, 동시 편집 잠금 없음).
"""

import json
import sys
import uuid
from html import escape
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

WEBAPP_DIR = Path(__file__).resolve().parent
FLOWER_DIR = WEBAPP_DIR.parent
CODE_DIR = FLOWER_DIR / "code"

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import collection_bot
import correction_bot
import delivery_photo_bot
import dispatch_bot
import order_classification_bot as ocb
import order_draft_bot
import order_split_bot as osb
import print_prep_bot
import review_manager_bot
import ribbon_price_bot
import sms_ledger_bot
import storage_bot
import transcription_bot

PENDING_PATH = WEBAPP_DIR / "pending_orders.json"
STOP_CLASSIFICATIONS = {"단순문의", "일반통화", "스팸무관"}
PRIORITY_ORDER = {"빨강": 0, "노랑": 1, "파랑": 2, "초록": 3}
PRIORITY_COLOR = {"빨강": "#e5484d", "노랑": "#f5a623", "파랑": "#3b82f6", "초록": "#22c55e"}

app = Flask(__name__)


def _load_pending() -> dict:
    if not PENDING_PATH.is_file():
        return {}
    return json.loads(PENDING_PATH.read_text(encoding="utf-8"))


def _save_pending(data: dict) -> None:
    PENDING_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif;
         max-width: 480px; margin: 0 auto; padding: 16px; background: #f7f7f8; color: #1a1a1a; }
  h1 { font-size: 20px; } h2 { font-size: 17px; }
  .card { background: white; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-decoration: none; color: inherit; display: block; }
  .badge { display: inline-block; color: white; font-size: 12px; font-weight: 600;
           padding: 2px 8px; border-radius: 999px; margin-right: 6px; }
  .field { margin-bottom: 10px; }
  .field label { display: block; font-size: 12px; color: #666; margin-bottom: 3px; }
  .field input, .field textarea { width: 100%; box-sizing: border-box; padding: 8px 10px;
           border: 1px solid #ddd; border-radius: 8px; font-size: 15px; }
  .warn { color: #e5484d; font-size: 12px; font-weight: 600; }
  .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 10px;
         font-size: 16px; font-weight: 600; margin-top: 10px; text-align: center; }
  .btn-approve { background: #22c55e; color: white; }
  .btn-reject { background: #eee; color: #e5484d; }
  .btn-new { background: #3b82f6; color: white; }
  .note { font-size: 12px; color: #888; margin-top: 4px; }
  a.back { color: #666; text-decoration: none; font-size: 14px; }
</style>
"""


@app.route("/")
def index():
    pending = _load_pending()
    items = sorted(
        pending.items(),
        key=lambda kv: PRIORITY_ORDER.get(kv[1]["review"]["review_priority"], 9),
    )
    cards = ""
    for pid, o in items:
        pr = o["review"]["review_priority"]
        color = PRIORITY_COLOR.get(pr, "#999")
        cards += (
            f'<a class="card" href="{url_for("detail", pid=pid)}">'
            f'<span class="badge" style="background:{color}">{pr}</span>'
            f'{escape(o["draft"].get("product") or "(상품 미확인)")} / '
            f'{escape(str(o["ribbon"].get("price") or "?"))}원'
            f'<div class="note">{escape(o["created_at"])}</div></a>'
        )
    if not cards:
        cards = '<p class="note">대기 중인 주문이 없습니다.</p>'
    html = f"""
    {BASE_STYLE}
    <h1>🌸 검수 대기 ({len(items)}건)</h1>
    {cards}
    <a class="btn btn-new" href="{url_for('new_order')}">+ 새 문의 입력</a>
    """
    return render_template_string(html)


@app.route("/new", methods=["GET", "POST"])
def new_order():
    if request.method == "GET":
        html = f"""
        {BASE_STYLE}
        <a class="back" href="{url_for('index')}">← 목록</a>
        <h1>새 문의 입력</h1>
        <form method="post">
          <div class="field"><label>수신 경로</label>
            <select name="source_type" style="width:100%;padding:8px;border-radius:8px;border:1px solid #ddd;">
              <option value="kakao">카카오톡</option>
              <option value="sms">문자</option>
              <option value="call">전화(받아적은 내용)</option>
              <option value="manual">직접 입력</option>
            </select>
          </div>
          <div class="field"><label>받은 내용(문자/카톡 원문 그대로 붙여넣기)</label>
            <textarea name="raw_text" rows="6" required></textarea>
          </div>
          <button class="btn btn-approve" type="submit">AI 판단 시작</button>
        </form>
        """
        return render_template_string(html)

    source_type = request.form.get("source_type", "kakao")
    raw_text = request.form.get("raw_text", "").strip()

    ctx = collection_bot.collect(source_type=source_type, raw_text=raw_text)
    tr = transcription_bot.transcribe(raw_audio=None, raw_image=None, raw_text=ctx["raw_text"])
    text = tr["stt_text"] or tr["ocr_text"] or ctx["raw_text"] or ""

    cls = ocb.classify_order(text)
    if cls["order_classification"] in STOP_CLASSIFICATIONS:
        html = f"""
        {BASE_STYLE}
        <a class="back" href="{url_for('index')}">← 목록</a>
        <h1>주문이 아닌 것으로 판단됨</h1>
        <p>AI 판단: <b>{escape(cls['order_classification'])}</b> - {escape(cls['reason'])}</p>
        <p class="note">주문이 맞는데 이렇게 나왔다면, AI가 헷갈린 경우입니다(알려진 한계). 다시 입력해보세요.</p>
        """
        return render_template_string(html)

    split = osb.split_order(text)
    if len(split["order_segments"]) > 1:
        note = f"⚠ 이 문의 안에 주문이 {len(split['order_segments'])}건 섞여있을 수 있습니다 - 첫 번째만 처리했고, 나머지는 따로 입력해주세요."
    else:
        note = ""
    seg = split["order_segments"][0]

    correction = correction_bot.correct_text(seg["segment_text"])
    draft = order_draft_bot.build_draft(correction["normalized_text"])
    ribbon = ribbon_price_bot.process_ribbon_and_price(draft["order_draft"], correction["normalized_text"])
    review = review_manager_bot.build_review(
        order_draft=draft["order_draft"],
        field_confidence=draft["field_confidence"],
        field_sources=draft["field_sources"],
        missing_fields=draft["missing_fields"],
        candidates=correction["candidates"],
        ribbon_message_raw=ribbon["ribbon_message_raw"],
        ribbon_message_final=ribbon["ribbon_message_final"],
        product_name=ribbon["product_name"],
        price=ribbon["price"],
        quantity=ribbon["quantity"],
        correction_log=correction["correction_log"],
        split_status=split["split_status"],
    )

    pid = uuid.uuid4().hex[:8]
    pending = _load_pending()
    pending[pid] = {
        "created_at": ctx.get("created_at") or "",
        "source_type": source_type,
        "raw_text": raw_text,
        "normalized_text": correction["normalized_text"],
        "draft": draft["order_draft"],
        "ribbon": ribbon,
        "review": review,
        "bundle_id": split["bundle_id"],
        "bundle_sequence": seg["bundle_sequence"],
        "split_note": note,
    }
    _save_pending(pending)
    return redirect(url_for("detail", pid=pid))


@app.route("/order/<pid>")
def detail(pid):
    pending = _load_pending()
    o = pending.get(pid)
    if not o:
        return redirect(url_for("index"))

    draft = o["draft"]
    fields_html = ""
    for key, val in draft.items():
        warn = ' <span class="warn">⚠ 확인 필요</span>' if val is None else ""
        fields_html += (
            f'<div class="field"><label>{escape(key)}{warn}</label>'
            f'<input name="field_{escape(key)}" value="{escape(str(val)) if val else ""}"></div>'
        )

    checklist_html = "".join(f"<li>{escape(c)}</li>" for c in o["review"]["review_checklist"]) or "<li>(없음)</li>"
    color = PRIORITY_COLOR.get(o["review"]["review_priority"], "#999")

    html = f"""
    {BASE_STYLE}
    <a class="back" href="{url_for('index')}">← 목록</a>
    <h1><span class="badge" style="background:{color}">{o['review']['review_priority']}</span> 주문 상세</h1>
    {f'<p class="warn">{escape(o["split_note"])}</p>' if o.get("split_note") else ""}
    <h2>원문</h2>
    <p class="note">{escape(o['raw_text'])}</p>
    <h2>정리된 정보 (필요하면 고치세요)</h2>
    <form method="post" action="{url_for('approve', pid=pid)}">
      {fields_html}
      <div class="field"><label>리본 문구</label>
        <input name="field_ribbon_message_final" value="{escape(o['ribbon'].get('ribbon_message_final') or '')}"></div>
      <div class="field"><label>가격(원)</label>
        <input name="field_price" value="{escape(str(o['ribbon'].get('price') or ''))}"></div>
      <div class="field"><label>수량</label>
        <input name="field_quantity" value="{escape(str(o['ribbon'].get('quantity') or ''))}"></div>
      <div class="field"><label>받는 분 배송지</label>
        <input name="field_delivery_address" value=""></div>
      <div class="field"><label>받는 분 연락처</label>
        <input name="field_delivery_phone" value=""></div>
      <h2>검수 체크리스트</h2>
      <ul>{checklist_html}</ul>
      <button class="btn btn-approve" type="submit">✅ 승인하고 처리</button>
    </form>
    <form method="post" action="{url_for('reject', pid=pid)}">
      <button class="btn btn-reject" type="submit">❌ 반려(대기 목록에서 삭제)</button>
    </form>
    <p class="note">반려를 누르면 이 문의는 목록에서 사라집니다 - "반려 후 어느 단계로 되돌릴지"는
    아직 정해지지 않은 항목이라(승인화면_프로토타입_v1.html README와 동일), 지금은 단순 삭제만 합니다.</p>
    """
    return render_template_string(html)


@app.route("/order/<pid>/approve", methods=["POST"])
def approve(pid):
    pending = _load_pending()
    o = pending.get(pid)
    if not o:
        return redirect(url_for("index"))

    confirmed_fields = {}
    for key in o["draft"].keys():
        confirmed_fields[key] = request.form.get(f"field_{key}") or None
    confirmed_fields["normalized_text"] = o["normalized_text"]
    confirmed_fields["ribbon_message_raw"] = o["ribbon"].get("ribbon_message_raw")
    confirmed_fields["ribbon_message_final"] = request.form.get("field_ribbon_message_final") or None
    confirmed_fields["product_name"] = confirmed_fields.get("product")
    confirmed_fields["price"] = request.form.get("field_price") or None
    confirmed_fields["quantity"] = request.form.get("field_quantity") or None
    confirmed_fields["delivery_address"] = request.form.get("field_delivery_address") or None
    confirmed_fields["delivery_phone"] = request.form.get("field_delivery_phone") or None

    record = storage_bot.save_order(
        confirmed_fields=confirmed_fields,
        manual_edits={},
        approval_action="주문확정",
        bundle_id=o["bundle_id"],
        bundle_sequence=o["bundle_sequence"],
    )
    printed = print_prep_bot.prepare_print(record)
    dispatched = dispatch_bot.dispatch(record, printed["driver_summary"], printed["delivery_memo"])
    photo = delivery_photo_bot.capture_delivery_photo(dispatched["dispatch_record"], photo_uri=None)
    sms_ledger_bot.send_and_ledger(
        order=record,
        delivery_photo=photo["delivery_photo"],
        photo_status=photo["photo_status"],
        bundle_id=o["bundle_id"],
        bundle_sequence=o["bundle_sequence"],
    )

    del pending[pid]
    _save_pending(pending)
    return redirect(url_for("index"))


@app.route("/order/<pid>/reject", methods=["POST"])
def reject(pid):
    pending = _load_pending()
    pending.pop(pid, None)
    _save_pending(pending)
    return redirect(url_for("index"))


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
