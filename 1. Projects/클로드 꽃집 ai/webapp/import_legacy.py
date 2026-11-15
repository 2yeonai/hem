"""Offline legacy JSON migration. Dry run by default; execution requires explicit operator approval.
Never run this against customer data without the owner's approval and a verified backup.
"""
import argparse
import hashlib
import json
from pathlib import Path
from psycopg.types.json import Jsonb
import database


def load_records(pending_path, orders_path):
    records = []
    if pending_path:
        pending = json.loads(Path(pending_path).read_text())
        if not isinstance(pending, dict):
            raise ValueError('대기 주문 JSON 형식 오류')
        for pid, payload in pending.items():
            if not isinstance(payload, dict) or not isinstance(payload.get('draft'), dict):
                raise ValueError('대기 주문 구조 오류')
            records.append(('pending:' + pid, payload, 'pending', None))
    if orders_path:
        old = json.loads(Path(orders_path).read_text())
        for pid, record in old['orders'].items():
            fields = record['confirmed_fields']
            if not isinstance(fields, dict):
                raise ValueError('확정 주문 구조 오류')
            events = [e for e in old.get('workflow_events', []) if e.get('order_id') == pid]
            records.append(('legacy:' + pid, {'legacy_record': record, 'legacy_events': events}, 'confirmed', fields))
    return records


def import_records(records, execute=False):
    if not execute:
        return {'validated': len(records), 'inserted': 0, 'dry_run': True}
    inserted = 0
    with database.connect() as conn:
        for pid, payload, status, fields in records:
            fingerprint = hashlib.sha256(json.dumps([payload,status,fields],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            existing = conn.execute('SELECT payload FROM orders WHERE id=%s FOR UPDATE', (pid,)).fetchone()
            if existing:
                if existing['payload'].get('_import_fingerprint') != fingerprint:
                    raise ValueError('이전 이관과 내용이 다릅니다. 자동 덮어쓰지 않습니다.')
                continue
            stored = dict(payload, _import_fingerprint=fingerprint)
            conn.execute('INSERT INTO orders(id,payload,status,confirmed) VALUES (%s,%s,%s,%s)',
                         (pid,Jsonb(stored),status,Jsonb(fields)))
            if fields:
                for kind in ('recipient','sender'):
                    conn.execute('INSERT INTO customers(id,order_id,kind,details) VALUES (%s,%s,%s,%s)',
                                 (pid+':'+kind,pid,kind,Jsonb({k:v for k,v in fields.items() if k.startswith(kind+'_')})))
                # Historical mock delivery results are NOT evidence of actual delivery.
                conn.execute('INSERT INTO deliveries(order_id,details) VALUES (%s,%s)',
                             (pid,Jsonb({k:v for k,v in fields.items() if k.startswith('delivery_')})))
            database.event(conn,pid,None,'legacy_imported',{'fingerprint':fingerprint})
            inserted += 1
    return {'validated':len(records),'inserted':inserted,'dry_run':False}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pending')
    parser.add_argument('--orders')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--owner-approved',action='store_true')
    args=parser.parse_args()
    if args.execute and not args.owner_approved:
        parser.error('--execute requires --owner-approved after explicit owner approval')
    print(json.dumps(import_records(load_records(args.pending,args.orders),args.execute)))
