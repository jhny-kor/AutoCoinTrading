"""
수정 요약
- 업비트 private 웹소켓 연결에 필요한 JWT 토큰과 Authorization 헤더 생성 helper 를 추가했다.
"""

from __future__ import annotations

import uuid

import jwt


def build_upbit_private_jwt(access_key: str, secret_key: str) -> str:
    """업비트 private 웹소켓 연결용 JWT 토큰을 만든다."""
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def build_upbit_private_ws_headers(access_key: str, secret_key: str) -> list[str]:
    """업비트 private 웹소켓 연결용 헤더 목록을 만든다."""
    token = build_upbit_private_jwt(access_key, secret_key)
    return [f"Authorization: Bearer {token}"]
