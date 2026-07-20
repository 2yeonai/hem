"""notify_hemi.py — 혜미 폰으로 승인 요청/알림 푸시 보내기 (ntfy 방식, 토큰 불필요)

사용법:
  python notify_hemi.py "제목" "내용"
  python notify_hemi.py "승인 요청" "방역 완료보고서 1건 검수 대기 중입니다"

동작 조건: 혜미 폰에 ntfy 앱 설치 + 아래 TOPIC 구독 (1회, 카톡_알림봇_방법조사.md A-① 참고)
주의: 이 채널로는 승인 '요청'만 보낸다. 실제 승인/발송은 항상 혜미가 한다(company_charter).
     비밀번호·고객 개인정보·금액 상세는 절대 푸시에 넣지 않는다(제목+한 줄 안내만).
"""
import sys
import urllib.request

TOPIC = "hemi-moon-approve-x7k3q9"  # 혜미 폰 ntfy 앱에서 이 이름 그대로 구독
URL = f"https://ntfy.sh/{TOPIC}"


def send(title: str, message: str) -> int:
    req = urllib.request.Request(
        URL,
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8").decode("latin-1"), "Priority": "high", "Tags": "bell"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"[OK] 푸시 발송됨 (HTTP {r.status}) → {URL}")
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    sys.exit(send(sys.argv[1], sys.argv[2]))
