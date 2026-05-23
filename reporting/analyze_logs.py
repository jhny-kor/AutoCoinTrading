"""
수정 요약
- 2026-05-24: 텔레그램 리포트가 전체 분석 로그를 읽다 죽지 않도록 최신 날짜/최신 레코드 전용 로더를 추가했다.
- 확장된 분석 로그 필드에 맞춰 거래량 배수, RSI, 스프레드, 캔들 범위 통계를 함께 요약하도록 개선
- 공개 기준 매수 준비 횟수와 대표 스킵 사유를 함께 보여주도록 개선

분석용 로그 요약 도구

- analysis_logs 폴더의 JSONL 파일을 읽어 코인별 특성을 요약한다.
- 거래소/심볼별로 신호 빈도, 평균 이격도, 변동성, MA 위 체류 비율 등을 계산한다.

사용 예시
- .venv/bin/python analyze_logs.py
- .venv/bin/python analyze_logs.py --exchange okx
- .venv/bin/python analyze_logs.py --symbol BTC/USDT
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from log_path_utils import iter_files

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class Summary:
    """심볼별 누적 통계."""

    exchange: str
    symbol: str
    count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    above_ma_count: int = 0
    gap_sum: float = 0.0
    gap_max: float = 0.0
    change_sum: float = 0.0
    abs_change_sum: float = 0.0
    close_sum: float = 0.0
    close_sq_sum: float = 0.0
    volume_ratio_sum: float = 0.0
    volume_ratio_count: int = 0
    volatility_sum: float = 0.0
    volatility_count: int = 0
    rsi_sum: float = 0.0
    rsi_count: int = 0
    spread_pct_sum: float = 0.0
    spread_pct_count: int = 0
    candle_range_sum: float = 0.0
    candle_range_count: int = 0
    public_buy_ready_count: int = 0
    buy_blockers: Counter = field(default_factory=Counter)
    first_time: str | None = None
    last_time: str | None = None

    def add(self, record: dict):
        """레코드 1건을 누적한다."""
        self.count += 1
        self.bullish_count += 1 if record.get("bullish_signal") else 0
        self.bearish_count += 1 if record.get("bearish_signal") else 0
        self.above_ma_count += 1 if record.get("above_ma") else 0

        gap_pct = float(record.get("gap_pct", 0.0))
        close_change_pct = float(record.get("close_change_pct", 0.0))
        close_price = float(record.get("close", 0.0))

        self.gap_sum += gap_pct
        self.gap_max = max(self.gap_max, gap_pct)
        self.change_sum += close_change_pct
        self.abs_change_sum += abs(close_change_pct)
        self.close_sum += close_price
        self.close_sq_sum += close_price * close_price
        self.public_buy_ready_count += 1 if record.get("public_buy_ready") else 0

        volume_ratio = record.get("volume_ratio")
        if volume_ratio is not None:
            self.volume_ratio_sum += float(volume_ratio)
            self.volume_ratio_count += 1

        avg_abs_change_pct = record.get("avg_abs_change_pct")
        if avg_abs_change_pct is not None:
            self.volatility_sum += float(avg_abs_change_pct)
            self.volatility_count += 1

        rsi = record.get("rsi")
        if rsi is not None:
            self.rsi_sum += float(rsi)
            self.rsi_count += 1

        spread_pct = record.get("spread_pct")
        if spread_pct is not None:
            self.spread_pct_sum += float(spread_pct)
            self.spread_pct_count += 1

        candle_range_pct = record.get("candle_range_pct")
        if candle_range_pct is not None:
            self.candle_range_sum += float(candle_range_pct)
            self.candle_range_count += 1

        for blocker in record.get("public_buy_blockers", []) or []:
            self.buy_blockers[str(blocker)] += 1

        collected_at = record.get("collected_at")
        if collected_at is not None:
            if self.first_time is None or collected_at < self.first_time:
                self.first_time = collected_at
            if self.last_time is None or collected_at > self.last_time:
                self.last_time = collected_at

    @property
    def avg_gap_pct(self) -> float:
        return self.gap_sum / self.count if self.count else 0.0

    @property
    def avg_change_pct(self) -> float:
        return self.change_sum / self.count if self.count else 0.0

    @property
    def avg_abs_change_pct(self) -> float:
        return self.abs_change_sum / self.count if self.count else 0.0

    @property
    def above_ma_ratio_pct(self) -> float:
        return (self.above_ma_count / self.count * 100) if self.count else 0.0

    @property
    def bullish_ratio_pct(self) -> float:
        return (self.bullish_count / self.count * 100) if self.count else 0.0

    @property
    def bearish_ratio_pct(self) -> float:
        return (self.bearish_count / self.count * 100) if self.count else 0.0

    @property
    def close_stddev_pct(self) -> float:
        if self.count < 2:
            return 0.0
        mean = self.close_sum / self.count
        variance = (self.close_sq_sum / self.count) - (mean * mean)
        variance = max(variance, 0.0)
        stddev = math.sqrt(variance)
        return (stddev / mean * 100) if mean else 0.0

    @property
    def avg_volume_ratio(self) -> float:
        return self.volume_ratio_sum / self.volume_ratio_count if self.volume_ratio_count else 0.0

    @property
    def avg_volatility_pct(self) -> float:
        return self.volatility_sum / self.volatility_count if self.volatility_count else 0.0

    @property
    def avg_rsi(self) -> float:
        return self.rsi_sum / self.rsi_count if self.rsi_count else 0.0

    @property
    def avg_spread_pct(self) -> float:
        return self.spread_pct_sum / self.spread_pct_count if self.spread_pct_count else 0.0

    @property
    def avg_candle_range_pct(self) -> float:
        return self.candle_range_sum / self.candle_range_count if self.candle_range_count else 0.0

    @property
    def public_buy_ready_ratio_pct(self) -> float:
        return (self.public_buy_ready_count / self.count * 100) if self.count else 0.0

    def top_buy_blockers(self, limit: int = 3) -> str:
        """대표 매수 차단 사유를 문자열로 반환한다."""
        if not self.buy_blockers:
            return "없음"
        return ", ".join(
            f"{label} {count}회"
            for label, count in self.buy_blockers.most_common(limit)
        )


def iter_recent_date_dirs(log_dir: Path, max_date_dirs: int | None = None) -> list[Path]:
    """최신 날짜 디렉터리를 내림차순으로 반환한다."""
    if not log_dir.exists():
        return []
    date_dirs = sorted(
        (
            path
            for path in log_dir.iterdir()
            if path.is_dir() and DATE_DIR_RE.match(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    if max_date_dirs is None:
        return date_dirs
    return date_dirs[:max(max_date_dirs, 0)]


def iter_record_files(log_dir: Path, max_date_dirs: int | None = None) -> list[Path]:
    """분석용 JSONL 파일 목록을 반환한다."""
    if not log_dir.exists():
        return []

    if max_date_dirs is None:
        files = iter_files(log_dir, "*.jsonl")
    else:
        files = []
        for date_dir in iter_recent_date_dirs(log_dir, max_date_dirs=max_date_dirs):
            files.extend(iter_files(date_dir, "*.jsonl"))
        if not files:
            files = sorted(path for path in log_dir.glob("*.jsonl") if path.is_file())

    return [path for path in files if path.name != "errors.jsonl"]


def iter_records(log_dir: Path, max_date_dirs: int | None = None) -> Iterable[dict]:
    """분석용 로그 레코드를 순차적으로 읽는다."""
    if not log_dir.exists():
        return

    for path in iter_record_files(log_dir, max_date_dirs=max_date_dirs):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def load_records(log_dir: Path, max_date_dirs: int | None = None) -> list[dict]:
    """분석용 로그 파일을 읽는다."""
    return list(iter_records(log_dir, max_date_dirs=max_date_dirs))


def read_latest_record(path: Path, max_scan_bytes: int = 1024 * 1024) -> dict | None:
    """JSONL 파일의 마지막 유효 레코드 1건을 꼬리에서 읽는다."""
    if not path.exists() or path.name == "errors.jsonl":
        return None

    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            file_size = handle.tell()
            read_size = min(file_size, max_scan_bytes)
            handle.seek(file_size - read_size)
            data = handle.read(read_size)
    except OSError:
        return None

    for raw_line in reversed(data.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            return json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            continue
    return None


def load_latest_records(
    log_dir: Path,
    *,
    symbols: set[str] | None = None,
    max_date_dirs: int = 3,
) -> list[dict]:
    """심볼별 최신 분석 레코드만 빠르게 읽는다."""
    latest_by_key: dict[tuple[str, str], tuple[str, dict]] = {}

    for path in iter_record_files(log_dir, max_date_dirs=max_date_dirs):
        record = read_latest_record(path)
        if not record:
            continue
        exchange = str(record.get("exchange", "")).strip()
        symbol = str(record.get("symbol", "")).strip()
        if not exchange or not symbol:
            continue
        if symbols is not None and symbol not in symbols:
            continue
        collected_at = str(record.get("collected_at", "")).strip()
        key = (exchange, symbol)
        current = latest_by_key.get(key)
        if current is None or collected_at > current[0]:
            latest_by_key[key] = (collected_at, record)

    return [record for _, record in latest_by_key.values()]


def build_summaries(records: Iterable[dict]) -> list[Summary]:
    """레코드 목록을 심볼별 요약으로 변환한다."""
    grouped: dict[tuple[str, str], Summary] = {}

    for record in records:
        exchange = record.get("exchange", "unknown")
        symbol = record.get("symbol", "unknown")
        key = (exchange, symbol)
        if key not in grouped:
            grouped[key] = Summary(exchange=exchange, symbol=symbol)
        grouped[key].add(record)

    return sorted(grouped.values(), key=lambda item: (item.exchange, item.symbol))


def build_recent_summaries(log_dir: Path, max_date_dirs: int = 1) -> list[Summary]:
    """최신 날짜 분석 로그만 사용해 심볼별 요약을 만든다."""
    return build_summaries(iter_records(log_dir, max_date_dirs=max_date_dirs))


def print_summary(summaries: list[Summary]):
    """요약 결과를 콘솔에 출력한다."""
    if not summaries:
        print("분석할 데이터가 없습니다. 먼저 analysis_log_collector.py 를 실행해 주세요.")
        return

    for item in summaries:
        print("=" * 88)
        print(f"{item.exchange.upper()}  {item.symbol}")
        print(f"- 수집 구간: {item.first_time} ~ {item.last_time}")
        print(f"- 수집 건수: {item.count}")
        print(
            f"- 매수 신호: {item.bullish_count}회 ({item.bullish_ratio_pct:.2f}%), "
            f"매도 신호: {item.bearish_count}회 ({item.bearish_ratio_pct:.2f}%)"
        )
        print(f"- MA 위 체류 비율: {item.above_ma_ratio_pct:.2f}%")
        print(
            f"- 평균 이격도: {item.avg_gap_pct:.4f}%, "
            f"최대 이격도: {item.gap_max:.4f}%"
        )
        print(
            f"- 평균 변화율: {item.avg_change_pct:.4f}%, "
            f"평균 절대 변화율: {item.avg_abs_change_pct:.4f}%"
        )
        print(f"- 종가 표준편차 비율: {item.close_stddev_pct:.4f}%")
        if item.volume_ratio_count:
            print(f"- 평균 거래량 배수: {item.avg_volume_ratio:.4f}배")
        if item.volatility_count:
            print(f"- 평균 변동성(절대 변화율): {item.avg_volatility_pct:.4f}%")
        if item.rsi_count:
            print(f"- 평균 RSI: {item.avg_rsi:.2f}")
        if item.spread_pct_count:
            print(f"- 평균 스프레드: {item.avg_spread_pct:.4f}%")
        if item.candle_range_count:
            print(f"- 평균 캔들 고저폭: {item.avg_candle_range_pct:.4f}%")
        print(
            f"- 공개 기준 매수 준비 비율: {item.public_buy_ready_count}회 "
            f"({item.public_buy_ready_ratio_pct:.2f}%)"
        )
        print(f"- 대표 매수 차단 사유: {item.top_buy_blockers()}")

        if item.avg_gap_pct < 0.3:
            print("- 해석: 이동평균선 주변에서 비교적 잔잔하게 움직이는 편입니다.")
        elif item.avg_gap_pct < 1.0:
            print("- 해석: 적당한 이격도를 보이며 추세 확인형 전략과 무난하게 맞을 수 있습니다.")
        else:
            print("- 해석: 이격도가 큰 편이라 신호는 적어도 변동성 대응이 중요합니다.")

        if item.close_stddev_pct >= 1.0:
            print("- 해석: 단기 변동성이 큰 편이라 분할 진입과 리스크 관리가 더 중요합니다.")


def filter_records(
    records: list[dict], exchange: str | None = None, symbol: str | None = None
) -> list[dict]:
    """조건에 따라 레코드를 거른다."""
    filtered = records
    if exchange:
        filtered = [r for r in filtered if r.get("exchange") == exchange]
    if symbol:
        filtered = [r for r in filtered if r.get("symbol") == symbol]
    return filtered


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(description="분석용 로그 요약 도구")
    parser.add_argument(
        "--log-dir",
        default="analysis_logs",
        help="분석용 JSONL 로그 폴더 경로",
    )
    parser.add_argument(
        "--exchange",
        choices=["okx", "upbit"],
        help="특정 거래소만 분석",
    )
    parser.add_argument(
        "--symbol",
        help="특정 심볼만 분석 (예: BTC/USDT, BTC/KRW)",
    )
    return parser


def main():
    """프로그램 진입점."""
    parser = build_parser()
    args = parser.parse_args()

    records = load_records(Path(args.log_dir))
    records = filter_records(records, exchange=args.exchange, symbol=args.symbol)
    summaries = build_summaries(records)
    print_summary(summaries)


if __name__ == "__main__":
    main()
