"""Additional review regressions. All identities and data are synthetic."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from test_stage1 import app, database, isolated_schema, login, csrf, payload
from import_legacy import import_records


def test_unicode_csrf_rejected_without_server_error():
    c=login()
    assert c.post('/logout',data={'csrf_token':'가상토큰'}).status_code==400


def test_overlong_password_cannot_authenticate_by_truncation():
    password='x'*1024
    database.create_user('long',password,'staff')
    c=app.test_client();c.get('/login')
    assert c.post('/login',data={'csrf_token':csrf(c),'username':'long','password':password+'extra'}).status_code==401


def test_account_creation_rejects_unusable_lengths():
    with pytest.raises(ValueError):
        database.create_user('u'*101,'synthetic-password','staff')
    with pytest.raises(ValueError):
        database.create_user('normal','x'*1025,'staff')


def test_import_dry_run_rejects_incomplete_payload():
    with pytest.raises(ValueError):
        import_records([('pending:bad',{'draft':{}},'pending',None)])


def test_concurrent_legacy_import_is_idempotent():
    records=[('pending:parallel',payload(),'pending',None)]
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:import_records(records,True)['inserted'],range(2)))
    assert sorted(results)==[0,1]


def test_import_empty_confirmed_fields_keeps_related_rows():
    import_records([('legacy:empty',{'legacy_record':{}},'confirmed',{})],True)
    with database.connect() as conn:
        assert conn.execute('SELECT count(*) AS n FROM deliveries').fetchone()['n']==1


def test_role_change_applies_to_existing_session():
    c=login()
    with database.connect() as conn:
        conn.execute("UPDATE users SET role='driver' WHERE username='staff'")
    assert c.get('/').status_code==403


def test_invalid_import_batch_rolls_back():
    records=[('pending:good',payload(),'pending',None),('pending:bad',{},'unknown',None)]
    with pytest.raises(ValueError):
        import_records(records,True)
    assert not database.pending_orders()
