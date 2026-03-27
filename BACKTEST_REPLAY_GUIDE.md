# 백테스트 / 리플레이 가이드

## 목적

`backtest_replay.py` 는 실거래 봇과 같은 설정 로더를 사용해, 로컬 OHLCV 파일로 전략을 다시 재생하는 1차 오프라인 검증 도구입니다.

현재 범위

- 알트 MA 전략 리플레이
- BTC EMA 전략 리플레이
- 공개 OHLCV 저장용 `fetch`
- 결과 요약 JSON, 거래 JSONL, 자산곡선 JSONL 출력

## 1. 시세 데이터 저장

예시

```bash
.venv/bin/python backtest_replay.py fetch \
  --exchange upbit \
  --symbol BTC/KRW \
  --timeframe 1m \
  --limit 2000 \
  --output data/upbit_btc_krw_1m.jsonl
```

지원 출력 형식

- `.jsonl`
- `.csv`

필수 컬럼은 아래 여섯 개입니다.

- `timestamp_ms`
- `open`
- `high`
- `low`
- `close`
- `volume`

## 2. 알트 전략 리플레이

예시

```bash
.venv/bin/python backtest_replay.py run \
  --strategy alt \
  --exchange upbit \
  --symbol XRP/KRW \
  --input data/upbit_xrp_krw_1m.jsonl \
  --timeframe 1m \
  --initial-cash 1000000
```

## 3. BTC 전략 리플레이

예시

```bash
.venv/bin/python backtest_replay.py run \
  --strategy btc \
  --exchange okx \
  --symbol BTC/USDT \
  --input data/okx_btc_usdt_1m.jsonl \
  --timeframe 1m \
  --initial-cash 1000
```

BTC 전략은 입력 주기가 더 낮으면 내부에서 `5m`, `15m` 로 리샘플링합니다.

## 4. 주요 옵션

- `--initial-cash`
  - 시작 자금
- `--fee-rate-pct`
  - 편도 수수료율 직접 지정
- `--risk-per-trade`
  - 현재 버전에서는 `가용 현금 사용 비율` 성격
- `--min-buy-order-value`
  - 거래소 최소 주문 금액 직접 지정
- `--max-daily-loss-quote`
  - 일일 최대 손실 제한 직접 지정
- `--output-dir`
  - 결과 저장 루트

## 5. 결과 파일

실행 결과는 `reports/backtests/<timestamp>__<strategy>__<symbol>/` 아래에 저장됩니다.

- `summary.json`
  - 수익률, 거래 수, 승률, 최대 낙폭
- `trades.jsonl`
  - 백테스트 체결 이력
- `equity_curve.jsonl`
  - 자산곡선

## 5.1 실거래와 비교

백테스트 결과 디렉토리를 기준으로 실거래 `trade_history` 와 비교할 수 있습니다.

예시

```bash
.venv/bin/python compare_backtest_to_live.py \
  --backtest-dir reports/backtests/20260327_230344__alt__XRP_KRW \
  --exchange upbit \
  --since 2026-03-20 \
  --until 2026-03-27
```

비교 결과는 같은 디렉토리에 아래 파일로 저장됩니다.

- `comparison.json`
- `comparison.md`

## 5.2 주간 배치 / 전후 비교

주간 점검과 설정 변경 전후 비교는 `backtest_report_runner.py` 로 묶어서 실행할 수 있습니다.

주간 배치 예시

```bash
.venv/bin/python backtest_report_runner.py weekly
```

설정 변경 전 스냅샷 예시

```bash
.venv/bin/python backtest_report_runner.py snapshot \
  --label before_tune \
  --since 2026-03-20 \
  --until 2026-03-27
```

설정 변경 후 스냅샷 예시

```bash
.venv/bin/python backtest_report_runner.py snapshot \
  --label after_tune \
  --since 2026-03-20 \
  --until 2026-03-27
```

전후 비교 예시

```bash
.venv/bin/python backtest_report_runner.py diff \
  --before-dir reports/backtest_batches/<before_dir> \
  --after-dir reports/backtest_batches/<after_dir>
```

배치 결과는 `reports/backtest_batches/...` 아래에 저장됩니다.

- `batch_summary.json`
- `batch_summary.md`
- `diff_summary.json`
- `diff_summary.md`

## 6. 현재 제한 사항

- 실봇 100% 복제보다 `같은 설정 기반의 1차 오프라인 검증`에 초점을 둡니다.
- 포트폴리오 배분, 복수 심볼 동시 운용, 실제 주문 응답 품질은 아직 포함하지 않았습니다.
- 입력 데이터 품질이 낮으면 결과도 그대로 왜곡됩니다.
- 현재 실전 `.env` 값이 보수적이면 거래가 0건으로 나올 수 있습니다.

## 7. 다음 단계 권장

- 실거래 로그와 백테스트 결과 차이의 원인 자동 요약
- `trade_history.jsonl` 기반 상태 복원 범위를 트레일링/레짐/쿨다운까지 확장
- 전략별 테스트 샘플 데이터와 회귀 테스트 추가
