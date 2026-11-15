import time
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from flask import g
from test_stage1 import app,database,isolated_schema,login,csrf
from test_stage2 import mock_ai,submit
from evidence import enrich
from analysis_worker import bounded
import app as web


def test_delivery_extraction_and_evidence():
    text='배송일: 2026-12-05; 배송시간: 13:20; 배송주소: 가상시 시험로 3; 연락처: 000-0000-0000'
    result=enrich({'order_draft':{}},text)
    assert result['order_draft']==dict(delivery_date='2026-12-05',delivery_time='13:20',delivery_address='가상시 시험로 3',delivery_phone='000-0000-0000')
    assert all(v in text for v in result['field_evidence'].values())


def test_hallucinated_source_not_displayed():
    r=enrich({'order_draft':{'delivery_address':'없는주소'},'field_evidence':{'delivery_address':'조작근거'},'field_confidence':{'delivery_address':.99}},'가상 원문')
    assert r['field_confidence']['delivery_address']==0
    assert r['field_evidence']['delivery_address'] is None


def test_worker_deadline(monkeypatch):
    monkeypatch.setenv('AI_REQUEST_TIMEOUT_SECONDS','.1')
    start=time.monotonic()
    with pytest.raises(TimeoutError): bounded(lambda:time.sleep(5))
    assert time.monotonic()-start<2


def test_draft_restored_and_stale_write_rejected(monkeypatch):
    mock_ai(monkeypatch);c=login();submit(c)
    pid=next(iter(database.pending_orders()))
    data={'csrf_token':csrf(c),'version':1,'field_recipient_name':'수정 수신인','field_price':'12345','field_delivery_address':'가상 수정주소'}
    assert c.post(f'/order/{pid}/draft',data=data).status_code==302
    body=c.get(f'/order/{pid}').get_data(as_text=True)
    assert '12345' in body and '가상 수정주소' in body and '수정 수신인' in body
    assert '신뢰도' in body and '원문:' in body
    assert c.post(f'/order/{pid}/draft',data=data).status_code==409
    with database.connect() as conn:
        row=conn.execute('SELECT status,payload FROM orders').fetchone()
        assert row['status']=='pending' and row['payload']['draft']['recipient_name']=='수신인'


def test_draft_denies_viewer(monkeypatch):
    c=login('viewer')
    assert c.post('/order/missing/draft',data={'csrf_token':csrf(c)}).status_code==403


def test_retry_limit(monkeypatch):
    mock_ai(monkeypatch)
    monkeypatch.setattr(web.ocb,'classify_order',lambda t:(_ for _ in ()).throw(ValueError()))
    c=login();r=submit(c)
    for _ in range(5): c.post(r.location,data={'csrf_token':csrf(c),'action':'retry'})
    with database.connect() as conn:
        row=conn.execute('SELECT attempts,state FROM intakes').fetchone()
        assert row['attempts']==3 and row['state']=='error'


def test_processing_lease_blocks_retry(monkeypatch):
    from intake import receive
    iid,_=receive('가상 처리중',None)
    with database.connect() as conn:
        conn.execute("UPDATE intakes SET state='processing',attempt_token='existing',lease_until=now()+interval '1 minute'")
    with app.test_request_context():
        g.user={'id':1};app.extensions['analyze_intake'](iid)
    with database.connect() as conn:
        assert conn.execute('SELECT attempt_token FROM intakes').fetchone()['attempt_token']=='existing'


def test_expired_lease_recovered(monkeypatch):
    from intake import receive
    mock_ai(monkeypatch);iid,_=receive('가상 만료',None)
    with database.connect() as conn:
        conn.execute("UPDATE intakes SET state='processing',attempt_token='old',lease_until=now()-interval '1 minute'")
    with app.test_request_context():
        g.user={'id':1};app.extensions['analyze_intake'](iid)
    assert len(database.pending_orders())==1


def test_late_result_cannot_overwrite_manual(monkeypatch):
    from intake import receive
    import analysis_worker
    iid,_=receive('가상 늦은 응답',None)
    def concurrent_manual(fn):
        with database.connect() as conn:
            conn.execute("UPDATE intakes SET state='manual',attempt_token=NULL WHERE id=%s",(iid,))
        return 'ready',{'proposals':[],'text':'late'}
    monkeypatch.setattr(analysis_worker,'bounded',concurrent_manual)
    with app.test_request_context():
        g.user={'id':1};app.extensions['analyze_intake'](iid)
    with database.connect() as conn:
        assert conn.execute('SELECT state FROM intakes').fetchone()['state']=='manual'
    assert not database.pending_orders()


def test_ai_delivery_visible_on_review(monkeypatch):
    mock_ai(monkeypatch)
    monkeypatch.setattr(web.osb,'split_order',lambda t:{'split_status':'완료','order_segments':[{'segment_text':t}]})
    c=login();submit(c,'배송일: 2026-12-05; 배송시간: 13:20; 배송주소: 가상주소; 연락처: 000-0000-0000')
    pid=next(iter(database.pending_orders()))
    body=c.get(f'/order/{pid}').get_data(as_text=True)
    assert '2026-12-05' in body and '95%' in body and '가상주소' in body


def test_model_delivery_contract_without_paid_api(monkeypatch):
    import order_draft_bot
    import llm_client
    captured={}
    def fake(**kwargs):
        captured.update(kwargs)
        return {'order_draft':{'delivery_date':'2026-12-05','delivery_time':'13:20','delivery_address':'가상주소','delivery_phone':'000-0000-0000'},
                'field_evidence':{'delivery_address':'주소 가상주소'},'field_confidence':{'delivery_address':.8}}
    monkeypatch.setattr(llm_client,'call_llm_json',fake)
    r=order_draft_bot._draft_llm('주소 가상주소')
    assert 'delivery_date' in captured['system_prompt'] and 'field_evidence' in captured['system_prompt']
    assert r['order_draft']['delivery_address']=='가상주소'


def test_repeated_delivery_dates_need_confirmation():
    r=enrich({'order_draft':{}},'배송일: 2026-12-05; 배송일: 2026-12-06')
    assert not r['order_draft'].get('delivery_date')
