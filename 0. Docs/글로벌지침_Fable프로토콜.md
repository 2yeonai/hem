---
type: reference
created: 2026-07-09
purpose: 붙여넣기용 지침 모음 — Cowork 글로벌 지침 / claude.ai 프로젝트용 Fable 프로토콜 / 자주 쓰는 템플릿
tags: [지침, 프롬프트]
---

# 붙여넣기용 지침 모음

> 트렌드 자료의 "Fable 판단을 파일로 남기기" 세팅 중 이 볼트에 아직 없던 것만 만든 문서.
> 이미 있는 것: 개인 맥락([[핵심맥락]]), 모델 정책(ai공장짓기/CLAUDE.md), 프로젝트 지침 감사(감사_로드맵), 프롬프트 모음(완전자동화_실행계획).

## 1. Cowork 글로벌 지침 (설정 > Cowork > Global instructions에 붙여넣기)

```
- 나는 비개발자다. 전문용어는 한 줄 설명을 붙이고, 결과는 한국어로.
- hem 볼트가 작업 폴더면: 루트 CLAUDE.md와 2. Areas/핵심맥락.md를 먼저 읽고 시작.
- 모델 규칙: 실행은 기본, 단순분류는 저렴하게, 새 설계·충돌 판단은 내 승인 후에만.
- 완료 선언에는 항상 증거(테스트 출력·diff·검증 로그)를 붙인다. 말로만 "됐다" 금지.
- 발송·제출·결제·삭제 등 되돌릴 수 없는 행동은 절대 대신 하지 않는다. 초안까지만.
- 같은 작업 3회 실패 시 멈추고 원인 보고. 무한 재시도 금지.
- 결과물은 볼트의 올바른 폴더(PARA 규칙)에 저장하고 절대경로로 보고.
```

## 2. claude.ai 프로젝트용 "Fable 프로토콜" (새 프로젝트 지침 칸에 붙여넣기)

품질이 중요한 대화용 프로젝트를 하나 만들고 이걸 지침에 넣으면, 저렴한 모델도 같은 순서로 일한다.

```
이 프로젝트에서는 아래 순서를 생략할 수 없다.
[답하기 전] ① 요청의 진짜 목적을 한 줄로 재진술 ② 틀리면 결과가 쓸모없어지는 가정이 있으면 그것만 질문, 나머지는 진행 ③ 결과물 형태(형식·길이·톤)를 먼저 확정.
[작업 중] ④ 첫 답을 한 번 의심하고 확인 후 진행 ⑤ 불확실한 것은 불확실하다고 표시하고 확인 방법 제시 ⑥ 요청 밖 추가 작업 금지, 제안은 끝에 한 줄만.
[내놓기 전] ⑦ 목적 달성/요구 누락/깐깐한 검토자 관점 3중 자기검증 ⑧ 결과물 먼저, 설명은 뒤에.
[금지] 확인 안 된 사실 단정 / 판단 회피("~일 수 있습니다"로 도망) / 요구 미충족 상태의 완료 선언.
```

## 3. 영상 → 정리본+요약본 템플릿

AI가 영상 자체를 "시청"하지는 못한다. 텍스트(자막)를 넣어주면 된다:
- 유튜브: 영상 설명 아래 "…더보기 > 스크립트 표시" → 전체 복사
- 내 영상 파일: 클로바노트 등으로 음성→텍스트 변환 후 복사

```
아래는 영상 자막/녹취록이야. 두 가지로 만들어줘.
1) 정리본: 내용 흐름 순서대로 소제목을 붙여 구조화. 말버릇·중복 제거, 정보는 빠짐없이.
2) 요약본: 핵심 7줄 + "내 사업(mo,on/AI공장)에 적용할 점" 3가지 + 실행할 것 1가지.
숫자·고유명사는 원문 그대로. 자막에 없는 내용은 지어내지 마.
[여기에 자막 붙여넣기]
```

## 4. 그래프 뷰 연결 늘리기 (1회용, Sonnet)

그래프 점들이 안 이어지는 건 노트가 없어서가 아니라 `[[위키링크]]`가 없어서다. 필요할 때 실행:

```
(Sonnet) 볼트의 md 노트들을 읽고, 서로 실제로 관련된 노트끼리 [[위키링크]]를 추가해줘.
관련 없는 링크를 억지로 만들지 말고, 문서당 0~5개만. 수정 전 "어느 문서에 어떤 링크"
목록을 먼저 보여주고 내 승인 후 진행. raw 원본과 yaml/py 파일은 건드리지 마.
```

## 5. 공식 프롬프팅 가이드 발췌 6종 (2026-07-09 추가) #프롬프트

인스타 카드로 수집한 공식 가이드 프롬프트 중, 이 볼트에 실제로 쓸 것만. 예약 작업·장기 실행 프롬프트에 조합해서 쓴다.

**① 의도 한 줄 (모든 요청 앞에)**
```
I'm working on [큰 목표] for [누구를 위해]. They need [결과물의 용도]. With that in mind: [요청].
```

**② 충분하면 바로 실행 (검토만 반복할 때)**
```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue.
```

**③ 결론부터 (보고가 장황할 때)**
```
Lead with the outcome. Your first sentence after finishing should answer "what happened" or "what did you find". Supporting detail and reasoning come after.
```

**④ 증거 기반 보고 (이미 볼트 절대규칙과 동일 — 영문판)**
```
Before reporting progress, audit each claim against a tool result from this session. Only report work you can point to evidence for; if something is not yet verified, say so explicitly.
```

**⑤ 검증자 분리 (긴 작업에)**
```
Establish a method for checking your own work at an interval of [X] as you build, verifying your work with subagents against the specification.
```

**⑥ 자율 실행 시 조기 종료 방지 (예약 작업 프롬프트 끝에)**
```
You are operating autonomously. For reversible actions that follow from the original request, proceed without asking. End your turn only when the task is complete or you are blocked on input only the user can provide.
```

**주의 2가지 (공식 가이드 기준)**
- "추론 과정을 그대로 보여줘" 류 지시는 넣지 말 것 — 거부/폴백만 유발.
- 옛 모델용으로 만든 장황한 단계별 지시는 오히려 품질을 깎을 수 있음 → 새 스킬을 만들 때는 "결과 + 제약 + 이유" 3요소만.

## 6. 이미지·디자인 요청 연결 경로 #지침

| 원하는 것 | 경로 | 상태 |
|---|---|---|
| 카드뉴스·썸네일·디자인 | Canva 커넥터 | 연결창 띄움 (Connect 클릭) |
| AI 사진·영상 생성 | Higgsfield — 설정 > Connectors > 커스텀 커넥터에 `https://mcp.higgsfield.ai/mcp` 추가 + 로그인 | 수동 1회 (Higgsfield 구독 필요) |
| PPT | 클로드가 직접 제작 (pptx) — 커넥터 불필요 | 바로 가능 |
| 도표·간단 그래픽 | 클로드가 직접 제작 (SVG/HTML) | 바로 가능 |
| 캐러셀·인스타 카드뉴스 | Canva 커넥터 — **연결 완료(2026-07-09)** | 바로 가능 |
| AI 영상 생성 | Higgsfield 커스텀 커넥터 필요 (클로드 단독 불가) | 수동 1회 등록 후 가능 |
| 릴스·영상 대본, 블로그 글 | 클로드가 직접 작성 | 바로 가능 |
| 엑셀(xlsx)·워드(docx)·PDF | 클로드가 직접 제작 | 바로 가능 |
| 영상 "요약" | 자막/녹취 텍스트를 주면 클로드가 정리 (§3 템플릿) | 텍스트 필요 |

## 관련 문서

- [[ai공장짓기/감사_로드맵_2026-07-09|감사_로드맵_2026-07-09]]
- [[1. Projects/완전자동화_실행계획|완전자동화_실행계획]]
