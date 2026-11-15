"""Real pg_dump/restore round-trip into a new disposable DB; synthetic data only."""
import os
import subprocess
import uuid
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg import sql
from test_stage1 import database, isolated_schema, add


def test_backup_restores_orders_users_customers_deliveries_and_events(tmp_path):
    pid=add()
    database.transition(pid,1,1,'confirmed',{'recipient_name':'가상 검증','delivery_address':'가상주소'})
    with database.connect() as conn:
        schema=conn.execute('SELECT current_schema() AS s').fetchone()['s']
    settings=conninfo_to_dict(os.environ['TEST_DATABASE_URL'])
    target='restore_'+uuid.uuid4().hex
    admin=make_conninfo(**dict(settings,dbname='postgres'))
    restored=make_conninfo(**dict(settings,dbname=target))
    with psycopg.connect(admin,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target)))
    try:
        dump=tmp_path/'synthetic.dump'
        subprocess.run(['pg_dump','--dbname',os.environ['TEST_DATABASE_URL'],'--schema',schema,'--format=c','--file',str(dump)],check=True,capture_output=True)
        subprocess.run(['pg_restore','--exit-on-error','--dbname',restored,str(dump)],check=True,capture_output=True)
        with psycopg.connect(restored) as conn:
            for table,n in [('orders',1),('customers',2),('deliveries',1),('order_events',2),('users',4)]:
                assert conn.execute(sql.SQL('SELECT count(*) FROM {}.{}').format(sql.Identifier(schema),sql.Identifier(table))).fetchone()[0]==n
    finally:
        with psycopg.connect(admin,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(target)))
