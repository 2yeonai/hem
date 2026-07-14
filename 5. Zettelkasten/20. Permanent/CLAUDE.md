---
type: doc
status: approved
tags: [policy, zettelkasten, permanent]
---

# 5. Zettelkasten/20. Permanent 운영 지침 (CLAUDE.md)

> 전체 5. Zettelkasten 공통 원칙은 [[5. Zettelkasten/CLAUDE|5. Zettelkasten/CLAUDE.md]] 참고. 이 문서는 `20. Permanent/` 폴더 전용 규칙만 다룸.

## 폴더 역할
- **영구 노트 (내 통찰)**
- **내용**: Literature를 바탕으로 내가 재해석한 아이디어
- **특징**: 하나의 명확한 주장, 최소 2개 이상 다른 노트와 연결

---

## 핵심 원칙

### One Idea per Note
- 하나의 노트에 하나의 아이디어만
- 제목은 명확한 주장 또는 개념
- 예: "원자적 사고의 힘" (O), "생산성" (X)

### 최소 2개 이상 연결 (고아 노트 방지)
- 모든 Permanent 노트는 최소 2개 이상의 다른 노트와 연결
- `related[]` 필드에 명시
- 본문에도 `[[링크]]`로 연결

---

## 프론트매터 규칙

```yaml
type: permanent
status: active
created: 2026-07-08      # 허용 (지식 진화 추적)
updated: 2026-07-08      # 허용 (지식 진화 추적)
tags: []
related: []              # 최소 2개 이상 권장
```

**필수 필드**:
- `type: permanent` - 고정
- `status: active` - 고정
- `created`, `updated` - Templater 자동 입력
- `related` - **최소 2개 이상** 노트 링크

**금지 필드**:
- ❌ `due` - 완료 개념 없음
- ❌ `source`, `author` - Permanent는 본문에 출처 표기 (원출처는 Literature 노트에 이미 있음)

### `updated` 갱신 규칙

**✅ 갱신 대상**: 아이디어 발전, 생각 정제, 새 섹션 추가, 연결(`related`) 추가/변경
**❌ 갱신 금지**: 오타 수정만, 태그만 추가/삭제, 포맷팅 변경

---

## 워크플로우 (3~4단계: 통찰 → 진화)

```
단계 3: Literature 읽고 내 생각 정리
→ 20. Permanent에 통찰 작성
- 내 언어로 재구성
- 최소 2개 노트와 연결
- 하나의 아이디어만

단계 4: 시간이 지나면서 Permanent 노트 업데이트
- 새로운 연결 발견
- 생각 정제
- 발전 방향 추가
```

---

## Literature vs Permanent 구분

| 항목 | Literature | Permanent |
|------|------------|-----------|
| **목적** | 원천 보존 | 통찰 생성 |
| **내용** | 저자의 생각 | 내 생각 |
| **어조** | 객관적 요약 | 주장/해석 |
| **연결** | 최소 (관련 Permanent만) | 최소 2개 이상 |
| **인용** | 필수 | 선택 |
| **완성도** | 읽은 즉시 작성 | 시간 두고 정제 |

---

## ZK → PARA 복제 시나리오: Permanent를 프로젝트 문서로 활용

ZK 원본은 이동하지 않고 **복제본만** PARA로 보낸다 (원칙은 [[5. Zettelkasten/CLAUDE|5. Zettelkasten/CLAUDE.md]] 참고):

```
① 원본 유지: 5. Zettelkasten/20. Permanent/개념.md
② 복제 → 1. Projects/프로젝트명/개념-적용.md
③ Frontmatter 수정:
   - type: project (또는 문서 타입)
   - created/updated/related 삭제
   - due 추가 (필요 시)
```

---

## Dataview 활용 예시

### 고아 노트 (연결 < 2)

```dataview
LIST
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent" AND length(related) < 2
```

### 최신 Permanent (10개)

```dataview
TABLE file.ctime as "생성일", length(related) as "연결 수"
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent"
SORT file.ctime DESC
LIMIT 10
```

### 연결이 많은 Permanent (허브 노트)

```dataview
TABLE length(related) as "연결 수", tags
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent"
SORT length(related) DESC
LIMIT 20
```

### 최근 업데이트된 Permanent (활발히 진화 중)

```dataview
TABLE updated, length(related) as "연결 수"
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent"
SORT updated DESC
LIMIT 10
```

### 지식 진화 추적 (최초-최신 간격)

```dataview
TABLE
  created as "생성",
  updated as "최종 갱신",
  round((date(updated) - date(created)).days, 0) + "일" as "진화 기간"
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent"
SORT (date(updated) - date(created)).days DESC
LIMIT 20
```

**효과**: 어떤 Permanent 노트가 오랫동안 발전했는지 확인 (지식 진화 가시화)

### 장기 미갱신 노트 (휴면 상태)

```dataview
TABLE
  updated as "최종 갱신",
  round((date(today) - date(updated)).days, 0) + "일 전" as "경과"
FROM "5. Zettelkasten/20. Permanent"
WHERE type = "permanent"
  AND date(updated) < date(today) - dur(90 days)
SORT updated ASC
LIMIT 20
```

**효과**: 90일 이상 미갱신 노트 발견 → 재검토 기회

---

## 베스트 프랙티스: Permanent는 명확하게

- 제목이 주장을 담아야 함
- 예: "원자적 사고의 힘" (O), "생산성" (X)
- 하나의 아이디어만 (One Idea per Note)

---

## 금지/주의(안티패턴)

* Permanent에 여러 아이디어 혼합 (One Idea 위반)
* 연결 없는 Permanent (고아 노트)
* Permanent를 4. Archive로 이동 (영구 보관 전용, [[5. Zettelkasten/CLAUDE|공통 원칙]] 참고)
* `created`/`updated`/`related` 필드 삭제 (ZK는 이 필드들을 허용 — PARA와 다름)

---

## 유지보수 체크리스트

### 주간 (매주 일요일)
* [ ] Permanent 노트 최소 1개 작성

### 월간 (매월 첫 주)
* [ ] 고아 노트 (연결 < 2) 찾아 연결 추가
* [ ] 허브 노트 (연결 많은 노트) 검토
* [ ] 그래프 뷰로 연결 패턴 확인

### 분기 (3개월마다)
* [ ] 전체 Permanent 노트 리뷰
* [ ] 태그 정리 (미사용/중복 태그 제거)
* [ ] 연결 강화 (새로운 관계 발견)
* [ ] 시스템 회고 (개선 사항 도출)

<!-- ok -->
