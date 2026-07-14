---
type: doc
status: approved
tags: [policy, zettelkasten, inbox]
---

# 5. Zettelkasten/00. Inbox 운영 지침 (CLAUDE.md)

> 전체 5. Zettelkasten 공통 원칙은 [[5. Zettelkasten/CLAUDE|5. Zettelkasten/CLAUDE.md]] 참고. 이 문서는 `00. Inbox/` 폴더 전용 규칙만 다룸.

## 폴더 역할
- **빠른 메모 수집함** — 5. Zettelkasten으로 들어오는 모든 것의 입구
- **정리 주기**: 주 1회 (Literature 또는 Permanent로 승격, 또는 폐기)
- **특징**: 완벽하지 않아도 OK, 연결 없어도 OK — Inbox는 품질 기준이 없는 유일한 폴더

---

## 여기 들어가는 것

- 읽거나 보다가 떠오른 즉흥적인 생각/인용/메모
- 나중에 Literature 노트로 정리할 원천(책/글/영상)의 임시 캡처
- 아직 "하나의 아이디어"로 다듬어지지 않은 단상
- 프론트매터도, 연결도 필요 없음 — 캡처 마찰을 최소화하는 것이 이 폴더의 유일한 목적

## 여기 들어가지 않는 것

- 이미 완성된 문헌 요약 → `10. Literature/`로 바로
- 이미 명확한 주장 하나로 정리된 통찰 → `20. Permanent/`로 바로
- 프로젝트/영역 관련 실무 메모 → PARA(`1. Projects/`, `2. Areas/`)로

---

## 워크플로우 (1단계: 수집)

```
읽기/시청 → 00. Inbox에 빠른 메모
- 완벽하지 않아도 OK
- 핵심만 캡처
```

## 처리 (주간 정리)

- 매주 일요일(또는 정해진 주기) Inbox 비우기
- 7일 이상 된 메모 → `10. Literature/` 또는 `20. Permanent/`로 승격
- 가치 없는 메모는 삭제 (Inbox는 4. Archive 이동 대상이 아니라 그냥 지워도 되는 유일한 ZK 폴더)

---

## Dataview 활용 예시

### Inbox 정리 대상 (7일 이상)

```dataview
TABLE file.ctime as "생성일"
FROM "5. Zettelkasten/00. Inbox"
WHERE file.ctime < date(today) - dur(7 days)
SORT file.ctime ASC
```

---

## 유지보수 체크리스트 (매주 일요일)

* [ ] Inbox 비우기 (7일 이상 메모 정리)
* [ ] 승격 대상은 Literature/Permanent로, 가치 없는 메모는 삭제

<!-- ok -->
