"""PostgreSQL persistence. No implicit schema creation or legacy JSON import."""
import os
import uuid
from pathlib import Path
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from werkzeug.security import generate_password_hash


@contextmanager
def connect():
    url = os.environ.get('DATABASE_URL', '')
    if not url.startswith(('postgresql://', 'postgres://')):
        raise RuntimeError('DATABASE_URL must point to PostgreSQL')
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=5) as conn:
        yield conn


def migrate():
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(72611016)')
        conn.execute(Path(__file__).with_name('schema.sql').read_text())


def create_user(username, password, role):
    if role not in {'admin', 'staff', 'viewer', 'driver'}:
        raise ValueError('Invalid role')
    if not 12 <= len(password) <= 1024 or not 1 <= len(username.strip()) <= 100:
        raise ValueError('사용자 이름과 12자 이상의 비밀번호가 필요합니다.')
    with connect() as conn:
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)',
                     (username.strip(), generate_password_hash(password), role))


def pending_orders():
    with connect() as conn:
        rows = conn.execute("SELECT id, payload, version, review_draft FROM orders WHERE status='pending'").fetchall()
        return {r['id']: dict(r['payload'], version=r['version'], review_draft=r['review_draft']) for r in rows}


def add_pending(pid, payload, actor):
    with connect() as conn:
        conn.execute('INSERT INTO orders (id, payload) VALUES (%s,%s)', (pid, Jsonb(payload)))
        event(conn, pid, actor, 'received', {'source_type': payload.get('source_type')})


def event(conn, pid, actor, kind, detail):
    conn.execute('INSERT INTO order_events (order_id, actor_id, kind, detail) VALUES (%s,%s,%s,%s)',
                 (pid, actor, kind, Jsonb(detail)))


class Conflict(Exception):
    pass


def transition(pid, version, actor, status, fields=None):
    """Lock one order; customer, delivery and audit changes commit atomically."""
    if status not in {'confirmed', 'rejected'}:
        raise ValueError('Invalid transition')
    with connect() as conn:
        row = conn.execute('SELECT * FROM orders WHERE id=%s FOR UPDATE', (pid,)).fetchone()
        if not row or row['status'] != 'pending' or row['version'] != version:
            raise Conflict('이미 처리되었거나 변경된 주문입니다. 목록을 새로고침해주세요.')
        fields = fields or {}
        conn.execute('UPDATE orders SET status=%s, confirmed=%s, version=version+1, updated_at=now() WHERE id=%s',
                     (status, Jsonb(fields), pid))
        if status == 'confirmed':
            # Do not merge people by name/phone: the same contact can represent several recipients.
            for kind in ('recipient', 'sender'):
                conn.execute('INSERT INTO customers (id, order_id, kind, details) VALUES (%s,%s,%s,%s)',
                             (uuid.uuid4().hex, pid, kind, Jsonb({k: v for k, v in fields.items()
                              if k.startswith(kind + '_')})))
            conn.execute('INSERT INTO deliveries (order_id, details) VALUES (%s,%s)',
                         (pid, Jsonb({k: v for k, v in fields.items() if k.startswith('delivery_')})))
        event(conn, pid, actor, status, {'before': row['status'], 'confirmed_fields': fields})


def save_review(pid, version, actor, fields):
    with connect() as conn:
        row=conn.execute("UPDATE orders SET review_draft=%s,version=version+1,updated_at=now() WHERE id=%s AND version=%s AND status='pending' RETURNING id",(Jsonb(fields),pid,version)).fetchone()
        if not row: raise Conflict('다른 검수자가 변경했습니다. 새로고침 후 다시 확인해주세요.')
        event(conn,pid,actor,'review_saved',{'fields':fields})
