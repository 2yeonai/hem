# 정부지원사업 AI Factory — 미래 비전 (Future Vision)

> **주의**: 이 문서는 지금 당장 구현 대상이 아닙니다.
> 셀프 사용 단계를 넘어 실제로 여러 사용자에게 배포/판매하는 SaaS 단계로
> 갈 때 참고할 로드맵입니다. 회사 헌장(company_charter.md)의 "성장 경로"
> 섹션에서 SaaS 전환을 검토하는 시점에 이 문서를 다시 꺼내 보세요.
>
> 지금 스킬(gov-support-app-skill)에 이 문서의 인프라(크롤러, OCR 벤더,
> PostgreSQL/OpenSearch/Airflow, 다계정 RBAC 등)를 넣지 마세요 — 헌장에서
> "당장 판매 없음, 나 혼자 사용"으로 확정한 것과 정면으로 충돌합니다.
> 대신 이 문서의 **알고리즘/판단 로직**(8-심사위원, 감점 전파, LOCK 상태
> 머신, PSST 일관성 검사, 위험표현 사전)만 골라서 지금 스킬에 반영합니다.
> 어떤 부분을 지금 반영하는지는 `docs/personal-use-scope.md` 참고.

---

## Executive summary

이 대화들에서 일관되게 드러난 당신의 목표는 **"입력폼 앱"이 아니라 "정부지원사업 심사관+작성자+발표코치 역할을 수행하는 AI Factory"**를 만드는 것이다. 핵심은 사용자가 공고 내용을 다시 입력하지 않게 하고, **공고를 AI가 매일 수집·분석한 뒤 사업자 DB와 자동 매칭하고, 아이디어를 심사위원 시점으로 공격·정제하여, 사업신청서 초안부터 발표·Q&A까지 한 흐름으로 자동 생성**하는 데 있다. 이 제품은 단순 요약기가 아니라, 자격·중복수혜·지원제외 업종·배점 전략·증빙 부족·감점 전파를 판단하는 **규칙 엔진 + LLM 협업 시스템**이어야 한다. K-Startup, 기업마당, 소상공인24는 실제로 정부·공공 지원사업 공고와 신청 절차의 핵심 포털이며, 공고는 PDF/HWP/HWPX 첨부를 동반하는 경우가 많아 문서 파싱 체계가 제품의 중심이 되어야 한다.

권고 결론은 분명하다. **MVP는 "공고 PDF·신청서 양식·사업자증 3파일 업로드 → 자동분석 → LOCK DRAFT → 재작업 지시 → 신청서 초안/발표자료/Q&A 생성"**이어야 하고, 그 위에 **일일 공고 크롤러, 사업자 매칭, 규칙 업데이트, 강의/노하우 반영, 감사 로그, 운영 승인 단계**를 올려야 한다.

## 대화에서 드러난 제품 정의

**"AI가 매일 정부지원사업 공고를 수집하고, 내 사업자와 맞는 공고를 골라주며, 공고를 읽는 순간부터 0단계 자격 검토, 아이디어 선택, PSST 설계, 8명 심사위원 검수, 감점 전파, 예산·증빙 점검, 재작업 지시, 사업신청서 초안, 발표자료, 발표 Q&A, HANDOFF 문서까지 자동으로 생산하는 시스템."**

세 가지를 동시에 해야 한다: 문서 분석기, 심사모사 엔진, 작성 자동화기.

## 기능 범위와 사용자 흐름

| 기능 | 우선순위 | 핵심 산출물 | 책임자 |
|---|---|---|---|
| 일일 공고 수집 크롤러 | 최상 | notice_raw, notice_files, 수집 로그 | 개발 |
| PDF/HWP/HWPX 파싱·OCR | 최상 | notice_parsed, table blocks, key fields | 개발 + AI |
| 심사표·지원제외·자격 자동추출 | 최상 | notice_summary, eligibility_rules, score_schema | AI |
| 사업자 DB 매칭 | 최상 | applicant_fit_score, mismatch reasons | 개발 + AI |
| 아이디어 후보 자동평가 | 최상 | idea_ranking, 탈락사유, 추천안 | AI |
| PSST 생성·일관성 검사 | 최상 | psst_outline, missing links, 수정안 | AI |
| 8-심사위원 모드 | 상 | judge_reviews_8, attack questions | AI |
| 감점 전파 엔진 | 상 | deduction graph, total_risk_score | AI |
| 재작업 지시서 자동생성 | 상 | revision_order.md | AI |
| LOCK 규칙 엔진 | 최상 | LOCK_DRAFT / LOCKED / BLOCKED | 개발 + AI |
| 발표 스크립트·Q&A 생성 | 상 | pitch_script, QNA_bank | AI |
| Export / HANDOFF | 최상 | analysis bundle, API payload, docs zip | 개발 |
| 규칙/프롬프트 버전관리 | 상 | rule registry, prompt changelog | 개발 + 운영 |
| 감사 로그·사람 승인 | 최상 | approval logs, audit trail | 개발 + 운영 |

## 기술 아키텍처와 데이터 요건 (SaaS 단계용 — 지금 불필요)

- 문서 인식: CLOVA OCR / Azure Document Intelligence / Upstage Document Parse
- HWP/HWPX 파싱: Apache Tika (HWP), XML 직독 (HWPX)
- 저장: PostgreSQL + 객체저장소 + OpenSearch(벡터 검색)
- 오케스트레이션: Airflow(배치 수집) + Temporal(트랜잭션)
- 한국어 NLP: Kiwi/KoNLPy + Sentence Transformers
- 관측성: OpenTelemetry, Prometheus, Langfuse, MLflow

## 알고리즘과 규칙 엔진 설계 (★ 지금 스킬에 반영할 핵심 자산)

### 배점전략 추출 규칙
```text
if 최고배점 == 실행계획/실현가능성:
    문장 비중 = 높음
    요구 산출물 = 월별 일정, 단계별 결과물, 검증지표
    발표공격 = "기간 내 가능?" "대표가 직접 운영 가능?"
if 최고배점 == 사업 필요성:
    요구 산출물 = 문제 실측치, 비용/시간/오류 근거
if 최고배점 == 예산 적정성:
    요구 산출물 = 항목별 견적, 산출물 연결표, 용도-성과 체인
```

### 아이디어 매칭 점수식
```text
총점 =
  공고적합성 0.20 + 문제명확성 0.15 + 실행가능성 0.20 +
  증빙가능성 0.15 + 예산적합성 0.10 + AI필요성 0.10 + 발표방어력 0.10
  - 탈락급감점 - 감점전파
```

### 감점 전파 규칙 (예시)
```text
견적서 없음: 예산적합성 -5, 실행가능성 -3, 발표방어력 -2
실측치 없음: 문제명확성 -4, 성과예측 신뢰 -3, PSST 일관성 -2
AI 필요성 약함: 공고적합성 -3, 기술설득력 -4, 발표방어력 -2
```

### PSST 일관성 검사
```text
Problem 없음 -> LOCK 금지
Problem은 있으나 실측 없음 -> DRAFT + 증빙 요청
Solution이 Problem과 1:1 매핑 안 됨 -> 재작업
Scale-up 목표 있으나 채널/고객/매출근거 없음 -> 재작업
Team 역량이 과업과 무관 -> 발표리스크 경고
```

### 위험표현 사전
| 위험 표현 | 이유 | 대체 권고 |
|---|---|---|
| 완벽히 해결 | 과장·보증성 | 위험을 줄임 / 오류를 완화함 |
| 100% 자동화 | 실무 불신 | 반자동화 / 검수 기반 자동화 |
| 자동 발송 | 책임·개인정보 리스크 | 발송 대기열 생성 |
| AI가 판단 | 통제권 불분명 | 대표자 검수 후 추천 |
| 전국 확장 | 과대 확장 | 협약기간 내 시범운영 |
| 외주 개발 | 주체성 약화 | 기능 구축 및 현장 실증 |
| 장비 구매 | 구매성 예산 위험 | 실증용 장비 활용 또는 렌탈 |

### LOCK 조건 트리
```text
LOCK 가능 =
  공고 파싱 완료
  AND 자격 3종 확인(사업자상태/체납/중복수혜)
  AND 최종 아이디어 확정
  AND PSST 필수 슬롯 충족
  AND 위험표현 치명건수 = 0
  AND 예산 견적 근거 확보
  AND 필수 증빙 매핑 완료
  AND 사람 승인 기록 존재
```
상태: `BLOCKED`, `DRAFT`, `READY_FOR_APPROVAL`, `LOCKED`

## 자동 작성 산출물 목록 (★ 지금 스킬에 반영할 핵심 자산)

| 산출물 파일 | 내용 |
|---|---|
| notice_summary.md | 공고 핵심 요약, 자격·제외·서류·일정 |
| scoring_strategy.md | 배점전략, 분량 전략, 증빙 집중 포인트 |
| applicant_risk_check.md | 사업자·체납·업종·중복수혜 리스크 |
| idea_comparison_table.md | 아이디어 후보 평가 및 추천 |
| psst_analysis.md | PSST 구조, 누락 링크, 보완안 |
| judge_review_8.md | 8-심사위원 리뷰와 공격 질문 |
| deduction_map.md | 감점 전파 그래프 |
| revision_order.md | 재작업 지시서 |
| budget_review.md | 견적, 산출물 연결, 구매성 위험 검토 |
| application_draft.md | 사업신청서 초안 |
| pitch_script.md | 발표 스크립트 |
| presentation_attack_qna.md | 공격 질문·모범 답안 |
| lock_report.md | LOCK 상태와 차단 사유 |
| handoff_bundle.json | 상태·버전 정보 묶음 (SaaS 단계에선 API 페이로드, 지금은 로컬 JSON) |

## 운영·보안 로드맵 (SaaS 단계용 — 지금 불필요)

- Rule Registry / Prompt Registry / Review Dataset / Approval Log
- 개인정보 파기정책(90~180일), RBAC, 첨부문서 암호화, 다운로드 워터마크, 감사 로그
- 단계별 로드맵: MVP(1~3개월) → 6개월(크롤러, 사업자매칭, 8-심사위원) → 12개월(발표슬라이드 자동생성, 다계정)
- 예상 인력/예산: MVP만 해도 PM 1, 풀스택 1~2, AI엔지니어 1, 0.8억~1.8억 원

## 리스크와 대응 (SaaS 단계에서 재검토)

| 리스크 | 설명 | 대응 |
|---|---|---|
| OCR 오류 | 스캔 공고, 표 깨짐 | confidence score, human review, 레이아웃 파서 병행 |
| 공고 비표준성 | 공고마다 양식 다름 | source별 parser profile |
| HWP/HWPX 다양성 | 변형 서식 | 전용 파서 + PDF 변환 fallback |
| 법적 제한 | 개인정보·민감정보 | 목적 제한, 최소수집, 파기정책 |
| 과대평가 위험 | AI가 "합격 가능" 과신 | LOCK/추천을 "근거 기반 DRAFT"로 표기 |
| 모델 드리프트 | 정책 변화 | 규칙 버전관리, 월간 회귀테스트 |

---
*원본: 2026-07-06 작성된 요구정의 보고서 전문 보관. SaaS 전환 검토 시 재열람.*

## 관련 문서

- [[클로드 ai 자동화/company_charter|company_charter]]
- [[클로드 정부지원사업 ai/HANDOFF|HANDOFF (정부지원사업)]]
- [[클로드 정부지원사업 ai/gov-support-skill/정부지원사업_판정로직_확장스펙|정부지원사업_판정로직_확장스펙]]
