# TODO_CLI.md — CLI 미구현·후속 작업 목록

우선순위순. 각 항목은 10_handoff/GITHUB_ISSUES.md의 이슈와 대응.

## 1. AI API 연동 (후속 확장 — 지금 하지 않기로 한 것)

- ai_prompt_*.md 를 Anthropic API로 직접 호출하는 `--ai` 플래그
- 전제: API 키 관리 방식 결정(사람), 비용 상한 설정
- 현재 구조가 프롬프트 파일을 이미 만들므로 호출부만 추가하면 됨

## 2. input.md → input.json 변환기

- 텍스트 양식(01_inputs/input_form.md)으로 작성한 것을 JSON으로 변환
- v1에서는 AI 세션이 수동 변환. 규칙 기반 파서는 공고문 다양성 때문에 후순위

## 3. 위험 표현 스캐너 개선

- 현재: 단순 부분 문자열 매칭 → 오탐 가능 (예: 인용·방어 문맥도 검출)
- 개선: 예외 문맥 목록(스캔 리포트 자신, "금지" 언급 행 제외), 대체 표현 자동 제안 출력

## 4. 단계 산출물 검증 (validate 커맨드)

- `run_factory.py <p> --validate`: input.json을 input_schema.json으로 검증 (stdlib만으로 간이 검증기)
- 현재는 필수 키 4개만 확인

## 5. REVIEWED/LOCKED 상태 전환 커맨드

- `mark_reviewed.py <p> <stage>`: 사람이 검수 완료를 기록하는 안전한 경로
- LOCKED는 여전히 LOCK_STATUS.md 수동 기재 원칙 유지

## 6. 테스트 자동화

- 스모크 테스트(cli_test_log.md의 시나리오)를 pytest 없이 assert 스크립트로: `08_factory_tools/test_smoke.py`
- 시나리오: 생성→빈 입력 실행→PENDING_APPROVAL 확인→승인→전 단계 완주→BLOCKED 케이스

## 7. Windows 호환 확인

- 경로·인코딩(UTF-8) 확인 필요. 현재 pathlib + encoding="utf-8" 명시로 대비만 됨 [확인 필요]

## 완료된 것 (v0.1)

- [x] 프로젝트 스캐폴딩 (create_project.py)
- [x] 7단계 파이프라인 + 상태 관리 (run_factory.py)
- [x] BLOCKED / PENDING_APPROVAL 게이트
- [x] danger_words.md 자동 파싱 위험 표현 스캔
- [x] AI 프롬프트 생성 (ideas/lock/judge)
- [x] 자동 재작업 지시서·HANDOFF 생성 (정지 시에도)

<!-- ok -->
