---
type: doc
status: approved
tags: [policy, templates]
version: 1.0.0
owner: "본인"
updated: "2026-07-08"
summary: "템플릿 시스템 운영 규칙, 레지스트리, 버전 관리 및 호환성 검증"
scope: "6. Templates 폴더"
audience: "본인"
keywords: ["templates", "templater", "versioning", "registry", "compatibility"]
related: ["CLAUDE.md"]
---

# 6. Templates 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `6. Templates/` 폴더의 목적·구조·규칙을 빠르게 이해
- ✅ 템플릿 버전 관리 및 호환성 검증
- ✅ 작업 시 자동 참조되어 맥락 파악 가속

---

## 폴더 역할

- **6. Templates = 노트 생성 템플릿 보관소**
- 원칙: **일관성 유지 · Templater 활용 · 각 폴더 CLAUDE.md 규칙 준수 · 버전 관리**
- 목적: 표준화된 노트 생성, 품질 보증, 변경 추적

---

## 템플릿 레지스트리 (SSOT)

**Single Source of Truth** - 모든 템플릿의 중앙 레지스트리. 아래 표는 실제 템플릿 파일이 생성될 때마다 갱신할 것 — 지금은 설계만 있고 파일은 아직 없다.

| ID | Name | target | status | version | Templater | Note |
|----|------|--------|--------|---------|-----------|------|
| project | Project | project | draft | 0.1.0 | >=1.24 | 일반 프로젝트 |
| project-hub | Project Hub | project | draft | 0.1.0 | >=1.24 | 대형 프로젝트 허브 |
| area | Area | area | draft | 0.1.0 | >=1.24 | 영역 관리 |
| resource | Resource | resource | draft | 0.1.0 | none | 참고 자료 |
| literature | Literature | literature | draft | 0.1.0 | >=1.24 | 문헌 노트 |
| permanent | Permanent | permanent | draft | 0.1.0 | >=1.24 | 영구 노트 |
| docs | 0. Docs | doc | draft | 0.1.0 | >=1.24 | 문서 |
| archive | 4. Archive | archive | draft | 0.1.0 | >=1.24 | 보관 항목 |

### 레지스트리 필드 설명

**ID**: 템플릿 식별자 (파일명 기준, 예: `project.md`)
**Name**: 템플릿 표시 이름
**target**: 생성될 노트의 `type` 값 (project, area, resource 등)
**status**: 템플릿 상태 (draft | review | approved | deprecated | superseded)
**version**: 템플릿 버전 (semver 준수: MAJOR.MINOR.PATCH)
**Templater**: 필요한 Templater 플러그인 최소 버전
**Note**: 간단한 설명

실제로 템플릿 파일을 만들면 이 표에 실제 `version`/`status`/수정일을 반영해 최신 상태로 유지한다.

---

## 템플릿 Frontmatter 규칙

모든 템플릿 파일은 **2개의 Frontmatter 블록**을 가져야 합니다.

### 구조

```yaml
---
# === 템플릿 메타데이터 (이 섹션은 실제 노트에 복사 안 됨) ===
type: template
target: project         # project | area | resource | literature | permanent | doc | archive
status: approved        # draft | review | approved | deprecated | superseded
version: 1.2.0          # semver
compat:
  templater: ">=1.24.0"
  obsidian: ">=1.0.0"
changelog_url: "[[6. Templates/CHANGELOG]]"
superseded_by: ""       # 대체 템플릿 ID (deprecated/superseded 시)
# ===============================================

# === 실제 노트 Frontmatter (아래부터 복사됨) ===
type: project
status: todo
due: <% tp.date.now("YYYY-MM-DD", 7) %>
# area: <% tp.file.cursor(1) %>
# tags: []
---
```

### 필드 설명

#### 템플릿 메타데이터 (상단)

**type: template** (필수)
- 항상 `template` 고정
- Dataview로 템플릿만 필터링 가능

**target** (필수)
- 생성될 노트의 `type` 값
- ENUM: `project`, `area`, `resource`, `literature`, `permanent`, `doc`, `archive`

**status** (필수)
- 템플릿 수명주기 상태
- ENUM: `draft`, `review`, `approved`, `deprecated`, `superseded`

**version** (필수)
- Semantic Versioning 준수
- 형식: `MAJOR.MINOR.PATCH`
- 예: `1.2.0`

**compat** (필수)
- 호환성 정보
- `templater`: Templater 플러그인 최소 버전 (또는 `"none"`)
- `obsidian`: Obsidian 최소 버전

**changelog_url** (권장)
- 변경 이력 문서 링크
- 예: `[[6. Templates/CHANGELOG]]`

**superseded_by** (조건부 필수)
- `deprecated` 또는 `superseded` 상태일 때 필수
- 대체 템플릿 ID 명시
- 예: `"project-v2"`

#### 실제 노트 Frontmatter (하단)

- 각 폴더 CLAUDE.md 규칙 준수
- Templater 동적 값 사용 (날짜, 커서 등)
- 주석으로 선택 필드 표시

### `updated` 필드 관리

**폴더별 `updated` 갱신 규칙** (각 폴더 CLAUDE.md 참조):

**ZK (5. Zettelkasten)**:
- ✅ 내용 변화 (아이디어 발전, 생각 정제, 연결 추가)
- ❌ 오타/태그만 수정, 포맷팅 변경

**0. Docs**:
- ✅ 본문 수정 (절차 변경, 정책 보강, 예시 추가)
- ❌ 오타/키워드만 추가, Changelog만 추가

**PARA (1. Projects/2. Areas/3. Resources)**:
- ❌ `updated` 필드 사용 안 함 (OS 메타 `file.mtime` 사용)

---

## 버전 & 상태 수명주기

### 상태 흐름도

```
draft (작성 중)
  ↓
review (검토 중)
  ↓
approved (승인됨, 프로덕션 사용)
  ↓
deprecated (사용 중단 예정, 마이그레이션 가이드 제공)
  ↓
superseded (대체됨, 새 템플릿으로 완전 이동)
```

### 상태별 정의

| 상태 | 설명 | 사용 | 변경 이력 | 마이그레이션 |
|------|------|------|-----------|--------------|
| **draft** | 작성 중, 테스트 필요 | 금지 | 불필요 | 불필요 |
| **review** | 검토 중, 피드백 수집 | 테스트 전용 | 불필요 | 불필요 |
| **approved** | 승인됨, 프로덕션 사용 | ✅ 권장 | 필수 | 불필요 |
| **deprecated** | 사용 중단 예정 | ⚠️ 기존 노트만 | 필수 | 필수 |
| **superseded** | 대체됨 | ❌ 금지 | 필수 | 완료됨 |

### 버전 관리 (Semantic Versioning)

```
MAJOR.MINOR.PATCH
예: 1.2.3
```

**MAJOR (주 버전)**:
- **Breaking Changes** (기존 노트와 호환 불가)
- Frontmatter 필드 삭제/이름 변경
- 본문 구조 대폭 변경
- 예: `1.x.x` → `2.0.0`

**MINOR (부 버전)**:
- **Backward Compatible** (기존 노트 호환)
- 새 섹션 추가
- 선택 필드 추가
- 예: `1.2.x` → `1.3.0`

**PATCH (패치 버전)**:
- **Bug Fix / 개선**
- 오타 수정
- 주석 개선
- 예: `1.2.3` → `1.2.4`

---

## 호환성 관리

### Templater 플러그인 버전

템플릿이 사용하는 Templater 기능에 따라 최소 버전 명시:

```yaml
compat:
  templater: ">=1.24.0"  # Templater 1.24.0 이상 필요
```

**특수 값**:
- `"none"`: Templater 불필요 (순수 마크다운)
- `">=1.24.0"`: Templater 1.24.0 이상 필요

### Obsidian 버전

```yaml
compat:
  obsidian: ">=1.0.0"  # Obsidian 1.0.0 이상
```

### 호환성 검증

Dataview 쿼리로 자동 검증 (후술)

---

## 변경 통제 프로세스

### 템플릿 수정 시 필수 절차

#### 1. 버전 변경 판단

```
오타 수정/주석 개선 → PATCH 증가 (1.2.3 → 1.2.4)
섹션 추가/선택 필드 추가 → MINOR 증가 (1.2.3 → 1.3.0)
필드 삭제/구조 변경 → MAJOR 증가 (1.2.3 → 2.0.0)
```

#### 2. CHANGELOG.md 업데이트

```markdown
## YYYY-MM-DD - project.md v1.3.0

### 변경 사항
- "리스크 & 대응" 섹션 추가

### 마이그레이션 가이드
- 기존 노트: 영향 없음 (호환)
- 신규 노트: 리스크 섹션 작성 권장

### Breaking Changes
- 없음
```

#### 3. 레지스트리 업데이트

`6. Templates/CLAUDE.md` 레지스트리 표의 해당 템플릿 버전/날짜 갱신

#### 4. 관련 폴더 CLAUDE.md 업데이트

템플릿을 사용하는 폴더의 CLAUDE.md에서 버전 정보 갱신

---

### Breaking Changes 처리

**금지**: 기존 템플릿을 Breaking Change로 수정

**권장**: 신규 템플릿 생성 후 supersede

```
project.md (v1.2.0, deprecated)
  ↓ superseded_by
project-v2.md (v2.0.0, approved)
```

**절차**:
1. 신규 템플릿 생성 (`project-v2.md`)
2. 구 템플릿 상태 변경: `deprecated`
3. `superseded_by` 필드 설정: `"project-v2"`
4. CHANGELOG에 마이그레이션 가이드 작성
5. 레지스트리 업데이트

---

## 폴더 구조 원칙

- **평면 구조**: 하위 폴더 없이 모든 템플릿을 한 곳에
- **네이밍 규칙**: `{target}.md` 형식 (예: `project.md`, `area.md`)
  - 대안: `tpl-{target}.md` (선택 사항, 명시적 식별)
- **메타 파일**: `CLAUDE.md`, `CHANGELOG.md`

### 목표 구조 (아직 템플릿 파일 자체는 미생성)

```
6. Templates/
├── CLAUDE.md              # 이 문서 (운영 지침 & 레지스트리)
├── CHANGELOG.md           # 변경 이력 통합 (TODO)
├── project.md             # 일반 프로젝트 (TODO)
├── project-hub.md         # 대형 프로젝트 허브 (TODO)
├── area.md                # 영역 관리 (TODO)
├── resource.md             # 참고 자료 (TODO)
├── literature.md          # 문헌 노트 (TODO)
├── permanent.md            # 영구 노트 (TODO)
├── docs.md                 # 문서 (TODO)
└── archive.md               # 보관 항목 (TODO)
```

---

## Claude 작업 지침

### Claude가 템플릿을 호출/수정할 때 준수 사항

1. **핵심 YAML 필드 보존**
   - 템플릿 메타데이터 (`type: template`, `target`, `status`, `version`) 절대 삭제 금지
   - 실제 노트 Frontmatter는 각 폴더 CLAUDE.md 규칙 준수

2. **버전 변경 시 절차 준수**
   - 버전 증가 → CHANGELOG 업데이트 → 레지스트리 갱신

3. **Breaking Changes 금지**
   - 기존 템플릿 수정 시 호환성 유지
   - Breaking Change 필요 시 신규 템플릿 생성

4. **Templater 사용 규칙**
   - 동적 값은 Templater 문법 사용 (`<% %>`)
   - 예시 값은 주석 또는 플레이스홀더로

5. **각 폴더 CLAUDE.md 참조**
   - 템플릿 수정 전 해당 폴더의 CLAUDE.md 필독
   - Frontmatter 금지 필드 확인 (예: PARA는 `created`/`updated` 금지)

---

## Dataview 검증 대시보드

### 모든 템플릿 현황

```dataview
TABLE
  target as "대상",
  status as "상태",
  version as "버전",
  compat.templater as "Templater",
  file.mtime as "업데이트"
FROM "6. Templates"
WHERE type = "template"
SORT status ASC, version DESC
```

### Deprecated 템플릿 (마이그레이션 필요)

```dataview
LIST superseded_by as "대체 템플릿"
FROM "6. Templates"
WHERE type = "template" AND status = "deprecated"
```

### Draft/Review 템플릿 (승인 대기)

```dataview
TABLE target, version, file.mtime as "업데이트"
FROM "6. Templates"
WHERE type = "template" AND (status = "draft" OR status = "review")
SORT file.mtime DESC
```

### 호환성 경고 (Templater 버전 체크)

```dataview
TABLE compat.templater as "Templater 요구", compat.obsidian as "Obsidian 요구"
FROM "6. Templates"
WHERE type = "template"
  AND compat.templater != "none"
SORT file.name ASC
```

### 템플릿 사용 통계 (간접 추정)

**Notes by Type** (각 target 노트 개수):

```dataview
TABLE
  length(rows) as "노트 수"
FROM ""
WHERE type != "template" AND type != "doc" AND type != "hub"
GROUP BY type
SORT length(rows) DESC
```

---

## 태그 사용 원칙

- **템플릿 파일 자체**에는 태그 불필요 (type: template로 식별)
- **생성된 노트**는 각 폴더 CLAUDE.md 태그 규칙 준수

---

## 예시 템플릿 구조

### Project 템플릿 (project.md)

```markdown
---
# === 템플릿 메타데이터 ===
type: template
target: project
status: approved
version: 1.2.0
compat:
  templater: ">=1.24.0"
  obsidian: ">=1.0.0"
changelog_url: "[[6. Templates/CHANGELOG]]"
superseded_by: ""
# ===============================================

# === 실제 노트 Frontmatter ===
type: project
status: todo
due: <% tp.date.now("YYYY-MM-DD", 7) %>
# area: <% tp.file.cursor(1) %>
# tags: []
---

# <% tp.file.title %>

## 목표(Outcome)
<!-- 이 프로젝트가 완료되면 무엇을 달성하는가? -->
<% tp.file.cursor(2) %>

## 배경
<!-- 왜 이 프로젝트를 시작했는가? -->

## 완료 기준(Definition of Done)
- [ ] <% tp.file.cursor(3) %>

## 범위/비범위
- **In scope:**
- **Out of scope:**

## 마일스톤
- <% tp.date.now("YYYY-MM-DD", 7) %>:
- <% tp.date.now("YYYY-MM-DD", 14) %>:

## 리스크 & 대응
- 리스크: ... / 대응: ...

## 진행 로그
- <% tp.date.now("YYYY-MM-DD") %>:

## 참조
- [[2. Areas/]]
- 자료: [[]] · 문헌: [[]]
```

---

## 베스트 프랙티스

### 1. 템플릿 변경은 semver 준수

- **Bug Fix** (오타/주석) → PATCH
- **기능 추가** (새 섹션) → MINOR
- **구조 변경** (필드 삭제) → MAJOR (신규 템플릿 생성)

### 2. Breaking Changes는 신규 템플릿으로

- ❌ 기존 템플릿 수정: `project.md` v2.0.0
- ✅ 신규 템플릿 생성: `project-v2.md` v2.0.0 + `project.md` deprecated

### 3. CHANGELOG는 간결하게

- 변경 사항 (1-2줄)
- 마이그레이션 가이드 (필요 시)
- Breaking Changes (있으면 명시)

### 4. 레지스트리는 항상 최신 상태 유지

- 템플릿 수정 시 즉시 반영
- 버전/날짜 정확히 갱신

### 5. Templater 커서 위치 활용

```markdown
## 목표
<% tp.file.cursor(1) %>  ← Tab으로 바로 이동

## 범위
- **In scope**: <% tp.file.cursor(2) %>
```

### 6. 주석으로 가이드 제공

```yaml
# area: Operations  # 연결된 영역 (선택)
# tags: [priority/high]  # 필요할 때만 (0-3개)
```

### 7. 폴더 CLAUDE.md와 100% 일치

템플릿 Frontmatter ↔ 폴더 CLAUDE.md 규칙 완벽 동기화

---

## 금지/주의(안티패턴)

### ❌ 다목적 템플릿 (스파게티)

```markdown
# 범용 노트 템플릿
<!-- 프로젝트도 되고, 영역도 되고, 자료도 되는 템플릿 -->
```

**문제**: 일관성 없음, 검증 불가

**해결**: 목적별 전용 템플릿 생성

---

### ❌ 폴더 CLAUDE 규칙 무시

```yaml
# project.md
type: project
created: 2026-07-08  ← 금지! (PARA는 created 사용 안 함)
```

**문제**: 각 폴더 CLAUDE.md 규칙 위반

**해결**: 폴더 CLAUDE.md 필독 후 템플릿 작성

---

### ❌ 템플릿 YAML을 실제 값으로 하드코딩

```yaml
# ❌ 잘못된 예
due: 2026-07-08  # 고정 값

# ✅ 올바른 예
due: <% tp.date.now("YYYY-MM-DD", 7) %>  # 동적 값
```

---

### ❌ 버전 미관리 (템플릿 무정부 상태)

```yaml
# 템플릿 메타데이터 없음
type: project
status: todo
```

**문제**: 변경 추적 불가, 호환성 검증 불가

**해결**: 모든 템플릿에 메타데이터 필수

---

### ❌ CHANGELOG 누락

템플릿 수정 후 CHANGELOG 업데이트 없음

**문제**: 변경 이력 손실, 마이그레이션 가이드 없음

**해결**: 수정 → CHANGELOG → 레지스트리 순서 준수

---

## 유지보수 체크리스트

### 월간 (매월 1일, 15분)

- [ ] **레지스트리 정합성 확인**
  - [ ] 템플릿 파일 vs 레지스트리 표 일치
  - [ ] 버전 번호 정확성
  - [ ] 날짜 최신화

- [ ] **Deprecated 템플릿 처리**
  - [ ] 3개월 이상 deprecated → superseded 전환
  - [ ] 마이그레이션 가이드 검토

- [ ] **Dataview 대시보드 검증**
  - [ ] 모든 쿼리 정상 작동
  - [ ] Draft/Review 템플릿 승인 검토

### 분기 (3개월마다, 30분)

- [ ] **템플릿 품질 감사**
  - [ ] 각 폴더 CLAUDE.md 규칙 vs 템플릿 Frontmatter 일치
  - [ ] Templater 문법 정상 작동
  - [ ] 커서 위치 적절성

- [ ] **버전/상태 정리**
  - [ ] Draft 상태 오래된 템플릿 삭제 또는 승인
  - [ ] Superseded 템플릿 파일 4. Archive 이동 검토

- [ ] **CHANGELOG 정리**
  - [ ] 오래된 변경 이력 요약
  - [ ] 중요 마일스톤만 유지

- [ ] **호환성 검증**
  - [ ] Templater 플러그인 업데이트 확인
  - [ ] Obsidian 버전 업데이트 확인
  - [ ] 템플릿 compat 필드 갱신

---

## Hub 파일 (TODO — 아직 미생성)

Hub 파일(`00_XXX_Hub.md`) 운영 규칙: `0. Docs/Hub-운영-가이드.md` 참고 — **단, 이 가이드 문서와 아래의 개별 템플릿 파일들은 전부 아직 만들어지지 않았습니다.** 실제로 노트가 쌓이기 시작하면 이 문서의 레지스트리 표를 기준으로 하나씩 만들 것.

---

## 관련 문서

- **변경 이력**: `6. Templates/CHANGELOG.md` (TODO — 아직 미생성)
- **Hub 시스템**: `0. Docs/Hub-운영-가이드.md` (TODO — 아직 미생성)
- **루트 운영 지침**: [[CLAUDE]]

---

## Changelog
- 2026-07-08: 볼트 정리 과정에서 발견된 이전 템플릿(`6. Templates-CLAUDE.md` 폴더, `owner: kamwoo`)을 번호 없는 `Templates/` 구조로 이전 — 개인 메타데이터 일반화, 경로 참조를 번호 없는 형식으로 통일, 실제로는 아직 만들어지지 않은 템플릿 파일들의 레지스트리 상태를 `approved`에서 `draft`로 정정, Hub/CHANGELOG 참조는 TODO로 명시
- 2026-07-08: 공식 구조를 번호형(`6. Templates/` 등)으로 재확정 — 볼트 전체 폴더 경로 참조를 번호 있는 형식으로 갱신
