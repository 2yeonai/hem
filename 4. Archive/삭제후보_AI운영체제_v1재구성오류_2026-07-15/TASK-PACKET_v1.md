---
type: schema-template
tags: [ai공장, ai운영체제, 지침]
created: 2026-07-15
---
# TASK-PACKET v1 — 작업 패킷 양식

> ⚠️ 재구성 안내: 이 파일은 2026-07-15 세션에서 만들어졌으나 볼트에 저장되지 못하고 유실된 원본을 대체하는 **v1 재구성본**이다. 원본의 정확한 필드명·문구와 다를 수 있다. 실제로 써보면서 다듬을 것.

## 이게 뭔가
[[ai공장짓기/AI운영체제_설계서|AI운영체제_설계서]]가 정의하는 "일" 단위 하나. PRD 1개가 여러 TASK-PACKET으로 쪼개지거나(1 PRD → n PACKET), 단발성 업무는 PRD 없이 패킷 하나만 만들어 바로 시작한다.

## 저장 위치
`ops/tasks/<날짜>_<짧은식별자>/packet.md`

## 양식

```markdown
---
packet_id: <날짜>_<짧은식별자>   # 예: 2026-07-15_ai운영체제-v1재구성
prd_ref: <연결된 PRD 파일 경로 또는 "단발(PRD 없음)">
status: 대기 | 진행중 | 완료 | 보류
model_tier: haiku | sonnet | fable
created: <날짜>
---

## 목표 (한 문장)
무엇을 만들면 끝인지 한 줄로.

## 배경
왜 이 작업이 필요한가 — 관련 세션로그/decision-log 링크.

## 범위
- 포함:
- 제외:

## 완료 조건 (Definition of Done)
- [ ] 조건 1
- [ ] 조건 2

## model_tier 선택 근거
[[ai공장짓기/routing-policy|routing-policy]] 기준 어디에 해당하는지 한 줄.

## 관련 문서
```

## 규칙
- `model_tier: fable`을 쓰려면 [[ai공장짓기/routing-policy|routing-policy]]의 승인 절차(먼저 물어보고 승인받기)를 거친 뒤에만 값을 채운다.
- 패킷은 실행 중 내용이 바뀌면 직접 덮어쓰지 말고 "변경" 섹션을 추가해 이력을 남긴다(승인블록의 version_history 관례와 동일한 발상).
- 완료되면 같은 폴더에 `result-card.md`([[ai공장짓기/RESULT-CARD_v1|RESULT-CARD_v1]] 양식)를 만들어 짝을 맞춘다.

## 관련 문서
- [[ai공장짓기/AI운영체제_설계서|AI운영체제_설계서]]
- [[ai공장짓기/RESULT-CARD_v1|RESULT-CARD_v1]]
- [[ai공장짓기/routing-policy|routing-policy]]
- [[ops/tasks/README|ops/tasks 폴더 규약]]

<!-- ok -->
