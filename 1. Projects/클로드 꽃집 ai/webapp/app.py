"""기존 AI/검수 UI를 재사용하는 PostgreSQL 기반 주문 웹앱.
승인은 저장까지만 수행하며 실제 배송/문자는 별도 승인된 단계에서 처리한다.
다중 주문 분리는 2단계에서 보완 예정.
"""

import re
import sys
import uuid
from html import escape
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template_string, request, url_for
import database
from security import init_security

WEBAPP_DIR = Path(__file__).resolve().parent
FLOWER_DIR = WEBAPP_DIR.parent
CODE_DIR = FLOWER_DIR / "code"

if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import collection_bot
import correction_bot
import order_classification_bot as ocb
import order_draft_bot
import order_split_bot as osb
import review_manager_bot
import ribbon_price_bot
import transcription_bot

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
init_security(app)
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
    return database.pending_orders()


def render_page(html):
    # Data must never become Jinja template source (including {{ ... }} in raw orders).
    token = escape(app.jinja_env.globals['csrf_token']())
    html = re.sub(r'(<form\b[^>]*>)', lambda m: m.group(1) +
                  f'<input type="hidden" name="csrf_token" value="{token}">', html)
    return render_template_string('<!doctype html><html lang="ko"><meta name="viewport" '
                                  'content="width=device-width,initial-scale=1">{{ body|safe }}</html>', body=html)


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
            f'<span class="badge" style="background:{style["bg"]};color:{style["text"]}">{escape(pr)}</span>'
            f'{escape(o["draft"].get("product") or "(상품 미확인)")} / '
            f'{escape(str(o["ribbon"].get("price") or "?"))}원'
            f'<div class="note">{escape(o["created_at"])}</div></a>'
        )
    if not cards:
        cards = '<p class="note">대기 중인 주문이 없습니다.</p>'
    html = f"""
    {BASE_STYLE}
    <form method="post" action="/logout"><button>로그아웃</button></form>
    <h1>🌸 검수 대기 ({len(items)}건)</h1>
    {cards}
    <a class="btn btn-new" href="{url_for('new_order')}">+ 새 문의 입력</a>
    """
    return render_page(html)


@app.route("/new", methods=["GET", "POST"])
def new_order():
    return redirect(url_for("intakes"), code=307 if request.method == "POST" else 302)


@app.route("/order/<pid>")
def detail(pid):
    pending = _load_pending()
    o = pending.get(pid)
    if not o:
        return redirect(url_for("index"))

    if o.get('intake_id'):
        import intake
        fields = dict(o['draft'])
        fields['price'] = o['ribbon'].get('price')
        fields['ribbon_message_final'] = o['ribbon'].get('ribbon_message_final')
        fields.update(o.get('review_draft') or {})
        inputs = ''
        for key,label in intake.FIELDS.items():
            source_key={'price':'amount_krw','ribbon_message_final':'ribbon_phrase_raw'}.get(key,key)
            conf=o.get('field_confidence',{}).get(source_key,0)
            evidence=o.get('field_evidence',{}).get(source_key) or '원문 근거 확인 필요'
            inputs += (f'<div class="field"><label>{escape(label)}</label><input name="field_{key}" value="{escape(str(fields.get(key) or ""))}">'
                       f'<p class="note">신뢰도 {float(conf):.0%} · 원문: {escape(str(evidence))}</p></div>')
        return render_page(BASE_STYLE + '<h1>개별 주문 검수</h1>' +
            f'<pre>{escape(o["normalized_text"])}</pre><p>이름 역할과 금액을 직접 확인하세요. 저장된 초안이 있으면 복원됩니다.</p><form method="post" action="/order/{pid}/approve"><input type="hidden" name="version" value="{o["version"]}">'+inputs+
            f'<button formnovalidate formaction="/order/{pid}/draft">초안 임시 저장</button>'+
            '<label><input type="checkbox" name="reviewed" value="yes" required>원문과 받는 분·보내는 분·금액·배송정보를 대조했습니다.</label><button>주문 확정</button></form>')
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
    <h1><span class="badge" style="background:{pr_style['bg']};color:{pr_style['text']}">{escape(o['review']['review_priority'])}</span> 주문 상세</h1>
    {f'<p class="warn">{escape(o["split_note"])}</p>' if o.get("split_note") else ""}
    <h2>{'원문(녹음파일 음성인식 결과 - 틀린 부분 있을 수 있음)' if o.get('from_audio') else '원문'}</h2>
    <p class="note">{escape(o['raw_text'])}</p>
    <h2>정리된 정보 (필요하면 고치세요)</h2>
    <form method="post" action="{url_for('approve', pid=pid)}">
      <input type="hidden" name="version" value="{o['version']}">
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
      <input type="hidden" name="version" value="{o['version']}">
      <button class="btn btn-reject" type="submit">❌ 반려(기록 보존)</button>
    </form>
    <p class="note">반려해도 원문과 분석 결과는 보존됩니다. 승인은 주문 저장까지만 진행합니다.</p>
    """
    return render_page(html)


@app.route("/order/<pid>/approve", methods=["POST"])
def approve(pid):
    pending = _load_pending()
    o = pending.get(pid)
    if not o:
        return "이미 처리된 주문입니다.", 409

    if o.get('intake_id'):
        import intake
        confirmed_fields = {k: request.form.get('field_'+k, '').strip() for k in intake.FIELDS}
        errors = intake.validate(confirmed_fields)
        if request.form.get('reviewed') != 'yes': errors.append('원문 대조 확인')
        if errors: return render_page(BASE_STYLE + '<p>확인 필요: '+escape(', '.join(errors))+'</p><p>뒤로 돌아가 입력을 보완해주세요.</p>'), 422
        confirmed_fields['amount_krw'] = confirmed_fields['price'] = int(confirmed_fields['price'])
        confirmed_fields['product_name'] = confirmed_fields['product']
        try:
            database.transition(pid, int(request.form.get('version','0')), g.user['id'], 'confirmed', confirmed_fields)
        except ValueError: abort(400)
        except database.Conflict as exc: return str(exc),409
        return redirect(url_for('index'))
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

    try:
        database.transition(pid, int(request.form.get('version', '0')), g.user['id'], 'confirmed', confirmed_fields)
    except ValueError:
        abort(400)
    except database.Conflict as exc:
        return str(exc), 409
    return redirect(url_for("index"))


@app.route("/order/<pid>/reject", methods=["POST"])
def reject(pid):
    try:
        database.transition(pid, int(request.form.get('version', '0')), g.user['id'], 'rejected')
    except ValueError:
        abort(400)
    except database.Conflict as exc:
        return str(exc), 409
    return redirect(url_for("index"))


@app.post('/order/<pid>/draft')
def save_draft(pid):
    import intake
    fields={k:request.form.get('field_'+k,'').strip() for k in intake.FIELDS}
    try:
        database.save_review(pid,int(request.form.get('version','0')),g.user['id'],fields)
    except ValueError: abort(400)
    except database.Conflict as exc: return str(exc),409
    return redirect(url_for('detail',pid=pid))


import intake
intake.register(app, sys.modules[__name__])

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
