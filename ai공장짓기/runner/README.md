---
tags: [ai공장, 플랫폼, 지침]
created: 2026-07-12
---

# 범용 러너 (universal runner) — 사용법

> ④ AI회사 플랫폼의 실행 엔진. 어떤 공장이든 manifest.yaml + 핸들러만 주면
> 같은 방식으로 실행한다. 설계 근거: [[ai공장짓기/설계노트/1_플랫폼_공통_스펙_(모든_공장이_따르는_것)|설계노트 1-4·1-5]] (2026-07-08 Fable 확정), 구현: 2026-07-12.

## 1부 — 대표님용 (쉬운 설명)

- **이게 뭔가요?** 지금까지는 공장(방역 등)마다 실행 프로그램을 따로 만들었는데,
  이제 **실행기 하나**가 모든 공장의 설계도(manifest.yaml)를 읽어 대신 돌립니다.
  새 공장을 만들 때 실행기를 또 만들 필요가 없어졌습니다.
- **뭘 지켜주나요?**
  - 설계도가 틀렸으면(없는 단계 참조, 순환 등) **실행 전에** 거부합니다.
  - 각 단계가 약속한 결과물을 안 내놓으면 **그 자리에서 멈춥니다**(몰래 고치지 않음).
  - 승인 안 난 문서/글은 발송·게시 단계가 **한 번 더 확인해서 차단**합니다.
  - 반려하면 사유에 따라 알맞은 단계로 되돌아가 다시 만듭니다(최대 3회, 넘으면 사람 호출).
  - 같은 입력을 두 번 주면 두 번째는 건너뜁니다(비용 절약 — 재실행 게이트).
  - Fable(최고비용 모델)을 공장 단계에 배정하는 것 자체를 금지합니다.
- **아직 안 되는 것**: 실제 AI 호출(전부 목업), 상주형(챗봇 운영모드) 공장, 실제 검수 큐.

## 2부 — 다음 세션/개발용

### 실행 명령 (볼트 루트 기준)
```bash
# 검증만
python3 ai공장짓기/runner/runner.py <manifest.yaml> --validate-only

# 실행 (방역 예시)
python3 ai공장짓기/runner/runner.py "1. Projects/클로드 방역 ai/manifest.yaml" \
  --handlers ai공장짓기/runner/adapters/pest_adapter.py \
  --input "1. Projects/클로드 방역 ai/test/temp_mock_input_임시.json" --trigger event

# 테스트 3종 (전부 PASS 상태 유지할 것)
python3 ai공장짓기/runner/test/test_runner_selftest.py      # 러너 자체 14건
python3 ai공장짓기/runner/test/test_pest_on_runner.py       # 방역 연결 10건
python3 "1. Projects/클로드 콘텐츠 ai/test/test_content_on_runner.py"   # 콘텐츠 공장 9건
```

### 파일 구성
| 파일 | 역할 |
|---|---|
| runner.py | 러너 본체 (정적검증/실행/경계검증/재시도/반려루프/재실행게이트/로그) |
| adapters/pest_adapter.py | 방역 연결 어댑터 — 방역 run.py의 mock을 재사용 (방역 폴더 무수정) |
| test/demo_manifest.yaml, demo_handlers.py | 자체 테스트용 데모 공장 |
| logs/ | 실행 로그(JSON, stage별 입력해시/소요시간/성공실패) |
| state/ | 재실행게이트 해시 저장소 |

### 핸들러 계약 (새 공장 연결 시 이것만 구현)
- `STAGE_FUNCS: {stage_id: fn(ctx, stage) -> str}` — 필수(단, model stage는 없으면 MockModelProvider가 대체)
- `evaluate_run_if(condition, ctx)` / `pending_rejections(ctx, stage_id)` / `should_stop(ctx, stage)` / `batch_items(ctx, entry_stage)` — 전부 선택

### MVP에서 뺀 것 (설계노트 1-5 그대로 — 인터페이스 자리만 있음)
반려루프 실제 집행 큐 / human 검수 SLA 시스템 / resident 골격 / 검수원등급(review) 실제 집행 / 실제 LLM API 호출(ModelProvider 서브클래스 자리만)

### 오류가 나면
[[ai공장짓기/failure_log|failure_log.md]]의 카드 형식으로 기록할 것. 히스토리 삭제 금지.

## 관련 문서

- [[2. Areas/핵심맥락|핵심맥락]]
- [[2. Areas/Claude 세션로그/2026-07-12|2026-07-12]]
- [[1. Projects/클로드 콘텐츠 ai/SKILL|SKILL]]
- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log_skill-factory-architecture]]
- [[클로드 ai 자동화/ai-platform/ai 공장 종합 기획|ai 공장 종합 기획]]

<!-- ok -->
