# NEXT_ROADMAP.md — 다음 로드맵

## v0.2 — 실전 1회전 (최우선)

1. **실제 공고 1건 투입** — 앱 새 프로젝트로 입력 → 재작업 지시서 1순위 해소 → AI 정밀 검수 → 사람 LOCK
2. 실전에서 나온 오탐·누락으로 엔진 규칙 보정 (특히 어휘 겹침 기준, 위험 표현 오탐)
3. run_factory.py(CLI)와 engines.py 로직 통합 — CLI가 engines를 호출하도록

## v0.3 — AI adapter

4. `ai_adapter.py`: `generate(prompt)->str` 구현 (Anthropic API, 키는 환경변수) — 프롬프트 파일 재사용, 규칙 판정 옆에 AI 판정 병기
5. AI 채점 결과를 results.json에 병합 → 화면에서 "규칙 vs AI" 비교 표시
6. 비용 상한·호출 로그

## v0.4 — 본문 생산 라인 연결

7. PSST 본문 작성 워크플로우(grant_workflow 8~13단계)를 앱 탭으로: 작성전략 → 본문 구조 → 증빙 연결표 → 예산표 편집기
8. 발표자료(B라인)·발표연습기(C라인) 화면: 목차 생성, 불일치 감지, Q&A 리허설 체크

## v0.5 — UI 고도화 (필요해지면)

9. React/Vite 또는 Streamlit 전환 검토 — 엔진이 순수 함수라 교체 비용 낮음. 단, "의존성 0개로 어디서나 실행"의 가치와 교환인지 먼저 판단
10. 프로젝트 아카이브·비교(과거 공고 대비 무엇이 달라졌나)

## 부채 목록 (잊지 말 것)

- 위험 표현 스캐너 문맥 인식 (KNOWN_LIMITATIONS #5)
- input.md → input.json 변환기 (TODO_CLI #2)
- Windows 실행 검증 (TODO_CLI #7)
- E라인(라벨 PDF 실제 생성)·D라인(브랜드 말투) 미착수
