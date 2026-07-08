---
type: doc
status: approved
tags: [policy, areas]
---

# 2. Areas 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `2. Areas/` 폴더의 목적·구조·규칙을 빠르게 이해
- ✅ 작업 시 자동 참조되어 맥락 파악 가속

---

## 폴더 역할 (PARA의 A)
- **2. Areas = 기한 없는 지속적 책임 영역**
- 원칙: **정기 리뷰 · 상태 관리 · 프로젝트와 명확 구분**
- 예시: 건강, 재무, 직무 역량, 인간관계, 운영 시스템

---

## 프론트매터 규칙 (Area 노트 최소 스키마)

Area 노트(개별 파일)에만 적용:

```yaml
type: area
status: active             # active | inactive | archived
# review_cycle: monthly     # optional, 리뷰 주기
# tags: [area/operations]   # 필요 시 허용 집합 내 사용
```

**금지**

* `due` 필드 없음 (기한 없는 지속 영역)
* `related*` 필드 불가 → 본문 `[[링크]]` 사용
* `created`/`updated`는 OS 메타(`file.ctime`/`file.mtime`)로 자동 관리

### ⚠️ OS 메타데이터 주의사항

**PARA 폴더는 OS 메타 활용** (`file.ctime`, `file.mtime`)

**주의**:
- ❌ 파일 **복사** 시 → `file.ctime` 복사 시점으로 변경됨
- ❌ 파일 **이동** 시 → 일부 OS에서 `file.ctime` 변경될 수 있음
- ❌ 클라우드 동기화 후 → 메타데이터 손실 가능

**권장**:
- Area 보관 시: 원본 날짜 보존 위해 **이동(Move)** 사용
- 중요 Area: 본문에 시작일 명시 또는 `created` 필드 예외적 사용 고려

---

## 상태 정의

| 상태         | 의미           | 행동                |
| ---------- | ------------ | ----------------- |
| `active`   | 현재 운영 중      | 월 1회 리뷰 로그 업데이트   |
| `inactive` | 일시 중단        | 1. Projects로 재활성화 가능 |
| `archived` | 더 이상 유지하지 않음 | `4. Archive/`로 이동 |

---

## 리뷰 주기 원칙

* **기본 주기:** `review_cycle: monthly`
* **주요 항목:** 목표, 현황, 관련 프로젝트, 리스크, 개선사항
* **형식:** `## 리뷰 로그` 섹션에 날짜별 기록

---

## 폴더 구조 원칙

* 2. Areas는 **평면 구조** (하위 폴더 없음)
* 책임 영역별로 독립 노트 유지
* 대용량 자료는 `7. Attachments/`에 저장 후 링크

---

## Claude 작업 지침

* **템플릿:** `6. Templates/area.md` 사용
* **리뷰 로그:** 월 1회 이상 업데이트 (날짜 기록)
* **상태 전환:** inactive/archived로 변경 시 사유 명시
* **프로젝트 연결:** 본문에 `[[1. Projects/프로젝트명]]` 링크
* **Dataview 활용:** 관련 프로젝트 자동 집계 쿼리 포함

---

## 관련 폴더 연계

### 1. Projects/
Area에서 파생된 구체적 프로젝트들. Area 노트에서 관련 프로젝트를 Dataview로 자동 집계.

```dataview
table status, due
from "1. Projects"
where contains(area, this.file.name)
sort due asc
```

### 4. Archive/
`archived` 상태 Area는 **1주 이내** `4. Archive/`로 이동. 더 이상 활동하지 않는 책임 영역.

### 3. Resources/
참고 자료는 본문에서 `[[자료명]]`으로 링크. Frontmatter `related` 사용 금지.

### 5. Zettelkasten/
Literature/Permanent 노트는 본문에서 참조. Area 운영에서 얻은 통찰은 Permanent 노트로 승격.

---

## 태그 사용 원칙

* **필요할 때만**: 실제 Dataview 쿼리·검색에 쓰일 때만 태깅(기본 0개 OK)
* **최대 3개**: 한 노트당 태그 0–3개
* **네임스페이스**: `#area/operations`, `#area/development` 형식
* **중복 금지**: YAML(`type/status`)과 의미 중복 태그 금지

### 2. Areas 폴더 — 허용 태그 집합

* 영역 분류: `#area/operations`, `#area/development`, `#area/personal`
* 리뷰 상태: `#review/overdue`, `#review/needed`
* 우선순위: `#priority/high`, `#priority/low`

**금지**: `#area/active`, `#status/*` (Frontmatter와 중복)

---

## Dataview 활용 예시

### 활성 영역 목록

```dataview
table status, file.mtime as "최종 리뷰"
from "2. Areas"
where type = "area" and status = "active"
sort file.mtime desc
```

### 리뷰 필요 영역 (30일 이상 미리뷰)

```dataview
table file.mtime as "마지막 리뷰"
from "2. Areas"
where type = "area"
  and status = "active"
  and file.mtime < date(today) - dur(30 days)
sort file.mtime asc
```

### 비활성/보류 영역

```dataview
table file.link as "Area", status
from "2. Areas"
where type = "area" and (status = "inactive" or status = "archived")
sort file.name asc
```

### 특정 Area의 관련 프로젝트

```dataview
table status, due
from "1. Projects"
where type = "project" and contains(area, "Operations")
sort due asc
```

---

## 예시 Area 템플릿(본문 구조)

> 실제 템플릿 파일은 `6. Templates/area.md`에 별도 보관 권장

```markdown
---
type: area
status: active
# review_cycle: monthly
# tags: [area/operations]
---

# <영역 제목>

## 목적
<!-- 이 영역이 담당하는 책임과 역할 -->

## 현황
<!-- 현재 상태, 주요 지표, KPI 등 -->

## 관련 프로젝트 (자동 집계)
```dataview
table status, due
from "1. Projects"
where contains(area, this.file.name)
sort due asc
```

## 리뷰 로그
- 2025-10-14:
- 2025-09-10:

## 참조
- [[3. Resources/관련자료]]
- [[5. Zettelkasten/관련노트]]
```

---

## 리뷰 로그 예시

```markdown
## 리뷰 로그
- 2025-10-14: 선교 훈련 영역 현황 점검, 신규 프로젝트 2건 계획.
- 2025-09-10: 학생 관리 프로세스 개선 중.
```

---

## 베스트 프랙티스

1. **1 Area = 1 책임 단위** (사람, 시스템, 부문 등)
2. **명확한 상태 관리:** `active` ↔ `inactive` ↔ `archived` 전환 시점 기록
3. **리뷰 중심 운영:** "성과"보다 "유지·개선" 중심
4. **1. Projects와 구분:**
   - Area: "건강" (지속)
   - Project: "10kg 감량" (기한)
5. **정기 리뷰 습관:** 월초 첫 주에 모든 active Area 리뷰
6. **KPI 추적:** 가능하면 정량 지표 포함 (예: "월 독서량 3권")

---

## 1. Projects vs 2. Areas 구분 기준

| 질문 | 1. Projects | 2. Areas |
|------|----------|-------|
| 완료 기준이 있나? | ✅ 있음 (DoD) | ❌ 없음 (지속) |
| 마감일이 있나? | ✅ 있음 (`due`) | ❌ 없음 |
| 끝나면 사라지나? | ✅ 4. Archive 이동 | ❌ 계속 유지 |
| 예시 | "웹사이트 리뉴얼" | "웹사이트 운영" |

---

## 금지/주의(안티패턴)

* YAML에 `due/created/updated/related*` **기입 금지**
* Area를 Project처럼 관리 (완료 체크 금지)
* 리뷰 없이 방치 (최소 분기 1회 리뷰 필수)
* 너무 세분화 (예: "독서", "영화", "음악" → "문화생활"로 통합)

---

## 유지보수 체크리스트(분기 1회)

* 템플릿/실사용 노트의 **필드·상태값 일치** 확인
* `active` 상태인데 **30일 이상 미리뷰** 항목 점검
* `inactive` → `archived` 전환 검토
* 태그 감사: 허용 집합 이탈·중복·모호 태그 정리
* Area와 1. Projects 연결 상태 확인 (Dataview 쿼리 작동 검증)

---

## Hub 파일 (TODO — 아직 미생성)

`00_Areas_Hub.md` 사용법: `0. Docs/Hub-운영-가이드.md` 참고 — **단, 이 가이드 문서와 Hub 파일 둘 다 아직 만들어지지 않았습니다.** 필요해지면 `0. Docs/CLAUDE.md`의 TODO 목록을 보고 만들 것.
