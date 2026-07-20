#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_muscle_map.py — 2단계: 카드 근육 ↔ (마네킹 부위 + Z-Anatomy 메시명) 매핑표 생성.

- mesh: 3D 뷰어 마네킹의 세그먼트 키(하이라이트 대상). 뷰어가 이 키로 해당 부위 메시를 강조.
- z_anatomy: Z-Anatomy/BodyParts3D 가 쓰는 표준 해부학명(향후 실제 glTF 메시 매칭용 조회 키).
  ⚠️ 실제 .blend/glTF 오브젝트명(예: 'Soleus.l'/'Soleus.r')은 내려받아 대조하지 않았으므로,
     여기 표준명은 '조회 키'이며 export 별 접미사 차이는 3단계 자산연동 때 확정해야 함.
- z_status: direct(단일 근육 메시) / group(여러 메시 묶음) / joint(근육 아닌 관절낭·인대).

지어내지 않음: 근거가 애매한 부위는 note에 명시하고 mesh는 가장 가까운 세그먼트로.
"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\82106\Desktop\hem\1. Projects\클로드 RTS AI")
DATA_PATH = ROOT / "app" / "data.json"
OUT_PATH = ROOT / "app" / "muscle_map.json"

# 마네킹 세그먼트 키(뷰어와 공유): head, neck, torsoUpper, torsoLower, pelvis,
#   upperArm, foreArm, hand, thigh, shin, foot  (좌우는 뷰어가 side로 확장)
# 각 항목: (mesh, face, region_ko, z_anatomy, z_status)
MAP = {
    # ---- 목 ----
    "technique-20-DNF": (["neck"], "front", "목 앞 심부(경추 앞)",
        "Longus colli / Longus capitis / Rectus capitis anterior & lateralis", "group"),
    "technique-13-사각근": (["neck"], "side", "목 옆(경추 측면)", "Scalenus (anterior/medius/posterior)", "group"),
    "technique-16-흉쇄유돌근": (["neck"], "front", "목 앞(빗장~귀뒤)", "Sternocleidomastoid", "direct"),
    "technique-17-판상근": (["neck"], "back", "목 뒤(척추~머리)", "Splenius capitis / Splenius cervicis", "group"),
    "technique-18-후두하근": (["head"], "back", "뒤통수 밑(상부경추)", "Suboccipital group (rectus capitis post. major/minor, obliquus capitis sup./inf.)", "group"),
    "technique-19-이복근": (["neck"], "front", "턱 아래(설골 위)", "Digastric", "direct"),
    # ---- 어깨·견갑 ----
    "technique-03-견갑거근": (["neck", "torsoUpper"], "back", "목~어깨뼈 위각", "Levator scapulae", "direct"),
    "technique-02-능형근": (["torsoUpper"], "back", "척추~어깨뼈 안쪽", "Rhomboid major / minor", "group"),
    "technique-08-상부승모근": (["neck", "torsoUpper"], "back", "목~어깨 위", "Trapezius (descending/upper)", "direct"),
    "technique-21-중부승모근": (["torsoUpper"], "back", "어깨뼈 사이(중간)", "Trapezius (transverse/middle)", "direct"),
    "technique-10-하부승모근": (["torsoUpper"], "back", "등 중간(아래 등세모)", "Trapezius (ascending/lower)", "direct"),
    "technique-09-전거근": (["torsoUpper"], "side", "옆구리 갈비~어깨뼈", "Serratus anterior", "direct"),
    "technique-12-극상근": (["torsoUpper"], "back", "어깨뼈 가시 위", "Supraspinatus", "direct"),
    "technique-14-극하근": (["torsoUpper"], "back", "어깨뼈 가시 아래", "Infraspinatus", "direct"),
    "technique-15-소원근": (["torsoUpper"], "back", "어깨뼈 가쪽(작은원근)", "Teres minor", "direct"),
    "technique-07-대원근": (["torsoUpper"], "back", "어깨뼈 아래각(큰원근)", "Teres major", "direct"),
    "technique-06-견갑하근": (["torsoUpper"], "front", "어깨뼈 앞면(심부)", "Subscapularis", "direct"),
    "technique-04-광배근": (["torsoUpper", "torsoLower"], "back", "넓은 등~허리", "Latissimus dorsi", "direct"),
    "technique-05-GH전방관절낭": (["torsoUpper"], "front", "어깨 앞 관절주머니", "Glenohumeral joint capsule (anterior)", "joint"),
    "technique-11-GH후방관절낭": (["torsoUpper"], "back", "어깨 뒤 관절주머니", "Glenohumeral joint capsule (posterior)", "joint"),
    # ---- 가슴 ----
    "technique-61-대흉근": (["torsoUpper"], "front", "앞가슴(큰가슴근)", "Pectoralis major", "direct"),
    "technique-01-소흉근": (["torsoUpper"], "front", "앞가슴 심부(작은가슴근)", "Pectoralis minor", "direct"),
    # ---- 몸통·코어 ----
    "technique-22-복직근": (["torsoLower"], "front", "배 앞(식스팩)", "Rectus abdominis", "direct"),
    "technique-24-외복사근": (["torsoLower"], "side", "옆구리 겉(배바깥빗근)", "Obliquus externus abdominis", "direct"),
    "technique-23-내복사근": (["torsoLower"], "side", "옆구리 속(배속빗근)", "Obliquus internus abdominis", "direct"),
    "technique-25-복횡근": (["torsoLower"], "front", "배 가로(심부 코어)", "Transversus abdominis", "direct"),
    "technique-28-척추기립근": (["torsoLower", "torsoUpper"], "back", "척추 양옆 세로근", "Erector spinae (iliocostalis/longissimus/spinalis)", "group"),
    "technique-26-다열근": (["torsoLower"], "back", "척추 심부 안정근", "Multifidus", "direct"),
    "technique-27-요방형근": (["torsoLower"], "back", "허리 네모근(옆허리)", "Quadratus lumborum", "direct"),
    "technique-30-장요근": (["torsoLower", "pelvis"], "front", "허리~골반 앞 심부", "Psoas major / Iliacus (iliopsoas)", "group"),
    "technique-31-횡격막": (["torsoLower"], "front", "가슴~배 경계(호흡근)", "Diaphragm (thoracic)", "direct"),
    "technique-29-골반기저근": (["pelvis"], "front", "골반 바닥", "Pelvic floor (levator ani / coccygeus)", "group"),
    # ---- 엉덩이·고관절 ----
    "technique-32-대둔근": (["pelvis"], "back", "엉덩이 큰 근육", "Gluteus maximus", "direct"),
    "technique-33-중둔근": (["pelvis"], "side", "엉덩이 옆(중간볼기)", "Gluteus medius", "direct"),
    "technique-34-소둔근": (["pelvis"], "side", "엉덩이 옆 심부(작은볼기)", "Gluteus minimus", "direct"),
    "technique-36-이상근": (["pelvis"], "back", "엉덩이 심부(궁둥구멍근)", "Piriformis", "direct"),
    "technique-37-심부외회전근군": (["pelvis"], "back", "엉덩이 심부 외회전근(이상근 제외 4종)",
        "Deep lateral rotators (gemellus sup./inf., obturator int./ext., quadratus femoris)", "group"),
    "technique-35-대퇴근막장근": (["pelvis", "thigh"], "side", "골반 앞옆(TFL)", "Tensor fasciae latae", "direct"),
    # ---- 허벅지 앞(대퇴사두·봉공) ----
    "technique-48-내측광근": (["thigh"], "front", "허벅지 앞 안쪽(VM/VMO)", "Vastus medialis", "direct"),
    "technique-47-외측광근": (["thigh"], "front", "허벅지 앞 가쪽(VL)", "Vastus lateralis", "direct"),
    "technique-49-중간광근": (["thigh"], "front", "허벅지 앞 심부(VI)", "Vastus intermedius", "direct"),
    "technique-41-봉공근": (["thigh"], "front", "허벅지 앞 사선(재봉근)", "Sartorius", "direct"),
    # ---- 허벅지 안쪽(내전근) ----
    "technique-44-장내전근": (["thigh"], "inner", "허벅지 안쪽(긴모음근)", "Adductor longus", "direct"),
    "technique-45-단내전근": (["thigh"], "inner", "허벅지 안쪽(짧은모음근)", "Adductor brevis", "direct"),
    "technique-46-대내전근": (["thigh"], "inner", "허벅지 안쪽(큰모음근)", "Adductor magnus", "direct"),
    "technique-42-박근": (["thigh"], "inner", "허벅지 안쪽 얇은근(두덩정강근)", "Gracilis", "direct"),
    "technique-43-치골근": (["thigh"], "inner", "샅~허벅지 안쪽(두덩근)", "Pectineus", "direct"),
    # ---- 허벅지 뒤(햄스트링) ----
    "technique-38-대퇴이두근": (["thigh"], "back", "허벅지 뒤 가쪽(넙다리두갈래)", "Biceps femoris (long/short head)", "direct"),
    "technique-39-반건양근": (["thigh"], "back", "허벅지 뒤 안쪽(반힘줄)", "Semitendinosus", "direct"),
    "technique-40-반막양근": (["thigh"], "back", "허벅지 뒤 안쪽 심부(반막)", "Semimembranosus", "direct"),
    "technique-50-슬와근": (["shin"], "back", "무릎 뒤(오금근)", "Popliteus", "direct"),
    # ---- 종아리·발목 ----
    "technique-51-비복근": (["shin"], "back", "종아리 겉(장딴지근)", "Gastrocnemius", "direct"),
    "technique-52-가자미근": (["shin"], "back", "종아리 심부(넙치근)", "Soleus", "direct"),
    "technique-54-후경골근": (["shin"], "back", "정강 뒤 심부(뒤정강근)", "Tibialis posterior", "direct"),
    "technique-57-장무지굴근": (["shin", "foot"], "back", "정강 뒤~엄지(긴엄지굽힘)", "Flexor hallucis longus", "direct"),
    "technique-58-장지굴근": (["shin", "foot"], "back", "정강 뒤~발가락(긴발가락굽힘)", "Flexor digitorum longus", "direct"),
    "technique-53-전경골근": (["shin"], "front", "정강 앞(앞정강근)", "Tibialis anterior", "direct"),
    "technique-59-장무지신근": (["shin", "foot"], "front", "정강 앞~엄지(긴엄지폄)", "Extensor hallucis longus", "direct"),
    "technique-60-장지신근": (["shin", "foot"], "front", "정강 앞~발가락(긴발가락폄)", "Extensor digitorum longus", "direct"),
    "technique-55-장비골근": (["shin"], "side", "종아리 가쪽(긴종아리근)", "Fibularis (peroneus) longus", "direct"),
    "technique-56-단비골근": (["shin"], "side", "종아리 가쪽(짧은종아리근)", "Fibularis (peroneus) brevis", "direct"),
}


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    ids = [t["id"] for t in data["techniques"]]
    out = {}
    unmapped = []
    for t in data["techniques"]:
        cid = t["id"]
        fm = t["frontmatter"]
        if cid in MAP:
            mesh, face, region_ko, z_anat, z_status = MAP[cid]
            out[cid] = {
                "id": cid,
                "muscle_ko": fm.get("근육명", ""),
                "muscle_en": fm.get("근육명_영문", ""),
                "mesh": mesh,
                "face": face,
                "side": "both",
                "region_ko": region_ko,
                "z_anatomy": z_anat,
                "z_status": z_status,
            }
        else:
            unmapped.append(cid)

    result = {
        "note": "카드 영문 근육명 ↔ 마네킹 부위(mesh) + Z-Anatomy 표준명 매핑. z_anatomy는 조회 키(실제 export 오브젝트명 접미사는 3단계에서 확정).",
        "mannequin_segments": ["head", "neck", "torsoUpper", "torsoLower", "pelvis",
                               "upperArm", "foreArm", "hand", "thigh", "shin", "foot"],
        "counts": {"mapped": len(out), "unmapped": len(unmapped),
                   "by_status": {}},
        "cards": out,
        "unmapped": unmapped,
    }
    st = {}
    for c in out.values():
        st[c["z_status"]] = st.get(c["z_status"], 0) + 1
    result["counts"]["by_status"] = st

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_muscle_map] mapped={len(out)}/{len(ids)} unmapped={len(unmapped)} status={st}")
    if unmapped:
        print("  UNMAPPED:", unmapped)


if __name__ == "__main__":
    main()
