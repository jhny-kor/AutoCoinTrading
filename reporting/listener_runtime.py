from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from bot_logger import BotLogger
from reporting.telegram_notifier import format_telegram_request_error
from strategy_settings import load_managed_symbols

WEEKDAY_NAME_TO_INDEX = {
    "MON": 0,
    "TUE": 1,
    "WED": 2,
    "THU": 3,
    "FRI": 4,
    "SAT": 5,
    "SUN": 6,
}


@dataclass(frozen=True)
class ListenerSettings:
    """텔레그램 명령 리스너 설정."""

    poll_interval_sec: int
    offset_path: Path
    report_state_path: Path
    analysis_log_dir: Path
    okx_symbols: list[str]
    upbit_symbols: list[str]
    recent_log_line_count: int
    daily_report_enabled: bool
    morning_report_hour: int
    noon_report_hour: int
    evening_report_hour: int
    night_report_hour: int
    weekly_report_enabled: bool
    weekly_report_weekday: int
    weekly_report_hour: int


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_listener_settings() -> ListenerSettings:
    """환경 변수에서 리스너 설정을 읽는다."""
    load_dotenv()

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    return ListenerSettings(
        poll_interval_sec=int(os.getenv("TELEGRAM_COMMAND_POLL_INTERVAL_SEC", "5")),
        offset_path=log_dir / "telegram_command_listener.offset",
        report_state_path=log_dir / "telegram_daily_report_state.json",
        analysis_log_dir=Path(os.getenv("ANALYSIS_LOG_DIR", "analysis_logs")),
        okx_symbols=load_managed_symbols("okx"),
        upbit_symbols=load_managed_symbols("upbit"),
        recent_log_line_count=int(os.getenv("TELEGRAM_RECENT_LOG_LINE_COUNT", "5")),
        daily_report_enabled=parse_bool(
            os.getenv("TELEGRAM_DAILY_REPORT_ENABLED", "true"),
            default=True,
        ),
        morning_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_MORNING_HOUR", "8")),
        noon_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_NOON_HOUR", "12")),
        evening_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_EVENING_HOUR", "18")),
        night_report_hour=int(os.getenv("TELEGRAM_DAILY_REPORT_NIGHT_HOUR", "21")),
        weekly_report_enabled=parse_bool(
            os.getenv("TELEGRAM_WEEKLY_REPORT_ENABLED", "true"),
            default=True,
        ),
        weekly_report_weekday=WEEKDAY_NAME_TO_INDEX.get(
            os.getenv("TELEGRAM_WEEKLY_REPORT_WEEKDAY", "MON").strip().upper(),
            0,
        ),
        weekly_report_hour=int(os.getenv("TELEGRAM_WEEKLY_REPORT_HOUR", "9")),
    )


def telegram_api_request(
    bot_token: str,
    method: str,
    payload: dict | None = None,
    timeout: int = 30,
) -> tuple[dict | None, str | None]:
    """텔레그램 Bot API 를 호출한다."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        return None, format_telegram_request_error(exc)

    try:
        result = json.loads(raw_body)
    except (ValueError, json.JSONDecodeError) as exc:
        return None, format_telegram_request_error(exc)

    if isinstance(result, dict) and result.get("ok") is False:
        description = result.get("description")
        if isinstance(description, str) and description.strip():
            return None, description.strip()
        return None, "텔레그램 API 가 요청을 거부했습니다."

    return result, None


def get_updates(
    bot_token: str,
    offset: int,
    timeout: int = 20,
) -> tuple[list[dict], str | None]:
    """새 텔레그램 업데이트 목록을 가져온다."""
    query = urllib.parse.urlencode({"offset": offset, "timeout": timeout})
    result, error = telegram_api_request(
        bot_token,
        f"getUpdates?{query}",
        payload=None,
        timeout=timeout + 5,
    )
    if error:
        return [], error
    if not result:
        return [], "텔레그램 업데이트 응답이 비어 있습니다."
    return result.get("result", []), None


def load_offset(path: Path) -> int:
    """마지막으로 처리한 update offset 을 읽는다."""
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def save_offset(path: Path, offset: int) -> None:
    """마지막으로 처리한 update offset 을 저장한다."""
    path.write_text(str(offset), encoding="utf-8")


def initialize_offset_if_needed(
    bot_token: str,
    settings: ListenerSettings,
    logger: BotLogger,
) -> int:
    """초기 실행 시 과거 메시지를 건너뛰도록 offset 을 맞춘다."""
    current_offset = load_offset(settings.offset_path)
    if current_offset > 0:
        return current_offset

    updates, error = get_updates(bot_token, offset=0, timeout=0)
    if error:
        logger.log(f"초기 텔레그램 offset 조회 실패: {error}")
        return 0
    if not updates:
        return 0

    next_offset = max(update["update_id"] for update in updates) + 1
    save_offset(settings.offset_path, next_offset)
    logger.log(
        f"기존 텔레그램 메시지 {len(updates)}건은 재처리하지 않도록 offset 을 {next_offset} 으로 맞췄습니다."
    )
    return next_offset


def load_report_state(path: Path) -> dict[str, str]:
    """일일 리포트 전송 상태를 읽는다."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}


def save_report_state(path: Path, state: dict[str, str]) -> None:
    """일일 리포트 전송 상태를 저장한다."""
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

