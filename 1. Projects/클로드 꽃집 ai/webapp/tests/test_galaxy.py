import io
from test_stage1 import app,database,isolated_schema,login,csrf
from test_stage2 import mock_ai


def test_public_manifest_and_worker_only():
    c=app.test_client()
    m=c.get('/galaxy.webmanifest').json
    assert m['share_target']['method']=='POST'
    assert m['share_target']['params']['files'][0]['name']=='files'
    assert c.get('/galaxy-sw.js').status_code==200
    assert c.get('/galaxy').status_code==302


def test_share_requires_confirmation_auth_csrf():
    c=login()
    assert c.post('/galaxy-share',data={'text':'가상'}).status_code==400
    assert c.post('/galaxy-share',data={'csrf_token':csrf(c)}).status_code==409
    assert not database.pending_orders()
    assert c.get('/galaxy').status_code==200
    assert 'name="csrf_token"' in c.get('/galaxy').get_data(as_text=True)


def test_viewer_driver_cannot_use_share():
    for role in ['viewer','driver']:
        assert login(role).get('/galaxy').status_code==403


def test_shared_synthetic_audio_existing_intake(monkeypatch):
    mock_ai(monkeypatch)
    import app as web
    monkeypatch.setattr(web.transcription_bot,'transcribe',lambda **kw:{'engine_meta':{'real_api_connected':True},'stt_text':'가상 주문 전사'})
    c=login()
    def post():return c.post('/intakes',data={'csrf_token':csrf(c),'audio':(io.BytesIO(b'fake-call'),'call.wav')})
    a=post();b=post()
    assert a.location==b.location
    assert len(database.pending_orders())==1
