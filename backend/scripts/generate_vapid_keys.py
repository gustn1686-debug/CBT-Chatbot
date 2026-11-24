"""웹 푸시(상담 시간 알림)용 VAPID 키를 만든다.

    python scripts/generate_vapid_keys.py

출력된 두 줄을 레포 루트의 .env 에 붙여 넣는다. 개인키는 비밀이다 (저장소·채팅에 올리지 않는다).
키를 바꾸면 이미 알림을 켠 기기는 앱에서 알림을 다시 켜야 한다.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate() -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return _b64url(public), _b64url(private)


if __name__ == "__main__":
    public_key, private_key = generate()
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
