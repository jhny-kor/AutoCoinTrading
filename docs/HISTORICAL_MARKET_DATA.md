# 과거 시장 데이터 수집 기준

이 문서는 백테스트와 실거래 판단 개선에 사용할 장기 과거 데이터 수집 기준입니다.

## 수집 기간

- BTC, ETH: 최근 3년
- 그 외 알트: 최근 1년
- 기본 주기: `1m`

`1m` 데이터를 원본으로 저장하면 BTC의 `5m/15m` 확인봉과 알트의 `1m/5m` 판단을 모두 리샘플링으로 재현할 수 있습니다.

## 수집 대상

- OKX: `BTC/USDT`, `ETH/USDT`, 현재 운영/분석 심볼
- 업비트: `BTC/KRW`, `ETH/KRW`, 현재 운영/분석 심볼
- 현재 운영 심볼은 `config/runtime.toml` 과 env override 를 통해 읽습니다.

## 저장 경로

- OHLCV: `historical_data/{exchange}/{symbol}/{timeframe}/ohlcv.jsonl`
- OKX funding: `historical_data/okx/{symbol}/funding_rate.jsonl`
- 요약: `historical_data/collection_summary.json`
- `historical_data/` 는 대용량 재생성 캐시이므로 git 에 올리지 않습니다.

예:

```text
historical_data/okx/BTC_USDT/1m/ohlcv.jsonl
historical_data/okx/BTC_USDT/funding_rate.jsonl
historical_data/upbit/BTC_KRW/1m/ohlcv.jsonl
```

## OHLCV 필드

- `exchange`: `okx` 또는 `upbit`
- `symbol`: `BTC/USDT`, `BTC/KRW` 같은 내부 표준 심볼
- `market_id`: 거래소 원본 마켓 ID
- `timeframe`: 예: `1m`
- `timestamp_ms`: 캔들 기준 시각
- `datetime_utc`: UTC ISO 시각
- `open`, `high`, `low`, `close`: OHLC 가격
- `volume`: 백테스트 호환용 base 거래량
- `volume_base`: base 거래량
- `quote_volume`: quote 거래대금
- `source`: 원본 API
- `collected_at`: 수집 시각

OKX 추가 필드:

- `okx_vol_ccy`
- `okx_vol_ccy_quote`
- `confirm`

업비트 추가 필드:

- `candle_date_time_utc`
- `candle_date_time_kst`

## OKX Funding 필드

- `exchange`
- `symbol`
- `swap_inst_id`
- `funding_time_ms`
- `datetime_utc`
- `funding_rate`
- `realized_rate`
- `method`
- `formula_type`
- `inst_type`
- `source`
- `collected_at`

## 수집 명령

계획 확인:

```bash
.venv/bin/python tools/historical_market_collector.py plan
```

전체 수집:

```bash
.venv/bin/python tools/historical_market_collector.py collect
```

백그라운드 전체 수집:

```bash
.venv/bin/python tools/historical_market_collector.py launch
.venv/bin/python tools/historical_market_collector.py status
```

`launch` 로 시작한 수집은 기본적으로 완료/실패 시 텔레그램 알림을 보냅니다. 이미 실행 중인 수집 PID 를 감시해 완료 알림만 붙일 때는 아래 명령을 사용합니다.

```bash
.venv/bin/python tools/historical_market_collector.py launch-watch
```

테스트용 1페이지 수집:

```bash
.venv/bin/python tools/historical_market_collector.py collect --max-pages 1 --skip-funding
```

특정 거래소만 수집:

```bash
.venv/bin/python tools/historical_market_collector.py collect --exchange okx
```

특정 심볼만 수집:

```bash
.venv/bin/python tools/historical_market_collector.py collect --exchange upbit --symbols BTC/KRW,ETH/KRW
```

## 제한 사항

- 과거 호가 스냅샷은 공개 REST API로 장기간 소급 수집하지 않습니다.
- 호가 기반 체결 모델은 앞으로 누적되는 `analysis_logs` 와 웹소켓 live snapshot 을 사용합니다.
- 업비트 분봉 API는 체결이 없는 구간의 캔들이 생성되지 않을 수 있어, 저장된 캔들 수가 시간 구간의 이론값보다 적을 수 있습니다.
- 장기 `1m` 수집은 API 호출 수가 많으므로 중간에 끊겨도 같은 명령을 다시 실행해 이어받는 방식으로 운영합니다.
