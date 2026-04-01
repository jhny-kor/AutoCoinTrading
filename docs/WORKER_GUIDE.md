# WORKER GUIDE

이 문서는 작업자가 현재 `auto_coin_bot` 저장소를 빠르게 읽고, 어떤 작업을 할 때 어느 파일부터 봐야 하는지 바로 판단할 수 있도록 정리한 안내서입니다.

## 1. 먼저 보는 순서

작업을 시작할 때는 아래 순서로 보는 것이 가장 빠릅니다.

1. [README.md](/Users/plo/Documents/auto_coin_bot/README.md)
   현재 운영 기준, 실행 방법, 로그 위치를 먼저 확인합니다.
2. [docs/PLANS.md](/Users/plo/Documents/auto_coin_bot/docs/PLANS.md)
   지금 적용 중인 전략과 다음 조정 계획을 확인합니다.
3. [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md)
   왜 이 값으로 바뀌었는지, 최근 조정 근거를 확인합니다.
4. [docs/MODULE_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/MODULE_GUIDE.md)
   모듈 역할을 빠르게 찾습니다.

## 2. 디렉토리 구조 그림

아래 그림 파일이 현재 소스 디렉토리 구조를 요약합니다.

![worker-directory-map](/Users/plo/Documents/auto_coin_bot/docs/worker_directory_map.svg)

원본 파일:
- [docs/worker_directory_map.svg](/Users/plo/Documents/auto_coin_bot/docs/worker_directory_map.svg)

## 3. 디렉토리별 역할

### 루트

- 루트의 `*.py` 중 일부는 실제 본체이고, 일부는 `settings/`, `tools/`, `reporting/` 본체를 가리키는 호환 래퍼입니다.
- 최근 작업은 먼저 `docs/`, `core/`, 실제 전략 본체 파일에서 확인하는 편이 안전합니다.

### `run/`

- 실행 진입점입니다.
- `bot_manager.py` 가 여기 있는 스크립트를 실제 프로세스로 띄웁니다.
- 운영 중 프로세스 재기동/상태 확인은 이 경로 기준으로 보면 됩니다.

### `core/`

- 거래소 공통 실행, 전략 계산, 리스크 계산, 포지션 수명주기, 공통 메트릭을 둡니다.
- 최근 업비트 지연 완화는 [core/execution/upbit.py](/Users/plo/Documents/auto_coin_bot/core/execution/upbit.py)에 들어갔습니다.
- 프로그램 메타데이터와 런타임 bootstrap 은 [core/runtime](/Users/plo/Documents/auto_coin_bot/core/runtime)에 있습니다.
- 새로운 공통 규칙은 먼저 `core/`로 내릴 수 있는지 확인하는 편이 좋습니다.

### `settings/`

- `.env`를 실제 구조체로 읽는 본체입니다.
- 알트 공통 전략은 [settings/strategy_settings.py](/Users/plo/Documents/auto_coin_bot/settings/strategy_settings.py), BTC 전략은 [settings/btc_trend_settings.py](/Users/plo/Documents/auto_coin_bot/settings/btc_trend_settings.py)에서 읽습니다.

### 전략 본체 파일

- OKX 알트: [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
- 업비트 알트: [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
- OKX BTC: [okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/okx_btc_ema_trend_bot.py)
- 업비트 BTC: [upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_btc_ema_trend_bot.py)

작업 기준:
- 진입/청산 조건 조정은 전략 본체와 `core/strategy`, `core/risk`를 같이 봅니다.
- 주문/지연/재시도 조정은 `core/execution`을 먼저 봅니다.
- 포지션 복구나 체결 후 상태 문제는 `state_recovery.py`, `trade_history_logger.py`, `structured_log_manager.py`를 같이 봅니다.

### `reporting/`

- 분석/비교/텔레그램 리포트 본체입니다.
- 텔레그램 리스너 설정/offset/polling 은 [reporting/listener_runtime.py](/Users/plo/Documents/auto_coin_bot/reporting/listener_runtime.py)에 분리되어 있습니다.
- `/positions`용 거래소 스냅샷은 [reporting/position_snapshot.py](/Users/plo/Documents/auto_coin_bot/reporting/position_snapshot.py)에 있습니다.
- 백테스트 대 실거래 비교는 [reporting/compare_backtest_to_live.py](/Users/plo/Documents/auto_coin_bot/reporting/compare_backtest_to_live.py)를 봅니다.

### `tools/`

- 백테스트, 분석 수집, 헬스체크, 로그 압축 같은 운영 도구 본체입니다.
- 루트의 `backtest_replay.py`, `backtest_report_runner.py`, `log_archive_manager.py`는 이쪽 구현을 부르는 래퍼가 섞여 있습니다.

### `docs/`

- 현재 운영 기준 문서는 모두 여기 있습니다.
- 작업자 기준 핵심 문서는 다음 네 개입니다.
  - [docs/WORKER_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/WORKER_GUIDE.md)
  - [docs/PLANS.md](/Users/plo/Documents/auto_coin_bot/docs/PLANS.md)
  - [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md)
  - [docs/MODULE_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/MODULE_GUIDE.md)

## 4. 작업 종류별 시작 파일

### 전략 수치 조정

- 먼저 [docs/PLANS.md](/Users/plo/Documents/auto_coin_bot/docs/PLANS.md), [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md)
- 실제 값 반영: [`.env.example`](/Users/plo/Documents/auto_coin_bot/.env.example), [`.env`](/Users/plo/Documents/auto_coin_bot/.env)
- 로더 확인: [settings/strategy_settings.py](/Users/plo/Documents/auto_coin_bot/settings/strategy_settings.py), [settings/btc_trend_settings.py](/Users/plo/Documents/auto_coin_bot/settings/btc_trend_settings.py)

세부 순서:
1. 최근 실거래와 백테스트 비교를 먼저 확인합니다.
2. 바꿀 값이 알트 공통인지, BTC 전용인지 구분합니다.
3. `.env.example` 와 실제 `.env` 를 같이 갱신합니다.
4. 로더가 해당 키를 실제로 읽는지 확인합니다.
5. 변경 근거는 `docs/STRATEGY_DECISIONS.md`, 현재 운영 방향은 `docs/PLANS.md`에 남깁니다.

### 진입/청산 로직 변경

- 알트: [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py), [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
- BTC: [upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_btc_ema_trend_bot.py), [okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/okx_btc_ema_trend_bot.py)
- 공통 계산: [core/strategy](/Users/plo/Documents/auto_coin_bot/core/strategy), [core/risk](/Users/plo/Documents/auto_coin_bot/core/risk)

세부 순서:
1. 먼저 어느 거래소/전략 파일에서 실제 조건문을 쓰는지 찾습니다.
2. 같은 규칙이 양 거래소 공통인지 확인합니다.
3. 공통화 가능한 계산은 `core/strategy` 또는 `core/risk` 로 내릴지 먼저 판단합니다.
4. 변경 후 `trade_history_logger.py` 와 `structured_log_manager.py` 에 남는 로그 필드가 부족하지 않은지 확인합니다.
5. 실거래 영향을 주는 경우 최근 로그 해석과 기대 효과를 문서에 남깁니다.

### 업비트/OKX 주문 지연 문제

- 업비트: [core/execution/upbit.py](/Users/plo/Documents/auto_coin_bot/core/execution/upbit.py)
- OKX: [core/execution/okx.py](/Users/plo/Documents/auto_coin_bot/core/execution/okx.py)
- 체결 품질 확인: [trade_history_logger.py](/Users/plo/Documents/auto_coin_bot/trade_history_logger.py)

세부 순서:
1. `trade_history.jsonl` 의 `api_latency_ms`, `exchange_ack_latency_ms`, `fill_ratio`, `slippage_bps` 를 먼저 확인합니다.
2. 지연이 주문 응답 자체인지, 주문 전후 조회 부하인지 구분합니다.
3. 재시도, 타임아웃, 캐시, websocket 대체 중 어느 층의 문제인지 먼저 정합니다.
4. 주문 직후 상태가 바뀌는 경로면 캐시 무효화까지 같이 넣습니다.
5. 변경 후 최소한 `py_compile` 과 최근 체결 로그 확인 기준을 같이 남깁니다.

### 로그/백테스트/비교

- 로그 구조: [structured_log_manager.py](/Users/plo/Documents/auto_coin_bot/structured_log_manager.py), [trade_history_logger.py](/Users/plo/Documents/auto_coin_bot/trade_history_logger.py)
- 백테스트 실행: [tools/backtest_replay.py](/Users/plo/Documents/auto_coin_bot/tools/backtest_replay.py), [tools/backtest_report_runner.py](/Users/plo/Documents/auto_coin_bot/tools/backtest_report_runner.py)
- 실거래 비교: [reporting/compare_backtest_to_live.py](/Users/plo/Documents/auto_coin_bot/reporting/compare_backtest_to_live.py)

세부 순서:
1. 먼저 비교 대상 기간을 명확히 정합니다.
2. 가능하면 같은 기간의 실거래와 백테스트를 맞춥니다.
3. 손절 분석이면 `MFE`, `MAE`, 보유시간, 종료 사유를 같이 봅니다.
4. 수익 확대 분석이면 `MFE 대비 실현 순익률` 을 같이 봅니다.
5. 최종 결론은 “손절 방지용”과 “수익 확대용”을 분리해 적습니다.

### 문서 정리

- 운영 기준: [README.md](/Users/plo/Documents/auto_coin_bot/README.md)
- 현재 계획: [docs/PLANS.md](/Users/plo/Documents/auto_coin_bot/docs/PLANS.md)
- 변경 근거: [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md)
- 모듈 안내: [docs/MODULE_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/MODULE_GUIDE.md)

세부 순서:
1. 현재 상태를 바꿨으면 `docs/PLANS.md`를 갱신합니다.
2. 왜 바꿨는지 근거가 있으면 `docs/STRATEGY_DECISIONS.md`를 갱신합니다.
3. 파일 역할이 바뀌었으면 `docs/MODULE_GUIDE.md`를 갱신합니다.
4. 사용자 관점 실행 흐름이 바뀌었으면 `README.md`를 갱신합니다.

### 운영 재기동

- 프로세스 상태/재기동: [bot_manager.py](/Users/plo/Documents/auto_coin_bot/bot_manager.py)
- launchd 관련 파일: [launchd](/Users/plo/Documents/auto_coin_bot/launchd)

세부 순서:
1. 현재 실행 상태를 먼저 확인합니다.
2. 설정 변경이 크면 `stop all` 후 `start all` 로 재기동합니다.
3. 일부 프로세스만 남으면 개별 `stop --force` 로 정리합니다.
4. 재기동 후 PID 와 실행시간을 다시 확인합니다.
5. 설정 반영 여부는 최신 로그 첫 구간에서 확인합니다.

### 테스트와 검증

- 단위 테스트: [tests](/Users/plo/Documents/auto_coin_bot/tests)
- 빠른 문법 확인: `py_compile`

세부 순서:
1. 수정 범위가 좁으면 `python3 -m py_compile ...` 를 우선 돌립니다.
2. 계산 로직을 바꿨으면 관련 테스트를 찾습니다.
3. 백테스트 툴을 건드렸으면 최소한 최근 결과 파일이 정상 저장되는지 봅니다.
4. 주문/로그 구조를 바꿨으면 새 필드가 실제 로그에 찍히는지 확인합니다.

## 5. 지금 기준 핵심 포인트

- 손절 억제 우선 축:
  - `ETH/USDT`
  - `ETH/KRW`
  - `BTC/KRW`
- 수익 러너 확대 우선 축:
  - `BTC/USDT`
  - `XRP/KRW`
  - `XRP/USDT`
- 업비트는 주문 응답 지연이 구조적으로 남으므로, 저엣지 진입은 더 보수적으로 보는 편이 맞습니다.

## 6. 작업 후 체크리스트

### 공통 체크

- `.env` 와 `.env.example` 반영이 같이 되었는지 확인
- 수정한 소스 최상단 `수정 요약` 주석을 갱신했는지 확인
- 한글 설명 주석이 필요한 부분은 한글로 적었는지 확인
- 문서 반영이 필요한지 확인

### 전략/설정 변경 체크

- 알트/BTC 양쪽에 같은 구조로 반영해야 할 내용이 빠지지 않았는지 확인
- 실제 로더가 새 키를 읽는지 확인
- 손절 방지용인지, 수익 확대용인지 목적을 분리해 기록했는지 확인

### 실행/지연 변경 체크

- 재시도, 타임아웃, 캐시가 주문 흐름을 망치지 않는지 확인
- 주문 직후 캐시 무효화가 필요한 경로에 빠짐없이 들어갔는지 확인
- 실행 품질 로그 필드가 그대로 남는지 확인

### 검증 체크

- `py_compile` 또는 관련 테스트를 돌렸는지 확인
- 필요하면 `bot_manager.py status` 로 재기동 상태를 확인
- 백테스트/리포트 변경이면 결과 파일 생성까지 확인

### 문서 체크

- 변경 근거는 `docs/STRATEGY_DECISIONS.md`
- 현재 운영 방향은 `docs/PLANS.md`
- 작업자 안내는 `docs/WORKER_GUIDE.md`
- 모듈 역할 변화는 `docs/MODULE_GUIDE.md`
