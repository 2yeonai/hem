---
type: doc
status: approved
tags: [policy, archive]
---

# 4. Archive 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `4. Archive/` 폴더의 목적·구조·규칙을 빠르게 이해
- ✅ 작업 시 자동 참조되어 맥락 파악 가속

---

## 폴더 역할 (PARA의 마지막 A)
- **4. Archive = 완료/종료/미사용 항목 보관소**
- 원칙: **삭제 금지 (Delete Never, 4. Archive Always) · Append Only · 검색/참조/재활용 가능**
- 목적: 프로젝트 히스토리, 참고용 자료, 재활용 가능 항목 보관

---

## 보관 대상

| 폴더 | 이동 조건 | 예시 |
|------|------------|------|
| `1. Projects/` | `status: completed` | 완료된 프로젝트 |
| `2. Areas/` | `status: inactive` | 종료된 책임 영역 |
| `3. Resources/` | 3개월 이상 미사용 | 오래된 자료 |
| 기타 | 관리 필요 없음 | 임시 저장 문서, 폐기 예정 자료 |

---

## 프론트매터 규칙 (4. Archive 노트 스키마)

4. Archive 노트(개별 파일)에만 적용:

```yaml
type: archive
status: archived
archived_date: 2025-10-14      # 이동일자 (Templater 자동 입력)
original_folder: "1. Projects" # 원본 폴더명
# completed_date: 2025-10-14   # 1. Projects만 선택적 사용

# 복귀(회귀) 범위 - 개선된 필드
return_candidates: ["1. Projects", "2. Areas", "3. Resources", "5. Zettelkasten"]
return_target: "1. Projects"   # 최종 복귀 위치 (단일 선택)
recyclable: yes                # yes | no | partial

# tags: [archive/project]
```

**필수 필드**
* `type: archive` - 항상 고정
* `status: archived` - 항상 고정
* `archived_date` - Templater로 자동 입력
* `original_folder` - 원본 폴더명 (예: "1. Projects")
* `return_candidates` - 복귀 후보 목록 (배열)
* `return_target` - 최종 복귀 위치 (단일 값 또는 "none")
* `recyclable` - 재활용 가능성 (yes/no/partial)

**선택 필드**
* `completed_date` - 프로젝트 완료일 (1. Projects만)

**금지 필드**
* `due`, `related*`, `created`, `updated` → 시스템 메타 사용 (`file.ctime`, `file.mtime`)

---

## 핵심 원칙

### 1. 삭제 금지 (Delete Never, 4. Archive Always)
- ❌ 삭제 (Delete): 복구 불가, 정보 손실
- ✅ 보관 (4. Archive): 언제든 검색/참조/재활용 가능

### 2. Append Only
- 4. Archive로 이동한 파일은 **수정하지 않음**
- 원본 상태 그대로 보존
- 재활용 시 복사 후 새 파일로 작업

### 3. 검색/참조/재활용
- 완료된 프로젝트 참고용
- 과거 자료 검색
- 유사 프로젝트 재활용

---

## Claude 작업 지침

* **이동 시 필수 기록**: `original_folder` 필드에 원본 폴더명 기재
* **Append Only**: 4. Archive 파일은 수정 금지 (읽기 전용)
* **재활용 프로세스**: "복사 → 원본 폴더로 이동 → 상태 변경" 순서
* **Dataview 활용**: `archived_date` 기준 필터링으로 정리 시점 파악

---

## 관련 폴더 연계

### 1. Projects/
`status: completed` 프로젝트는 **1주 이내** `4. Archive/`로 이동. DoD 충족, 산출물 정리 완료 후.

### 2. Areas/
`status: inactive` 영역은 4. Archive로 이동. 더 이상 책임지지 않는 영역.

### 3. Resources/
3개월 이상 미사용 자료 (`file.mtime < 90 days`)는 4. Archive로 이동. 정기 정리 시.

### 5. Zettelkasten/
**4. Archive 이동 금지**. 5. Zettelkasten은 영구 보관 전용 (Literature, Permanent 모두).

---

## PARA 흐름도

```
1. Projects (진행) → completed → 4. Archive/
2. Areas (활성) → inactive → 4. Archive/
3. Resources (참고) → 3개월+ 미사용 → 4. Archive/
5. Zettelkasten → 4. Archive 이동 금지 (영구 보관)
```

---

## 태그 사용 원칙

* **필요할 때만**: 실제 Dataview 쿼리·검색에 쓰일 때만 태깅
* **원본 태그 유지**: 4. Archive 이동 시 기존 태그는 그대로 보존

### 4. Archive 폴더 — 허용 태그 집합

* 원본 분류: `#archive/project`, `#archive/area`, `#archive/resource`, `#archive/temp`

**금지**: `#archive/archived`, `#status/*` (Frontmatter와 중복)

---

## Dataview 활용 예시

### 최근 보관 항목 (10개)

```dataview
table original_folder, file.mtime as "보관일"
from "4. Archive"
where type = "archive"
sort file.mtime desc
limit 10
```

### 폴더별 보관 통계

```dataview
table count(rows) as "보관 개수"
from "4. Archive"
where type = "archive"
group by original_folder
```

### 오래된 보관 항목 (6개월 이상)

```dataview
table file.link as "파일", archived_date
from "4. Archive"
where type = "archive"
  and date(today) - date(archived_date) > dur(180 days)
sort archived_date asc
```

### 재활용 후보 (최근 접근한 4. Archive)

```dataview
table original_folder, file.mtime as "최종 접근"
from "4. Archive"
where type = "archive"
  and file.mtime >= date(today) - dur(30 days)
sort file.mtime desc
```

### 완료된 프로젝트 (4. Archive)

```dataview
table archived_date, file.link as "프로젝트"
from "4. Archive"
where type = "archive"
  and contains(original_folder, "1. Projects")
sort archived_date desc
limit 20
```

### 재활용 가능 항목 (복귀 대상별)

```dataview
TABLE return_target, archived_date, original_folder
FROM "4. Archive"
WHERE recyclable = "yes"
GROUP BY return_target
SORT archived_date DESC
```

### 1. Projects로 복귀 가능한 항목

```dataview
TABLE file.link as "파일", archived_date, original_folder, recyclable
FROM "4. Archive"
WHERE contains(return_candidates, "1. Projects")
  AND recyclable = "yes"
SORT archived_date DESC
```

### 복귀 대상 미정 항목

```dataview
TABLE original_folder, archived_date, recyclable
FROM "4. Archive"
WHERE return_target = ""
SORT archived_date DESC
```

---

## 예시 4. Archive 템플릿(본문 구조)

> 실제 템플릿 파일은 `6. Templates/archive.md`에 별도 보관 권장

```markdown
---
type: archive
status: archived
original_folder: "1. Projects"
archived_date: <% tp.date.now("YYYY-MM-DD") %>
# completed_date: 2025-10-14

# 복귀(회귀) 범위
return_candidates: ["1. Projects", "2. Areas", "3. Resources", "5. Zettelkasten"]
return_target: "1. Projects"
recyclable: yes
tags: [archive/project]
---

# <보관 항목 제목>

## 보관 사유
<!-- 왜 4. Archive로 이동했는가? -->
프로젝트 완료 (DoD 충족)

## 원본 정보
- Original folder: [[1. Projects/프로젝트명]]
- Archived: 2025-10-14

## 복귀 계획
- 복귀 대상: 1. Projects (유사 프로젝트 템플릿으로 재사용)
- 재활용 가능 여부: yes
- 복귀 시점: 필요 시
```

---

## 표준 ENUM 정의

### original_folder (원본 위치)
```yaml
- "1. Projects"
- "2. Areas"
- "3. Resources"
- "5. Zettelkasten"
- "0. Docs"        # 예외적
```

### return_target (복귀 위치, 단일 선택)
```yaml
- "1. Projects"     # 새 프로젝트로 재활용
- "2. Areas"        # 영역 관리로 전환
- "3. Resources"    # 참고 자료로 복귀
- "5. Zettelkasten" # 지식 노트로 승격
- "none"            # 복귀 불필요
```

### recyclable (재활용 가능성)
```yaml
- yes              # 재활용 가능
- no               # 영구 보관만
- partial          # 일부만 재활용
```

---

## 복귀 시나리오별 매핑

| 원본 폴더 | 4. Archive 이유 | 복귀 후보 | return_target | 예시 |
|---------|------------|----------|---------------|------|
| 1. Projects | completed | 1. Projects | "1. Projects" | 유사 프로젝트 템플릿 |
| 1. Projects | completed | 3. Resources | "3. Resources" | 산출물을 참고 자료로 |
| 2. Areas | inactive | 1. Projects | "1. Projects" | 영역을 프로젝트로 전환 |
| 2. Areas | inactive | 2. Areas | "2. Areas" | 나중에 재활성화 |
| 3. Resources | 3개월+ | 3. Resources | "3. Resources" | 관심사 재부상 시 |
| 3. Resources | 3개월+ | 5. Zettelkasten | "5. Zettelkasten" | 깊은 학습으로 승격 |
| 5. Zettelkasten | ❌ | - | - | **4. Archive 이동 금지** |

---

## 재활용 프로세스

### 상황: 4. Archive의 프로젝트를 참고해 새 프로젝트 시작

1. **4. Archive에서 파일 복사** (원본 유지)
2. **새 이름으로 `1. Projects/`에 생성**
3. **Frontmatter 수정**: `type: project`, `status: todo`, `due` 지정
4. **내용 수정**: 새 프로젝트에 맞게 조정
5. **4. Archive 원본은 그대로 유지**

---

## 4. Archive vs 삭제

| 항목 | 4. Archive | 삭제 |
|------|---------|------|
| **원칙** | 4. Archive Always | Delete Never |
| **목적** | 검색/참조/재활용 | 완전 제거 |
| **복구** | 언제든 가능 | 불가능 |
| **비용** | 저장 공간 (무시 가능) | 0 |
| **가치** | 프로젝트 히스토리 보존 | 정보 손실 |

---

## 베스트 프랙티스

1. **삭제 금지 원칙**: 모든 완료/종료 항목은 4. Archive로 이동
2. **분기 1회 정리**: 3개월마다 4. Archive 대상 Dataview로 확인
3. **original_folder 필수**: 원본 위치 기록으로 재활용 용이
4. **재활용 가능성**: "혹시 나중에 참고할까?" → 4. Archive
5. **태그 유지**: 원본 태그 그대로 보존해 검색 용이
6. **읽기 전용**: 4. Archive 파일은 수정하지 않음

---

## 금지/주의(안티패턴)

* 4. Archive 파일을 직접 수정 (Append Only 위반)
* 삭제 (정보 손실)
* `original_folder` 누락 (재활용 시 맥락 손실)
* 5. Zettelkasten 파일 4. Archive 이동 (영구 보관 전용)
* 4. Archive를 "쓰레기통"으로 취급 (재활용 가능한 자산)

---

## 유지보수 체크리스트(분기 1회)

* **완료 프로젝트** 4. Archive 이동 확인 (`status: completed`)
* **비활성 영역** 4. Archive 이동 검토 (`status: inactive`)
* **미사용 자료** (3개월+) Dataview로 확인 후 이동
* 6개월 이상 오래된 4. Archive 항목 검토 (재활용 가능성)
* `original_folder` 필드 누락 항목 보정
* 태그 정리 (원본 태그 유지 확인)
