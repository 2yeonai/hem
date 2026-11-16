#!/usr/bin/env bash
# Run from webapp. PostgreSQL must be a disposable local test database.
set -euo pipefail
: "${TEST_DATABASE_URL:?Set disposable local PostgreSQL test database}"
: "${TEST_CHROMIUM:?Set headless-shell or Chrome executable}"
PYTHON_BIN=${PYTHON_BIN:-python}
export DATABASE_URL="$TEST_DATABASE_URL" APP_ENV=development
export SECRET_KEY=synthetic-browser-local-test-only-000000000000
export ANTHROPIC_API_KEY='' OPENAI_API_KEY=''
export PYTHONPATH="$PWD"
export PGOPTIONS="-c search_path=browser_test_$(date +%s)_${RANDOM}"
mkdir -p tests/artifacts
export TEST_SCREENSHOT="$PWD/tests/artifacts/failure.png"
"$PYTHON_BIN" - <<'PY'
import os
from urllib.parse import urlparse
import psycopg
from psycopg import sql
u=urlparse(os.environ['DATABASE_URL'])
assert u.hostname in ('localhost','127.0.0.1') and 'test' in u.path, 'Disposable loopback test DB required'
schema=os.environ['PGOPTIONS'].split('=')[1]
with psycopg.connect(os.environ['DATABASE_URL']) as c:
 c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
import database
database.migrate();database.create_user('synthetic','Synthetic-password-123','staff')
with database.connect() as c:
 assert c.execute("SELECT active,role FROM users WHERE username='synthetic'").fetchone()=={'active':True,'role':'staff'}
print('Synthetic account exists and active; APP_ENV=development')
PY
"$PYTHON_BIN" -m flask --app app run --host 127.0.0.1 --port 5099 > tests/artifacts/server.log 2>&1 &
app_pid=$!
trap 'kill "$app_pid" 2>/dev/null || true' EXIT
node tests/galaxy_queue_browser.cjs | tee tests/artifacts/browser.log
