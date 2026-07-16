# project_generator_spec.md — 프로젝트 생성 규칙

구현: create_project.py / 대상: 공고 1건 = 프로젝트 1개

## 프로젝트명 규칙

- 형식: `<연도>-<공고약칭>` 권장 (예: `2026-digital-sme`). 영문 소문자·숫자·하이픈만 허용, 그 외 문자는 하이픈으로 치환.
- 예약어 금지: `mvp_test_01` (샘플 전용), `sample*`
- 동일 이름 존재 시: 덮어쓰지 않고 에러 종료 (기존 프로젝트 보호)

## 자동 생성되는 폴더·파일

```
01_inputs/<project>/input.json      ← input_schema.json 기반 빈 템플릿 (없는 값은 "미확보")
04_outputs/<project>/project.json   ← 상태 파일 (전 단계 PENDING)
04_outputs/<project>/               ← 산출물 폴더
05_reviews/<project>/               ← 검수 폴더
```

- `06_locks/LOCK_STATUS.md`에는 자동 기입하지 않는다 — LOCK 기록은 사람/AI 세션이 검수 후 수동으로 (자동 LOCK 금지 원칙)
- `--sample` 플래그로 생성 시 project.json에 `is_sample: true` → 전 단계 LOCKED 전환 영구 차단 (D-006)

## 생성 직후 안내 (CLI 출력)

1. `01_inputs/<project>/input.json`을 채워라 — 특히 notice.raw_text, notice.exclusions
2. 값이 없으면 비우지 말고 `"미확보"`로 — 공장이 [확인 필요]로 추적한다
3. 다음 명령: `python 08_factory_tools/run_factory.py <project> --step all`

## input.md 병행 지원

- 텍스트로 작업하고 싶으면 `01_inputs/input_form.md` 양식을 `01_inputs/<project>/input.md`로 채워도 된다.
- v1 CLI는 input.json만 파싱한다. input.md → input.json 변환은 AI 세션이 담당 (TODO_CLI.md #3).

<!-- ok -->
