---
type: doc
status: approved
tags: [policy, zettelkasten]
---

# 5. Zettelkasten 폴더 운영 지침 (CLAUDE.md)

## 문서 목적
- ✅ Claude Code(저)를 위한 컨텍스트 제공
- ✅ `5. Zettelkasten/` 전체(00. Inbox / 10. Literature / 20. Permanent)의 목적·구조·규칙을 빠르게 이해
- ✅ 작업 시 자동 참조되어 맥락 파악 가속
- 하위 폴더별 세부 규칙은 각 폴더의 CLAUDE.md 참고: [[5. Zettelkasten/00. Inbox/CLAUDE|00. Inbox]] · [[5. Zettelkasten/10. Literature/CLAUDE|10. Literature]] · [[5. Zettelkasten/20. Permanent/CLAUDE|20. Permanent]]

---

## 폴더 역할 (지식 발전소)
- **5. Zettelkasten = 시간 독립적 영구 지식 저장소**
- 원칙: **One Idea per Note · 최소 2개 연결 · Literature → Permanent 흐름 · 4. Archive 이동 금지**
- 목적: PARA(1. Projects/2. Areas/3. Resources/4. Archive)의 작업 실행과 분리된 순수 지식 발전. "지식 발전소"와 "프로젝트 작업대"를 분리한다는 것이 이 볼트 전체의 핵심 철학.

---

## 하위 구조 한눈에 보기

| 폴더 | 역할 | 정리 주기 |
|---|---|---|
| `00. Inbox/` | 빠른 메모 수집함 | 주 1회 (Literature/Permanent로 승격 또는 폐기) |
| `10. Literature/` | 문헌 노트 — 저자의 생각을 내 언어로 객관적 요약 | 필요할 때마다 작성, 14일 이상 지나면 Permanent 승격 검토 |
| `20. Permanent/` | 영구 노트 — Literature를 바탕으로 재해석한 내 통찰 | 시간을 두고 계속 진화 |

---

## 핵심 원칙

### 1. One Idea per Note
- 하나의 노트에 하나의 아이디어만
- 제목은 명확한 주장 또는 개념
- 예: "원자적 사고의 힘", "연결이 만드는 통찰"

### 2. 최소 2개 이상 연결 (고아 노트 방지)
- 모든 Permanent 노트는 최소 2개 이상의 다른 노트와 연결
- `related[]` 필드에 명시
- 본문에도 `[[링크]]`로 연결

### 3. Literature → Permanent 흐름
```
읽기 → 00. Inbox (빠른 메모)
     → 10. Literature (원천 정리)
     → 20. Permanent (내 생각으로 재구성)
```

### 4. Archive 이동 금지
- 5. Zettelkasten 노트는 **영구 보관**
- 완료 개념 없음 (계속 진화)
- 삭제 금지, 수정만 가능

---

## PARA vs ZK 프론트매터 비교표

| 필드 | PARA (P/A/R/Ar) | ZK Literature | ZK Permanent |
|------|-----------------|---------------|--------------|
| `type` | ✅ | ✅ | ✅ |
| `status` | ✅ | ✅ | ✅ |
| `created` | ❌ OS 메타 | ✅ 진화 추적 | ✅ 진화 추적 |
| `updated` | ❌ OS 메타 | ✅ 진화 추적 | ✅ 진화 추적 |
| `due` | ✅ 1. Projects만 | ❌ | ❌ |
| `source` | ❌ | ✅ | ❌ |
| `author` | ❌ | ✅ | ❌ |
| `related` | ❌ 본문 링크 | ❌ | ✅ 최소 2개 |
| `tags` | ✅ 선택 | ✅ 선택 | ✅ 선택 |

### 핵심 차이점

**PARA**: 시간 제약적 실행 → OS 메타 활용 (관리 비용 0)
**ZK**: 시간 독립적 지식 → 명시적 필드 (진화 과정 추적)

세부 frontmatter 스키마는 [[5. Zettelkasten/10. Literature/CLAUDE|10. Literature]], [[5. Zettelkasten/20. Permanent/CLAUDE|20. Permanent]] 참고.

---

## ZK → PARA 이동 원칙 (복제본만)

### 원칙
- **ZK 원본은 절대 이동 금지** (영구 보관)
- PARA에서 활용 필요 시 **복제본만 생성**
- 복제본은 PARA 규칙 따름 (`created`/`updated`/`related` 제거)

### 금지 사항
- ❌ ZK 노트를 PARA로 이동 (잘라내기)
- ❌ ZK 노트에 PARA 규칙 적용 (`due` 추가 등)
- ❌ ZK 노트를 4. Archive로 이동

구체적인 복제 시나리오(Literature→Resource, Permanent→Project)는 각 하위 폴더 CLAUDE.md 참고.

---

## Claude 작업 지침

* **템플릿 사용**: `6. Templates/literature.md`, `6. Templates/permanent.md`
* **Literature → Permanent**: Inbox 또는 Literature에서 시작, Permanent로 승격
* **4. Archive 금지**: 5. Zettelkasten 노트는 절대 4. Archive 이동 안 함
* **복제본 원칙**: PARA 활용 시 복제본만, 원본은 ZK 유지
* 노트 타입별 세부 규칙(One Idea, 최소 2연결, 객관적 요약 등)은 각 하위 폴더 CLAUDE.md를 따를 것

---

## 관련 폴더 연계

### 1. Projects/ & 2. Areas/ & 3. Resources/
- **참조 방향**: PARA → ZK (일방향)
- **방법**: 본문에 `[[5. Zettelkasten/노트명]]` 링크
- **복제본**: 필요 시 ZK에서 복제 → PARA로 이동

### 4. Archive/
- **ZK → 4. Archive 이동 금지**
- ZK는 영구 보관 전용
- 삭제 필요 없음 (계속 진화)

---

## 태그 사용 원칙

* **필요할 때만**: 실제 Dataview 쿼리·검색에 쓰일 때만 태깅
* **최대 3개**: 한 노트당 태그 0–3개
* **주제 중심**: `#thinking`, `#knowledge-work`, `#atomicity` 형식

### 5. Zettelkasten 폴더 — 허용 태그 집합

* Literature: `#literature`, `#book`, `#article`, `#video`
* Permanent: `#concept`, `#principle`, `#method`, `#observation`
* 주제별: `#productivity`, `#learning`, `#writing`, `#programming`

**금지**: `#permanent/active`, `#status/*` (Frontmatter와 중복)

---

## 베스트 프랙티스 (전체 공통)

### 1. 연결 먼저, 완성은 나중에
- 완벽한 노트보다 연결된 노트가 더 가치 있음
- 초안 상태로 두고 연결부터 만들기
- 시간이 지나면서 자연스럽게 정제

### 2. 주기적 연결 강화
- 월 1회: 고아 노트 찾아 연결 추가
- 분기 1회: 허브 노트 (연결 많은 노트) 확인
- 그래프 뷰로 연결 패턴 시각화

### 3. 태그보다 링크
- 태그는 보조 수단
- 주된 연결은 `[[링크]]`와 `related[]` 필드
- 태그는 주제 분류 정도만

노트 타입별 세부 베스트 프랙티스(Inbox 비우기, 객관적 Literature 작성, 명확한 Permanent 작성)는 각 하위 폴더 CLAUDE.md 참고.

---

## 5. Zettelkasten 워크플로우 (전체 흐름)

```
단계 1 (수집): 읽기/시청 → 00. Inbox에 빠른 메모 — 완벽하지 않아도 OK, 핵심만 캡처
단계 2 (정리): 주 1회 Inbox 정리 → 10. Literature에 객관적 요약 작성
단계 3 (통찰): Literature 읽고 내 생각 정리 → 20. Permanent에 통찰 작성, 최소 2개 노트와 연결
단계 4 (진화): 시간이 지나면서 Permanent 노트 업데이트 — 새로운 연결 발견, 생각 정제
```

각 단계의 구체적인 작성 규칙은 해당 하위 폴더 CLAUDE.md 참고.

---

## 금지/주의(안티패턴) — 전체 공통

* ZK 노트를 4. Archive로 이동 (영구 보관 전용)
* ZK 노트를 PARA로 이동 (복제본 원칙 위반)
* `created`/`updated`/`related` 필드 삭제 (ZK는 허용 — PARA와 다름)
* 완벽주의 (초안 상태로 시작, 점진적 정제)

노트 타입별 금지사항(Permanent에 여러 아이디어 혼합, Literature에 의견 포함 등)은 각 하위 폴더 CLAUDE.md 참고.

---

## 유지보수 체크리스트 개요

세부 체크리스트는 각 하위 폴더 CLAUDE.md에 있음. 전체 리듬은 다음과 같다:

* **주간 (매주 일요일)**: Inbox 비우기, Literature/Permanent 노트 최소 1개씩 작성
* **월간 (매월 첫 주)**: 고아 노트 연결 보강, Literature→Permanent 승격 후보 확인, 허브 노트 검토
* **분기 (3개월마다)**: 전체 Permanent 리뷰, 태그 정리, 시스템 회고

---

## Hub 파일 (TODO — 아직 미생성)

`00_ZK_Hub.md` 사용법: `0. Docs/Hub-운영-가이드.md` 참고 — **단, 이 가이드 문서와 Hub 파일 둘 다 아직 만들어지지 않았습니다.** 노트가 늘어 전체 그래프/허브 뷰가 실제로 필요해지면 `0. Docs/CLAUDE.md`의 TODO 목록을 보고 만들 것.

<!-- ok -->
