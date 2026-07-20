---
name: weekly-synthesis-sonnet
description: 매주 일요일4:00 주간 종합 노트를 2. Areas/Claude 세션로그/에 저장 (소넷)
---

모델: 이 작업은 반드시 소넷(Sonnet) 모델로 실행한다.

작업 폴더는 옵시디언 볼트(C:\Users\82106\Desktop\hem)다. 다음을 순서대로 수행해줘.
1. "2. Areas/Claude 세션로그/" 폴더에서 최근 7일치 일일 노트(YYYY-MM-DD.md)를 전부 읽는다. 없으면 있는 만큼만 읽는다.
2. "2. Areas/핵심맥락.md"를 읽어 전체 맥락(4개 공장 현황, 다음 결정 포인트)을 파악한다.
3. "2. Areas/Claude 세션로그/CLAUDE.md"의 폴더 규칙을 따른다 — 과거기록/ 폴더는 절대 수정하지 않는다, 사실 기록 위주로 작성한다.
4. 이번 주 변화 / 정체된 것 / 다음 주 주목할 것 3부분으로 구성된 주간 종합 노트를 작성한다. frontmatter는 다음을 따른다:
```
---
type: session-log
date: YYYY-MM-DD
tags: [area/claude-log]
---
```
5. 저장 경로는 "2. Areas/Claude 세션로그/주간종합_오늘날짜(YYYY-MM-DD).md".
6. 이번 주 로그가 하나도 없었으면 "이번 주 세션 없음"이라고만 짧게 기록하고 끝낸다 — 내용을 지어내지 않는다. sentinel 스캔

<!-- ok -->
