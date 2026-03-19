"""
텔레그램 알림 유틸

- 오류 알림에 인시던트 ID 와 승인형 버튼(재기동/상세/수정 요청/무시)을 함께 보낼 수 있도록 확장했다.
- 날짜 표기는 유지하고, 그 밖의 숫자는 텔레그램 전송 직전에 세 자리마다 쉼표가 들어가도록 공통 포맷을 적용했다.
- .env 설정이 있으면 텔레그램으로 메시지를 전송한다.
- 설정이 없거나 비활성화되어 있으면 조용히 아무 동작도 하지 않는다.
- 봇 체결, 손절, 에러 같은 이벤트 알림에 사용한다.
- 텔레그램 전송 실패 원인을 timeout, HTTP 권한 오류 기준으로 진단할 수 있게 개선했다.
- 일반 운영 알림과 수동 확인 요청도 같은 모듈에서 즉시 전송할 수 있게 확장했다.
- 단독 실행 시 임의 메시지나 확인 요청 메시지를 CLI 로 보낼 수 있다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv
from incident_manager import register_incident

NUMERIC_TOKEN_RE = re.compile(r"(?<![\w/:\-,])(-?\d+(?:\.\d+)?)(?![\w/:\-,])")


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
        if isinstance(reason, TimeoutError):
            return "요청 시간이 초과되었습니다."
        return f"네트워크 오류: {reason}"

    if isinstance(exc, TimeoutError):
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
    if "." in raw:
        whole, fraction = raw.split(".", 1)
        if not whole:
            whole = "0"
        return f"{sign}{int(whole):,}.{fraction}"
    return f"{sign}{int(raw):,}"


def format_telegram_text_numbers(text: str) -> str:
    """날짜/시간 표현을 제외한 숫자에 세 자리 쉼표를 적용한다."""
    return NUMERIC_TOKEN_RE.sub(
        lambda match: format_numeric_token(match.group(1)),
        text,
    )


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


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
        return self.send_message(f"[{exchange_name}] {symbol} 매수 체결\n{detail}")

    def notify_sell_fill(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """익절 매도 체결 알림을 보낸다."""
        if not self.enable_sell_notification:
            return False
        return self.send_message(f"[{exchange_name}] {symbol} 매도 체결\n{detail}")

    def notify_stop_loss_fill(
        self, exchange_name: str, symbol: str, detail: str
    ) -> bool:
        """손절 매도 체결 알림을 보낸다."""
        if not self.enable_stop_loss_notification:
            return False
        return self.send_message(f"[{exchange_name}] {symbol} 손절 발생\n{detail}")

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
        )
        text = (
            f"[{exchange_name}] {symbol} 에러 발생\n"
            f"인시던트 ID: {incident['id']}\n"
            f"반복 횟수: {incident['count']}\n"
            f"{detail}"
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
    load_dotenv()

    return TelegramNotifier(
        enabled=parse_bool(os.getenv("TELEGRAM_ENABLED", "false"), default=False),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        enable_buy_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_BUY", "true"), default=True
        ),
        enable_sell_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_SELL", "true"), default=True
        ),
        enable_stop_loss_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_STOP_LOSS", "true"), default=True
        ),
        enable_error_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_ERROR", "true"), default=True
        ),
        enable_daily_limit_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_DAILY_LIMIT", "true"), default=True
        ),
        enable_attention_notification=parse_bool(
            os.getenv("TELEGRAM_NOTIFY_ATTENTION", "true"), default=True
        ),
        enable_error_action_buttons=parse_bool(
            os.getenv("TELEGRAM_ENABLE_ERROR_ACTION_BUTTONS", "true"), default=True
        ),
    )


if __name__ == "__main__":
    sys.exit(main())
