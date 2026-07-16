# 혜미식 AI 작업 공장 (hyemi-ai-factory)

단발성 결과물이 아니라, 반복해서 결과물을 만들어내는 정부지원사업 전용 AI 작업 공장.

한 문장 정의: **공고와 심사표를 먼저 읽고, 아이디어 후보를 평가해 가장 점수 가능성이 높은 방향을 선정한 뒤, 본문·예산·증빙·발표·Q&A까지 심사위원이 납득할 수 있는 구조로 잠그는 공장.**

## 생산라인

| 라인 | 이름 | 워크플로우 |
|---|---|---|
| A | 정부지원사업 공장 | 02_workflows/grant_workflow.md |
| B | 발표자료 공장 | 02_workflows/presentation_workflow.md |
| C | 발표연습기 공장 | 02_workflows/qna_workflow.md |
| D | 콘텐츠 변환 공장 | 02_workflows/content_workflow.md |
| E | 업무자동화 아이템 설계 공장 | 02_workflows/automation_item_workflow.md |

라우팅: 02_workflows/factory_orchestrator_workflow.md

## 폴더 구조

```
hyemi-ai-factory/
├── FACTORY_DESIGN.md      전체 공장 설계서 (1차 공정 산출물)
├── README.md / CLAUDE.md / AGENTS.md / PLAN.md / DECISIONS.md / MEMORY.md / HANDOFF.md
├── 00_rules/       운영규칙 (위험표현, 채점기준, LOCK 규칙, 체크리스트)
├── 01_inputs/      입력자료 양식과 실제 입력
├── 02_workflows/   생산라인별 워크플로우
├── 03_templates/   산출물 템플릿
├── 04_outputs/     산출물 (프로젝트별 폴더)
├── 05_reviews/     심사위원 모드 검수 결과
├── 06_locks/       LOCK 기록
├── 07_samples/     샘플·테스트 데이터
├── 08_factory_tools/ 공장 도구 정의 (MVP 생성기 등)
├── 09_mvp_notice_lock/ 첫 MVP: 공고 분석·아이디어 LOCK 생성기
└── 10_handoff/     세션 인계문
```

## 앱 실행 (Hyemi Grant Factory)

```bash
python3 08_factory_tools/app.py   # → http://127.0.0.1:8787
```

공고문·신청자·아이디어를 화면에서 입력하면 분석 15종이 프로젝트별 파일로 생성된다.
자세히: LOCAL_RUN_GUIDE.md(실행) / APP_USAGE.md(사용법) / APP_ARCHITECTURE.md(구조) / KNOWN_LIMITATIONS.md(한계 필독) / TEST_REPORT.md(테스트 결과)

## 사용법 (AI 세션에서)

1. `CLAUDE.md`와 `HANDOFF.md`를 먼저 읽는다.
2. 새 공고 작업: `01_inputs/input_form.md`를 채워 `01_inputs/<프로젝트명>/`에 저장.
3. `09_mvp_notice_lock/README.md`의 실행 프롬프트로 MVP를 돌린다.
4. 산출물은 `04_outputs/<프로젝트명>/`, 검수는 `05_reviews/<프로젝트명>/`에 생성.
5. LOCK 통과 항목은 `06_locks/LOCK_STATUS.md`에 기록.

## 절대 원칙

- 특정 공고·업종·아이템에 고정하지 않는다. 매번 현재 공고 기준으로 다시 판단한다.
- 무조건 긍정 금지. 칭찬보다 감점 위험·누락·충돌·실행 불가능성을 먼저 말한다.
- 샘플·가정값은 반드시 `[확인 필요]` 태그를 단다.
- LOCK 이후 새 아이디어는 본문에 섞지 않고 확장 아이디어로 분리한다.

<!-- ok -->
