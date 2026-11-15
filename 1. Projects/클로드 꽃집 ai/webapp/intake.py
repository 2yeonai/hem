"""Durable deduplicated intake; AI outputs remain proposals until human review."""
import hashlib
import json
import uuid
from html import escape
from datetime import date, time
from flask import request, g, redirect, url_for, abort
from psycopg.types.json import Jsonb
import database

FIELDS = {'recipient_name':'받는 분 이름','recipient_org':'받는 기관','sender_name':'보내는 분 이름',
          'sender_org':'보내는 기관','product':'상품','price':'금액(원)','ribbon_message_final':'리본 문구',
          'delivery_date':'배송일 YYYY-MM-DD','delivery_time':'배송시간 HH:MM',
          'delivery_address':'배송주소','delivery_phone':'연락처'}


def validate(fields):
    errors=[label for key,label in FIELDS.items() if key not in {'recipient_org','sender_org'} and not str(fields.get(key) or '').strip()]
    try:
        if int(fields.get('price',''))<=0: raise ValueError()
    except (ValueError,TypeError): errors.append('금액은 양의 정수')
    try: date.fromisoformat(fields.get('delivery_date',''))
    except (ValueError,TypeError): errors.append('배송일 형식')
    try: time.fromisoformat(fields.get('delivery_time',''))
    except (ValueError,TypeError): errors.append('배송시간 형식')
    return errors


def receive(text,audio):
    fingerprint=hashlib.sha256((b'audio:'+audio) if audio else ('text:'+text.strip()).encode()).hexdigest()
    with database.connect() as conn:
        row=conn.execute('INSERT INTO intakes(id,fingerprint,raw_text,audio) VALUES (%s,%s,%s,%s) ON CONFLICT(fingerprint) DO NOTHING RETURNING id',
                         (uuid.uuid4().hex,fingerprint,text,audio)).fetchone()
        if row: return row['id'],True
        return conn.execute('SELECT id FROM intakes WHERE fingerprint=%s',(fingerprint,)).fetchone()['id'],False


def register(app, web):
    @app.route('/intakes',methods=['GET','POST'])
    def intakes():
        if request.method=='POST':
            text=request.form.get('raw_text','').strip()
            f=request.files.get('audio'); audio=f.read() if f and f.filename else None
            if not text and not audio: abort(400)
            iid,fresh=receive(text,audio)
            if fresh: analyze(iid)
            return redirect(url_for('intake_detail',iid=iid))
        with database.connect() as conn: rows=conn.execute('SELECT id,state FROM intakes ORDER BY created_at DESC LIMIT 100').fetchall()
        links=''.join(f'<p><a href="/intake/{r["id"]}">{escape(r["state"])} · {r["id"][:8]}</a></p>' for r in rows)
        return web.render_page(web.BASE_STYLE+'<h1>문의 접수 기록</h1><form method="post" enctype="multipart/form-data"><textarea name="raw_text" aria-label="원문"></textarea><input type="file" name="audio" accept="audio/*"><button>접수·분석</button></form>'+links)

    def analyze(iid):
        # Lock before any AI invocation: concurrent retries cannot create duplicate orders.
        with database.connect() as conn:
            row=conn.execute('SELECT * FROM intakes WHERE id=%s FOR UPDATE',(iid,)).fetchone()
            if row['state'] in {'ready','manual'}: return
            try:
                text=row['raw_text']
                if row['audio']:
                    tr=web.transcription_bot.transcribe(raw_audio=bytes(row['audio']))
                    if not tr['engine_meta']['real_api_connected']: raise ValueError('transcription')
                    text=tr['stt_text']
                cls=web.ocb.classify_order(text)
                split=web.osb.split_order(text)
                analysis={'classification':cls,'split':split,'text':text}
                # Existing bots signal fallback in metadata; never hide this from the operator.
                if 'LLM' in json.dumps(analysis,ensure_ascii=False): raise ValueError('fallback')
                if cls['order_classification'] in web.STOP_CLASSIFICATIONS:
                    state='non_order'
                elif split['split_status']!='완료' or any(float(s.get('split_confidence', 1)) < 0.7 for s in split['order_segments']): state='needs_split'
                else:
                    proposals=[]
                    for seg in split['order_segments']:
                        correction=web.correction_bot.correct_text(seg['segment_text'])
                        draft=web.order_draft_bot.build_draft(correction['normalized_text'])
                        ribbon=web.ribbon_price_bot.process_ribbon_and_price(draft['order_draft'],correction['normalized_text'])
                        proposals.append({'segment':seg,'correction':correction,'draft':draft,'ribbon':ribbon})
                    analysis['proposals']=proposals
                    if 'LLM' in json.dumps(proposals,ensure_ascii=False): raise ValueError('fallback')
                    with conn.transaction():
                        save_orders(conn,iid,proposals,text)
                    state='ready'
                conn.execute('UPDATE intakes SET state=%s,analysis=%s WHERE id=%s',(state,Jsonb(analysis),iid))
            except Exception as exc:
                import psycopg
                if isinstance(exc, psycopg.Error): raise
                conn.execute("UPDATE intakes SET state='error',analysis=%s WHERE id=%s",(Jsonb({'error':'AI 분석 실패 또는 응답 검증 실패. 수동 접수하거나 재시도해주세요.'}),iid))

    def save_orders(conn,iid,proposals,text):
        if not proposals or len(proposals)>30: raise ValueError('count')
        for index,p in enumerate(proposals,1):
            fields=p['draft']['order_draft']
            payload={'raw_text':text,'normalized_text':p['segment']['segment_text'],'created_at':'',
                     'source_type':'intake','draft':fields,'ribbon':p['ribbon'],
                     'review':{'review_priority':'노랑','review_checklist':['받는 분·보내는 분·금액·배송정보를 원문과 대조하세요.']},
                     'bundle_id':iid,'bundle_sequence':{'index':index,'total':len(proposals)},
                     'intake_id':iid,'field_confidence':p['draft'].get('field_confidence',{})}
            pid=uuid.uuid4().hex
            conn.execute('INSERT INTO orders(id,payload) VALUES (%s,%s)',(pid,Jsonb(payload)))
            database.event(conn,pid,g.user['id'],'received',{'intake_id':iid})

    @app.route('/intake/<iid>',methods=['GET','POST'])
    def intake_detail(iid):
        if request.method=='POST':
            if request.form.get('action')=='retry': analyze(iid)
            else:
                # One editable block per order, explicit separator; immutable original retained.
                segments=[s.strip() for s in request.form.get('segments','').split('\n---\n') if s.strip()]
                if not segments or len(segments)>30: abort(400)
                with database.connect() as conn:
                    row=conn.execute('SELECT * FROM intakes WHERE id=%s FOR UPDATE',(iid,)).fetchone()
                    if not row: abort(404)
                    if row['state'] in {'ready','manual'}: return '이미 주문 생성됨',409
                    proposals=[{'segment':{'segment_text':s},'draft':{'order_draft':{}},'ribbon':{}} for s in segments]
                    save_orders(conn,iid,proposals,row['raw_text'])
                    conn.execute("UPDATE intakes SET state='manual' WHERE id=%s",(iid,))
            return redirect(url_for('intake_detail',iid=iid))
        with database.connect() as conn:
            row=conn.execute('SELECT * FROM intakes WHERE id=%s',(iid,)).fetchone()
            if not row: abort(404)
            orders=conn.execute("SELECT id FROM orders WHERE payload->>'intake_id'=%s",(iid,)).fetchall()
        links=''.join(f'<p><a href="/order/{r["id"]}">개별 주문 검수</a></p>' for r in orders)
        return web.render_page(web.BASE_STYLE+f'<h1>접수 상태: {escape(row["state"])}</h1><pre>{escape(row["raw_text"] or (row["analysis"] or {}).get("text", ""))}</pre>'+links+
            '<p>AI 실패·구분 불확실 시 아래에 주문별 내용을 입력하고, 주문 사이에 새 줄로 ---를 넣으세요. 원문은 보존됩니다.</p>'+
            '<form method="post"><textarea name="segments" rows="12"></textarea><button>수동 분리·접수</button></form><form method="post"><input type="hidden" name="action" value="retry"><button>AI 재시도</button></form>')
