#!/usr/bin/env python3
"""
vault_check.py — 볼트 규칙 강제 종합 검사기

배경: `0. Docs/규칙강제_설계_2026-07-18.md` — 규칙이 문서로만 존재해 계속
안 지켜지는 문제를, git 커밋 순간 자동 검사(pre-commit hook)로 강제하는
3단 체계로 전환한다. handoff_check.py(HANDOFF 신선도 + 작업선언 잔류)가
2026-07-17에 처음 검증한 "규칙은 스크립트로 검사한다" 접근을 볼트 전체
규칙으로 확장한 것이 이 스크립트다.

두 모드:

1) 전체 모드 (인자 없이 실행): `python3 vault_check.py`
   - handoff_check.py의 기존 검사 전부(서브프로세스로 호출, 출력 그대로 표시)
   - 볼트 루트 직속 md 파일 중 허용 목록 밖 파일 나열
   - 14일 이상 수정 안 된 md 속 미체크 체크박스(`- [ ]`) 파일 상위 10개 (WARN)

2) pre-commit 모드: `python3 vault_check.py --pre-commit`
   - 스테이징된 파일만 검사(빠르게, 1초 이내 목표)
   - H1: 볼트 루트 직속에 새로 추가되는 md가 허용 목록 밖 → FAIL
   - H2: 스테이징된 md 파일의 마지막 비어있지 않은 줄이 sentinel(`<!-- ok -->`)
     아님 → FAIL (일부 경로 예외, 아래 SENTINEL_EXEMPT_PREFIXES 참고)
   - H3: `1. Projects/` 직속(하위 폴더 아님)에 새로 추가되는 md에
     frontmatter type:/status:/due: 중 하나라도 없음 → FAIL
   - H4: 파일명이 비밀 파일 패턴(.env, *.key, *credentials*, *.pem)과 일치
     → FAIL
   - WARN(신선도 등)은 pre-commit 모드에서는 출력하지 않는다(속도·소음 방지).
   - FAIL이 하나라도 있으면 exit 1 + 한국어로 "무엇이 왜 막혔고 어떻게
     고치는지" 출력. 전부 통과하면 exit 0.
   - 환경변수 VAULT_CHECK_SKIP=1 이면 모든 검사를 건너뛰고 경고만 출력 후
     exit 0(긴급 탈출구 — 커밋 메시지에 사유를 남길 것).

Windows cp949 콘솔 대비 UTF-8로 재설정한다.
"""
import sys
import os
import re
import subprocess
import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 이 스크립트는 <vault>/1. Projects/ai공장짓기/scripts/vault_check.py 에 위치.
# scripts -> ai공장짓기 -> "1. Projects" -> <vault root>
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
HANDOFF_CHECK_PATH = os.path.join(SCRIPT_DIR, "handoff_check.py")

# ── H1: 볼트 루트 직속 md 허용 목록 ──────────────────────────────────────
# 2026-07-18 시점 실제 루트에 있는 tracked md 기준으로 하드코딩
# (git ls-files -- '*.md' | awk -F'/' 'NF==1' 로 확인).
ALLOWED_ROOT_MD = {
    "0. 최우선_확인파일.md",
    "AGENTS.md",
    "CLAUDE.md",
    "LLM위키_홈.md",
    "START-HERE.md",
}

# ── H2: sentinel 검사 예외 경로(접두사, '/' 구분자) ─────────────────────
SENTINEL_EXEMPT_PREFIXES = (
    "2. Areas/Claude 세션로그/과거기록/",
    "_inbox/",
    ".obsidian/",
)

SENTINEL = "<!-- ok -->"

# ── H4: 비밀 파일 패턴 ───────────────────────────────────────────────────
SECRET_PATTERNS = [
    re.compile(r"(^|/)\.env(\.|$)"),          # .env, .env.local 등
    re.compile(r"\.key$", re.IGNORECASE),      # *.key
    re.compile(r"credentials", re.IGNORECASE), # *credentials*
    re.compile(r"\.pem$", re.IGNORECASE),      # *.pem
]

# ── WARN: 전체 모드 전용 상수 ────────────────────────────────────────────
STALE_CHECKBOX_DAYS = 14
STALE_CHECKBOX_TOP_N = 10
CHECKBOX_RE = re.compile(r"^\s*-\s\[\s\]\s", re.MULTILINE)
SKIP_DIR_NAMES = {".git", ".obsidian", "node_modules", "__pycache__"}


# ── 공통 유틸 ─────────────────────────────────────────────────────────────

def run_git(args):
    """VAULT_ROOT에서 git 명령을 실행하고 (returncode, stdout) 반환.
    실패 시 (1, "")."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=VAULT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return result.returncode, result.stdout


def staged_name_status():
    """git diff --cached --name-status 결과를 [(status, path), ...]로 반환.
    rename(R100 등)은 새 경로만 취해 status를 'R'로 정규화한다."""
    code, out = run_git(["diff", "--cached", "--name-status", "-z"])
    if code != 0 or not out:
        return []
    parts = out.split("\x00")
    entries = []
    i = 0
    while i < len(parts):
        field = parts[i]
        if not field:
            i += 1
            continue
        status = field[0]
        if status == "R" or status == "C":
            # 형식: R100 <NUL> old <NUL> new <NUL>
            if i + 2 >= len(parts):
                break
            new_path = parts[i + 2]
            entries.append((status, new_path))
            i += 3
        else:
            if i + 1 >= len(parts):
                break
            path = parts[i + 1]
            entries.append((status, path))
            i += 2
    return entries


def read_staged_content(path):
    """git show :<path> 로 스테이징된(작업트리 아님) 버전의 내용을 읽는다."""
    code, out = run_git(["show", f":{path}"])
    if code != 0:
        return None
    return out


def last_nonempty_line(text):
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def has_frontmatter_keys(text, keys):
    """text 맨 앞 '---' ... '---' 블록 안에 keys(각각 'type:' 등)가
    전부 있는지 확인. 블록이 없으면 False."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {k: False for k in keys}
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return {k: False for k in keys}
    block = "\n".join(lines[1:end_idx])
    result = {}
    for k in keys:
        pattern = re.compile(r"^" + re.escape(k) + r"\s*\S", re.MULTILINE)
        result[k] = bool(pattern.search(block))
    return result


def is_secret_filename(path):
    basename = os.path.basename(path)
    for pat in SECRET_PATTERNS:
        if pat.search(basename) or pat.search(path):
            return True
    return False


def is_exempt_from_sentinel(path):
    return any(path.startswith(prefix) for prefix in SENTINEL_EXEMPT_PREFIXES)


# ── pre-commit 모드 ───────────────────────────────────────────────────────

def precommit_check():
    if os.environ.get("VAULT_CHECK_SKIP") == "1":
        print("[SKIP] VAULT_CHECK_SKIP=1 — vault_check 검사를 건너뜁니다.")
        print("       ⚠ 검사 생략됨 — 커밋 메시지에 사유를 남기세요.")
        return 0

    entries = staged_name_status()
    if not entries:
        return 0

    failures = []  # (rule, message)

    added_or_renamed = [p for s, p in entries if s in ("A", "R")]
    content_check_targets = [p for s, p in entries if s in ("A", "M", "R", "C")]

    # H1: 루트 직속 새 md가 허용 목록 밖
    for path in added_or_renamed:
        if "/" in path:
            continue
        if not path.lower().endswith(".md"):
            continue
        if path not in ALLOWED_ROOT_MD:
            failures.append((
                "H1",
                f"'{path}' — 볼트 루트에는 정해진 파일만 둘 수 있습니다.\n"
                f"   → 새로 만든 문서는 볼트 루트가 아니라 '1. Projects/' 폴더 "
                f"안(해당 프로젝트 폴더)에 저장하세요.\n"
                f"   → 정말 루트에 있어야 하는 파일이면 vault_check.py의 "
                f"ALLOWED_ROOT_MD 목록에 추가해야 합니다(임의로 하지 말고 상의)."
            ))

    # H2: 스테이징된 md 파일 sentinel 누락
    for path in content_check_targets:
        if not path.lower().endswith(".md"):
            continue
        if is_exempt_from_sentinel(path):
            continue
        content = read_staged_content(path)
        if content is None:
            continue
        last = last_nonempty_line(content)
        if last != SENTINEL:
            failures.append((
                "H2",
                f"'{path}' — 문서의 마지막 줄이 저장 완료 표시(`{SENTINEL}`)가 "
                f"아닙니다(실제 마지막 줄: {last[:50]!r}).\n"
                f"   → 이 표시는 파일이 중간에 잘리지 않고 끝까지 저장됐다는 "
                f"확인 도장입니다. 문서 맨 끝 줄에 `{SENTINEL}` 을 추가하세요."
            ))

    # H3: '1. Projects/' 직속 새 md에 frontmatter type/status/due 누락
    for path in added_or_renamed:
        if not path.lower().endswith(".md"):
            continue
        prefix = "1. Projects/"
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix):]
        if "/" in rest:
            continue  # 하위 폴더는 대상 아님(직속 파일만)
        content = read_staged_content(path)
        if content is None:
            continue
        keys_present = has_frontmatter_keys(content, ["type:", "status:", "due:"])
        missing = [k.rstrip(":") for k, present in keys_present.items() if not present]
        if missing:
            failures.append((
                "H3",
                f"'{path}' — '1. Projects/' 바로 아래에 새로 만든 프로젝트 "
                f"문서인데 필수 정보({', '.join(missing)})가 빠졌습니다.\n"
                f"   → 문서 맨 위에 다음처럼 3줄을 추가하세요:\n"
                f"     ---\n     type: project\n     status: todo\n"
                f"     due: YYYY-MM-DD\n     ---"
            ))

    # H4: 비밀 파일 패턴
    for status, path in entries:
        if status == "D":
            continue
        if is_secret_filename(path):
            failures.append((
                "H4",
                f"'{path}' — 비밀번호/키로 보이는 파일은 커밋할 수 없습니다.\n"
                f"   → 이 파일을 git에 올리지 마세요(.gitignore에 추가 권장). "
                f"실수로 이미 커밋된 적이 있다면 즉시 키를 재발급하세요."
            ))

    if not failures:
        print("[PASS] vault_check --pre-commit — 하드 위반 없음")
        return 0

    print("=" * 60)
    print("[커밋 차단됨] 아래 문제를 고친 뒤 다시 커밋하세요.")
    print("=" * 60)
    for rule, msg in failures:
        print(f"\n[{rule} FAIL] {msg}")
    print("\n" + "-" * 60)
    print("정말 예외적으로 이번 한 번만 통과시켜야 한다면(권장하지 않음):")
    print('  VAULT_CHECK_SKIP=1 git commit -m "..."')
    print("→ 이 경우 커밋 메시지에 왜 건너뛰었는지 사유를 꼭 남기세요.")
    print("-" * 60)
    return 1


# ── 전체 모드 ─────────────────────────────────────────────────────────────

def full_run_handoff_check():
    print("== (1) handoff_check.py 통합 실행 ==")
    if not os.path.isfile(HANDOFF_CHECK_PATH):
        print(f"[ERROR] handoff_check.py를 찾을 수 없음: {HANDOFF_CHECK_PATH}")
        return True
    try:
        result = subprocess.run(
            [sys.executable, HANDOFF_CHECK_PATH],
            cwd=VAULT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[ERROR] handoff_check.py 실행 실패: {e}")
        return True
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return result.returncode != 0


def full_check_root_md():
    print("\n== (2) 볼트 루트 직속 md 허용 목록 검사 ==")
    any_violation = False
    try:
        entries = os.listdir(VAULT_ROOT)
    except OSError as e:
        print(f"[ERROR] 볼트 루트를 읽을 수 없음: {e}")
        return True
    for name in sorted(entries):
        full_path = os.path.join(VAULT_ROOT, name)
        if not os.path.isfile(full_path):
            continue
        if not name.lower().endswith(".md"):
            continue
        if name not in ALLOWED_ROOT_MD:
            print(f"[WARN] 허용 목록 밖 루트 md 파일: {name}")
            any_violation = True
    if not any_violation:
        print("[OK] 루트 md 파일 전부 허용 목록 안")
    return any_violation


def full_check_stale_checkboxes():
    print(f"\n== (3) {STALE_CHECKBOX_DAYS}일 이상 정체 + 미체크 체크박스 (상위 {STALE_CHECKBOX_TOP_N}개) ==")
    today = datetime.date.today()
    candidates = []  # (age_days, count, rel_path)
    for dirpath, dirnames, filenames in os.walk(VAULT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for fn in filenames:
            if not fn.lower().endswith(".md"):
                continue
            full_path = os.path.join(dirpath, fn)
            try:
                mtime = os.path.getmtime(full_path)
            except OSError:
                continue
            age_days = (today - datetime.date.fromtimestamp(mtime)).days
            if age_days < STALE_CHECKBOX_DAYS:
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            count = len(CHECKBOX_RE.findall(text))
            if count > 0:
                rel_path = os.path.relpath(full_path, VAULT_ROOT).replace(os.sep, "/")
                candidates.append((age_days, count, rel_path))

    if not candidates:
        print("[OK] 해당 없음")
        return

    candidates.sort(key=lambda t: (-t[0], -t[1]))
    for age_days, count, rel_path in candidates[:STALE_CHECKBOX_TOP_N]:
        print(f"[WARN] {rel_path} — {age_days}일 정체, 미체크 항목 {count}개")
    if len(candidates) > STALE_CHECKBOX_TOP_N:
        print(f"... 외 {len(candidates) - STALE_CHECKBOX_TOP_N}개 더 있음(상위 {STALE_CHECKBOX_TOP_N}개만 표시)")


def full_check():
    warn1 = full_run_handoff_check()
    warn2 = full_check_root_md()
    full_check_stale_checkboxes()  # soft warn, exit code에 영향 없음
    return 1 if (warn1 or warn2) else 0


def main():
    if "--pre-commit" in sys.argv[1:]:
        sys.exit(precommit_check())
    sys.exit(full_check())


if __name__ == "__main__":
    main()
