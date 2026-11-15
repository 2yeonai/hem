"""Synthetic integration tests; requires an explicitly isolated PostgreSQL test database."""
import os
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SECRET_KEY'] = 'synthetic-test-secret-not-for-production-000'
os.environ['APP_ENV'] = 'development'
# No API credentials used by this test suite.
os.environ['ANTHROPIC_API_KEY'] = ''
os.environ['OPENAI_API_KEY'] = ''
if not os.environ.get('TEST_DATABASE_URL'):
    raise RuntimeError('TEST_DATABASE_URL required; never run against production')
os.environ['DATABASE_URL'] = os.environ['TEST_DATABASE_URL']
import database
from app import app
import app as web


@pytest.fixture(autouse=True)
def isolated_schema():
    # Each test has its own schema; never truncate pre-existing tables.
    schema = 'test_' + uuid.uuid4().hex
    with database.connect() as conn:
        conn.execute(f'CREATE SCHEMA {schema}')
    previous = os.environ.get('PGOPTIONS')
    os.environ['PGOPTIONS'] = f'-c search_path={schema}'
    database.migrate()
    app.config['TESTING'] = True
    for role in ('admin','staff','viewer','driver'):
        database.create_user(role, 'Synthetic-password-123', role)
    yield
    if previous is None:
        os.environ.pop('PGOPTIONS', None)
    else:
        os.environ['PGOPTIONS'] = previous
    with database.connect() as conn:
        conn.execute(f'DROP SCHEMA {schema} CASCADE')


def csrf(client):
    with client.session_transaction() as s:
        return s['csrf']


def login(role='staff'):
    c = app.test_client()
    c.get('/login')
    assert c.post('/login', data={'username':role,'password':'Synthetic-password-123','csrf_token':csrf(c)}).status_code == 302
    c.get('/login')  # obtain rotated token
    return c


def payload(raw='익명 테스트 주문'):
    return dict(raw_text=raw, normalized_text=raw, created_at='2026-11-16',
                source_type='manual', draft={'product':'시험 꽃','recipient_name':'테스트 받는분'},
                ribbon={'price':10000}, review={'review_priority':'노랑','review_checklist':[]},
                bundle_id='synthetic-bundle', bundle_sequence={'index':1,'total':1})


def add(raw='익명 테스트 주문'):
    pid=uuid.uuid4().hex
    database.add_pending(pid,payload(raw),1)
    return pid


def test_anonymous_routes_protected():
    c=app.test_client()
    for path in ('/','/new','/order/unknown'):
        assert c.get(path).status_code == 302
    assert c.post('/order/unknown/approve').status_code == 302


def test_login_and_csrf():
    c=app.test_client()
    c.get('/login')
    assert c.post('/login',data={'username':'staff'}).status_code == 400
    c=login()
    pid=add()
    assert c.post(f'/order/{pid}/reject').status_code == 400
    assert pid in database.pending_orders()


def test_role_boundaries():
    viewer=login('viewer'); driver=login('driver')
    pid=add()
    assert viewer.get('/').status_code == 200
    assert viewer.get('/new').status_code == 403
    assert viewer.post(f'/order/{pid}/reject',data={'csrf_token':csrf(viewer)}).status_code == 403
    assert driver.get('/').status_code == 403
    assert driver.get(f'/order/{pid}').status_code == 403


def test_logout_revokes_copied_cookie():
    c=login(); cookie=c.get_cookie('session').value
    assert c.post('/logout',data={'csrf_token':csrf(c)}).status_code == 302
    other=app.test_client(); other.set_cookie('session',cookie)
    assert other.get('/').status_code == 302


def test_disabled_user_and_session_expiry():
    c=login()
    with database.connect() as conn:
        conn.execute("UPDATE users SET active=false WHERE username='staff'")
    assert c.get('/').status_code == 302
    c=login('admin')
    with database.connect() as conn:
        conn.execute("UPDATE auth_sessions SET expires_at=now()-interval '1 second'")
    assert c.get('/').status_code == 302


def test_account_lockout():
    c=app.test_client();c.get('/login')
    for _ in range(5):
        assert c.post('/login',data={'username':'staff','password':'wrong','csrf_token':csrf(c)}).status_code == 401
    assert c.post('/login',data={'username':'staff','password':'Synthetic-password-123','csrf_token':csrf(c)}).status_code == 401


def test_approve_atomic_and_duplicate_blocked(monkeypatch):
    c=login();pid=add()
    response=c.post(f'/order/{pid}/approve',data={'csrf_token':csrf(c),'version':1,
                    'field_recipient_name':'테스트 확인자','field_delivery_phone':'000-0000-0000'})
    assert response.status_code == 302
    with database.connect() as conn:
        row=conn.execute('SELECT * FROM orders WHERE id=%s',(pid,)).fetchone()
        assert row['status']=='confirmed' and row['payload']['raw_text']=='익명 테스트 주문'
        assert conn.execute('SELECT count(*) AS n FROM customers').fetchone()['n']==2
        assert conn.execute('SELECT status FROM deliveries').fetchone()['status']=='unassigned'
        assert conn.execute('SELECT count(*) AS n FROM order_events').fetchone()['n']==2
    assert c.post(f'/order/{pid}/approve',data={'csrf_token':csrf(c),'version':1}).status_code == 409


def test_rejection_keeps_original():
    c=login();pid=add()
    assert c.post(f'/order/{pid}/reject',data={'csrf_token':csrf(c),'version':1}).status_code==302
    with database.connect() as conn:
        row=conn.execute('SELECT * FROM orders WHERE id=%s',(pid,)).fetchone()
        assert row['status']=='rejected' and row['payload']['draft']
    assert pid not in database.pending_orders()


def test_concurrent_approval():
    pid=add()
    def attempt(_):
        try:
            database.transition(pid,1,1,'confirmed',{'recipient_name':'테스트'})
            return 'ok'
        except database.Conflict:
            return 'conflict'
    with ThreadPoolExecutor(2) as executor:
        assert sorted(executor.map(attempt,range(2)))==['conflict','ok']


def test_transaction_rollback():
    pid=add()
    # Invalid actor FK forces event failure AFTER order/customer/delivery changes.
    with pytest.raises(Exception):
        database.transition(pid,1,999999,'confirmed',{'recipient_name':'테스트'})
    assert pid in database.pending_orders()
    with database.connect() as conn:
        assert conn.execute('SELECT count(*) AS n FROM deliveries').fetchone()['n']==0


def test_template_injection_escaped():
    c=login();pid=add('{{ 7*7 }} <script>alert(1)</script>')
    body=c.get(f'/order/{pid}').get_data(as_text=True)
    assert '{{ 7*7 }}' in body and '&lt;script&gt;' in body
    assert '<script>' not in body
    assert 'name="csrf_token"' in body and 'name="version"' in body


def test_migration_idempotent_and_reconnect():
    pid=add();database.migrate()
    # Fresh connections see committed values, independent of Python memory.
    assert database.pending_orders()[pid]['raw_text']=='익명 테스트 주문'


def test_headers_and_password_hash():
    c=login();r=c.get('/')
    assert r.headers['Cache-Control']=='no-store'
    assert r.headers['X-Frame-Options']=='DENY'
    with database.connect() as conn:
        row=conn.execute("SELECT password_hash FROM users WHERE username='staff'").fetchone()
        assert row['password_hash'].startswith('scrypt:')


def test_new_order_reuses_bots(monkeypatch):
    c=login()
    monkeypatch.setattr(web.ocb,'classify_order',lambda text:{'order_classification':'주문'})
    monkeypatch.setattr(web.osb,'split_order',lambda text:{'order_segments':[{'segment_text':text,'bundle_sequence':{'index':1,'total':1}}],'bundle_id':'test','split_status':'완료'})
    monkeypatch.setattr(web.correction_bot,'correct_text',lambda text:{'normalized_text':text,'candidates':[],'correction_log':[]})
    monkeypatch.setattr(web.order_draft_bot,'build_draft',lambda text:{'order_draft':{'product':'시험 꽃'},'field_confidence':{},'field_sources':{},'missing_fields':[]})
    monkeypatch.setattr(web.ribbon_price_bot,'process_ribbon_and_price',lambda *args:{'ribbon_message_raw':None,'ribbon_message_final':None,'product_name':'시험 꽃','price':10000,'quantity':1})
    monkeypatch.setattr(web.review_manager_bot,'build_review',lambda **kwargs:{'review_priority':'노랑','review_checklist':[]})
    r=c.post('/new',data={'csrf_token':csrf(c),'source_type':'manual','raw_text':'가상 주문 테스트'})
    assert r.status_code==302
    assert len(database.pending_orders())==1
    assert c.get(r.location).status_code==200


def test_stale_version_rejected():
    c=login();pid=add()
    assert c.post(f'/order/{pid}/reject',data={'csrf_token':csrf(c),'version':99}).status_code==409
    assert pid in database.pending_orders()


def test_legacy_import_dry_run_and_idempotence(tmp_path):
    import json
    from import_legacy import load_records, import_records
    pending=tmp_path/'pending.json'; old=tmp_path/'orders.json'
    pending.write_text(json.dumps({'test':payload()}))
    old.write_text(json.dumps({'orders':{'old':{'confirmed_fields':{'recipient_name':'가상 수신자'}}},'workflow_events':[]}))
    rows=load_records(pending,old)
    assert import_records(rows)['dry_run']
    assert not database.pending_orders()
    assert import_records(rows,True)['inserted']==2
    assert import_records(rows,True)['inserted']==0
    rows[0][1]['raw_text']='changed'
    with pytest.raises(ValueError):
        import_records(rows,True)


def test_database_outage_is_safe(monkeypatch):
    import psycopg
    from contextlib import contextmanager
    c=login()
    @contextmanager
    def broken():
        raise psycopg.OperationalError('sensitive DSN must never be shown')
        yield
    monkeypatch.setattr(database,'connect',broken)
    response=c.get('/')
    assert response.status_code==503
    assert 'sensitive' not in response.get_data(as_text=True)


def test_empty_input_and_invalid_version():
    c=login();pid=add()
    assert c.post('/new',data={'csrf_token':csrf(c),'raw_text':''}).status_code==200
    assert c.post(f'/order/{pid}/approve',data={'csrf_token':csrf(c),'version':'bad'}).status_code==400
    assert pid in database.pending_orders()


def test_no_unapproved_delivery_or_sms_code():
    source=Path(web.__file__).read_text()
    assert 'send_and_ledger(' not in source
    assert 'capture_delivery_photo(' not in source
    assert 'storage_bot.save_order(' not in source


def test_production_cookie_and_missing_secret(monkeypatch):
    from flask import Flask
    from security import init_security
    monkeypatch.setenv('APP_ENV','production')
    production=Flask('production_test');init_security(production)
    response=production.test_client().get('/login')
    assert 'Secure;' in response.headers['Set-Cookie']
    assert 'HttpOnly;' in response.headers['Set-Cookie']
    monkeypatch.setenv('SECRET_KEY','')
    with pytest.raises(RuntimeError):
        init_security(Flask('bad_config'))
