# ----------------------------------------------------------------------
# cowork_provider.py — B안(2026-07-12 혜미 확정): Cowork(Claude 세션)가
# model stage를 수행하는 프로바이더 스텁.
#
# 동작 (스텁 범위):
#   1) model stage 호출 시 요청 카드(JSON)를 cowork_queue/requests/에 남긴다.
#      카드 = stage id, tier, 입력(io.reads 값), 채워야 할 필드(io.writes), 지시 힌트.
#   2) cowork_queue/responses/에 같은 키의 응답 파일이 있으면 그 값을 적용한다.
#      (응답은 Cowork 세션/예약작업의 Claude가 카드를 읽고 작성 — 사람 손 없음)
#   3) 응답이 없으면 mock 값으로 임시 채우고 "PENDING" 표시 — 파이프라인 검증은
#      계속 돌고, 실값은 다음 실행에서 적용됨 (rerun_gate와 궁합).
#
# 실제 API 프로바이더(A안)가 필요해지면 ModelProvider를 상속한 별도 클래스로
# 추가하면 됨 — runner.py는 무수정 (Runner(model_provider=...)로 주입).
# ----------------------------------------------------------------------
import json, os, time, hashlib
from runner import MockModelProvider


class CoworkModelProvider(MockModelProvider):
    def __init__(self, queue_dir=None):
        base = queue_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "cowork_queue")
        self.req_dir = os.path.join(base, "requests")
        self.res_dir = os.path.join(base, "responses")
        os.makedirs(self.req_dir, exist_ok=True)
        os.makedirs(self.res_dir, exist_ok=True)

    def _key(self, stage, ctx):
        reads = (stage.get("io") or {}).get("reads") or []
        payload = {k: ctx.get(k) for k in reads}
        blob = json.dumps({"sid": stage["id"], "in": payload},
                          ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16], payload

    def call(self, stage, tier, ctx, shared_context):
        sid = stage["id"]
        h, payload = self._key(stage, ctx)
        name = f"{sid}-{h}.json"
        res_path = os.path.join(self.res_dir, name)
        writes = (stage.get("io") or {}).get("writes") or []

        if os.path.exists(res_path):
            with open(res_path, encoding="utf-8") as f:
                data = json.load(f)
            fields = data.get("fields") or {}
            missing = [w for w in writes if w not in fields]
            if missing:  # 불완전 응답은 계약 위반 — 적용하지 않고 정지 유도
                raise RuntimeError(f"cowork 응답 불완전: {name} 누락 필드 {missing}")
            for w in writes:
                ctx[w] = fields[w]
            return f"[CoworkModelProvider] tier={tier} — 응답 적용({name})"

        req_path = os.path.join(self.req_dir, name)
        if not os.path.exists(req_path):
            card = {"stage": sid, "tier": tier, "reads": payload, "writes": writes,
                    "instruction_hint": stage.get("description") or stage.get("name") or sid,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "howto": "Claude(Cowork): reads를 보고 writes 필드를 채운 "
                             "{'fields': {...}} JSON을 responses/에 같은 파일명으로 저장"}
            with open(req_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
        super().call(stage, tier, ctx, shared_context)  # mock 임시 채움
        return f"[CoworkModelProvider] tier={tier} — PENDING(요청 카드 {name}), mock 임시 채움"
