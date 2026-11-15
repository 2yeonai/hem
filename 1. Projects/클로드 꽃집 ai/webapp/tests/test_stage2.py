import io
import pytest
from test_stage1 import app, database, isolated_schema, login, csrf
import app as web
from intake import validate


def mock_ai(monkeypatch,n=1,uncertain=False):
    monkeypatch.setattr(web.ocb,'classify_order',lambda t:{'order_classification':'주문전화'})
    monkeypatch.setattr(web.osb,'split_order',lambda t:{'split_status':'확인필요' if uncertain else '완료','order_segments':[{'segment_text':f'가상 주문 {i}'} for i in range(n)]})
    monkeypatch.setattr(web.correction_bot,'correct_text',lambda t:{'normalized_text':t})
    monkeypatch.setattr(web.order_draft_bot,'build_draft',lambda t:{'order_draft':{'recipient_name':'수신인','sender_name':'발신인','product':'가상 꽃'}})
    monkeypatch.setattr(web.ribbon_price_bot,'process_ribbon_and_price',lambda d,t:{'price':10000,'ribbon_message_final':'축하'})


def submit(c,text='가상 주문'):
    return c.post('/intakes',data={'csrf_token':csrf(c),'raw_text':text})


@pytest.mark.parametrize('n',[1,2,3])
def test_all_orders_created(monkeypatch,n):
    mock_ai(monkeypatch,n);c=login();r=submit(c)
    assert r.status_code==302
    rows=list(database.pending_orders().values())
    assert len(rows)==n
    assert {r['bundle_sequence']['index'] for r in rows}==set(range(1,n+1))
    assert all(r['bundle_sequence']['total']==n for r in rows)
    assert len({r['bundle_id'] for r in rows})==1


def test_duplicate_text(monkeypatch):
    mock_ai(monkeypatch,2);c=login()
    a=submit(c);b=submit(c)
    assert a.location==b.location and len(database.pending_orders())==2


def test_uncertain_manual_split(monkeypatch):
    mock_ai(monkeypatch,1,True);c=login();r=submit(c)
    assert not database.pending_orders()
    assert c.post(r.location,data={'csrf_token':csrf(c),'segments':'가상 첫째\n---\n가상 둘째'}).status_code==302
    assert len(database.pending_orders())==2
    assert c.post(r.location,data={'csrf_token':csrf(c),'segments':'중복'}).status_code==409


def test_ai_failure_preserves_and_retries(monkeypatch):
    mock_ai(monkeypatch)
    monkeypatch.setattr(web.ocb,'classify_order',lambda t:(_ for _ in ()).throw(RuntimeError('secret')))
    c=login();r=submit(c)
    assert 'error' in c.get(r.location).get_data(as_text=True)
    assert not database.pending_orders()
    mock_ai(monkeypatch)
    assert c.post(r.location,data={'csrf_token':csrf(c),'action':'retry'}).status_code==302
    assert len(database.pending_orders())==1


def test_non_order_is_retained(monkeypatch):
    mock_ai(monkeypatch)
    monkeypatch.setattr(web.ocb,'classify_order',lambda t:{'order_classification':'일반통화'})
    c=login();r=submit(c,'가상 안부')
    assert 'non_order' in c.get(r.location).get_data(as_text=True)
    with database.connect() as conn:
        assert conn.execute('SELECT raw_text FROM intakes').fetchone()['raw_text']=='가상 안부'


def test_missing_delivery_and_reviewer_values(monkeypatch):
    mock_ai(monkeypatch);c=login();submit(c)
    pid=next(iter(database.pending_orders()))
    data={'csrf_token':csrf(c),'version':1,'reviewed':'yes'}
    assert c.post(f'/order/{pid}/approve',data=data).status_code==422
    fields=dict(recipient_name='수신 수정',sender_name='발신 수정',product='난',price='23000',ribbon_message_final='수정 문구',delivery_date='2026-12-01',delivery_time='11:30',delivery_address='가상주소',delivery_phone='000-0000-0000')
    data.update({'field_'+k:v for k,v in fields.items()})
    assert c.post(f'/order/{pid}/approve',data=data).status_code==302
    with database.connect() as conn:
        f=conn.execute('SELECT confirmed FROM orders').fetchone()['confirmed']
        assert f['price']==f['amount_krw']==23000 and f['recipient_name']=='수신 수정'
    assert c.post(f'/order/{pid}/approve',data=data).status_code==409


def test_duplicate_audio_on_stt_failure(monkeypatch):
    monkeypatch.setattr(web.transcription_bot,'transcribe',lambda **kw:{'engine_meta':{'real_api_connected':False}})
    c=login()
    def upload(): return c.post('/intakes',data={'csrf_token':csrf(c),'audio':(io.BytesIO(b'synthetic-audio'),'test.wav')})
    assert upload().location==upload().location
    with database.connect() as conn:
        assert conn.execute('SELECT count(*) AS n FROM intakes').fetchone()['n']==1


def test_mixed_products_amounts_and_roles(monkeypatch):
    mock_ai(monkeypatch,3)
    def draft(t):
        i=int(t.rsplit(' ',1)[1])
        return {'order_draft':{'recipient_name':f'받는{i}','sender_name':f'보내는{i}','product':['난','화환','꽃다발'][i]}}
    monkeypatch.setattr(web.order_draft_bot,'build_draft',draft)
    monkeypatch.setattr(web.ribbon_price_bot,'process_ribbon_and_price',lambda d,t:{'price':(int(t.rsplit(' ',1)[1])+1)*10000})
    c=login();submit(c)
    rows=sorted(database.pending_orders().values(),key=lambda x:x['bundle_sequence']['index'])
    assert [r['ribbon']['price'] for r in rows]==[10000,20000,30000]
    assert [r['draft']['product'] for r in rows]==['난','화환','꽃다발']
    assert all(r['draft']['recipient_name']!=r['draft']['sender_name'] for r in rows)


def test_intake_database_failure_no_false_success(monkeypatch):
    from contextlib import contextmanager
    import psycopg
    c=login()
    original=database.connect
    calls=0
    @contextmanager
    def fail_write():
        nonlocal calls
        calls+=1
        if calls>1: raise psycopg.OperationalError('secret')
        with original() as conn: yield conn
    monkeypatch.setattr(database,'connect',fail_write)
    r=submit(c)
    assert r.status_code==503 and 'secret' not in r.get_data(as_text=True)


def test_partial_analysis_creates_no_orders(monkeypatch):
    mock_ai(monkeypatch,3)
    def fail_second(t):
        if t.endswith('1'): raise ValueError('bad AI response')
        return {'order_draft':{'product':'가상'}}
    monkeypatch.setattr(web.order_draft_bot,'build_draft',fail_second)
    c=login();r=submit(c)
    assert 'error' in c.get(r.location).get_data(as_text=True)
    assert not database.pending_orders()
