---
type: policy
tags: [ai공장, ai운영체제, 지침]
created: 2026-07-15
---
# routing-policy.md — 모델 티어 라우팅 정책

> ⚠️ 재구성 안내: 2026-07-15 세션 원본 유실로 인한 v1 재구성본. 정책 자체의 내용(아래 표)은 이미 볼트에 확정돼 있던 [[ai공장짓기/CLAUDE.md|ai공장짓기/CLAUDE.md 모델 사용 기준]]을 그대로 옮겨온 것이라 신뢰도가 높음 — 재구성 리스크가 있는 부분은 "TASK-PACKET 연동" 절뿐.

## 기준 (원본: ai공장짓기/CLAUDE.md)
| 티어 | 언제 쓰나 | 승인 필요? |
|---|---|---|
| Haiku | 단순 분류/태깅(이름 뽑기, 같은 것끼리 묶기) | 불필요 |
| Sonnet (기본값) | Cowork 작업 전반 — 이 표에 없는 모든 것 | 불필요 |
| Fable (고비용) | 설계를 새로 정해야 할 때 / 서로 다른 정보가 충돌할 때 | **필수 — "Fable 써야 할 것 같은데 진행할까요?" 먼저 물어보고 승인 후에만** |

## TASK-PACKET 연동
- 모든 [[ai공장짓기/TASK-PACKET_v1|TASK-PACKET]]은 `model_tier` 필드에 위 셋 중 하나를 적는다.
- `model_tier: fable`을 적으려는 시점에 아직 혜미 승인을 못 받았다면, 패킷을 `보류` 상태로 두고 승인 질문부터 던진다 — 패킷을 먼저 만들고 나중에 승인받는 순서 금지(거꾸로 하면 "이미 결정된 것처럼" 보여서 승인의 의미가 없어짐).
- 승인받은 뒤에는 decision-log에 어떤 패킷이 Fable을 썼는지, 왜 그랬는지(`why_fable`) 한 줄 남긴다 — 기존 decision-log의 각 항목이 이미 이 형식(배경/확정된 구조/why_fable/아직 반영 안 된 것/다음 액션)을 쓰고 있으므로 그대로 따른다.

## 이 정책이 대체하지 않는 것
공장별(꽃집/방역/정부지원/콘텐츠 등) manifest.yaml 안의 `kind: model`+`tier` 필드는 별개 — 그건 "파이프라인 stage 하나가 어떤 비용의 모델을 쓰는가"이고, 이 문서는 "Claude 세션 자체가 지금 어떤 티어로 일하고 있는가"를 다룬다. 둘이 이름은 비슷하지만 레이어가 다르다.

## 관련 문서
- [[ai공장짓기/CLAUDE.md|모델 사용 기준(원본)]]
- [[ai공장짓기/AI운영체제_설계서|AI운영체제_설계서]]
- [[ai공장짓기/TASK-PACKET_v1|TASK-PACKET_v1]]
- [[ai공장짓기/decision-log_skill-factory-architecture|decision-log]]

<!-- ok -->
