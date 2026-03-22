# MODULE GUIDE

## 문서 목적

이 문서는 현재 `auto_coin_bot` 프로젝트의 모듈을 `기능 단위`로 빠르게 찾을 수 있도록 정리한 안내서입니다.

기준 원칙:

- 현재 폴더는 `단타/인트라데이 전용`입니다.
- 장타/스윙 전용 설계는 별도 폴더 `/Users/plo/Documents/auto_coin_bot_swing` 에서 관리합니다.
- 같은 기능이라도 `공통 모듈`, `거래소별 모듈`, `전략별 모듈`을 구분해서 봅니다.

## 1. 공통 설정 / 전략 로더

### 공통 전략 설정

- [strategy_settings.py](/Users/plo/Documents/auto_coin_bot/strategy_settings.py)
  - 알트 공통 전략 설정 로더
  - 공통 전략 값, 심볼별 이격도/익절률/손절률/거래량 기준
  - 감시 심볼 목록과 운영 심볼 목록 로드

- [btc_trend_settings.py](/Users/plo/Documents/auto_coin_bot/btc_trend_settings.py)
  - BTC 전용 EMA 추세추종 설정 로더
  - EMA, ATR, 거래량, 트레일링, 부분 익절, 순익 보호, 피라미딩 설정 관리

### 환경 변수

- [.env.example](/Users/plo/Documents/auto_coin_bot/.env.example)
  - 실제로 사용하는 키 기준 예시
  - 새 설정을 추가할 때 같이 갱신하는 기준 문서

## 2. 공통 로그 / 분석 모듈

### 텍스트 로그

- [bot_logger.py](/Users/plo/Documents/auto_coin_bot/bot_logger.py)
  - 콘솔 출력 + 날짜별 파일 로그 공통 처리
  - 배너 로그, 색상 로그, 신호 로그 출력

- [log_path_utils.py](/Users/plo/Documents/auto_coin_bot/log_path_utils.py)
  - 날짜별 로그 경로 생성
  - 최신 파일 탐색, 여러 파일 라인 읽기

### 구조화 로그

- [structured_log_manager.py](/Users/plo/Documents/auto_coin_bot/structured_log_manager.py)
  - `system / strategy / trade` 구조화 로그 기록
  - 퍼널 단계별 통과/차단 사유 집계
  - `summary_1h` 시간 버킷 요약 생성

- [trade_history_logger.py](/Users/plo/Documents/auto_coin_bot/trade_history_logger.py)
  - 통합 체결 이력 JSONL 기록
  - 실현 손익, 순손익, MFE/MAE, 보유 시간 기록
  - 주문 ID, API 지연, 체결 비율, 슬리피지 등 실행 품질 기록

### 분석 수집 / 분석 도구

- [analysis_log_collector.py](/Users/plo/Documents/auto_coin_bot/analysis_log_collector.py)
  - 시장 상태 분석용 JSONL 수집기
  - 이격도, 변동성, 거래량, RSI, 호가 미시구조 기록

- [analyze_logs.py](/Users/plo/Documents/auto_coin_bot/analyze_logs.py)
  - 분석용 시장 로그를 거래소/심볼별로 요약

- [analyze_strategy_logs.py](/Users/plo/Documents/auto_coin_bot/analyze_strategy_logs.py)
  - 구조화 전략 로그와 체결 로그를 함께 읽어 퍼널 병목, 거래 품질, 시간대 성과를 집계

## 3. 공통 운영 / 제어 모듈

### 봇 제어

- [bot_manager.py](/Users/plo/Documents/auto_coin_bot/bot_manager.py)
  - 단타 프로젝트 관리 대상 프로세스 시작/중지/상태 확인
  - PID 파일 기반 보조 상태 추적
  - 부팅 자동시작 시 `ps` 권한 이슈 대응 포함

### 텔레그램 운영

- [telegram_notifier.py](/Users/plo/Documents/auto_coin_bot/telegram_notifier.py)
  - 매수/매도/손절/에러/운영 알림 전송
  - 숫자 3자리 쉼표 포맷
  - 에러 인시던트 버튼 메시지 전송

- [telegram_command_listener.py](/Users/plo/Documents/auto_coin_bot/telegram_command_listener.py)
  - `/status`, `/positions`, `/pnl`, `/analysis`, `/weekly`, `/last`
  - 일일/주간 리포트 자동 전송
  - 현재 시장 해석과 전략 추천 문구 생성

- [incident_manager.py](/Users/plo/Documents/auto_coin_bot/incident_manager.py)
  - 에러 인시던트 기록
  - 재기동/상세 보기/수정 요청/무시 상태 관리

## 4. 공통 포트폴리오 / 계산 모듈

- [portfolio_allocator.py](/Users/plo/Documents/auto_coin_bot/portfolio_allocator.py)
  - 목표 비중 기반 신규 매수 예산 제한
  - 누적 투입 원가 기준 포트폴리오 계산
  - 거래량 강세 시 보수적 동적 오버웨이트

## 5. 거래소별 모듈

### OKX 공통 기능

- [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
  - 현재는 `OKX 알트 전략` 본체이면서
  - 동시에 아래 공통 기능도 일부 포함합니다.
  - OKX 클라이언트 생성
  - OKX 현물 잔고 조회
  - OKX 시장가 주문 공통 처리
  - OKX OHLCV 조회 보조

### 업비트 공통 기능

- [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
  - 현재는 `업비트 알트 전략` 본체이면서
  - 동시에 아래 공통 기능도 일부 포함합니다.
  - 업비트 클라이언트 생성
  - 업비트 현물 잔고 조회
  - 업비트 1호가 조회
  - 업비트 OHLCV 조회
  - 업비트 `429` 재시도/backoff
  - 업비트 KRW 주문 버퍼
  - 업비트 시장가 매수 공통 helper

## 6. 전략별 본체 모듈

### 알트 전략

- [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
  - OKX 알트 단타 전략
  - 1분봉 MA 돌파
  - 부분 익절 / 부분 손절 / 순익 보호 익절 / 브레이크이븐 가드
  - 포트폴리오 배분 반영

- [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
  - 업비트 알트 단타 전략
  - 1분봉 MA 돌파
  - 부분 익절 / 부분 손절 / 순익 보호 익절 / 브레이크이븐 가드
  - 업비트 전용 주문 버퍼 / 재시도 반영

### BTC 전략

- [okx_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/okx_btc_ema_trend_bot.py)
  - OKX BTC EMA 추세추종 전략
  - 5분봉 + 15분봉 확인
  - 부분 익절 / 순익 보호 / 트레일링 / 강한 상방 조정 보유

- [upbit_btc_ema_trend_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_btc_ema_trend_bot.py)
  - 업비트 BTC EMA 추세추종 전략
  - 5분봉 + 15분봉 확인
  - 업비트 전용 주문 버퍼 / 재시도 반영
  - 부분 익절 / 순익 보호 / 트레일링 / 강한 상방 조정 보유

## 7. 로그/운영 보조 스크립트

- [migrate_logs_to_dated_dirs.py](/Users/plo/Documents/auto_coin_bot/migrate_logs_to_dated_dirs.py)
  - 기존 로그를 날짜별 폴더 구조로 이동

- [log_archive_manager.py](/Users/plo/Documents/auto_coin_bot/log_archive_manager.py)
  - 오래된 로그 압축 보관

## 8. 현재 구조에서 기억할 점

- 공통 기능이 아직 일부 전략 파일 안에 함께 들어 있습니다.
  - 예: 업비트 공통 helper 일부는 [upbit_ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/upbit_ma_crossover_bot.py)
  - 예: OKX 공통 helper 일부는 [ma_crossover_bot.py](/Users/plo/Documents/auto_coin_bot/ma_crossover_bot.py)
- 즉 현재 구조는 완전한 레이어 분리라기보다 `전략 본체 + 거래소 공통 helper 일부 포함` 형태입니다.

## 9. 앞으로 모듈 분리하면 좋은 후보

- 업비트 전용 공통 helper 분리
  - 예: `upbit_exchange_utils.py`
- OKX 전용 공통 helper 분리
  - 예: `okx_exchange_utils.py`
- 공통 시장 지표 계산 분리
  - 예: `market_indicators.py`
- 공통 청산 보조 로직 분리
  - 예: `exit_helpers.py`

현재는 안정 운영이 우선이라 전략 파일 안에 일부 공통 기능이 남아 있지만,
앞으로 리팩터링할 때는 위 방향으로 나누면 구조가 더 읽기 쉬워집니다.
