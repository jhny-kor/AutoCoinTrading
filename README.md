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

### 수시 확인

- 텔레그램
  - `/status`
  - `/positions`
  - `/pnl`
  - `/analysis`
  - `/regime`
  - `/weekly`
  - `/last`
- 터미널
  - `.venv/bin/python bot_manager.py status`

### 정기 분석

- 시장 로그 요약: `.venv/bin/python analyze_logs.py`
- 전략 퍼널 분석: `.venv/bin/python analyze_strategy_logs.py`
- CSV 저장: `.venv/bin/python analyze_strategy_logs.py --csv reports/strategy_funnel.csv`

## 전략 요약

### 알트

- 1분봉 기반
- 상위 타임프레임 필터
- 거래량/변동성/신호 점수 필터
- 부분익절/부분손절
- 브레이크이븐/순익 보호
- 레짐 기반 전략 라우터

### BTC

- 5분봉 EMA + 15분봉 확인
- ATR 기반 손절/익절
- 부분익절 + 트레일링
- 순익 보호 익절
- 피라미딩 1회 제한
- 레짐 기반 전략 라우터

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
  - BTC `60%`
  - ETH `30%`
  - XRP `10%`
- 계산 기준
  - 현재 가용 현금
  - 코인별 남아 있는 누적 투입 원가
- 결과
  - 목표 비중을 넘는 코인은 신규 매수 제한
  - 부족한 코인만 목표 비중 안에서 추가 진입 허용

동적 오버웨이트는 거래량/추세 품질이 매우 좋을 때만 보수적으로 `+5%`까지 허용합니다.

## 로그 구조

- 운영 로그: `logs/YYYY-MM-DD/*.log`
- 분석 로그: `analysis_logs/YYYY-MM-DD/*.jsonl`
- 체결 로그: `trade_logs/YYYY-MM-DD/trade_history.jsonl`
- 전략 로그: `structured_logs/live/YYYY-MM-DD/*/strategy.jsonl`
- 시스템 로그: `structured_logs/live/YYYY-MM-DD/*/system.jsonl`
- 체결 구조화 로그: `structured_logs/live/YYYY-MM-DD/*/trade.jsonl`
- 업비트 웹소켓 런타임: `logs/runtime/upbit_ws/*`

오래된 로그는 최근 7일 원본 유지 후 `tar.gz` 로 압축합니다.

- 상태 확인: `.venv/bin/python log_archive_manager.py status`
- 수동 압축: `.venv/bin/python log_archive_manager.py compress`

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
- `/last`
- `/help`

## 테스트와 헬스체크

- 전체 테스트: `.venv/bin/python -m unittest discover -s tests -v`
- 운영 헬스체크: `.venv/bin/python tools/healthcheck.py`
- JSON 헬스체크: `.venv/bin/python tools/healthcheck.py --json`
- strict 모드: `.venv/bin/python tools/healthcheck.py --mode strict`

현재 테스트 범위:
- 알트 신호 계산
- 알트 청산 보호
- BTC 포지션 평가
- BTC/알트 레짐 라우터
- 상태 복구
- 퍼널 생성기
- 진입 상태 머신
- 체결률 기반 실행 품질 가드
- 포트폴리오 배분
- 운영 헬스체크

## 백테스트

- 단일 리플레이: `.venv/bin/python backtest_replay.py`
- 배치 리포트: `.venv/bin/python backtest_report_runner.py weekly`
- 레지스트리 갱신: `.venv/bin/python tools/update_backtest_registry.py`

결과:
- 단일: `reports/backtests/...`
- 배치: `reports/backtest_batches/...`
- 인덱스: `reports/backtest_registry.json`

상세 사용법은 [docs/BACKTEST_REPLAY_GUIDE.md](/Users/plo/Documents/auto_coin_bot/docs/BACKTEST_REPLAY_GUIDE.md) 를 봅니다.

## 검토가 필요한 부분

- [tools/healthcheck.py](/Users/plo/Documents/auto_coin_bot/tools/healthcheck.py)는 기본 `warning` 모드에서 `upbit_stream` 같은 비핵심 경로를 전체 실패로 보지 않습니다. 배포/장애 대응 시에는 `--mode strict` 기준을 언제 쓸지 운영 규칙을 더 명확히 정하면 좋습니다.
- README의 `Docker / Windows 실행파일` 같은 배포 안내는 현재 실제 릴리스 절차와 계속 맞는지 별도 확인이 필요합니다.
- 루트 호환 래퍼들은 아직 남아 있으므로, 실제 외부 사용 경로를 다시 확인한 뒤 정리 시점을 잡는 것이 좋습니다.
