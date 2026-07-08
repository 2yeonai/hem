# jbjw

혜미의 AI 작업 공장 저장소.

## Hyemi Grant Factory (정부지원사업 공장 앱)

공고문·신청자 정보·아이디어 후보를 넣으면 공고 분석 → 자격 리스크 → 아이디어 비교 → LOCK 판정 → 심사위원 검수 → 재작업 지시서 → HANDOFF까지 프로젝트별로 생성하는 로컬 앱. Python 3.9+만 있으면 실행된다 (외부 라이브러리·API 키 불필요).

```bash
cd hyemi-ai-factory
python3 08_factory_tools/app.py
# → http://127.0.0.1:8787  (대시보드에서 "샘플 프로젝트 실행" 클릭)
```

- 실행 안내: `hyemi-ai-factory/LOCAL_RUN_GUIDE.md`
- 사용법: `hyemi-ai-factory/APP_USAGE.md`
- 공장 전체 설계·규칙: `hyemi-ai-factory/README.md`, `FACTORY_DESIGN.md`
- 한계 고지(필독): `hyemi-ai-factory/KNOWN_LIMITATIONS.md`

핵심 원칙: 앱은 규칙 기반 예비 판정까지만 한다. **자격·아이디어·예산·제출의 확정은 사람이 하고, 공고 원문 없이는 LOCK되지 않는다.**
