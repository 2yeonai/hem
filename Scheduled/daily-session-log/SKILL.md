---
name: daily-session-log
description: 매일 22:30 오늘 세션 요약을 2. Areas/Claude 세션로그/에 저장
---

모델: 이 작업은 반드시 소넷(Sonnet) 모델로 실행한다.

작업 폴더는 옵시디언 볼트(C:\Users\82106\Desktop\hem)다. 다음을 순서대로 수행해줘.
1. mcp__session_info__list_sessions (필요시 ToolSearch로 로드)로 오늘 날짜에 진행된 Cowork 세션 목록을 확인한다.
2. 오늘 세션이 하나도 없었으면 아무 파일도 만들지 말고 여기서 종료한다 (빈 노트 금지).
3. 세션이 있었으면 각 세션을 mcp__session_info__read_transcript로 읽고 실제로 한 일만 사실 기록으로 정리한다 (해석·과장·추측 금지).
4. "2. Areas/Claude 세션로그/CLAUDE.md"에 있는 폴더 규칙과 일일 노트 형식을 반드시 먼저 읽고 그 형식 그대로 따른다:
```
---
type: session-log
date: YYYY-MM-DD
tags: [area/claude-log]
---
# YYYY-MM-DD 세션 기록
## 진행한 작업 (세션별)
- (세션 주제): 한 일 / 사용 모델 / 산출물 경로
## 결정사항
- (있으면. 설계 결정이면 ai공장짓기/decision-log_skill-factory-architecture.md에도 반영이 필요하다고만 메모하고, 실제 반영은 하지 않는다)
## 미해결 / 다음에 이어서
- (끊긴 지점, 다음 행동)
```
5. 저장 경로는 "2. Areas/Claude 세션로그/오늘날짜(YYYY-MM-DD).md". 같은 날짜 노트가 이미 있으면 덮어쓰지 말고 그 노트에 이어서 추가한다.
6. 관련 공장 폴더가 있으면 [[클로드 방역 ai]] 같은 위키링크를 본문에 건다.
7. "2. Areas/Claude 세션로그/과거기록/" 폴더는 절대 읽기 전용 원본이므로 수정하지 않는다.

<!-- ok -->
