#!/usr/bin/env bash
# sync_vault.sh — Git Bash용 볼트 동기화 도우미
#
# 배경: `0. Docs/기록체계_재설계_2026-07-17.md` §3-③ / §4.
# 이 볼트는 여러 계정/세션이 동시에 git을 건드리는 일이 실제로 있었고
# (같은 날 세션들이 서로 모르게 같은 파일을 고쳐 git index 충돌·내용
# 충돌이 났던 사례 있음), .git/index.lock 충돌도 반복됐다(2026-07-13,
# 2026-07-17). 이 스크립트는 pull -> add -> commit(계정태그 자동) ->
# push를 한 번에 묶고, lock 재시도를 표준화한다. 계정별 사전 등록은
# 필요 없다 — git config user.email의 @ 앞부분을 태그로 자동 사용한다.
#
# 사용법:
#   bash sync_vault.sh ["커밋 메시지"]
#   메시지를 생략하면 "자동 동기화"로 커밋한다.
#
# 동작 순서:
#   1. 계정태그 결정 (git config user.email의 @ 앞부분)
#   2. .git/index.lock 존재 시 60초 대기 후 재확인, 그래도 있으면
#      .git/index.lock.stale-<타임스탬프>로 치우고 진행
#   3. git pull --no-rebase origin main (충돌 시 중단, 사람에게 안내)
#   4. git add -A
#   5. 변경 있으면 git commit -m "vault sync <날짜> [태그]: <메시지>"
#   6. git push origin main
#   7. 각 단계 성공/실패를 한국어로 출력
#
# 주의: 이 스크립트는 실제 git 상태를 변경한다(pull/commit/push). 다른
# 세션이 git 작업 중일 수 있으므로, 실행 전 `ai공장짓기/현재작업현황.md`에
# [git] 선언을 남기고 끝나면 지우는 것을 권장한다(§3-③).

set -u

COMMIT_MSG_ARG="${1:-}"

# --- 0. 경로/사전 준비 ---------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts -> ai공장짓기 -> "1. Projects" -> <볼트 루트>
VAULT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$VAULT_ROOT" || { echo "[실패] 볼트 루트로 이동 못 함: $VAULT_ROOT"; exit 1; }

if ! command -v git >/dev/null 2>&1; then
    echo "[실패] git 명령을 찾을 수 없음 — 동기화 중단"
    exit 1
fi

if [ ! -d "$VAULT_ROOT/.git" ]; then
    echo "[실패] $VAULT_ROOT 는 git 저장소가 아님 — 동기화 중단"
    exit 1
fi

# --- 1. 계정태그 결정 -----------------------------------------------------
USER_EMAIL="$(git config user.email 2>/dev/null || true)"
if [ -z "$USER_EMAIL" ]; then
    echo "[경고] git config user.email 이 설정되어 있지 않음 — 태그를 [unknown]으로 대체"
    ACCOUNT_TAG="unknown"
else
    ACCOUNT_TAG="${USER_EMAIL%%@*}"
fi
echo "[정보] 계정태그: [$ACCOUNT_TAG] (출처: user.email=$USER_EMAIL)"

# --- 2. .git/index.lock 처리 ----------------------------------------------
LOCK_FILE="$VAULT_ROOT/.git/index.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "[대기] .git/index.lock 발견 — 60초 대기 후 재확인"
    sleep 60
    if [ -f "$LOCK_FILE" ]; then
        STALE_SUFFIX="$(date +%Y%m%d%H%M%S)"
        STALE_PATH="${LOCK_FILE}.stale-${STALE_SUFFIX}"
        if mv "$LOCK_FILE" "$STALE_PATH"; then
            echo "[처리] 60초 후에도 lock이 남아있어 치움: $STALE_PATH (표준 우회법)"
        else
            echo "[실패] index.lock 을 치우지 못함 — 동기화 중단 (수동 확인 필요: $LOCK_FILE)"
            exit 1
        fi
    else
        echo "[정보] 60초 대기 중 lock이 해제됨 — 계속 진행"
    fi
fi

# --- 3. git pull -----------------------------------------------------------
echo "[진행] git pull --no-rebase origin main"
if git pull --no-rebase origin main; then
    echo "[성공] pull 완료"
else
    echo "[실패] pull 중 문제 발생(충돌 가능성) — 자동 처리를 중단합니다."
    echo "        git status 로 충돌 파일을 확인하고 사람이 직접 병합/커밋해 주세요."
    exit 1
fi

# 병합 충돌이 남아있는지 이중 확인 (pull이 0을 반환해도 방어적으로 검사)
if git ls-files -u | grep -q .; then
    echo "[실패] 병합 충돌(unmerged) 파일이 남아있음 — 자동 처리를 중단합니다."
    echo "        git status 로 충돌 파일을 확인하고 사람이 직접 병합/커밋해 주세요."
    exit 1
fi

# --- 4. git add -A ----------------------------------------------------------
echo "[진행] git add -A"
if git add -A; then
    echo "[성공] add 완료"
else
    echo "[실패] add 중 문제 발생 — 동기화 중단"
    exit 1
fi

# --- 5. 변경 있으면 commit ---------------------------------------------------
if git diff --cached --quiet; then
    echo "[정보] 스테이지된 변경 없음 — commit 생략"
else
    TODAY="$(date +%Y-%m-%d)"
    if [ -n "$COMMIT_MSG_ARG" ]; then
        MSG_BODY="$COMMIT_MSG_ARG"
    else
        MSG_BODY="자동 동기화"
    fi
    COMMIT_MSG="vault sync ${TODAY} [${ACCOUNT_TAG}]: ${MSG_BODY}"
    echo "[진행] git commit -m \"$COMMIT_MSG\""
    if git commit -m "$COMMIT_MSG"; then
        echo "[성공] commit 완료"
    else
        echo "[실패] commit 중 문제 발생 — 동기화 중단"
        exit 1
    fi
fi

# --- 6. git push -------------------------------------------------------------
echo "[진행] git push origin main"
if git push origin main; then
    echo "[성공] push 완료"
else
    echo "[실패] push 중 문제 발생 — 원격 상태를 확인하고 필요 시 다시 pull 후 재시도하세요."
    exit 1
fi

echo "[완료] 볼트 동기화 정상 종료"
exit 0
