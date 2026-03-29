# SWING BOT DESIGN

## 목적

이 문서는 현재 `auto_coin_bot` 의 단타/인트라데이 구조와 분리된 `장타/스윙 전용 봇` 설계 초안을 정리합니다.

핵심 원칙은 아래와 같습니다.

- 기존 단타 봇과 완전히 분리된 폴더에서 운영합니다.
- `.env`, 로그, 텔레그램 알림, 자동시작, 포트폴리오 배분도 분리합니다.
- 공통 유틸은 재사용하되, 전략 로직과 운영 설정은 별도로 둡니다.
- 초기에는 `BTC / ETH / XRP` 만 대상으로 시작합니다.

## 추천 폴더 구조

추천 새 폴더:

- `/Users/plo/Documents/auto_coin_bot_swing`

추천 내부 구조:

```text
auto_coin_bot_swing/
  README.md
  PLANS.md
  STRATEGY_DECISIONS.md
  .env
  .env.example
  bot_manager.py
  swing_settings.py
  okx_swing_bot.py
  upbit_swing_bot.py
  telegram_notifier.py
  telegram_command_listener.py
  analysis_log_collector.py
  analyze_logs.py
  analyze_strategy_logs.py
  structured_log_manager.py
  trade_history_logger.py
  portfolio_allocator.py
  bot_logger.py
  log_path_utils.py
  logs/
  analysis_logs/
  structured_logs/
  trade_logs/
  launchd/
  scripts/
```

## 왜 폴더를 분리해야 하나

- 단타와 장타는 타임프레임, 손절/익절, 포지션 유지 시간, 기대 손익비가 다릅니다.
- 같은 폴더에서 같이 돌리면 `.env` 와 로그 해석이 쉽게 섞입니다.
- 텔레그램 알림도 단타와 장타가 섞이면 운영 판단이 어려워집니다.
- 장타는 장시간 포지션 유지가 많아 단타용 쿨다운/피라미딩/부분청산 로직과 충돌할 수 있습니다.

## 공통 모듈 재사용 후보

그대로 재사용 추천:

- `bot_logger.py`
- `telegram_notifier.py`
- `telegram_command_listener.py`
- `structured_log_manager.py`
- `trade_history_logger.py`
- `portfolio_allocator.py`
- `log_path_utils.py`
- `analysis_log_collector.py`
- `analyze_logs.py`
- `analyze_strategy_logs.py`

부분 복사 후 장타 전용으로 분리 추천:

- `bot_manager.py`
  - 장타용 관리 대상만 남긴 별도 매니저로 복사
- `btc_trend_settings.py`
  - 장타용 `swing_settings.py` 로 분리
- `strategy_settings.py`
  - 알트 단타 전용 항목은 줄이고, 장타용 파라미터만 다시 정리

재사용 비추천:

- `ma_crossover_bot.py`
- `upbit_ma_crossover_bot.py`
- `okx_btc_ema_trend_bot.py`
- `upbit_btc_ema_trend_bot.py`

이 파일들은 현재 단타/인트라데이 로직이 많이 들어가 있어서, 장타에서는 참고만 하고 새로 만드는 편이 안전합니다.

## 공통 설정 분리 원칙

장타 폴더 `.env` 에서는 아래처럼 별도 접두사를 권장합니다.

- `SWING_...`
- `SWING_OKX_...`
- `SWING_UPBIT_...`

예시:

```env
SWING_VERSION=swing_v1
SWING_SYMBOLS_OKX=BTC/USDT,ETH/USDT,XRP/USDT
SWING_SYMBOLS_UPBIT=BTC/KRW,ETH/KRW,XRP/KRW
SWING_TIMEFRAME=1h
SWING_CONFIRM_TIMEFRAME=4h
SWING_SLOW_CONFIRM_TIMEFRAME=1d
SWING_FAST_EMA_PERIOD=20
SWING_SLOW_EMA_PERIOD=50
SWING_CONFIRM_EMA_PERIOD=50
SWING_MIN_VOLUME_RATIO=1.20
SWING_MIN_EMA_SPREAD_PCT=0.15
SWING_MIN_ATR_PCT=0.30
SWING_MAX_ATR_PCT=8.00
SWING_STOP_MODE=atr
SWING_STOP_ATR_MULTIPLE=2.2
SWING_TAKE_PROFIT_MODE=atr
SWING_TAKE_PROFIT_ATR_MULTIPLE=4.0
SWING_ENABLE_TRAILING=true
SWING_TRAILING_DRAWDOWN_PCT=1.8
SWING_ENABLE_BREAK_EVEN_GUARD=true
SWING_BREAK_EVEN_GUARD_MIN_MFE_PCT=1.2
SWING_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT=0.2
SWING_MIN_TRADE_INTERVAL_SEC=14400
SWING_POSITION_RATIO_MAP=BTC:0.50,ETH:0.30,XRP:0.20
```

## 초기 전략안

초기 전략은 `느린 추세 확인 + 적은 거래 수 + 손익비 우선` 으로 가는 것이 좋습니다.

### 1. 기본 컨셉

- 메인 진입 타임프레임: `1시간봉`
- 확인 타임프레임: `4시간봉`
- 상위 레짐 확인: `일봉`
- 전략 성격: 추세추종 스윙
- 목표: 거래 횟수 감소, 손절 횟수 감소, 1회 수익 크기 확대

### 2. 진입 조건

- `1시간봉` 빠른 EMA > 느린 EMA
- 현재가가 빠른 EMA 위
- `4시간봉`도 EMA 상승 정렬
- `일봉`이 최소 중립 이상
- 거래량 배수 기준 통과
- ATR 비율이 너무 낮지도 높지도 않을 것

추천 초기 조건:

- `EMA 20 / 50`
- `4시간봉 확인 EMA 50`
- `일봉 종가 >= 일봉 EMA 20`
- `min_volume_ratio >= 1.20`
- `min_ema_spread_pct >= 0.15`
- `min_atr_pct >= 0.30`

### 3. 청산 조건

우선순위:

1. 손절
2. 브레이크이븐 가드
3. 부분 익절
4. 트레일링 익절
5. 추세 종료 청산

추천 초기값:

- 손절: `ATR 2.2배`
- 1차 부분 익절: `+2.0% ~ +2.5%`
- 브레이크이븐 가드:
  - `MFE >= 1.2%`
  - 순익이 `+0.2%` 아래로 밀리면 청산
- 트레일링:
  - 활성화 후 `1.8%` 되돌림

### 4. 포지션 운영

- 단타처럼 분할 매수 횟수를 많이 늘리지 않음
- 초기 버전은 `1회 진입 + 선택적 1회 추가매수` 정도만 허용
- 추가매수는 손실 물타기보다 `수익 구간 피라미딩`이 더 적합

추천:

- 기본은 `추가매수 비활성`
- 안정화 후 `수익 +2% 이상`에서만 1회 소액 추가

## 코인별 초기 방향

### BTC

- 장타에서 가장 우선
- 가장 안정적인 기준 코인
- 초기 비중 최우선

추천:

- 목표 비중 `50%`
- 가장 먼저 실거래 검증

### ETH

- 추세가 좋을 때 BTC 다음으로 가장 자연스럽게 장타 적용 가능
- 단타에서는 아쉬운 손절 반납이 있었지만, 장타에서는 더 잘 맞을 가능성 있음

추천:

- 목표 비중 `30%`

### XRP

- 단타에서는 승률은 좋지만 이익 크기가 작았음
- 장타에서는 변동성이 커서 유리할 수도 있지만, 가짜 돌파가 많을 수 있음

추천:

- 목표 비중 `20%`
- 초기에는 비중 낮게 유지

## 운영 분리 방안

### 텔레그램

권장:

- 장타용 별도 봇 토큰 또는
- 최소한 메시지 prefix 분리

예:

- `[SWING-OKX] BTC/USDT 매수 체결`
- `[SWING-UPBIT] ETH/KRW 브레이크이븐 청산`

### 로그

반드시 별도 폴더:

- `logs/YYYY-MM-DD/*.log`
- `analysis_logs/YYYY-MM-DD/*.jsonl`
- `structured_logs/live/YYYY-MM-DD/*`
- `trade_logs/YYYY-MM-DD/trade_history.jsonl`

장타와 단타 로그를 섞지 않는 것이 핵심입니다.

### 자동시작

장타 폴더 전용:

- 별도 `launchd plist`
- 별도 `scripts/autostart_all.sh`
- 별도 `bot_manager.py`

## 구현 순서 추천

### 1단계

- 새 폴더 생성
- 공통 유틸 복사
- 장타용 `.env.example` 정리
- 장타용 `bot_manager.py` 구성

### 2단계

- `okx_swing_bot.py`
- `upbit_swing_bot.py`
- 1시간봉/4시간봉/일봉 확인 구조 구현

### 3단계

- 장타용 텔레그램 명령 리스너 연결
- 장타용 분석 수집/리포트 연결

### 4단계

- 소액 또는 모의 운영
- 2주 이상 로그 누적
- 이후 손절/익절/브레이크이븐 기준 재조정

## 초기 운영 판단

장타 봇은 지금 단타 봇의 “상위 타임프레임 강화판”이 아니라, 별도 전략으로 보는 편이 맞습니다.

즉 방향은:

- 단타 폴더: 빠른 진입, 빠른 청산, 운영 실험
- 장타 폴더: 적은 진입, 긴 보유, 손익비 확대

이렇게 완전히 역할을 나누는 것이 가장 안전합니다.
