"""Authentication, server-side sessions, role checks and CSRF for the legacy Flask UI."""
import hashlib
import os
import secrets
from datetime import timedelta
import click
import psycopg
from flask import abort, g, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import database

DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))
LOGIN = '''<!doctype html><html lang="ko"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>온천꽃식물원 로그인</title><style>body{max-width:400px;margin:40px auto;padding:20px;font-family:sans-serif;background:#f7f5ef}input,button{box-sizing:border-box;width:100%;padding:14px;margin:8px 0}button{background:#1f5c3a;color:white;border:0}</style>
<h1>온천꽃식물원</h1><p>{{ message }}</p><form method="post">
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
<label>아이디<input name="username" autocomplete="username" required maxlength="100"></label>
<label>비밀번호<input type="password" name="password" autocomplete="current-password" required maxlength="1024"></label>
<button>로그인</button></form></html>'''


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def init_security(app):
    secret = os.environ.get('SECRET_KEY', '')
    if len(secret) < 32:
        raise RuntimeError('SECRET_KEY must contain at least 32 characters')
    app.config.update(SECRET_KEY=secret, SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=os.environ.get('APP_ENV') != 'development',
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8))

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']
    app.jinja_env.globals['csrf_token'] = csrf_token

    @app.before_request
    def protect():
        g.user = None
        if request.endpoint in {'static','galaxy_manifest','galaxy_worker'}:
            return
        if request.endpoint != 'login':
            token = session.get('auth', '')
            if token:
                with database.connect() as conn:
                    g.user = conn.execute('''SELECT u.* FROM users u JOIN auth_sessions s ON u.id=s.user_id
                        WHERE s.token_hash=%s AND s.expires_at>now() AND u.active''', (digest(token),)).fetchone()
            if not g.user:
                session.clear()
                return redirect(url_for('login'))
            if request.endpoint != 'logout':
                if g.user['role'] == 'driver':
                    abort(403)  # Delivery-only UI is a later stage, deny all shop data now.
                if (request.method not in {'GET', 'HEAD'} or request.endpoint in {'new_order','intakes'}) and g.user['role'] not in {'admin','staff'}:
                    abort(403)
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            expected = session.get('csrf', '')
            supplied = request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
                abort(400, '화면을 새로고침한 뒤 다시 시도해주세요.')

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.route('/login', methods=['GET','POST'])
    def login():
        message = '등록된 계정으로 로그인해주세요.'
        if request.method == 'POST':
            username = request.form.get('username', '')
            password = request.form.get('password', '')
            if not 1 <= len(username) <= 100 or not 1 <= len(password) <= 1024:
                return render_template_string(LOGIN, message='로그인할 수 없습니다. 입력을 확인해주세요.'), 401
            with database.connect() as conn:
                user = conn.execute('SELECT *, locked_until > now() AS locked FROM users WHERE username=%s FOR UPDATE', (username,)).fetchone()
                valid = check_password_hash(user['password_hash'] if user else DUMMY_HASH, password)
                if user and valid and user['active'] and not user['locked']:
                    conn.execute('UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=%s', (user['id'],))
                    token = secrets.token_urlsafe(32)
                    conn.execute("INSERT INTO auth_sessions VALUES (%s,%s,now()+interval '8 hours')", (digest(token),user['id']))
                    session.clear()
                    session.permanent = True
                    session['auth'] = token
                    return redirect(url_for('index'))
                if user and not user['locked']:
                    conn.execute("""UPDATE users SET failed_attempts=CASE WHEN locked_until IS NOT NULL THEN 1 ELSE failed_attempts+1 END,
                        locked_until=CASE WHEN locked_until IS NULL AND failed_attempts>=4 THEN now()+interval '15 minutes' ELSE NULL END WHERE id=%s""", (user['id'],))
            message = '로그인할 수 없습니다. 입력을 확인하거나 잠시 후 다시 시도해주세요.'
            return render_template_string(LOGIN, message=message), 401
        return render_template_string(LOGIN, message=message)

    @app.post('/logout')
    def logout():
        with database.connect() as conn:
            conn.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (digest(session.get('auth','')),))
        session.clear()
        return redirect(url_for('login'))

    @app.errorhandler(psycopg.Error)
    def database_error(error):
        # Never render DSN, SQL parameters or order contents to browser/logs.
        return '저장소 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.', 503

    @app.cli.command('init-db')
    def init_db():
        database.migrate()
        click.echo('DB schema version 1 ready')

    @app.cli.command('create-user')
    @click.option('--username', prompt=True)
    @click.option('--role', type=click.Choice(['admin','staff','viewer','driver']), default='staff')
    @click.password_option(confirmation_prompt=True)
    def create_user(username, role, password):
        database.create_user(username, password, role)
        click.echo('계정 생성 완료')
