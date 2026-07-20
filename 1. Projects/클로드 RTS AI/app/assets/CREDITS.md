---
type: project
status: in-progress
due: 2026-07-31
area: 클로드 RTS AI
tags: [priority/medium]
---

# 3D 근육 자산 출처 표시 (라이선스 준수 필수)

`muscles.glb`는 아래 소스에서 파생됐습니다. 앱을 배포(무료/유료 불문)할 때 반드시 아래 크레딧을 화면 어딘가(예: 정보/설정 화면, 앱 하단)에 표시해야 합니다.

## 출처
- **Z-Anatomy** — https://www.z-anatomy.com/ / https://github.com/Z-Anatomy/Models-of-human-anatomy — CC BY-SA 4.0
- 원본 모델: **BodyParts3D** — The Database Center for Life Science — CC-BY-SA 2.1 Japan (https://lifesciencedb.jp/bp3d/)

## 표시 문구(권장, 그대로 사용 가능)
> 3D 근육 모델: "Z-Anatomy - The libre 3D atlas of anatomy" (CC BY-SA 4.0), 원본 "BodyParts3D - The Database Center for Life Science" (CC-BY-SA 2.1 Japan) 기반.

## 라이선스 조건 요약 (CC BY-SA 4.0)
- **자유롭게 사용/재배포/수정 가능** — 상업적 이용 포함.
- **조건 1 (출처 표시, Attribution)**: 위 문구를 앱 어딘가에 표시.
- **조건 2 (동일조건변경허락, ShareAlike)**: 이 3D 모델 파일(`muscles.glb`) 자체 또는 이를 수정한 파생 3D 데이터를 재배포할 경우 동일한 CC BY-SA 라이선스로 배포해야 함. **이 의무는 3D 모델 데이터에만 적용되고, 앱의 나머지 코드(JS/HTML/카드 콘텐츠)에는 전염되지 않는다는 것이 일반적인 실무 해석입니다**(유사 사례: BodyExplorer 프로젝트가 모델=CC BY-SA 4.0, 코드=MIT로 명시적으로 분리 — [[Z-Anatomy_자산조사_2026-07-19]] 참고).
- 유료 판매 계획이 확정되면, 이 조건이 실제 사업 형태에 문제없는지 한 번 더 확인 권장(법률 자문까지는 아니어도 라이선스 원문 재확인).

## 처리 이력 (2026-07-19, [hyemi])
- 원본 `Startup.blend`(307MB, Z-Anatomy 전신 데이터)에서 프로젝트에 필요한 근육 61종(182개 메시, 좌우 포함)만 선별.
- Blender 헤드리스 스크립트(`scripts/blender_export_muscles.py`)로 Decimate(20%) 적용 후 glTF(.glb)로 추출 — 459,713 verts → 91,836 verts, 최종 파일 크기 약 3.9MB.
- 매핑표: `muscle_object_mapping.json` — `app/muscle_map.json`의 `z_anatomy` 키(카드 61장 기준) ↔ 이 glb 안의 실제 오브젝트 이름(`Gluteus maximus muscle.l` 등) 대응표.

<!-- ok -->
