---
type: doc
status: approved
tags: [policy, projects]
---

# 1. Projects 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `1. Projects/` 폴더의 목적·구조·규칙을 빠르게 이해
- ✅ 작업 시 자동 참조되어 맥락 파악 가속

---

## 폴더 역할 (PARA의 P)
- **1. Projects = 기한이 있는 목표 단위**
- 원칙: **완료 기준(DoD) 명시 · 마감일(due) 필수 · 작업 항목 체크박스화**

---

## 프론트매터 규칙 (프로젝트 노트 최소 스키마)
프로젝트 노트(개별 파일)에만 적용:
```yaml
type: project
status: todo            # todo | in-progress | completed | on-hold
due: 2025-12-31         # ISO 날짜, 프로젝트는 기한 필수
# area: Operations       # 허브/쿼리에 실제로 쓸 때만
# tags: [priority/high]  # 필요할 때만(허용 집합 내 0–3개)
```

**기재하지 않음**

- `created`, `updated` → OS 메타 사용(`file.ctime`, `file.mtime`)
- `related*` → 관계는 본문 [[링크]]/태그로 처리

### ⚠️ OS 메타데이터 주의사항

**PARA 폴더는 OS 메타 활용** (`file.ctime`, `file.mtime`)

**주의**:
- ❌ 파일 **복사** 시 → `file.ctime` 복사 시점으로 변경됨
- ❌ 파일 **이동** 시 → 일부 OS에서 `file.ctime` 변경될 수 있음
- ❌ 클라우드 동기화 후 → 메타데이터 손실 가능

**권장**:
- 프로젝트 완료 후 4. Archive 이동 시: 원본 날짜 보존 위해 **이동(Move)** 사용
- 중요 프로젝트: 본문에 생성일 명시 또는 `created` 필드 예외적 사용 고려

---

## 프로젝트 수명 주기 & 상태 정의

- **생성:** `status: todo`로 시작, `due` 지정
- **진행:** 착수 시 `in-progress`, 진행 로그를 날짜 기준으로 기록
- **완료:** DoD 충족 후 `completed`로 전환, 산출물 링크 정리
- **보류:** `on-hold`(사유 명시). 재개 시 `in-progress`

상태 표준:

- `todo` — 승인/대기, 준비 완료·미착수
- `in-progress` — 수행 중(주 1회 이상 로그 업데이트)
- `completed` — DoD 충족, 산출물/링크 정리 완료
- `on-hold` — 외부 의존·리소스 이슈로 일시 중단

---

## 폴더 구조 원칙

- 기본은 **평면 구조**. 대형/다학제 프로젝트만 하위 폴더(`1. Projects/프로젝트명/`)
- 대용량 산출물은 `7. Attachments/`에 저장하고 프로젝트 본문에서 링크

---

## Claude 작업 지침

- **템플릿:** `6. Templates/project.md` 사용
- **DoD:** "무엇이 되면 완료인가?"를 문장/체크리스트로 명시
- **진행 로그:** 날짜 단위 누적 기록
- **태스크:** 체크박스(`- [ ]`)로 관리, 완료 시 `- [x]`
- **마감일:** `due` 필드 필수. 없으면 `2. Areas/`로 이동 검토
- **연결:** 프론트매터 `area`는 **평문**(예: `Operations`), 본문에 `[[2. Areas/Operations]]` 링크

---

## 관련 폴더 연계

### 2. Areas/
프로젝트 종료 후에도 지속되는 책임·운영 영역 관리. 프로젝트 본문에서 `[[2. Areas/영역명]]`으로 연결.

### 4. Archive/
`completed` 상태 프로젝트는 **1주 이내** 이동. 나중에 참고용으로 검색 가능.

### 3. Resources/
참고 자료는 본문에서 `[[자료명]]`으로 링크. Frontmatter `related` 사용 금지.

### 5. Zettelkasten/
Literature/Permanent 노트는 본문에서 참조. 프로젝트에서 얻은 통찰은 Permanent 노트로 승격.

---

## 태그 사용 원칙 (공통 요약)

- **필요할 때만**: 실제 Dataview 쿼리·검색에 쓰일 때만 태깅(기본 0개 OK)
- **최대 3개**: 한 노트당 태그 0–3개
- **네임스페이스**: `#priority/high`처럼 슬래시(`/`) 사용
- **중복 금지**: YAML(`type/status/due/area`)과 **의미 중복 태그 금지**
- **정기 정리**: 분기마다 태그 감사(audit) → 미사용·모호 태그 제거/통합

---

## 1. Projects 폴더 — 허용 태그 집합（붙여넣기용）

- 우선순위: `#priority/high`, `#priority/medium`, `#priority/low`
- 리스크: `#risk/blocker`, `#risk/watch`
- 대기 상태: `#waiting/external`
- 캠페인/분기: `#campaign/YYYYQn` _(예: `#campaign/2025Q4`)_
- 릴리스(선택): `#release/vMAJOR.MINOR` _(예: `#release/v1.2`)_

금지(중복·혼선): `#project/*`, `#status/*`, `#area/*`

템플릿 주석 안내(복사용):

```yaml
# tags: [priority/high]   # 필요할 때만(허용 집합에서 0–3개)
```

---

## Dataview 활용 예시

### 진행 중(마감순)

```dataview
table status, due, file.mtime as "최종 수정"
from "1. Projects"
where type = "project" and status = "in-progress"
sort due asc
```

### 마감 임박(7일 이내)

```dataview
table due, status
from "1. Projects"
where type = "project"
  and status != "completed"
  and due >= date(today)
  and due <= date(today) + dur(7 days)
sort due asc
```

### 연체(Overdue)

```dataview
table due, status
from "1. Projects"
where type = "project"
  and status != "completed"
  and due < date(today)
sort due asc
```

### 최근 완료(10개)

```dataview
table file.mtime as "완료일"
from "1. Projects"
where type = "project" and status = "completed"
sort file.mtime desc
limit 10
```

### 태그 기반 예시

우선순위 높음:

```dataview
table due, status
from "1. Projects"
where type="project"
  and status!="completed"
  and contains(file.tags, "priority/high")
sort due asc
```

특정 분기 캠페인:

```dataview
table due, status
from "1. Projects"
where type="project"
  and status!="completed"
  and contains(file.tags, "campaign/2025Q4")
sort due asc
```

---

## 예시 프로젝트 템플릿(본문 구조)

> 실제 템플릿 파일은 `6. Templates/project.md`에 별도 보관 권장

```markdown
---
type: project
status: todo            # todo | in-progress | completed | on-hold
due: 2025-11-01
# area: Operations
# tags: [priority/high]
---

# 프로젝트 제목
## 목표(Outcome)
- …

## 완료 기준(Definition of Done)
- [ ] …

## 범위/비범위
- **In scope:** …
- **Out of scope:** …

## 마일스톤
- 2025-10-20: …
- 2025-11-01: …

## 리스크 & 대응
- …

## 진행 로그
- 2025-10-14: …

## 참조
- [[2. Areas/Operations]]
- 자료: [[리소스명]] · 문헌: [[논문/기사]]
```

---

## 금지/주의(안티패턴)

- YAML에 `created/updated/related*` **기입 금지**(중복·부정확)
- 같은 의미를 YAML·본문·태그에 **동시 중복** 금지
- 대형 프로젝트가 아닌데 **불필요 하위 폴더** 생성 금지

---

## 유지보수 체크리스트(분기 1회)

- 템플릿/실사용 노트의 **필드·상태값 일치** 확인
- `due` 누락 항목 보정
- 고아 프로젝트(DoD/로그/참조 미비) 정리
- 태그 감사: 허용 집합 이탈·중복·모호 태그 정리

---

## Hub 파일 (TODO — 아직 미생성)

`00_Projects_Hub.md` 사용법: `0. Docs/Hub-운영-가이드.md` 참고 — **단, 이 가이드 문서와 Hub 파일 둘 다 아직 만들어지지 않았습니다.** 프로젝트 수가 늘어 대시보드가 실제로 필요해지면 `0. Docs/CLAUDE.md`의 TODO 목록을 보고 만들 것.
