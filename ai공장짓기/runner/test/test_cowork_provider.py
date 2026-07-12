# cowork provider 스텁 테스트 (2026-07-12) — 러너 무수정 검증 포함
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from cowork_provider import CoworkModelProvider

STAGE = {"id": "draft_bot", "kind": "model", "tier": "mid",
         "io": {"reads": ["topic"], "writes": ["draft"]},
         "description": "주제로 초안 작성"}
SC = {"draft": {"type": "string"}, "topic": {"type": "string"}}

def run():
    tmp = tempfile.mkdtemp(); ok = 0
    try:
        p = CoworkModelProvider(queue_dir=tmp)
        ctx = {"topic": "테스트"}
        # 1) 응답 없음 → 요청 카드 생성 + mock 임시값 + PENDING
        d = p.call(STAGE, "mid", ctx, SC)
        reqs = os.listdir(os.path.join(tmp, "requests"))
        assert len(reqs) == 1 and "PENDING" in d and ctx.get("draft"), "케이스1 실패"
        ok += 1
        # 2) 응답 존재 → 실값 적용
        name = reqs[0]
        json.dump({"fields": {"draft": "진짜 초안"}},
                  open(os.path.join(tmp, "responses", name), "w", encoding="utf-8"), ensure_ascii=False)
        ctx2 = {"topic": "테스트"}
        d2 = p.call(STAGE, "mid", ctx2, SC)
        assert ctx2["draft"] == "진짜 초안" and "응답 적용" in d2, "케이스2 실패"
        ok += 1
        # 3) 불완전 응답 → 예외(정지)
        json.dump({"fields": {}}, open(os.path.join(tmp, "responses", name), "w", encoding="utf-8"))
        try:
            p.call(STAGE, "mid", {"topic": "테스트"}, SC); assert False, "케이스3: 예외 안 남"
        except RuntimeError:
            ok += 1
    finally:
        shutil.rmtree(tmp)
    print(f"=== cowork provider 테스트: {ok}/3 PASS ===")
    assert ok == 3

if __name__ == "__main__":
    run()
