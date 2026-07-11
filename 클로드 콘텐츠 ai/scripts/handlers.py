#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handlers.py — 콘텐츠 공장(주제→발행) 핸들러

현재 상태: 전부 mock(목업). 실제 LLM/게시 호출 없음 — 파이프라인 구조가
범용 러너 위에서 끝까지 도는지 증명하는 단계 (방역 스킬과 같은 방식).

실운영 전환 시 교체 지점:
  - model stage 4개: 러너의 ModelProvider 실제 구현으로 교체
  - 게시봇: Cowork 세션에서 Claude가 커넥터/Chrome으로 실제 게시
    (승인완료 검증 로직은 그대로 유지 — 이중방어)
"""

MAX_THREAD_CHARS = 500          # Threads 글자수 제한 (조건테이블 값 — 형식게이트)
DEFAULT_BANNED_WORDS = []       # 금지어 — 혜미 골든셋으로 채울 것


# ----- run_if 판정 -----

def evaluate_run_if(condition, ctx):
    if condition is None:
        return True, "run_if 없음 — 항상 실행"
    channels = ((ctx.get("topic") or {}).get("channels")) or []
    if condition == "블로그_채널이_선택됨":
        return ("blog" in channels), f"channels={channels}"
    if condition == "스레드_채널이_선택됨":
        return ("threads" in channels), f"channels={channels}"
    return False, f"알 수 없는 run_if '{condition}' — 안전하게 건너뜀"


# ----- 승인 블록 (schema v2 approval_block 패턴 — 방역과 동일 구조) -----

def _new_approval_block(prev_doc):
    prev = (prev_doc or {}).get("approval") or {}
    history = list(prev.get("version_history") or [])
    if prev.get("status") == "반려":
        history.append({"version": prev.get("version"), "status": "반려",
                        "rejection_reason": prev.get("rejection_reason")})
        version = (prev.get("version") or 1) + 1
    else:
        version = prev.get("version") or 1
    return {"status": "초안", "version": version, "approved_by": None,
            "approved_at": None, "rejection_reason": None, "version_history": history}


# ----- stage mock 함수 -----

def run_주제접수봇(ctx, stage):
    inp = ctx["_input"]
    ctx["topic"] = {
        "title": inp.get("topic", "(주제 미입력)"),
        "channels": inp.get("channels", ["blog", "threads"]),
        "tone": inp.get("tone", "따뜻하고 담백하게"),
        "reference": inp.get("reference"),
    }
    return f"주제 접수: {ctx['topic']['title']!r} → 채널 {ctx['topic']['channels']}"


def run_자료조사봇(ctx, stage):
    t = ctx["topic"]
    ctx["research_notes"] = {
        "facts": [f"[mock] '{t['title']}' 관련 핵심 사실 1", f"[mock] 핵심 사실 2"],
        "unverified": ["[mock] 사실 미확인 항목 — 실운영시 웹검색으로 검증"],
        "sources": [],
    }
    return "research_notes 생성 (mock — 실제 웹검색 없음)"


def run_분석카드봇(ctx, stage):
    n = ctx.get("_card_calls", 0)
    ctx["_card_calls"] = n + 1
    t = ctx["topic"]
    ctx["content_card"] = {
        "key_message": f"[mock v{n + 1}] {t['title']} — 핵심 메시지",
        "outline": ["도입", "본론1", "본론2", "마무리"],
        "evidence": ctx.get("research_notes", {}).get("facts", []),
        "banned_words": DEFAULT_BANNED_WORDS,
        "revision": n + 1,
    }
    return f"분석카드 v{n + 1} (모든 채널은 이 카드에서만 파생)"


def run_블로그작성봇(ctx, stage):
    card = ctx["content_card"]
    prev = ctx.get("blog_draft")
    ctx["blog_draft"] = {
        "title": f"[mock] {card['key_message']}",
        "body": f"[mock 블로그 본문 — 카드 v{card['revision']} 기반, 구조 {card['outline']}]",
        "tags": ["mock태그"],
        "approval_required": True,
        "approval": _new_approval_block(prev),
    }
    return f"blog_draft v{ctx['blog_draft']['approval']['version']} 작성 (mock)"


def run_스레드작성봇(ctx, stage):
    card = ctx["content_card"]
    prev = ctx.get("thread_draft")
    posts = [f"[mock 스레드 1/2 — 카드 v{card['revision']}]", "[mock 스레드 2/2]"]
    ctx["thread_draft"] = {
        "posts": posts,
        "approval_required": True,
        "approval": _new_approval_block(prev),
    }
    return f"thread_draft v{ctx['thread_draft']['approval']['version']} 작성 — 게시물 {len(posts)}개 (mock)"


def run_형식게이트봇(ctx, stage):
    problems = []
    banned = ((ctx.get("content_card") or {}).get("banned_words")) or []
    blog = ctx.get("blog_draft")
    if blog:
        if not blog.get("title"):
            problems.append("블로그 제목 없음")
        for w in banned:
            if w and w in (blog.get("body") or ""):
                problems.append(f"블로그 금지어 포함: {w}")
    thread = ctx.get("thread_draft")
    if thread:
        for i, post in enumerate(thread.get("posts") or [], 1):
            if len(post) > MAX_THREAD_CHARS:
                problems.append(f"스레드 {i}번 글자수 초과({len(post)}>{MAX_THREAD_CHARS})")
    ctx["format_check"] = {"passed": not problems, "problems": problems}
    return f"형식게이트: {'통과' if not problems else problems} (조건테이블 판정 — 질적 판단 없음)"


def run_대표승인(ctx, stage):
    """human 스텁 — 입력 JSON의 승인_시뮬레이션으로 채널별 승인/반려 흉내.
    형식: "승인" | "반려:형식|내용|제약위반" | {"blog": .., "threads": ..} | 리스트(회차별 순차 소비)"""
    idx = ctx.get("_승인_호출횟수", 0)
    ctx["_승인_호출횟수"] = idx + 1
    sim = ctx["_input"].get("승인_시뮬레이션", "승인")
    if isinstance(sim, list):
        sim = sim[min(idx, len(sim) - 1)] if sim else "승인"
    if isinstance(sim, str):
        sim = {"blog": sim, "threads": sim}
    summary = []
    for key, draft_key in (("blog", "blog_draft"), ("threads", "thread_draft")):
        doc = ctx.get(draft_key)
        if not doc or not doc.get("approval_required"):
            continue
        decision = sim.get(key, "승인")
        ap = doc.setdefault("approval", {})
        if str(decision).startswith("반려"):
            reason = decision.split(":", 1)[1] if ":" in decision else "내용"
            ap.update({"status": "반려", "rejection_reason": f"[mock] {reason}", "approved_by": None})
            ap["_reason_code"] = reason
        else:
            ap.update({"status": "승인완료", "approved_by": "[mock] 대표자",
                       "approved_at": ctx["_input"].get("created_at", "2026-07-12T00:00:00"),
                       "rejection_reason": None})
            ap.pop("_reason_code", None)
        summary.append(f"{key}={ap['status']}")
    return f"대표승인(스텁): {', '.join(summary) if summary else '(대상 없음)'}"


def run_게시봇(ctx, stage):
    """이중방어: 승인완료 아닌 초안은 절대 게시 안 함 (방역 문자장부봇 패턴)."""
    blocked, published = [], []
    for key, draft_key in (("blog", "blog_draft"), ("threads", "thread_draft")):
        doc = ctx.get(draft_key)
        if not doc:
            continue
        status = (doc.get("approval") or {}).get("status")
        if doc.get("approval_required") and status != "승인완료":
            blocked.append((key, status))
        else:
            published.append(key)
    if blocked:
        raise RuntimeError(f"[안전장치 발동 - 게시 차단] 승인완료 안 된 초안 게시 시도: {blocked}")
    ctx["publish_result"] = {
        "published": {k: f"[mock URL — 실제 게시 없음] {k}" for k in published},
        "note": "실제 게시는 Cowork 세션에서 승인 후 커넥터/Chrome으로 수행 (SKILL.md 참고)",
    }
    return f"게시(mock): {published}"


def run_기록봇(ctx, stage):
    pr = ctx.get("publish_result") or {}
    ctx["publish_log"] = {
        "entries": [{"channel": k, "url": v, "at": ctx["_input"].get("created_at", "2026-07-12")}
                    for k, v in (pr.get("published") or {}).items()],
    }
    return f"발행 장부 기록: {len(ctx['publish_log']['entries'])}건"


STAGE_FUNCS = {
    "주제접수봇": run_주제접수봇,
    "자료조사봇": run_자료조사봇,
    "분석카드봇": run_분석카드봇,
    "블로그작성봇": run_블로그작성봇,
    "스레드작성봇": run_스레드작성봇,
    "형식게이트봇": run_형식게이트봇,
    "대표승인": run_대표승인,
    "게시봇": run_게시봇,
    "기록봇": run_기록봇,
}


# ----- 반려 감지 (러너 반려루프용) -----

def pending_rejections(ctx, stage_id):
    if stage_id != "대표승인":
        return {}
    out = {}
    for key, draft_key in (("blog", "blog_draft"), ("threads", "thread_draft")):
        doc = ctx.get(draft_key)
        if doc and doc.get("approval_required"):
            ap = doc.get("approval") or {}
            if ap.get("status") == "반려":
                out[key] = ap.get("_reason_code", "내용")
    return out
