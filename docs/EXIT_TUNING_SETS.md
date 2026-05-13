# 청산 보정 세트 정리

현재 기준 요약

- canonical 기본값: [config/runtime.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.toml)
- canonical 세트: [config/sets](/Users/plo/Documents/auto_coin_bot/config/sets)
- 현재 적용 override: [config/runtime.local.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.local.toml)

현재 canonical 문서입니다.

상세 내용

- [EXIT_TUNING_SETS_2026-03-28.md](/Users/plo/Documents/auto_coin_bot/docs/EXIT_TUNING_SETS_2026-03-28.md)

현재 적용 세트

- `mixed`

2026-05-13 적용 메모

- 90일 민감도 백테스트에서 `profit_take_quicker`는 `upbit ETH/KRW`만 개선했고 `upbit XRP/KRW`는 악화됐다.
- 현재 적용값은 `ETH/KRW`에만 빠른 수익보호를 반영한다.
- `ETH/KRW min_take_profit_pct`: `0.75 -> 0.55`
- `ETH/KRW fee_protect_min_net_pnl_pct`: `기본 0.15 -> 심볼별 0.06`
- `BTC/USDT`, `BTC/KRW`는 ATR/거래량 완화가 손실 거래만 늘린 결과라 기존 보수 기준을 유지한다.
- `XRP/KRW`, `XRP/USDT`는 빠른 익절 전역 적용 대상에서 제외하고 별도 기준이 검증될 때까지 기존 보호 기준을 유지한다.

canonical 세트 파일

- [config/sets/conservative.toml](/Users/plo/Documents/auto_coin_bot/config/sets/conservative.toml)
- [config/sets/medium.toml](/Users/plo/Documents/auto_coin_bot/config/sets/medium.toml)
- [config/sets/mixed.toml](/Users/plo/Documents/auto_coin_bot/config/sets/mixed.toml)

현재 적용 override

- [config/runtime.local.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.local.toml)
