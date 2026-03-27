# 청산 보정 세트 정리

기준 날짜: 2026-03-28

이 문서는 최근 주간 백테스트/실거래 비교를 기준으로 정리한 `청산 보정 2세트` 문서입니다.

현재 적용 상태

- 적용 세트: `혼합형`
- 보관 기준선:
  - [conservative_exit_set_full](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_003929__conservative_exit_set_full)
  - [medium_exit_set_full](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_004605__medium_exit_set_full)
  - [diff 요약](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_005001__diff/diff_summary.md)

## 비교 근거

- [ETH/USDT 비교](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_002434__weekly/results/alt__okx__ETH_USDT/comparison.md)
- [ETH/KRW 비교](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_002434__weekly/results/alt__upbit__ETH_KRW/comparison.md)
- [XRP/KRW 비교](/Users/plo/Documents/auto_coin_bot/reports/backtest_batches/20260328_002434__weekly/results/alt__upbit__XRP_KRW/comparison.md)

## 보수형 세트

이 세트는 현재 `.env` 에 실제로 적용한 값입니다.

- `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT=0.15`
- `STRATEGY_MIN_TAKE_PROFIT_PCT_MAP`
  - `ETH/USDT:1.10`
  - `ETH/KRW:0.75`
  - `XRP/KRW:0.50`
  - `XRP/USDT:0.60`
- `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP`
  - `ETH/USDT:0.20`
  - `ETH/KRW:0.20`
- `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP`
  - `ETH/USDT:0.10`
  - `ETH/KRW:0.08`

해석

- ETH/USDT 는 손절 확대보다 `익절/브레이크이븐 보호를 조금 더 빨리 켜는 방향`
- ETH/KRW 는 `브레이크이븐 가드와 최소 익절률`을 소폭 완화
- XRP/KRW 는 `profit_protect` 와 `부분익절`이 더 빨리 나오도록 최소 익절률만 미세 완화
- XRP/USDT 는 심볼별 오버라이드가 거의 없던 상태라, 기본 청산값을 먼저 분리

## 중간형 세트

이 세트는 아직 적용하지 않은 비교 후보입니다.

partial env 파일:

- [env_overrides/medium_exit_set_2026-03-28.env](/Users/plo/Documents/auto_coin_bot/env_overrides/medium_exit_set_2026-03-28.env)

- `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT=0.12`
- `STRATEGY_MIN_TAKE_PROFIT_PCT_MAP`
  - `ETH/USDT:1.05`
  - `ETH/KRW:0.70`
  - `XRP/KRW:0.45`
  - `XRP/USDT:0.55`
- `STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP`
  - `ETH/USDT:0.18`
  - `ETH/KRW:0.18`
- `STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP`
  - `ETH/USDT:0.08`
  - `ETH/KRW:0.05`

해석

- 보수형보다 한 단계 더 빠르게 수익 보호와 브레이크이븐 보호를 작동시키는 세트
- 체결 수는 늘 수 있지만, 과도하게 조기 청산될 가능성도 함께 커집니다.

## 혼합형 세트

이 세트는 `중간형`이 더 좋았던 심볼과 `보수형`이 더 안전했던 심볼을 섞어 실제 `.env` 에 적용한 상태입니다.

- 공통 기본
  - `STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT=0.15`
- 심볼별 fee protect map
  - `ETH/USDT:0.12`
  - `XRP/KRW:0.12`
- 심볼별 최소 익절률
  - `ETH/USDT:1.05`  `중간형`
  - `ETH/KRW:0.75`   `보수형`
  - `XRP/KRW:0.45`   `중간형`
  - `XRP/USDT:0.60`  `보수형`
- 심볼별 브레이크이븐 가드
  - `ETH/USDT min_mfe=0.18, floor=0.08`  `중간형`
  - `ETH/KRW min_mfe=0.20, floor=0.08`   `보수형`

해석

- `ETH/USDT`, `XRP/KRW` 는 중간형 쪽이 더 나았으므로 더 빠른 보호 청산을 사용
- `ETH/KRW`, `XRP/USDT` 는 보수형 쪽이 더 안전하거나 표본이 약해 보수형 유지

## 나중에 비교하는 방법

현재는 혼합형이 적용된 상태이므로, 추가 비교는 아래 순서로 진행하면 됩니다.

1. 현재 기준 스냅샷 저장

- 이미 완료된 기준선:
  - `reports/backtest_batches/20260328_003929__conservative_exit_set_full`
  - `reports/backtest_batches/20260328_004605__medium_exit_set_full`

2. 중간형 값을 `.env` 에 적용

- 새로운 비교 세트를 만들 때는 [env_overrides/medium_exit_set_2026-03-28.env](/Users/plo/Documents/auto_coin_bot/env_overrides/medium_exit_set_2026-03-28.env) 같은 partial env 파일을 기준으로 필요한 키만 `.env` 에 덮어씁니다.

3. 알트 봇 재시작

```bash
.venv/bin/python bot_manager.py stop okx
.venv/bin/python bot_manager.py stop upbit
.venv/bin/python bot_manager.py start okx
.venv/bin/python bot_manager.py start upbit
```

4. 새 세트 스냅샷 저장

```bash
.venv/bin/python backtest_report_runner.py snapshot \
  --label <new_set_label> \
  --since 2026-03-21 \
  --until 2026-03-28
```

5. 전후 비교

```bash
.venv/bin/python backtest_report_runner.py diff \
  --before-dir reports/backtest_batches/20260328_003929__conservative_exit_set_full \
  --after-dir reports/backtest_batches/<new_set_dir>
```

## 운영 메모

- 현재 적용값은 `심볼별로 다른 청산 성격`을 쓰는 혼합형입니다.
- 즉 이번 조정은 “더 오래 버티기”보다 “실거래에서 손절로 밀리던 심볼만 더 빨리 보호하기”에 가깝습니다.
