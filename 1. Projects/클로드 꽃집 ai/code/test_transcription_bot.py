"""
test_transcription_bot.py - transcription_bot.py를 golden_set.yaml 텍스트로 검증

실제 오디오/이미지 파일이 이 vault엔 없으므로(알려진 한계), raw_audio/raw_image
자리에 텍스트를 직접 넣어 "이미 텍스트로 들어온 입력을 그대로 통과시키는 목업
STT/OCR" 동작을 검증한다.

실행: python3 test_transcription_bot.py
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import transcription_bot as tb

GOLDEN_SET_PATH = Path(__file__).parent.parent / "golden_set.yaml"

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    extra = "  (" + detail + ")" if detail else ""
    print("[" + status + "] " + label + extra)


def main():
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = {e["id"]: e for e in data["golden_set"]}

    # ---- case 1: raw_audio 목업 경로 — 항등 STT ----
    text_005 = entries["005"]["raw_text_full_call"]
    r1 = tb.transcribe(raw_audio=text_005)
    check("raw_audio가 있으면 stt_text로 그대로 나옴(목업 항등 STT)", r1["stt_text"] == text_005)
    check("raw_audio만 있으면 ocr_text는 None", r1["ocr_text"] is None)
    check(
        "engine_meta에 real_api_connected=False가 명시됨(알려진 한계 숨기지 않음)",
        r1["engine_meta"]["real_api_connected"] is False,
    )

    # ---- case 2: raw_image 목업 경로 — 항등 OCR ----
    r2 = tb.transcribe(raw_image="스크린샷 원문 텍스트 대역")
    check("raw_image가 있으면 ocr_text로 그대로 나옴(목업 항등 OCR)", r2["ocr_text"] == "스크린샷 원문 텍스트 대역")
    check("raw_image만 있으면 stt_text는 None", r2["stt_text"] is None)

    # ---- case 3: raw_text만 있는 sms/kakao 채널 — cleaned_text만 채움 ----
    raw_001 = entries["001"]["raw_variants"][0]["text"]
    r3 = tb.transcribe(raw_text=raw_001)
    check("raw_text만 있으면 stt_text/ocr_text는 둘 다 None", r3["stt_text"] is None and r3["ocr_text"] is None)
    check("cleaned_text는 raw_text 기반으로 채워짐", r3["cleaned_text"] == raw_001)

    # ---- case 4: cleaned_text 최소 정리(연속 공백) 확인 ----
    r4 = tb.transcribe(raw_text="여러   개의    공백   테스트")
    check("cleaned_text는 연속 공백을 하나로 정리(최소 정리, 의미 보정 아님)", r4["cleaned_text"] == "여러 개의 공백 테스트")

    total = len(results)
    passed = sum(1 for r in results if r[0] == PASS)
    print("")
    print(str(passed) + "/" + str(total) + " checks passed")
    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
