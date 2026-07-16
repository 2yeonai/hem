#!/usr/bin/env python3
"""새 공고 프로젝트 스캐폴딩 생성기.

사용법:
    python 08_factory_tools/create_project.py <프로젝트명> [--sample]

규칙: project_generator_spec.md
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # hyemi-ai-factory/

RESERVED = ("mvp_test_01", "sample")

INPUT_TEMPLATE = {
    "project_name": "",
    "created_at": "",
    "notice": {
        "title": "미확보",
        "agency": "미확보",
        "purpose": "미확보",
        "raw_text": "미확보",
        "apply_deadline": "미확보",
        "execution_period": "미확보",
        "eligibility": "미확보",
        "exclusions": "미확보",
        "budget": {
            "max_amount": "미확보",
            "self_pay_ratio": "미확보",
            "allowed_items": [],
            "excluded_items": [],
        },
        "format": {"form_type": "미확보", "page_limit": "미확보", "char_limit": "미확보"},
        "scoring": [],
        "presentation": {"required": "미확보", "present_minutes": "미확보", "qna_minutes": "미확보"},
        "bonus_items": [],
    },
    "applicant": {
        "name": "미확보",
        "biz_type": "미확보",
        "biz_years": "미확보",
        "industry": "미확보",
        "industry_code": "미확보",
        "channels": [],
        "duplicate_grant_history": "미확인",
        "tax_arrears": "미확인",
        "closed_biz_history": "미확인",
        "notes": "",
    },
    "ideas": [
        {
            "id": "idea1",
            "name": "",
            "problem": "",
            "target": "",
            "outputs": [],
            "budget_estimate": "미확보",
            "evidence_owned": [],
            "evidence_planned": [],
            "risks": [],
        }
    ],
    "evidence": {"owned": [], "planned": []},
    "budget_plan": [],
    "selected_idea_id": None,
    "approvals": {
        "eligibility_confirmed": False,
        "idea_selected": False,
        "budget_confirmed": False,
        "final_submission_approved": False,
    },
}

STAGES = ["notice", "risk", "ideas", "lock", "review", "revision", "handoff"]


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9가-힣-]+", "-", name.strip().lower()).strip("-")
    return slug or "project"


def main() -> int:
    ap = argparse.ArgumentParser(description="새 공고 프로젝트 생성")
    ap.add_argument("name", help="프로젝트명 (영문 소문자·숫자·하이픈 권장)")
    ap.add_argument("--sample", action="store_true", help="샘플 프로젝트 (LOCKED 전환 영구 차단)")
    args = ap.parse_args()

    project = slugify(args.name)
    if any(project.startswith(r) for r in RESERVED) and not args.sample:
        print(f"[FATAL] '{project}'는 예약어입니다 (샘플 전용 이름). 다른 이름을 쓰세요.")
        return 2

    input_dir = BASE / "01_inputs" / project
    output_dir = BASE / "04_outputs" / project
    review_dir = BASE / "05_reviews" / project

    if (input_dir / "input.json").exists() or (output_dir / "project.json").exists():
        print(f"[FATAL] 프로젝트 '{project}'가 이미 존재합니다. 기존 프로젝트는 덮어쓰지 않습니다.")
        return 2

    for d in (input_dir, output_dir, review_dir):
        d.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    tpl = json.loads(json.dumps(INPUT_TEMPLATE, ensure_ascii=False))
    tpl["project_name"] = project
    tpl["created_at"] = today
    (input_dir / "input.json").write_text(
        json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    state = {
        "project_name": project,
        "created_at": today,
        "updated_at": today,
        "is_sample": bool(args.sample),
        "stages": {s: "PENDING" for s in STAGES},
        "warnings": [],
        "blockers": [],
        "needs_confirmation": [],
    }
    (output_dir / "project.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[OK] 프로젝트 생성: {project}" + (" (샘플 모드)" if args.sample else ""))
    print(f"  1. 입력 채우기 : 01_inputs/{project}/input.json")
    print("     - 특히 notice.raw_text(공고 원문)와 notice.exclusions(지원제외 조항)")
    print('     - 없는 값은 비우지 말고 "미확보"/"미확인" 유지 → 공장이 [확인 필요]로 추적')
    print(f"  2. 실행       : python 08_factory_tools/run_factory.py {project} --step all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
