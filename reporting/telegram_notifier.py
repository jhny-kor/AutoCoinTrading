"""
수정 요약
- 2026-05-24: 거래소 API 허용 IP/화이트리스트 오류에는 운영 진단을 붙이고, 같은 인시던트 반복 알림을 dedupe 하도록 보강했다.
- 체결/손절/에러 텔레그램 알림 제목에서 심볼 앞에 초록 원 배지를 붙여 식별성을 높임

텔레그램 알림 유틸

- `config/runtime.toml` + env override / secrets 레이어를 중앙 환경 로더로 읽도록 정리
- typed config access helper 를 사용해 텔레그램 설정 로딩의 문자열 파싱을 일관되게 정리

- `07:40:03`, `01-00:52:55` 같은 실행시간 문자열은 숫자 포맷터가 건드리지 않도록 보호했다.
- 이미 쉼표가 들어간 숫자도 다시 깨지지 않도록 텔레그램 숫자 포맷터를 보정했다.
- 텔레그램 전송 실패 시 DNS 조회 실패, 연결 종료, 네트워크 미도달 같은 원인을 한국어로 더 분명하게 진단하도록 개선했다.
- 날짜를 제외한 텔레그램 숫자 포맷이 %, 초, 개, bp, ms 같은 단위가 붙어도 세 자리 쉼표가 적용되도록 보완했다.
- 오류 알림에 인시던트 ID 와 승인형 버튼(재기동/상세/수정 요청/무시)을 함께 보낼 수 있도록 확장했다.
- 날짜 표기는 유지하고, 그 밖의 숫자는 텔레그램 전송 직전에 세 자리마다 쉼표가 들어가도록 공통 포맷을 적용했다.
- 설정 레이어가 있으면 텔레그램으로 메시지를 전송한다.
- 설정이 없거나 비활성화되어 있으면 조용히 아무 동작도 하지 않는다.
- 봇 체결, 손절, 에러 같은 이벤트 알림에 사용한다.
- 텔레그램 전송 실패 원인을 timeout, HTTP 권한 오류 기준으로 진단할 수 있게 개선했다.
- 일반 운영 알림과 수동 확인 요청도 같은 모듈에서 즉시 전송할 수 있게 확장했다.
- 단독 실행 시 임의 메시지나 확인 요청 메시지를 CLI 로 보낼 수 있다.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from incident_manager import register_incident
from settings.config_access import env_bool, env_int, env_str
from settings.env import load_project_env

PROTECTED_DATETIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2})?)?"
)
PROTECTED_ELAPSED_TIME_RE = re.compile(r"\b\d+(?:-\d{1,2})?:\d{2}:\d{2}\b")
NUMERIC_TOKEN_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def extract_telegram_api_error_detail(body: bytes) -> str | None:
    """텔레그램 API 응답 본문에서 설명 문자열을 추출한다."""
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    description = payload.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def format_telegram_request_error(exc: Exception) -> str:
    """텔레그램 요청 예외를 사람이 읽기 쉬운 문장으로 바꾼다."""
    if isinstance(exc, urllib.error.HTTPError):
        detail = extract_telegram_api_error_detail(exc.read())
        status = f"HTTP {exc.code}"
        if exc.reason:
            status = f"{status} {exc.reason}"
        return f"{status}: {detail}" if detail else status

    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "요청 시간이 초과되었습니다."
        if isinstance(reason, socket.gaierror):
            return (
                "DNS 조회 실패: api.telegram.org 주소를 찾지 못했습니다. "
                f"네트워크 또는 DNS 설정을 확인하세요. ({reason})"
            )
        if isinstance(reason, ConnectionResetError):
            return f"연결이 전송 중 끊어졌습니다. ({reason})"
        if isinstance(reason, ConnectionRefusedError):
            return f"원격 서버가 연결을 거부했습니다. ({reason})"
        if isinstance(reason, OSError):
            if reason.errno == errno.ENETUNREACH:
                return f"네트워크에 연결할 수 없습니다. ({reason})"
            if reason.errno == errno.EHOSTUNREACH:
                return f"대상 호스트에 도달할 수 없습니다. ({reason})"
            if reason.errno == errno.ECONNRESET:
                return f"연결이 전송 중 끊어졌습니다. ({reason})"
        return f"네트워크 오류: {reason}"

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "요청 시간이 초과되었습니다."

    if isinstance(exc, ValueError):
        return f"응답 해석 실패: {exc}"

    return repr(exc)


def format_numeric_token(token: str) -> str:
    """숫자 토큰에 세 자리 쉼표를 넣되 소수점 자릿수는 유지한다."""
    if not token:
        return token
    sign = ""
    raw = token
    if raw.startswith("-"):
        sign = "-"
        raw = raw[1:]
    raw = raw.replace(",", "")
    if "." in raw:
        whole, fraction = raw.split(".", 1)
        if not whole:
            whole = "0"
        return f"{sign}{int(whole):,}.{fraction}"
    return f"{sign}{int(raw):,}"


def format_telegram_text_numbers(text: str) -> str:
    """날짜/시간 표현을 제외한 숫자에 세 자리 쉼표를 적용한다."""
    protected_tokens: list[str] = []

    def protect_token(match: re.Match[str]) -> str:
        protected_tokens.append(match.group(0))
        return f"__TEXT_TOKEN_{len(protected_tokens) - 1}__"

    masked_text = PROTECTED_DATETIME_RE.sub(protect_token, text)
    masked_text = PROTECTED_ELAPSED_TIME_RE.sub(protect_token, masked_text)

    def replace_number(match: re.Match[str]) -> str:
        token = match.group(0)
        start, end = match.span()
        prev_char = masked_text[start - 1] if start > 0 else ""
        next_char = masked_text[end] if end < len(masked_text) else ""

        # incident id, placeholder, code-like token 안의 숫자는 그대로 둔다.
        if prev_char == "_" or next_char == "_":
            return token
        if prev_char.isalpha() and next_char.isalpha():
            return token
        return format_numeric_token(token)

    formatted = NUMERIC_TOKEN_RE.sub(replace_number, masked_text)
    for index, protected in enumerate(protected_tokens):
        formatted = formatted.replace(f"__TEXT_TOKEN_{index}__", protected)
    return formatted


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def format_symbol_badge(symbol: str) -> str:
    """텔레그램 메시지에서 심볼 앞에 초록 원을 붙인다."""
    cleaned = symbol.strip()
    return f"🟢 {cleaned}" if cleaned else "🟢"


def classify_exchange_error_hint(detail: str) -> str | None:
    """거래소 오류 상세에서 운영자가 바로 조치할 수 있는 진단 힌트를 만든다."""
    lowered = detail.lower()
    if "no_authorization_ip" in lowered or "this is not a verified ip" in lowered:
        return (
            "현재 서버의 공인 IP가 업비트 Open API 키 허용 IP에 없습니다. "
            "Oracle Cloud 인스턴스의 예약/공인 IP를 확인해 업비트 API 키 허용 IP에 등록하세요."
        )
    if "not included in your api key" in lowered and "ip whitelist" in lowered:
        return (
            "현재 서버의 공인 IP가 OKX API 키 IP whitelist 에 없습니다. "
            "오류 메시지의 IP를 OKX API 키 whitelist 에 추가하거나 Oracle Cloud 예약 IP를 고정하세요."
        )
    if "requesttimeout" in lowered or "networkerror" in lowered:
        return (
            "거래소 응답 지연 또는 네트워크 시간초과입니다. 반복되면 Oracle Cloud 네트워크, DNS, "
            "거래소 장애 여부와 API 재시도 설정을 함께 확인하세요."
        )
    return None


@dataclass(frozen=True)
class TelegramNotifier:
    """텔레그램 전송 설정과 유틸 메서드."""

    enabled: bool
    bot_token: str
    chat_id: str
    enable_buy_notification: bool
    enable_sell_notification: bool
    enable_stop_loss_notification: bool
    enable_error_notification: bool
    enable_daily_limit_notification: bool
    enable_attention_notification: bool
    enable_error_action_buttons: bool
    error_dedupe_window_sec: int

    def send_message_detailed(
        self,
        text: str,
        *,
        reply_markup: dict | None = None,
    ) -> tuple[bool, str | None]:
        """텔레그램 메시지를 전송하고 실패 원인을 함께 반환한다."""
        if not self.enabled:
            return False, "텔레그램 알림이 비활성화되어 있습니다."
        if not self.bot_token or not self.chat_id:
            return False, "텔레그램 봇 토큰 또는 chat id 가 비어 있습니다."

        formatted_text = format_telegram_text_numbers(text)
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": formatted_text,
                **({"reply_markup": reply_markup} if reply_markup is not None else {}),
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            url=f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw_body = response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
            return False, format_telegram_request_error(exc)

        try:
            response_payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
            return False, format_telegram_request_error(exc)

        if isinstance(response_payload, dict) and response_payload.get("ok") is False:
            description = response_payload.get("description")
            if isinstance(description, str) and description.strip():
                return False, description.strip()
            return False, "텔레그램 API 가 요청을 거부했습니다."

        return True, None

    def send_message(self, text: str) -> bool:
        """텔레그램 메시지를 전송한다."""
        sent, _ = self.send_message_detailed(text)
        return sent

    def notify_buy_fill(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """매수 체결 알림을 보낸다."""
        if not self.enable_buy_notification:
            return False
        return self.send_message(f"[{exchange_name}] {format_symbol_badge(symbol)} 매수 체결\n{detail}")

    def notify_sell_fill(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """익절 매도 체결 알림을 보낸다."""
        if not self.enable_sell_notification:
            return False
        return self.send_message(f"[{exchange_name}] {format_symbol_badge(symbol)} 매도 체결\n{detail}")

    def notify_stop_loss_fill(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """손절 매도 체결 알림을 보낸다."""
        if not self.enable_stop_loss_notification:
            return False
        return self.send_message(f"[{exchange_name}] {format_symbol_badge(symbol)} 손절 발생\n{detail}")

    def notify_error_message(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """에러 알림을 보낸다."""
        if not self.enable_error_notification:
            return False
        incident = register_incident(
            exchange_name=exchange_name,
            symbol=symbol,
            detail=detail,
            dedupe_window_sec=self.error_dedupe_window_sec,
        )
        if incident.get("status") == "ignored" or int(incident.get("count", 1)) > 1:
            return False

        hint = classify_exchange_error_hint(detail)
        display_detail = f"{detail}\n진단: {hint}" if hint else detail
        text = (
            f"[{exchange_name}] {format_symbol_badge(symbol)} 에러 발생\n"
            f"인시던트 ID: {incident['id']}\n"
            f"반복 횟수: {incident['count']}\n"
            f"{display_detail}"
        )
        reply_markup = None
        if self.enable_error_action_buttons:
            incident_id = incident["id"]
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "재기동", "callback_data": f"inc:restart:{incident_id}"},
                        {"text": "상세 보기", "callback_data": f"inc:detail:{incident_id}"},
                    ],
                    [
                        {"text": "수정 요청", "callback_data": f"inc:fix:{incident_id}"},
                        {"text": "무시", "callback_data": f"inc:ignore:{incident_id}"},
                    ],
                ]
            }
        sent, _ = self.send_message_detailed(text, reply_markup=reply_markup)
        return sent

    def notify_daily_loss_limit(
        self, exchange_name: str, detail: str
    ) -> bool:
        """일일 손실 제한 도달 알림을 보낸다."""
        if not self.enable_daily_limit_notification:
            return False
        return self.send_message(
            f"[{exchange_name}] 일일 손실 제한 도달\n{detail}"
        )

    def notify_attention_required(self, source: str, detail: str) -> bool:
        """수동 확인이나 응답이 필요한 운영 알림을 보낸다."""
        if not self.enable_attention_notification:
            return False
        return self.send_message(f"[{source}] 확인 필요\n{detail}")


def build_parser() -> argparse.ArgumentParser:
    """텔레그램 알림 CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="텔레그램 알림 전송 도구")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--message",
        help="그대로 전송할 일반 메시지",
    )
    group.add_argument(
        "--attention",
        help="즉시 확인이 필요한 운영 메시지 본문",
    )
    parser.add_argument(
        "--source",
        default="운영",
        help="확인 요청 메시지에 붙일 출처 이름",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 에서 텔레그램 메시지를 전송한다."""
    args = build_parser().parse_args(argv)
    notifier = load_telegram_notifier()

    if args.message:
        sent, error = notifier.send_message_detailed(args.message)
    else:
        sent, error = notifier.send_message_detailed(
            f"[{args.source}] 확인 필요\n{args.attention}"
        )

    if sent:
        print("텔레그램 메시지 전송 완료")
        return 0

    print(f"텔레그램 메시지 전송 실패: {error or '알 수 없는 오류'}")
    return 1


def load_telegram_notifier() -> TelegramNotifier:
    """환경 변수에서 텔레그램 설정을 읽는다."""
    load_project_env()

    return TelegramNotifier(
        enabled=env_bool("TELEGRAM_ENABLED", False),
        bot_token=env_str("TELEGRAM_BOT_TOKEN", ""),
        chat_id=env_str("TELEGRAM_CHAT_ID", ""),
        enable_buy_notification=env_bool("TELEGRAM_NOTIFY_BUY", True),
        enable_sell_notification=env_bool("TELEGRAM_NOTIFY_SELL", True),
        enable_stop_loss_notification=env_bool("TELEGRAM_NOTIFY_STOP_LOSS", True),
        enable_error_notification=env_bool("TELEGRAM_NOTIFY_ERROR", True),
        enable_daily_limit_notification=env_bool("TELEGRAM_NOTIFY_DAILY_LIMIT", True),
        enable_attention_notification=env_bool("TELEGRAM_NOTIFY_ATTENTION", True),
        enable_error_action_buttons=env_bool("TELEGRAM_ENABLE_ERROR_ACTION_BUTTONS", True),
        error_dedupe_window_sec=env_int("TELEGRAM_ERROR_DEDUPE_WINDOW_SEC", 3600),
    )


if __name__ == "__main__":
    sys.exit(main())
