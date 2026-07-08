---
type: doc
status: approved
tags: [policy, zettelkasten, literature]
---

# 5. Zettelkasten/10. Literature 운영 지침 (CLAUDE.md)

> 전체 5. Zettelkasten 공통 원칙은 [[5. Zettelkasten/CLAUDE|5. Zettelkasten/CLAUDE.md]] 참고. 이 문서는 `10. Literature/` 폴더 전용 규칙만 다룸.

## 폴더 역할
- **문헌 노트 (저자의 생각)**
- **내용**: 책/글/영상에서 얻은 원천 자료를 객관적으로 요약
- **특징**: 저자의 주장을 내 언어로 번역 (해석 금지 — 내 의견은 Permanent로 분리)

---

## 프론트매터 규칙

```yaml
type: literature
status: active
created: 2026-07-08      # 허용 (지식 진화 추적)
updated: 2026-07-08      # 허용 (지식 진화 추적)
source: ""               # 출처 URL/서지
author: ""               # 저자/출처 주체
# tags: [literature]
```

**필수 필드**:
- `type: literature` - 고정
- `status: active` - 고정
- `created`, `updated` - Templater 자동 입력
- `source` - 출처 명시
- `author` - 저자 명시

**금지 필드**:
- ❌ `related` - Literature는 관계 정의 안 함 (관계는 Permanent의 역할)

### `updated` 갱신 규칙

**✅ 갱신 대상**: 본문 내용 수정, 새 섹션 추가, 인사이트 보강, 출처 보강
**❌ 갱신 금지**: 오타 수정만, 태그만 추가/삭제, 포맷팅 변경

---

## 워크플로우 (2단계: 정리)

```
주 1회 Inbox 정리
→ 10. Literature에 객관적 요약 작성
- 저자의 주장 정리
- 출처/저자 명시
- 인용 포함
```

---

## 3. Resources vs Literature 구분

3. Resources(`3. Resources/`)와 헷갈리기 쉽다 — 구분 기준은 [[3. Resources/CLAUDE|3. Resources/CLAUDE.md]]에도 있음:

| 항목 | 3. Resources         | Literature (ZK)  |
| -- | ----------------- | ---------------- |
| 목적 | 단순 참고/보관          | 깊은 학습/요약         |
| 정리 방식 | 원문 또는 핵심 요약       | 저자 생각 객관적 요약     |
| 연결 | 1. Projects/2. Areas 참조 | Permanent 노트와 연결 |
| 수명 | 3개월 미사용 시 정리      | 영구 보관            |
| 출처 | source/author/url | source/author 필수 |
| 형식 | 자유 형식             | 구조화된 요약          |

**Literature로 승격해야 하는 자료**: 깊이 있는 학습이 필요하고, 통찰을 얻어 Permanent 노트를 쓸 수 있고, 여러 개념 간 연결이 가능하고, 자주 참조하는 핵심 자료.

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

## ZK → PARA 복제 시나리오: Literature를 Resource로 활용

ZK 원본은 이동하지 않고 **복제본만** PARA로 보낸다 (원칙은 [[5. Zettelkasten/CLAUDE|5. Zettelkasten/CLAUDE.md]] 참고):

```
① 원본 유지: 5. Zettelkasten/10. Literature/책제목.md
② 복제 → 3. Resources/프로그래밍/책제목.md
③ Frontmatter 수정:
   - type: resource
   - created/updated 삭제
   - category 추가
```

---

## Dataview 활용 예시

### Literature → Permanent 후보 (14일 이상)

```dataview
TABLE file.ctime as "생성일", source, author
FROM "5. Zettelkasten/10. Literature"
WHERE type = "literature"
  AND file.ctime < date(today) - dur(14 days)
SORT file.ctime ASC
```

### 저자별 Literature

```dataview
TABLE author, count(rows) as "노트 수"
FROM "5. Zettelkasten/10. Literature"
WHERE type = "literature"
GROUP BY author
SORT count(rows) DESC
```

---

## 베스트 프랙티스: Literature는 객관적으로

- 저자의 주장을 있는 그대로 정리
- 내 의견은 Permanent로 분리
- 인용 필수 (출처 추적)

---

## 금지/주의(안티패턴)

* Literature에 내 의견 포함 (객관성 상실)
* 인용/출처 없이 요약만 작성
* Literature를 4. Archive로 이동 (영구 보관 전용, [[5. Zettelkasten/CLAUDE|공통 원칙]] 참고)

---

## 유지보수 체크리스트

### 주간 (매주 일요일)
* [ ] Literature 노트 최소 1개 작성

### 월간 (매월 첫 주)
* [ ] Literature → Permanent 후보 확인 (14일+ 경과)
