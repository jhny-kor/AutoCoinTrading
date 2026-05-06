# Auto Coin Bot

OKX와 업비트 현물 자동매매를 테스트하는 단타/인트라데이 프로젝트입니다.  
현재 구조는 `run/` 실행 진입점, `core/` 공통 전략/리스크/실행 로직, `settings/` 설정 로더, `reporting/` 분석/텔레그램, `tools/` 운영 유틸 기준으로 정리돼 있습니다.

## 현재 운영 기준

- 거래소
  - OKX: 알트 + BTC 전용 봇
  - 업비트: 알트 + BTC 전용 봇
- 전략
  - 알트: 1분봉 기반 진입 + 상위 타임프레임 확인 + 부분익절/부분손절/순익 보호
  - BTC: 5분봉/15분봉 EMA 추세추종 + ATR 기반 손절/익절 + 부분익절 + 트레일링
  - 공통: 거래량, ATR percentile, RSI, 최근 range 위치를 결합해 과열 추격 진입을 줄임
  - 알트: BTC 위험 레짐+고상관+알트 고ATR, 거래량+ATR+약한 체결/호가, 손절 후 유사 조건 재진입을 추가 차단
  - 알트: `volume`, `gap`, `HTF bullish`, `correlation` 은 단독 매수 근거가 아니라 감점/결합 필터로 사용
  - 공통: 체결마다 decision journal 을 남겨 risk review 와 reflection 을 누적
- 설정 기준
  - canonical 설정: [config/runtime.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.toml)
  - 로컬 override: [config/runtime.local.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.local.toml)
  - 비밀정보: [`.env.secrets`](/Users/plo/Documents/auto_coin_bot/.env.secrets)

## 문서 역할

- 현재 운영/사용 기준: [README.md](/Users/plo/Documents/auto_coin_bot/README.md)
- 작업자 안내: [docs/WORKER_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/WORKER_GUIDE.md)
- 모듈 구조: [docs/MODULE_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/MODULE_GUIDE.md)
- 전략 변경 이력: [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md)
- 계획/후보안: [docs/PLANS.md](/Users/plo/Documents/auto_coin_bot/docs/PLANS.md)
- 리팩토링 단계 기록: [docs/refactor_20260329](/Users/plo/Documents/auto_coin_bot/docs/refactor_20260329)
- 루트 호환 래퍼 정책: [docs/refactor_20260329/ROOT_WRAPPER_POLICY.md](/Users/plo/Documents/auto_coin_bot/docs/refactor_20260329/ROOT_WRAPPER_POLICY.md)

즉 과거 변경 내용이나 날짜별 반영 사항은 README에 누적하지 않고, `이력 문서`인 [docs/STRATEGY_DECISIONS.md](/Users/plo/Documents/auto_coin_bot/docs/STRATEGY_DECISIONS.md) 와 [docs/refactor_20260329](/Users/plo/Documents/auto_coin_bot/docs/refactor_20260329) 에서 관리합니다.

## 실행 프로그램

- OKX 알트: [run/ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/run/ma_crossover_bot.py)
- 업비트 알트: [run/upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/run/upbit_ma_crossover_bot.py)
- OKX BTC: [run/okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/run/okx_btc_ema_trend_bot.py)
- 업비트 BTC: [run/upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/run/upbit_btc_ema_trend_bot.py)
- 분석 수집기: [run/analysis_log_collector.py](/Users/plo/Documents/auto_coin_bot/run/analysis_log_collector.py)
- 업비트 웹소켓 수집기: [run/upbit_market_data_stream.py](/Users/plo/Documents/auto_coin_bot/run/upbit_market_data_stream.py)
- 텔레그램 명령 리스너: [run/telegram_command_listener.py](/Users/plo/Documents/auto_coin_bot/run/telegram_command_listener.py)
- 자동복구 감시기: [run/auto_recovery_watchdog.py](/Users/plo/Documents/auto_coin_bot/run/auto_recovery_watchdog.py)

## 빠른 시작

- 런타임 의존성 설치: `.venv/bin/pip install -r requirements.txt`
- 개발 의존성 포함 설치: `.venv/bin/pip install -r requirements-dev.txt`
- 전체 시작: `.venv/bin/python bot_manager.py start all`
- 상태 확인: `.venv/bin/python bot_manager.py status`
- 전체 중지: `.venv/bin/python bot_manager.py stop`

## 일상 운영 루틴

### 항상 실행

- `.venv/bin/python bot_manager.py start all`

포함 프로그램:
- OKX 알트
- 업비트 알트
- OKX BTC
- 업비트 BTC
- 분석 수집기
- 업비트 웹소켓 수집기
- 텔레그램 명령 리스너
- 자동복구 감시기

### 수시 확인

- 텔레그램
  - `/status`
  - `/positions`
  - `/pnl`
  - `/analysis`
  - `/regime`
  - `/weekly`
  - `/change`
  - `/shadow`
  - `/last`
- 터미널
  - `.venv/bin/python bot_manager.py status`

### 정기 분석

- 시장 로그 요약: `.venv/bin/python analyze_logs.py`
- 전략 퍼널 분석: `.venv/bin/python analyze_strategy_logs.py`
- CSV 저장: `.venv/bin/python analyze_strategy_logs.py --csv reports/strategy_funnel.csv`
- 변경 효과 자동 비교: `.venv/bin/python tools/change_effect_report.py --hours 12`
- 미체결 후보 가상 추적: `.venv/bin/python tools/shadow_candidate_tracker.py --hours 6 --horizon-minutes 60`

## 전략 요약

### 알트

- 1분봉 기반
- 상위 타임프레임 필터
- 거래량/변동성/신호 점수 필터
- 레짐별 전략 라우터
  - `CHOPPY` 계열: Bollinger mean reversion
  - `BREAKOUT_ATTEMPT`: breakout
  - `TRENDING` 계열: trend-follow/MA 경로
- 부분익절/부분손절
- 브레이크이븐/순익 보호
- 손절 방지 결합 가드
  - BTC 위험 레짐 + BTC 상관계수 + 알트 ATR percentile
  - 거래량 급증 + 고ATR + 약한 체결비율/호가 압력
  - 손절 후 1시간 안에 유사 조건 재진입 차단
- 알트 신호 점수는 `volume`/`gap` 단독 가중치를 낮추고 `slope`/`MACD`/`RSI`/`squeeze` 결합을 더 크게 봅니다.

### BTC

- 5분봉 EMA + 15분봉 확인
- 상위 추세는 `confirm_close > confirm_ema` 와 확인 EMA slope 하한을 함께 충족할 때만 유효 처리
- ATR 기반 손절/익절
- 거래량 보너스와 동적 오버웨이트는 ATR 동반 시에만 허용
- 부분익절 + 트레일링
- 순익 보호 익절
- 피라미딩 1회 제한
- 레짐 기반 전략 라우터

### 매수 검토 위원회

매수 후보는 기존 퍼널과 별도로 `strategy / risk / execution / portfolio / regime` 관점에서 한 번 더 평가합니다.

- 구현: [core/strategy/entry_committee.py](/Users/plo/Documents/auto_coin_bot/core/strategy/entry_committee.py)
- 설정: [config/runtime.toml](/Users/plo/Documents/auto_coin_bot/config/runtime.toml)의 `[entry_committee]`
- 현재 모드: `shadow`
- 동작: 구조화 로그에 `entry_committee` 투표 결과를 남기지만, 실거래 진입을 즉시 추가 차단하지는 않음
- 전환: 충분한 표본 검증 후 `mode = "active"` 로 바꾸면 위원회 거절이 실제 entry funnel 단계로 연결됨

### BTC 레짐 라우팅

현재 BTC는 보수형 8단계 레짐을 사용합니다.

- `LOW_ENERGY`
- `CHOPPY_LOW_VOL`
- `CHOPPY_HIGH_VOL`
- `BREAKOUT_ATTEMPT`
- `TRENDING_EARLY`
- `TRENDING_MATURE`
- `EXHAUSTION_RISK`
- `OVERHEATED`

이 레짐은 [core/strategy/regime_router.py](/Users/plo/Documents/auto_coin_bot/core/strategy/regime_router.py) 에서 먼저
- `skip`
- `breakout`
- `trend_follow`
전략 경로 중 하나로 라우팅한 뒤 기존 BTC 전략 엔진을 실행합니다.

BTC 진입 확인 루프는 루프 주기 `10초` 기준으로 심볼별 분리 적용합니다.

- `BTC/USDT`: `3회`
- `BTC/KRW`: `5회`

체감 지연:
- `BTC/USDT`: 첫 후보 감지 뒤 대략 `20초`
- `BTC/KRW`: 첫 후보 감지 뒤 대략 `40초`

## 포트폴리오 배분

현재 포트폴리오 배분은 강제 리밸런싱이 아니라 `신규 매수 허용 금액 제한` 방식입니다.

- 기본 목표 비중
  - BTC `45%`
  - ETH `30%`
  - XRP `15%`
  - SOL `10%`
- 계산 기준
  - 현재 가용 현금
  - 코인별 남아 있는 누적 투입 원가
- 결과
  - 목표 비중을 넘는 코인은 신규 매수 제한
  - 부족한 코인만 목표 비중 안에서 추가 진입 허용

동적 오버웨이트는 거래량/추세 품질이 매우 좋을 때만 보수적으로 `+5%`까지 허용합니다.

### Allocation Score

신규 진입 비중은 신호 점수만으로 키우지 않고 `signal / market / execution / diversification` 네 축을 합산해 보정합니다.

- 현재 가중치
  - signal `0.30`
  - market `0.30`
  - execution `0.25`
  - diversification `0.15`
- 손절 방지 반영
  - `volume_ratio >= 2.0` 이면서 `ATR percentile >= 70`이면 market score 감점
  - `orderbook_pressure_score < 50`이면 execution score 감점
  - BTC 상관계수 단독 페널티는 완화하고, 위험 레짐+고상관+알트 고ATR 조합에서 강하게 차단
  - `HTF bullish`, `signal_is_strong`, `volume_ratio`, `gap_pct`, `range_position_pct` 는 단독 긍정 신호로 쓰지 않고 결합 판단에만 사용

## 로그 구조

- 운영 로그: `logs/YYYY-MM-DD/*.log`
- 분석 로그: `analysis_logs/YYYY-MM-DD/*.jsonl`
- 체결 로그: `trade_logs/YYYY-MM-DD/trade_history.jsonl`
- 의사결정 저널: `reports/decision_journal/YYYY-MM-DD/decision_journal.jsonl`
- 전략 로그: `structured_logs/live/YYYY-MM-DD/*/strategy.jsonl`
- 시스템 로그: `structured_logs/live/YYYY-MM-DD/*/system.jsonl`
- 체결 구조화 로그: `structured_logs/live/YYYY-MM-DD/*/trade.jsonl`
- 업비트 웹소켓 런타임: `logs/runtime/upbit_ws/*`

오래된 로그는 보관 기간을 넘기면 삭제합니다. `structured_logs` 는 최근 5일, 나머지 로그 루트는 최근 7일 원본을 유지합니다.

- 상태 확인: `.venv/bin/python log_archive_manager.py status`
- 수동 정리: `.venv/bin/python log_archive_manager.py prune`
- 보관 기준: `structured_logs` 최근 5일 유지, 나머지 로그 루트는 최근 7일 유지

## 텔레그램

- 발송 유틸: [telegram_notifier.py](/Users/plo/Documents/auto_coin_bot/telegram_notifier.py)
- 명령 리스너: [run/telegram_command_listener.py](/Users/plo/Documents/auto_coin_bot/run/telegram_command_listener.py)
- 즉시 테스트: `.venv/bin/python run/telegram_command_listener.py --send-test`

지원 명령:
- `/test`
- `/status`
- `/positions`
- `/pnl`
- `/analysis`
- `/regime`
- `/weekly`
- `/change`
- `/shadow`
- `/last`
- `/help`

`/analysis` 와 `/weekly` 에는 최근 decision journal 기반 의사결정 리뷰가 포함됩니다.  
체결별 risk posture, 반복 우려 항목, 최근 reflection 을 함께 보여주며, journal 이 아직 없으면 최근 `trade_history` 를 같은 방식으로 임시 평가합니다.
`/change` 는 최신 git 변경 시각 전후의 진입 퍼널/체결/손절 변화를 비교하고, `/shadow` 는 실제 매수되지 않은 후보가 이후 가격 흐름에서 가상 익절/손절에 도달했는지 보여줍니다.
복합 리포트는 빈 보조 섹션을 숨기고, 숫자 나열보다 `판정`과 주요 병목이 먼저 보이도록 정리합니다.

## 테스트와 헬스체크

- 전체 테스트: `.venv/bin/python -m unittest discover -s tests -v`
- 운영 헬스체크: `.venv/bin/python tools/healthcheck.py`
- JSON 헬스체크: `.venv/bin/python tools/healthcheck.py --json`
- strict 모드: `.venv/bin/python tools/healthcheck.py --mode strict`
- 자동복구 1회 점검: `.venv/bin/python tools/auto_recovery_watchdog.py --once`
- 자동복구 관리 시작: `.venv/bin/python bot_manager.py start auto_recovery`

현재 테스트 범위:
- 알트 신호 계산
- 가중 신호 점수 계산
- mean reversion 신호 계산
- 알트 청산 보호
- BTC 청산 플래그
- BTC 포지션 평가
- BTC/알트 레짐 라우터
- 최근 7일 자동 튜닝 계산
- Sharpe 기반 후보 랭킹
- 상태 복구
- 퍼널 생성기
- 변경 효과 자동 비교
- 미체결 후보 가상 추적
- 매수 검토 위원회
- 진입 상태 머신
- 체결률 기반 실행 품질 가드
- 포트폴리오 배분
- decision journal / risk review
- 운영 헬스체크
- 자동복구 watchdog

## 백테스트

- 단일 리플레이: `.venv/bin/python backtest_replay.py`
- 배치 리포트: `.venv/bin/python backtest_report_runner.py weekly`
- 레지스트리 갱신: `.venv/bin/python tools/update_backtest_registry.py`

### override 실험 세트

live 설정을 건드리지 않고 백테스트에만 추가 override TOML 을 덮어써서 비교할 수 있습니다.

- 세트 경로
  - [config/sets](/Users/plo/Documents/auto_coin_bot/config/sets)
  - 예시 실험 세트
    - [btc_atr_strict.toml](/Users/plo/Documents/auto_coin_bot/config/sets/experiments/btc_atr_strict.toml)
    - [alt_gap_volume_conservative.toml](/Users/plo/Documents/auto_coin_bot/config/sets/experiments/alt_gap_volume_conservative.toml)
- 단일 실행
  - `.venv/bin/python backtest_replay.py run ... --override-set experiments/btc_atr_strict.toml`
- 배치 실행
  - `.venv/bin/python backtest_report_runner.py weekly --override-set experiments/alt_gap_volume_conservative.toml`
- 결과 연결
  - `summary.json`, `batch_summary.json`, `reports/backtest_registry.json` 에 `override_set_names`, `override_paths` 가 함께 저장됩니다.

결과:
- 단일: `reports/backtests/...`
- 배치: `reports/backtest_batches/...`
- 인덱스: `reports/backtest_registry.json`
- 요약 지표: `win_rate_pct`, `max_drawdown_pct`, `sharpe_ratio`, `profit_factor`
- 실행 모델 옵션:
  - `--slippage-bps`
  - `--buy-fill-ratio`
  - `--sell-fill-ratio`
  - `--latency-ms`
  - `--orderbook-input` 또는 배치의 `--orderbook-dir`

상세 사용법은 [docs/BACKTEST_REPLAY_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/BACKTEST_REPLAY_GUIDE.md) 를 봅니다.

## 검토가 필요한 부분

- [tools/auto_recovery_watchdog.py](/Users/plo/Documents/auto_coin_bot/tools/auto_recovery_watchdog.py)는 쿨다운과 시간당 재기동 제한을 둔 자동복구까지만 수행합니다. 코드 수정까지 자동화하는 self-healing 은 별도 검증/승인 절차 없이는 운영에 넣지 않는 것이 안전합니다.
- [tools/healthcheck.py](/Users/plo/Documents/auto_coin_bot/tools/healthcheck.py)는 기본 `warning` 모드에서 `upbit_stream` 같은 경고성 경로를 전체 실패로 보지 않습니다. 자동복구는 WARN도 기본 복구 대상으로 보지만, 배포/장애 대응 시 `--mode strict` 기준을 언제 쓸지 운영 규칙을 더 명확히 정하면 좋습니다.
- README의 `Docker / Windows 실행파일` 같은 배포 안내는 현재 실제 릴리스 절차와 계속 맞는지 별도 확인이 필요합니다.
- 루트 호환 래퍼들은 아직 남아 있으므로, 실제 외부 사용 경로를 다시 확인한 뒤 정리 시점을 잡는 것이 좋습니다.
