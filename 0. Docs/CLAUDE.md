---
title: "Docs 폴더 운영 규칙"
doc_type: "policy"
updated: "2026-07-08"
owner: "본인"
summary: "Docs 폴더의 문서 작성 및 관리 규칙"
scope: "Docs 폴더 내 모든 문서"
audience: "본인"
keywords: ["documentation", "frontmatter", "changelog", "flat-structure"]
related: ["CLAUDE.md"]
status: "active"
---

# Docs 폴더 운영 규칙

## 개요

`Docs` 폴더는 **운영 규칙, 정책, 프로세스 문서**를 보관합니다. PARA(Projects/Areas/Resources/Archive)나 Zettelkasten처럼 "콘텐츠"를 담는 폴더가 아니라, 이 볼트 자체를 어떻게 운영할지에 대한 메타 문서를 담는 폴더입니다.

### 핵심 원칙

1. **평면 구조**: 하위 폴더 없이 모든 문서를 한 곳에
2. **메타데이터 분류**: Frontmatter의 `doc_type`, `keywords`로 분류
3. **마이크로 Changelog**: 문서 하단에 변경 이력 간단히 기록

---

## Frontmatter 규칙

### 템플릿

```yaml
---
# 필수 (4개)
title: "<문서 제목>"
doc_type: "policy|procedure|howto|reference|decision"
updated: "YYYY-MM-DD"
owner: "본인"

# 권장 (5개) - 문맥 확보용
summary: "<1-2문장 요약>"
scope: "<적용 범위>"
audience: "본인|팀|전사"
keywords: ["<검색어1>", "<검색어2>"]
related: ["<연관 문서>"]

# 선택 (필요시에만)
status: "active|deprecated"
version: "1.0.0"
notes: "<짧은 주석>"
---
```

### doc_type 설명

- `policy`: 원칙, 가이드라인
- `procedure`: 절차, 프로세스
- `howto`: 실행 가이드, 튜토리얼
- `reference`: 참고 자료, 용어집
- `decision`: 의사결정 기록 (ADR)

### 작성 팁

- **title/summary/scope**만 잘 써도 문맥 80% 확보
- **version**은 파괴적 변화(구조/절차 변경)에만 사용
- **status**는 `active/deprecated`만 사용 (검토/승인 흐름 없음)

### `updated` 갱신 규칙

**✅ `updated` 갱신 대상**:
- 본문 내용 수정 (절차 변경, 정책 보강)
- 새로운 섹션 추가
- 예시 추가/변경
- Changelog 항목 추가 (단, Changelog 추가와 동시에 본문도 변경된 경우)

**❌ `updated` 갱신 금지** (내용 변화 아님):
- 오타/맞춤법 수정만
- 키워드(`keywords`) 추가만
- 포맷팅 변경 (줄바꿈, 들여쓰기)
- Changelog 항목만 추가 (본문 변경 없이)

**규칙**: *실질적 내용 변화가 있을 때만* `updated` 갱신

---

## Changelog 규칙

문서 하단에 **최대 5개 항목**만 유지:

```markdown
## Changelog
- YYYY-MM-DD: 무엇을 변경 + 왜 (1줄)
- YYYY-MM-DD: 다음 변경 사항 (1줄)
```

**규칙**:
- 무엇을 + 왜를 1줄로 요약
- 오래된 항목은 삭제
- 월간 집계 불필요 (개인 vault)

---

## 작성 예시

```markdown
---
title: "Git Commit 컨벤션"
doc_type: "procedure"
updated: "2026-07-08"
owner: "본인"
summary: "커밋 메시지 작성 규칙"
scope: "모든 프로젝트"
audience: "본인"
keywords: ["git", "commit", "convention"]
status: "active"
---

# Git Commit 컨벤션

## 형식
```
type(scope): subject
```

## type 종류
- feat: 새 기능
- fix: 버그 수정
- docs: 문서 수정
- refactor: 리팩토링

## Changelog
- 2026-07-08: 초기 작성 (Conventional Commits 기반)
```

---

## Dataview 활용

### 문서 타입별 보기
```dataview
TABLE doc_type, summary, updated
FROM "Docs"
SORT doc_type ASC, updated DESC
```

### 최근 업데이트된 문서
```dataview
TABLE doc_type, updated
FROM "Docs"
SORT updated DESC
LIMIT 10
```

### 키워드 검색
```dataview
LIST
FROM "Docs"
WHERE contains(keywords, "검색어")
```

---

## Hub 파일 체계 (TODO — 아직 미생성)

`Projects/CLAUDE.md`, `Areas/CLAUDE.md`, `Zettelkasten/CLAUDE.md`, `Templates/CLAUDE.md`는 전부 `[[Docs/Hub-운영-가이드]]`라는 문서와, 각 폴더의 `00_XXX_Hub.md`(예: `00_Projects_Hub.md`, `00_Areas_Hub.md`, `00_ZK_Hub.md`)를 참조합니다. 이 문서들은 **아직 실제로 존재하지 않습니다** — 폴더 구조를 정리하며 발견된 이전 템플릿의 설계 의도만 남아 있는 상태입니다.

**TODO**:
- [ ] `Docs/Hub-운영-가이드.md` 작성 — Hub 파일이 무엇이고 왜 쓰는지, 언제 만드는지 정의
- [ ] 필요해지면(노트가 많아져 폴더별 허브/대시보드가 실제로 필요할 때) `Projects/00_Projects_Hub.md`, `Areas/00_Areas_Hub.md`, `Zettelkasten/00_ZK_Hub.md` 등을 만들고 위 가이드에 맞춰 채움
- [ ] 그 전까지 다른 CLAUDE.md의 `[[Docs/Hub-운영-가이드]]` 링크는 죽은 링크(미생성)로 취급할 것 — 있는 것처럼 안내하지 말 것

---

## Changelog
- 2026-07-08: 볼트 정리 과정에서 발견된 이전 템플릿(`Docs-CLAUDE.md` 폴더, `0. Docs` 번호 표기, `owner: Kein`)을 번호 없는 `Docs/` 구조로 이전 — 개인 메타데이터 일반화, 경로 참조를 번호 없는 형식으로 통일, Hub 체계는 TODO로 명시
