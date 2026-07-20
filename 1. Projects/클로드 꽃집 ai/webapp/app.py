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
# [2026-07-20 스타일 갱신] 혜미가 준 UI 시안(꽃집 ui.png 등, 부드러운 크림/그린 톤
# + 옅은 배경색 배지)에 맞춰, 진한 단색 배지 대신 옅은 배경 + 진한 글자색 조합으로
# 바꿈. review_priority가 나타내는 뜻(빨강=급함~초록=여유)은 그대로 유지, 색상
# 톤만 시안에 맞춤. 이번 단계는 "색/분위기만" 맞추기로 혜미와 합의(홈 대시보드
# 등 화면 구조 변경은 다음 세션).
PRIORITY_STYLE = {
    "빨강": {"bg": "#fdecec", "text": "#c1272d"},
    "노랑": {"bg": "#fff4e0", "text": "#b6790a"},
    "파랑": {"bg": "#e8f0fd", "text": "#2a5cbf"},
    "초록": {"bg": "#e6f6ea", "text": "#1f8a4c"},
}

# order_draft_bot.FIELDS의 영문 필드명을 화면에 보여줄 한글 라벨로 바꾼다
# (2026-07-20 신설 - 혜미가 영어 필드명이 그대로 노출되는 걸 발견해서 추가).
FIELD_LABELS_KO = {
    "recipient_org": "받는 분 기관/단체",
    "recipient_name": "받는 분 이름",
    "recipient_title": "받는 분 직함",
    "sender_org": "보내는 분 기관/단체",
    "sender_name": "보내는 분 이름",
    "sender_title": "보내는 분 직함",
    "event": "경조사 종류",
    "amount_krw": "금액(원)",
    "product": "상품",
    "ribbon_phrase_raw": "리본 문구(원본 감지값)",
}
# 이 값보다 확신도가 낮으면 "값은 있지만 AI 추정치니 확인하라"는 경고를 보여준다.
LOW_CONFIDENCE_THRESHOLD = 0.6

app = Flask(__name__)
# OpenAI Whisper API 자체가 파일 하나당 25MB 제한이 있어(2026-07 기준) 그보다
# 넉넉하게 여기서도 25MB로 막아둔다(2026-07-20 신설) - Render 무료 인스턴스
# 메모리(512MB)도 보호하는 효과.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


@app.errorhandler(413)
def _file_too_large(_e):
    return render_template_string(
        BASE_STYLE
        + '<a class="back" href="/new">← 다시 입력</a>'
        + "<h1>파일이 너무 큽니다</h1>"
        + '<p class="note">녹음파일은 25MB까지만 됩니다. 더 짧게 녹음하거나 압축해서 다시 시도해주세요.</p>'
    ), 413


def _load_pending() -> dict:
    if not PENDING_PATH.is_file():
        return {}
    return json.loads(PENDING_PATH.read_text(encoding="utf-8"))


def _save_pending(data: dict) -> None:
    PENDING_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


BASE_STYLE = """
<style>
  /* [2026-07-20] 혜미가 준 UI 시안(꽃집 ui.png 등)의 크림 배경 + 그린 포인트
     톤으로 맞춤 - 화면 구조는 그대로, 색/카드 스타일만 갱신. */
  body { font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", sans-serif;
         max-width: 480px; margin: 0 auto; padding: 16px; background: #f7f5ef; color: #1f2a22; }
  h1 { font-size: 20px; color: #1f5c3a; font-weight: 700; }
  h2 { font-size: 15px; color: #4a5a4f; font-weight: 700; margin: 18px 0 8px; }
  .card { background: white; border-radius: 18px; padding: 16px 18px; margin-bottom: 10px;
          box-shadow: 0 2px 8px rgba(31,92,58,0.08); text-decoration: none; color: inherit; display: block; }
  .badge { display: inline-block; font-size: 12px; font-weight: 700;
           padding: 3px 10px; border-radius: 999px; margin-right: 6px; }
  .field { margin-bottom: 10px; }
  .field label { display: block; font-size: 12px; color: #6b7a70; margin-bottom: 3px; font-weight: 600; }
  .field input, .field textarea { width: 100%; box-sizing: border-box; padding: 10px 12px;
           border: 1px solid #e1ddd0; border-radius: 12px; font-size: 15px; background: #fdfcf9; }
  .warn { color: #c1272d; font-size: 12px; font-weight: 700; }
  .btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 14px;
         font-size: 16px; font-weight: 700; margin-top: 10px; text-align: center; }
  .btn-approve { background: #2f9e56; color: white; }
  .btn-reject { background: #f3f1ea; color: #c1272d; }
  .btn-new { background: #2f9e56; color: white; }
  .note { font-size: 12px; color: #8a8578; margin-top: 4px; }
  a.back { color: #6b7a70; text-decoration: none; font-size: 14px; }
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
        style = PRIORITY_STYLE.get(pr, {"bg": "#eee", "text": "#666"})
        cards += (
            f'<a class="card" href="{url_for("detail", pid=pid)}">'
            f'<span class="badge" style="background:{style["bg"]};color:{style["text"]}">{pr}</span>'
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
        <form method="post" enctype="multipart/form-data">
          <div class="field"><label>수신 경로</label>
            <select name="source_type" style="width:100%;padding:10px 12px;border-radius:12px;border:1px solid #e1ddd0;background:#fdfcf9;font-size:15px;">
              <option value="kakao">카카오톡</option>
              <option value="sms">문자</option>
              <option value="call">전화(녹음파일 또는 받아적은 내용)</option>
              <option value="manual">직접 입력</option>
            </select>
          </div>
          <div class="field"><label>받은 내용(문자/카톡 원문 그대로 붙여넣기)</label>
            <textarea name="raw_text" rows="6"></textarea>
          </div>
          <div class="field"><label>또는 통화 녹음파일 첨부(선택 - 위 칸 대신 이것만 넣어도 됨)</label>
            <input type="file" name="raw_audio_file" accept="audio/*">
            <p class="note">2026-07-20 신설: AI가 자동으로 텍스트로 바꿔줍니다(OpenAI 음성인식 사용,
            분당 약 8원 - Render에 OPENAI_API_KEY가 등록돼 있어야 동작하고, 없으면 실패 메시지가
            뜹니다). 위 텍스트 칸과 이 파일 중 최소 하나는 채워야 합니다.</p>
          </div>
          <button class="btn btn-approve" type="submit">AI 판단 시작</button>
        </form>
        """
        return render_template_string(html)

    source_type = request.form.get("source_type", "kakao")
    raw_text = request.form.get("raw_text", "").strip()
    audio_file = request.files.get("raw_audio_file")
    audio_bytes = None
    if audio_file and audio_file.filename:
        audio_bytes = audio_file.read()

    if not raw_text and not audio_bytes:
        html = f"""
        {BASE_STYLE}
        <a class="back" href="{url_for('new_order')}">← 다시 입력</a>
        <h1>입력이 비어있습니다</h1>
        <p class="note">문자 내용을 붙여넣거나 녹음파일을 첨부해주세요.</p>
        """
        return render_template_string(html)

    ctx = collection_bot.collect(
        source_type=source_type,
        raw_text=raw_text or None,
        raw_audio=audio_bytes,
    )
    tr = transcription_bot.transcribe(raw_audio=ctx["raw_audio"], raw_image=None, raw_text=ctx["raw_text"])
    text = tr["stt_text"] or tr["ocr_text"] or ctx["raw_text"] or ""

    if audio_bytes and not tr["engine_meta"]["real_api_connected"]:
        html = f"""
        {BASE_STYLE}
        <a class="back" href="{url_for('new_order')}">← 다시 입력</a>
        <h1>음성인식 실패</h1>
        <p class="note">녹음파일을 텍스트로 바꾸지 못했습니다. OPENAI_API_KEY가 Render에
        등록돼 있는지, 파일이 정상적인 오디오 파일인지 확인해주세요. 급하면 내용을
        직접 들어보고 텍스트로 옮겨 입력해도 됩니다.</p>
        """
        return render_template_string(html)

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
        # raw_text는 사람이 실제로 확인할 "원문"으로 쓰이므로, 녹음파일을 올렸을 땐
        # 원래 입력칸(빈칸)이 아니라 음성인식 결과 텍스트를 담는다(2026-07-20).
        "raw_text": text,
        "from_audio": bool(audio_bytes),
        "normalized_text": correction["normalized_text"],
        "draft": draft["order_draft"],
        "field_confidence": draft.get("field_confidence") or {},
        "field_sources": draft.get("field_sources") or {},
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
    confidence = o.get("field_confidence") or {}
    fields_html = ""
    for key, val in draft.items():
        label = FIELD_LABELS_KO.get(key, key)
        conf = confidence.get(key)
        if val is None:
            warn = ' <span class="warn">⚠ 확인 필요</span>'
        elif conf is not None and conf < LOW_CONFIDENCE_THRESHOLD:
            warn = ' <span class="warn">⚠ AI 추정치 - 꼭 확인</span>'
        else:
            warn = ""
        fields_html += (
            f'<div class="field"><label>{escape(label)}{warn}</label>'
            f'<input name="field_{escape(key)}" value="{escape(str(val)) if val else ""}"></div>'
        )

    # 배송지 기본값 제안: 받는 분 기관 + 이름이 있으면 자동으로 채워보고, 없으면
    # 빈칸으로 둔다 - 어느 쪽이든 사람이 승인 전에 직접 확인/수정 가능(2026-07-20 신설).
    suggested_address_parts = [p for p in (draft.get("recipient_org"), draft.get("recipient_name")) if p]
    suggested_address = (" ".join(suggested_address_parts) + "님") if suggested_address_parts else ""

    checklist_html = "".join(f"<li>{escape(c)}</li>" for c in o["review"]["review_checklist"]) or "<li>(없음)</li>"
    pr_style = PRIORITY_STYLE.get(o["review"]["review_priority"], {"bg": "#eee", "text": "#666"})

    html = f"""
    {BASE_STYLE}
    <a class="back" href="{url_for('index')}">← 목록</a>
    <h1><span class="badge" style="background:{pr_style['bg']};color:{pr_style['text']}">{o['review']['review_priority']}</span> 주문 상세</h1>
    {f'<p class="warn">{escape(o["split_note"])}</p>' if o.get("split_note") else ""}
    <h2>{'원문(녹음파일 음성인식 결과 - 틀린 부분 있을 수 있음)' if o.get('from_audio') else '원문'}</h2>
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
        <input name="field_delivery_address" value="{escape(suggested_address)}"></div>
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
