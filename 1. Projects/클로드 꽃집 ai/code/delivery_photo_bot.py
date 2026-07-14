"""
delivery_photo_bot.py — 배송사진봇 (12봇_kind분류표.yaml의 delivery_photo_bot 실제 구현)

역할: 배송 완료 증빙사진 촬영 흐름(촬영→미리보기→재촬영/사용선택)을 기록한다.
실제 카메라 연동(Capacitor Camera 플러그인)은 이 코드 환경에 없으므로, 사진 URI를
인자로 받는 것으로 그 흐름을 대신한다 — 판단 없음(사진이 오면 완료, 안 오면 대기).

12봇_kind분류표.yaml 대응:
  io.reads:  dispatch_record
  io.writes: delivery_photo, photo_status
"""


def capture_delivery_photo(dispatch_record, photo_uri=None):
    """
    공개 API. photo_uri가 있으면 photo_status="완료", 없으면 "대기"로 남긴다
    (사진이 없는데 임의로 완료 처리하지 않음).
    """
    photo_status = "완료" if photo_uri else "대기"
    return {
        "delivery_photo": photo_uri,
        "photo_status": photo_status,
    }
