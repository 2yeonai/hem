# LOCAL_RUN_GUIDE.md — 로컬 실행 안내

## 0. 필요한 것

- Python 3.9 이상 (그 외 아무것도 설치할 필요 없음 — 외부 라이브러리 0개, API 키 불필요)
- 확인: `python3 --version`

## 1. 실행 (웹앱)

```bash
cd hyemi-ai-factory
python3 08_factory_tools/app.py
```

브라우저에서 http://127.0.0.1:8787 접속. 중지는 Ctrl+C. (127.0.0.1 전용 — 외부 접속 불가)

## 2. 샘플 프로젝트 실행

대시보드에서 **"▶ 샘플 프로젝트 실행"** 클릭 → `sample-demo` 프로젝트가 생성되고 8개 탭에 결과가 뜬다.
샘플은 가상 공고다. 실제 공고 결과로 재사용 금지 (DECISIONS.md D-006).

## 3. 실제 공고 넣기

1. 대시보드 → "+ 새 프로젝트"
2. 공고문 원문 전체를 붙여넣는다 (비우면 [확인 필요] 모드 — LOCK·제출 판정이 막힌다)
3. 심사표·배점, 신청자 정보, 아이디어 후보 1~3개, 예산 계획 입력 (모르는 값은 비워둔다 — 지어내지 말 것)
4. "분석 실행" → 8개 탭 확인, 특히 ⑥ 재작업 지시서 1순위
5. 서류 확인 후 ④ LOCK 탭에서 승인 체크 → 재분석

## 4. 결과 확인

- 화면: 프로젝트 페이지 8개 탭
- 파일: `04_outputs/<프로젝트>/`(요약·비교표·LOCK·results.json), `05_reviews/<프로젝트>/`(검수 7종), `10_handoff/HANDOFF_<프로젝트>.md`
- ⑧ Export 탭에서 전 파일 열람·복사 + 다음 실행 프롬프트

## 5. CLI로 실행 (화면 없이)

```bash
python3 08_factory_tools/create_project.py <프로젝트명>   # 스캐폴딩
# 01_inputs/<프로젝트명>/input.json 채우기
python3 08_factory_tools/run_factory.py <프로젝트명> --step all
```

## 6. 테스트

```bash
python3 08_factory_tools/test_engines.py   # 엔진 단위 테스트 29건
```

## 7. 오류 발생 시 확인할 것

1. `python3 --version` 이 3.9 이상인가
2. `hyemi-ai-factory/` 폴더 안에서 실행했는가
3. 포트 8787이 이미 사용 중인가 → 기존 프로세스 종료 후 재실행
4. 입력 JSON을 직접 고쳤다면 문법 오류가 없는가 (`python3 -m json.tool 01_inputs/<p>/input.json`)
5. 화면에 빨간 오류 배너가 뜨면 그 문구와 `08_factory_tools/error_handling_rules.md` 대조

<!-- ok -->
