---
type: doc
status: approved
tags: [policy, resources]
---

# 3. Resources 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `3. Resources/` 폴더의 목적·구조·규칙을 빠르게 이해
- ✅ 작업 시 자동 참조되어 맥락 파악 가속

---

## 폴더 역할 (PARA의 R)
- **3. Resources = 주제별 참고 자료 및 관심사**
- 원칙: **재사용 중심 · 출처 명시 · 3개월 룰 적용**
- 예시: 프로그래밍 가이드, 디자인 레퍼런스, 교육 자료, 리더십 도서

---

## 프론트매터 규칙 (Resource 노트 최소 스키마)

Resource 노트(개별 파일)에만 적용:

```yaml
type: resource
status: active          # active | archived
category: "주제명"       # 예: "프로그래밍", "교육", "리더십"
# source: "출처 또는 플랫폼"
# author: "작성자/출판사"
# url: "https://..."
# tags: [resource/design]
```

**금지**

* `due`, `created`, `updated`, `related*` → OS 메타(`file.ctime`/`file.mtime`)로 자동 관리

### ⚠️ OS 메타데이터 주의사항

**PARA 폴더는 OS 메타 활용** (`file.ctime`, `file.mtime`)

**주의**:
- ❌ 파일 **복사** 시 → `file.ctime` 복사 시점으로 변경됨
- ❌ 파일 **이동** 시 → 일부 OS에서 `file.ctime` 변경될 수 있음
- ❌ 클라우드 동기화 후 → 메타데이터 손실 가능

**권장**:
- Resource 보관 시: 원본 날짜 보존 위해 **이동(Move)** 사용
- 중요 Resource: 본문에 추가일 명시 또는 `created` 필드 예외적 사용 고려

---

## 상태 정의

| 상태         | 의미          | 관리 기준           |
| ---------- | ----------- | --------------- |
| `active`   | 현재 참고 중     | 정기 검토 필요        |
| `archived` | 더 이상 사용 안 함 | 3개월 이상 미사용 시 이동 |

---

## 폴더 구조 원칙

* **주제별 하위 폴더 허용** (`3. Resources/프로그래밍/`, `3. Resources/AI/`, `3. Resources/디자인/`)
* 자료량이 적을 경우 평면 구조 유지
* **3개월 이상 미사용 자료는 `4. Archive/` 이동 검토** (file.mtime 기준)

---

## Claude 작업 지침

* **템플릿:** `6. Templates/resource.md` 사용
* **출처 명시:** `source`, `author`, `url` 필드 작성 (신뢰성 확보)
* **카테고리 분류:** 명확한 주제명 사용 (예: "프로그래밍", "AI", "리더십")
* **핵심 요약:** 중요 자료는 핵심 3줄 요약 작성
* **중복 방지:** 동일 주제 자료는 기존 노트에 병합
* **3개월 룰:** file.mtime < 90일 자료는 4. Archive 검토

---

## 관련 폴더 연계

### 1. Projects/ & 2. Areas/
1. Projects와 2. Areas에서 3. Resources를 **참조용**으로 링크. 본문에 `[[3. Resources/자료명]]` 형식 사용.

### 5. Zettelkasten/10. Literature/
**깊은 학습이 필요한 자료는 Literature로 승격**:
- ✅ 통찰을 얻어 Permanent 노트 작성 가능
- ✅ 여러 개념 간 연결 가능
- ✅ 자주 참조하는 핵심 자료

**3. Resources로 유지**:
- ✅ 단순 참고용 (치트시트, 레시피)
- ✅ 도구/라이브러리 문서
- ✅ 간단한 팁/가이드

### 4. Archive/
3개월 이상 미사용 자료는 `archived` 상태로 전환 후 `4. Archive/`로 이동.

---

## 태그 사용 원칙

* **필요할 때만**: 실제 Dataview 쿼리·검색에 쓰일 때만 태깅(기본 0개 OK)
* **최대 3개**: 한 노트당 태그 0–3개
* **네임스페이스**: `#resource/design` 형식

### 3. Resources 폴더 — 허용 태그 집합

* 주제별: `#resource/design`, `#resource/leadership`, `#resource/education`, `#resource/development`, `#resource/ai`
* 우선순위(공통): `#priority/high`, `#priority/medium`, `#priority/low`

**금지**: `#resource/active`, `#status/*` (Frontmatter와 중복)

---

## Dataview 활용 예시

### 카테고리별 자료

```dataview
table file.mtime as "최종 수정", source
from "3. Resources"
where type = "resource" and status = "active"
sort category asc, file.mtime desc
```

### 최근 추가 자료 (30일 이내)

```dataview
table category, source, file.ctime as "추가일"
from "3. Resources"
where type = "resource"
  and file.ctime >= date(today) - dur(30 days)
sort file.ctime desc
```

### 미사용 자료 (3개월 이상, 4. Archive 후보)

```dataview
table category, file.mtime as "최종 접근"
from "3. Resources"
where type = "resource"
  and status = "active"
  and file.mtime < date(today) - dur(90 days)
sort file.mtime asc
```

### 출처별 자료 그룹화

```dataview
table source, author, url
from "3. Resources"
where type = "resource" and status = "active"
group by source
```

### 특정 카테고리 자료

```dataview
table source, file.mtime as "최종 수정"
from "3. Resources"
where type = "resource"
  and status = "active"
  and contains(category, "프로그래밍")
sort file.mtime desc
```

---

## 예시 Resource 템플릿(본문 구조)

> 실제 템플릿 파일은 `6. Templates/resource.md`에 별도 보관 권장

```markdown
---
type: resource
status: active
category: "프로그래밍"
source: "MDN Web 0. Docs"
author: "Mozilla"
url: "https://developer.mozilla.org"
tags: [resource/development]
---

# JavaScript 비동기 처리 가이드

## 요약 (핵심 3줄)
1. Promise는 비동기 작업의 완료/실패를 나타내는 객체
2. async/await는 Promise를 동기 코드처럼 작성할 수 있게 함
3. try-catch로 에러 처리 가능

## 주요 내용
<!-- 필요한 부분만 발췌/정리 -->

## 활용 방안
<!-- 이 자료를 어떻게 활용할 것인가? -->

## 참조
- [[1. Projects/웹개발 프로젝트]]
- [[2. Areas/프로그래밍 역량]]
```

---

## 3. Resources vs Literature 구분

| 항목 | 3. Resources         | Literature (ZK)  |
| -- | ----------------- | ---------------- |
| 목적 | 단순 참고/보관          | 깊은 학습/요약         |
| 정리 방식 | 원문 또는 핵심 요약       | 저자 생각 객관적 요약     |
| 연결 | 1. Projects/2. Areas 참조 | Permanent 노트와 연결 |
| 수명 | 3개월 미사용 시 정리      | 영구 보관            |
| 출처 | source/author/url | source/author 필수 |
| 형식 | 자유 형식             | 구조화된 요약          |

### 승격 기준: 3. Resources → Literature

**Literature로 승격**:
- ✅ 깊이 있는 학습이 필요한 자료
- ✅ 통찰을 얻어 Permanent 노트 작성 가능
- ✅ 여러 개념 간 연결 가능
- ✅ 자주 참조하는 핵심 자료

**3. Resources로 유지**:
- ✅ 단순 참고용 (예: 치트시트, 레시피)
- ✅ 도구/라이브러리 문서
- ✅ 간단한 팁/가이드

---

## 베스트 프랙티스

1. **자료는 "보관"이 아니라 "재사용"이 목표**
2. **3개월 룰:** 3개월 이상 활용 없는 자료는 4. Archive로 이동
3. **요약 작성:** 중요한 자료는 핵심 요약 3줄 작성
4. **출처 명시:** 신뢰성 확보를 위해 source/author/url 필수
5. **중복 방지:** 동일한 주제 자료는 기존 노트에 병합
6. **승격 판단:** 깊은 학습 필요 시 Literature로 승격
7. **폴더 정리:** 주제별 하위 폴더 구조 유지 (예: `프로그래밍/`, `AI/`)

---

## 금지/주의(안티패턴)

* YAML에 `due/created/updated/related*` **기입 금지** (중복·부정확)
* 자료를 읽지 않고 무한정 쌓기만 하는 행위
* 출처 없이 복사·붙여넣기 (저작권·신뢰성 문제)
* 3개월 룰 무시하고 방치
* Literature와 3. Resources 구분 없이 혼용

---

## 유지보수 체크리스트(분기 1회)

* 템플릿/실사용 노트의 **필드·상태값 일치** 확인
* **3개월 이상 미사용 자료** Dataview 쿼리로 확인 → 4. Archive 이동
* 중복 자료 병합 (동일 주제/출처)
* 태그 감사: 허용 집합 이탈·중복·모호 태그 정리
* **Literature 승격 후보** 검토 (자주 참조하는 핵심 자료)
* 하위 폴더 구조 정리 (카테고리 재분류)
