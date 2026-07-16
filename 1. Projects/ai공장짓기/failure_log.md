---
tags: [ai공장, 플랫폼, 지침]
created: 2026-07-12
---

# failure_log — 오류·발견사항 장부 (하위 모델 수리용)

> **목적**: 어떤 세션의 어떤 모델(Haiku/Sonnet/Opus)이라도 이 파일만 읽으면
> 이어서 고칠 수 있게, 오류를 카드 형식으로 남긴다. (혜미 지시 2026-07-12:
> "오류는 기록해서 Fable 5 하위 모델도 고칠 수 있게 기록해줘")

## 기록 규칙 (모든 세션 공통 — 새 오류가 나면 이 형식으로 아래에 추가)

```yaml
- id: err-YYYY-MM-DD-NN          # 날짜+순번
  status: open | fixed | workaround   # workaround = 우회만 됨, 근본수정 남음
  symptom: ""                     # 무엇이 어떻게 잘못됐나 (에러 메시지 그대로)
  cause: ""                       # 원인 (모르면 "미상"이라고 쓰기 — 추측 금지)
  reproduce: ""                   # 재현 방법 (명령어 그대로)
  fix: ""                         # 해결/우회 방법 (한 일 그대로)
  remaining: ""                   # 남은 근본수정 (없으면 "없음")
  fixable_by: haiku | sonnet | opus   # 남은 수정을 맡길 수 있는 최소 티어
  files: []                       # 관련 파일 경로
```
- 고친 뒤에는 카드를 지우지 말고 status만 fixed로 바꾼다 (히스토리 보존 원칙).
- 에러 메시지는 요약하지 말고 **그대로 복사**한다 (하위 모델이 검색으로 찾게).

---

## 카드 목록

```yaml
- id: err-2026-07-12-01
  status: workaround
  symptom: "runner_mod.RunnerError: [경계검증 실패] stage '방문알림봇': 'visit_notice' 타입 불일치: 선언=object, 실제=str (자동수정 금지 — 공장 쪽 수정 필요)"
  cause: "방역 manifest.yaml은 visit_notice를 type: object로 선언했는데, 방역 run.py의 mock(run_방문알림봇)은 문자열을 씀. 기존 방역 전용 실행기는 경계검증이 없어 그동안 못 잡았고, 범용 러너의 경계검증(2026-07-12 신규)이 처음 잡아냄 — 러너가 정상 작동한다는 증거이기도 함"
  reproduce: "python3 ai공장짓기/runner/test/test_pest_on_runner.py (어댑터의 계약보정 래퍼를 제거하면 재현)"
  fix: "ai공장짓기/runner/adapters/pest_adapter.py에서 run_방문알림봇 출력을 manifest 계약(object)대로 감싸는 래퍼 추가 — 방역 폴더는 수정 안 함(원칙)"
  remaining: "방역 폴더 다음 작업 때 근본 통일: 방역 run.py의 run_방문알림봇이 object를 쓰게 고치거나(권장), manifest 선언을 string으로 바꾸거나 둘 중 하나. 통일 후 어댑터 래퍼 제거"
  fixable_by: sonnet
  files: ["1. Projects/클로드 방역 ai/manifest.yaml", "1. Projects/클로드 방역 ai/scripts/run.py", "ai공장짓기/runner/adapters/pest_adapter.py"]

- id: err-2026-07-12-02
  status: fixed
  symptom: "반려 루프가 max_loops 소진(ESCALATED)돼도 파이프라인이 후속 stage(발송 등)로 계속 진행함 — 미승인 상태로 다음 단계 가는 위험"
  cause: "runner.py _run_sequence가 STOP만 중단 사유로 인식하고 ESCALATED를 무시했음 (러너 최초 작성 시 누락)"
  reproduce: "자체 테스트 T4 (python3 ai공장짓기/runner/test/test_runner_selftest.py)"
  fix: "_run_sequence에서 result in ('STOP', 'ESCALATED')이면 시퀀스 중단하게 수정. T4·P5·C5 테스트로 검증(발송/게시 stage 미실행 확인)"
  remaining: "없음"
  fixable_by: sonnet
  files: ["ai공장짓기/runner/runner.py"]

- id: err-2026-07-12-03
  status: fixed
  symptom: "runner.py boundary_check 안에 아무 일도 안 하는 죽은 코드 블록(bool/number 예외처리 하려다 만 if문) 존재"
  cause: "최초 작성 시 bool이 int의 서브클래스인 경우 처리를 고민하다 정리 안 하고 남김"
  reproduce: "(코드 리뷰로만 발견 — 동작 오류는 없었음)"
  fix: "해당 블록 제거, 단순 타입 불일치 → 에러 규칙로 정리"
  remaining: "없음"
  fixable_by: haiku
  files: ["ai공장짓기/runner/runner.py"]

- id: obs-2026-07-12-04   # 오류 아닌 관찰(observation) — 수정 여부는 혜미 판단
  status: open
  symptom: "방역 manifest 정적검증 WARN 11건: (1) model stage 6개의 tier가 'sonnet'/'haiku' 등 모델명 — 플랫폼 규범(설계노트 1-2)은 티어명(low_cost/mid/high)만 허용, Fable 금지. 러너는 하위호환으로 해석해주지만 표기 통일 권장 (2) 방문알림봇·문서생성봇·리마인더봇의 교차 경로 읽기 5건 — entry_points/run_if 경로라 실제 문제 아님, 참고용"
  cause: "방역 manifest가 공통 스펙 확정(2026-07-08)보다 먼저(2026-07-07) 작성됨"
  reproduce: "python3 ai공장짓기/runner/runner.py '1. Projects/클로드 방역 ai/manifest.yaml' --validate-only"
  fix: "(아직 안 함 — 방역 폴더 수정 금지 원칙, 설계노트 8번 순서상 '방역: 공통규칙만 반영' 단계에서 tier 표기만 티어명으로 일괄 치환하면 됨)"
  remaining: "방역 manifest tier 6곳 표기 치환 (sonnet→mid, haiku→low_cost). 구조 변경 아님"
  fixable_by: haiku
  files: ["1. Projects/클로드 방역 ai/manifest.yaml"]
```

## 이번 세션에서 오류가 **안 난** 것 (예방책이 작동한 기록)
- **파일 잘림(truncation) 버그 0건** — 이번 세션은 처음부터 모든 코드/문서를
  bash heredoc으로 직접 쓰고(Write/Edit 도구 미사용) 쓸 때마다 py_compile /
  yaml.safe_load로 검증하는 규칙을 지킴. 이 방식이 유효하다는 실증.
  (근거: 루트 CLAUDE.md Gotchas, HANDOFF.md의 반복 재현 기록)

## 관련 문서
- [[ai공장짓기/HANDOFF|HANDOFF]]
- [[ai공장짓기/runner/README|범용 러너 사용법]]
- [[2. Areas/Claude 세션로그/2026-07-12|2026-07-12]]
- [[1. Projects/클로드 방역 ai/실행방법|실행방법]]
- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log_skill-factory-architecture]]

<!-- ok -->
