# APP_ARCHITECTURE.md — 앱 구조

## 기술 선택과 이유

**Python 표준 라이브러리 웹앱 (http.server)** — 이유:
1. 저장소에 Node 툴체인이 없고, 기존 공장(CLI·규칙 파싱)이 전부 Python 파일 기반
2. 의존성 0개 → 설치 실패 지점이 없고, `python3` 하나로 어디서든 실행
3. 데이터가 이미 저장소의 md/json 파일 — DB 서버·로그인·빌드 과정이 불필요
React/Vite·Streamlit은 NEXT_ROADMAP.md의 후속 후보로 남긴다 (엔진이 순수 함수라 UI 교체가 쉽다).

## 구성

```
08_factory_tools/
├── engines.py        규칙 기반 분석 엔진 8종 (순수 함수 — UI 없이 테스트 가능)
│   ├ notice_analyzer            공고 요약·원문 추출·배점 분석
│   ├ applicant_risk_checker     자격·체납·중복수혜 판정 (BLOCKED 게이트)
│   ├ idea_evaluator             6축 채점 → 추천/보류/탈락
│   ├ dangerous_expression_scanner  danger_words.md 파싱 대조 + 대체 제안
│   ├ budget_risk_checker        단순구매·외주·구독 플래그, 견적 필요 표시
│   ├ lock_engine                LOCK 가능 7조건 판정 (LOCKED는 절대 안 만듦)
│   ├ judge_review_engine        배점표 기반 예상 점수 + 제출 가능/보완/불가
│   ├ qna_generator / title_generator / summary_generator / revision_planner
│   └ analyze_all(data) → 통합 결과 dict
├── export_md.py      결과 dict → 파일 15종 (md 13 + results.json + HANDOFF)
├── app.py            웹 UI (http.server, 127.0.0.1:8787) — 화면 10종
├── create_project.py / run_factory.py   CLI 경로 (화면 없이 동일 폴더 규약)
├── test_engines.py   단위 테스트 29건
└── input_schema.json / output_schema.json / *_spec.md   실행 계약 문서
```

## 데이터 흐름

```
입력 폼/샘플 → 01_inputs/<p>/input.json  (저장소가 곧 DB)
    → engines.analyze_all()  (순수 함수, 부작용 없음)
    → export_md.export_all() → 04_outputs/<p>/ + 05_reviews/<p>/ + 10_handoff/
    → 화면은 04_outputs/<p>/results.json을 읽어 렌더링
```

승인(approvals)은 화면 체크박스 → input.json에 기록 → 재분석. 코드·AI가 대신 쓰지 않는다.

## AI adapter (후속 확장 자리)

엔진 결과는 규칙 판정이고, 정밀 판단은 ai_prompt(export의 next_step_prompt.md, CLI의 ai_prompt_*.md)로 분리돼 있다.
API 연동 시: `ai_adapter.generate(prompt: str) -> str` 함수 하나를 구현해 프롬프트 파일을 그대로 호출 본문으로 쓰면 된다. UI·엔진 수정 불필요.

## 보안·범위

- 서버는 127.0.0.1 바인딩 (외부 접속 불가), /file/ 경로는 저장소 밖 접근 차단
- 로그인·결제·외부 전송 없음. 모든 데이터는 로컬 파일

<!-- ok -->
