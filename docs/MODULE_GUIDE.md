# MODULE GUIDE

## 문서 목적

이 문서는 현재 `auto_coin_bot` 프로젝트의 모듈을 `기능 단위`로 빠르게 찾을 수 있도록 정리한 안내서입니다.

기준 원칙:

- 현재 폴더는 `단타/인트라데이 전용`입니다.
- 장타/스윙 전용 설계는 별도 폴더 `../auto_coin_bot_swing` 에서 관리합니다.
- 같은 기능이라도 `공통 모듈`, `거래소별 모듈`, `전략별 모듈`을 구분해서 봅니다.

## 1. 공통 설정 / 전략 로더

### 공통 전략 설정

- [settings/strategy_settings.py](settings/strategy_settings.py)
  - 알트 공통 전략 설정 로더
  - 공통 전략 값, 심볼별 이격도/익절률/손절률/거래량 기준
  - 감시 심볼 목록과 운영 심볼 목록 로드

- [settings/btc_trend_settings.py](settings/btc_trend_settings.py)
  - BTC 전용 EMA 추세추종 설정 로더
  - EMA, ATR, 거래량, 트레일링, 부분 익절, 순익 보호, 피라미딩 설정 관리

### 환경 변수

- [config/runtime.toml](config/runtime.toml)
  - canonical 운영 설정 파일
  - 전략, 리스크, 포트폴리오, 텔레그램 일반 설정의 기준값

- [config/runtime.example.toml](config/runtime.example.toml)
  - canonical 운영 설정 예시 파일

- [config/runtime.local.example.toml](config/runtime.local.example.toml)
  - local TOML override 예시 파일

- [config/sets](config/sets)
  - canonical 전략 세트 TOML 모음
  - 보수형/중간형/혼합형 세트 정의

- [.env.example](.env.example)
  - legacy 전체 예시 파일
  - split env / TOML 을 쓰지 않는 환경용 호환 예시

- [.env.settings.example](.env.settings.example)
  - 운영 override 예시 파일

- [.env.secrets.example](.env.secrets.example)
  - 비밀정보 예시 파일

## 2. 공통 로그 / 분석 모듈

### 텍스트 로그

- [bot_logger.py](bot_logger.py)
  - 콘솔 출력 + 날짜별 파일 로그 공통 처리
  - 배너 로그, 색상 로그, 신호 로그 출력

- [log_path_utils.py](log_path_utils.py)
  - 날짜별 로그 경로 생성
  - 최신 파일 탐색, 여러 파일 라인 읽기

### 구조화 로그

- [structured_log_manager.py](structured_log_manager.py)
  - `system / strategy / trade` 구조화 로그 기록
  - 퍼널 단계별 통과/차단 사유 집계
  - `summary_1h` 시간 버킷 요약 생성

- [trade_history_logger.py](trade_history_logger.py)
  - 통합 체결 이력 JSONL 기록
  - 실현 손익, 순손익, MFE/MAE, 보유 시간 기록
  - 주문 ID, API 지연, 체결 비율, 슬리피지 등 실행 품질 기록

### 분석 수집 / 분석 도구

- [analysis_log_collector.py](analysis_log_collector.py)
  - 시장 상태 분석용 JSONL 수집기
  - 이격도, 변동성, 거래량, RSI, 호가 미시구조 기록

- [upbit_market_data_stream.py](upbit_market_data_stream.py)
  - 업비트 공개/인증 웹소켓 시장데이터 수집기
  - 공개: trade / orderbook / candle.1m
  - 인증: myOrder / myAsset
  - 최신 스냅샷, 1분 캔들, private 이벤트 파일 저장
  - 5분/15분은 로컬 1분봉 리샘플을 전략/provider가 재사용

- [analyze_logs.py](analyze_logs.py)
  - 분석용 시장 로그를 거래소/심볼별로 요약

- [analyze_strategy_logs.py](analyze_strategy_logs.py)
  - 구조화 전략 로그와 체결 로그를 함께 읽어 퍼널 병목, 거래 품질, 시간대 성과를 집계

- [backtest_replay.py](backtest_replay.py)
  - 공개 OHLCV 저장용 `fetch` 서브커맨드 제공
  - 로컬 OHLCV 파일 기준 오프라인 전략 리플레이 실행
  - 알트 MA 전략과 BTC EMA 전략의 요약/거래 로그 출력

- [backtest_report_runner.py](backtest_report_runner.py)
  - 주간 배치 백테스트와 설정 변경 전후 비교를 묶어서 실행
  - fetch -> run -> compare 흐름을 심볼별로 자동 수행
  - 배치 요약과 전후 diff 요약 Markdown/JSON 생성

- [tools/apply_strategy_set.py](tools/apply_strategy_set.py)
  - `config/sets` 아래 TOML 세트를 현재 `config/runtime.local.toml` 에 반영
  - 보수형/중간형/혼합형 별칭 지원
  - dry-run 으로 변경될 `section.key` 미리보기 지원

- [tools/update_backtest_registry.py](tools/update_backtest_registry.py)
  - `reports/backtest_batches` 아래 batch/diff 결과를 인덱싱
  - `reports/backtest_registry.json` 자동 갱신
  - label, path, symbols, before/after 경로를 한 파일에서 조회 가능

- [update_backtest_registry.py](update_backtest_registry.py)
  - 루트 호환 실행 진입점
  - `tools.update_backtest_registry` 를 그대로 실행

- [compare_backtest_to_live.py](compare_backtest_to_live.py)
  - 백테스트 결과와 실거래 체결 이력을 같은 기준으로 비교
  - 승률, 순손익, 평균 손익률, 종료 사유를 함께 요약

## 3. 공통 운영 / 제어 모듈

### 봇 제어

- [bot_manager.py](bot_manager.py)
  - 단타 프로젝트 관리 대상 프로세스 시작/중지/상태 확인
  - PID 파일 기반 보조 상태 추적
  - 부팅 자동시작 시 `ps` 권한 이슈 대응 포함
  - defunct 프로세스가 pidfile 에 남아 재시작을 막지 않도록 `ps stat` 기반 정리 수행

### 텔레그램 운영

- [telegram_notifier.py](telegram_notifier.py)
  - 매수/매도/손절/에러/운영 알림 전송
  - 숫자 3자리 쉼표 포맷
  - 에러 인시던트 버튼 메시지 전송

- [telegram_command_listener.py](telegram_command_listener.py)
  - `/status`, `/positions`, `/pnl`, `/analysis`, `/weekly`, `/last`
  - 일일/주간 리포트 자동 전송
  - 현재 시장 해석과 전략 추천 문구 생성

- [reporting/listener_runtime.py](reporting/listener_runtime.py)
  - 텔레그램 리스너 설정 로드
  - polling, offset 저장, 예약 리포트 상태 저장 공통 처리
  - 리스너 본체에서 transport/runtime 보조 역할 분리

- [reporting/position_snapshot.py](reporting/position_snapshot.py)
  - `/positions` 응답용 거래소 잔고/평가 요약 공통 처리
  - 최신 추정 진입가와 복구 진입가 합성
  - 거래소 조회 실패 진단 문구 공통 처리

- [incident_manager.py](incident_manager.py)
  - 에러 인시던트 기록
  - 재기동/상세 보기/수정 요청/무시 상태 관리

## 4. 공통 포트폴리오 / 계산 모듈

- [portfolio_allocator.py](portfolio_allocator.py)
  - 목표 비중 기반 신규 매수 예산 제한
  - 누적 투입 원가 기준 포트폴리오 계산
  - 거래량 강세 시 보수적 동적 오버웨이트

- [core/risk/allocation.py](core/risk/allocation.py)
  - allocation score 계산
  - 알트/BTC 신규 진입 비중 계산 결과 객체 제공
  - 알트: 심볼 레짐, BTC 레짐, BTC ATR, ALT ATR, score, probe 보정 순서 관리
  - BTC: 심볼 레짐, BTC ATR, score, probe 보정 순서 관리
  - OKX/업비트 봇의 포지션 비중, allocation score, 포트폴리오 예산 로그 문구 공통화

- [core/risk/alt_exit.py](core/risk/alt_exit.py)
  - 알트 포지션 PnL/MFE/MAE 계산
  - 수수료 반영 순익 보호, 브레이크이븐, 거래량 급감 청산 판단
  - 무포지션 기본 지표와 부분익절/부분손절 pending 정책 계산
  - 매도 주문 직전 청산 비율과 reason key 결정
  - OKX 최소 수량/업비트 최소 금액에 걸리는 알트 부분청산의 전량 전환 또는 스킵 정책 결정
  - OKX/업비트 알트 봇의 청산 준비 상태 공통화

- [core/strategy/sol_probe.py](core/strategy/sol_probe.py)
  - SOL 제한형 probe 진입 허용 판단
  - SOL probe 대상 심볼의 단일 포지션/진입 횟수 보정
  - SOL probe 허용 시 `LOW_ENERGY`와 심볼 레짐 차단 우회 상태 공통 계산
  - SOL probe 최대 보유 시간 청산 판단과 거래소 공통 로그 문구 제공

- [core/strategy/funnels.py](core/strategy/funnels.py)
  - 알트/BTC 진입과 청산 퍼널 단계 생성
  - 알트 진입 기본 단계와 SOL/레짐/상관/체결/타이밍 가드 단계 공통화
  - OKX/업비트 알트 봇은 거래소별 주문 단계만 각 봇에 남기고 공통 가드는 이 모듈을 사용

- [core/strategy/alt_loop.py](core/strategy/alt_loop.py)
  - 알트 봇 루프의 진입/청산 퍼널 실행 stage 공통화
  - OKX/업비트 알트 봇의 `run_bot()`에서 반복되던 `buy_ready`/`sell_ready` 실행 코드를 분리

- [core/strategy/exit_reasons.py](core/strategy/exit_reasons.py)
  - 알트/BTC 청산 퍼널이 통과했을 때 기록할 대표 `ready_reason` 우선순위 결정
  - 손절, 부분익절, 순익보호, 트레일링, 시간청산 같은 청산 사유 우선순위를 봇 본문 밖에서 고정

- [state_recovery.py](state_recovery.py)
  - trade_history 기준 평균 진입가와 내부 상태 복구
  - 프로그램별 당일 실현 손익 재계산 helper 제공

- [core/runtime/bootstrap.py](core/runtime/bootstrap.py)
  - 알트/BTC 봇 초기 런타임 상태 복구 공통 helper
  - `run_bot()` 시작 구간의 중복 상태 구성 로직 축소

- [core/positions/lifecycle.py](core/positions/lifecycle.py)
  - 알트 매수 체결 후 평균 진입가, 진입 카운트, 고저가 상태 갱신
  - 알트 매도 체결 후 남은 수량, 진입 카운트, 손절 컨텍스트, 부분청산 완료 플래그 갱신
  - BTC 신규진입/추가매수 후 평균 진입가, 포지션 ID, trailing 초기값, 고저가, add-on count 계산
  - 알트/BTC 포지션 종료 후 내부 상태 초기화
  - OKX/업비트 알트 봇의 포지션 lifecycle 상태 변경 공통화

- [core/execution/order_adapters.py](core/execution/order_adapters.py)
  - OKX/업비트 시장가 주문 제출 어댑터
  - 주문 요청/응답 시각 기록, OKX `tgtCcy` 선택, 업비트 private 이벤트 보강과 캐시 무효화 후처리 공통화

- [core/execution/order_logging.py](core/execution/order_logging.py)
  - 알트/BTC 공통 `order_requested` strategy 로그 입력
  - 체결 후 strategy/trade 로그를 같은 actual/metrics 로 함께 남기는 표준 helper 제공

- [core/notifications/trade_messages.py](core/notifications/trade_messages.py)
  - OKX/업비트 체결 텔레그램 메시지 본문 생성
  - 매수 금액, 매도 금액, 체결가, 손익 금액의 거래소별 자리수를 설정으로 분리

- [core/runtime/program_registry.py](core/runtime/program_registry.py)
  - 관리 대상 프로그램 메타데이터 단일 소스
  - `bot_manager`, 헬스체크, 텔레그램 리포트가 공유하는 이름/스크립트/레이블 정의

## 5. 거래소별 모듈

### OKX 공통 기능

- [ma_crossover_bot.py](ma_crossover_bot.py)
  - 현재는 `OKX 알트 전략` 본체이면서
  - 동시에 아래 공통 기능도 일부 포함합니다.
  - OKX 클라이언트 생성
  - OKX 현물 잔고 조회
  - OKX 시장가 주문 공통 처리
  - OKX OHLCV 조회 보조

### 업비트 공통 기능

- [upbit_ma_crossover_bot.py](upbit_ma_crossover_bot.py)
  - 현재는 `업비트 알트 전략` 본체이면서
  - 동시에 아래 공통 기능도 일부 포함합니다.
  - 업비트 클라이언트 생성
  - 업비트 현물 잔고 조회
  - 업비트 1호가 조회
  - 업비트 OHLCV 조회
  - 업비트 `429` 재시도/backoff
  - 업비트 잔고/호가 짧은 TTL 캐시와 주문 직후 캐시 무효화
  - 업비트 KRW 주문 버퍼

- [core/execution/upbit.py](core/execution/upbit.py)
  - 업비트 공통 실행 유틸
  - 요청 재시도, KRW 주문 버퍼, 시장가 매수/매도 공통 경로
  - 잔고/호가 짧은 캐시, 최소 주문 경계 근처 전용 best bid 재조회
  - 업비트 시장가 매수 공통 helper

- [core/market_data](core/market_data)
  - 업비트 웹소켓 시장데이터 공통 계층
  - 최신 상태 메모리 저장소
  - 최신 스냅샷/1분 캔들 파일 저장
  - 공개/인증 웹소켓 연결/재연결 처리
  - 5분/15분 리샘플과 private myOrder/myAsset provider 처리
  - best bid, 1분봉, 5분/15분, private latest 재사용

## 6. 전략별 본체 모듈

### 알트 전략

- [ma_crossover_bot.py](ma_crossover_bot.py)
  - OKX 알트 단타 전략
  - 1분봉 MA 돌파
  - 부분 익절 / 부분 손절 / 순익 보호 익절 / 브레이크이븐 가드
  - 포트폴리오 배분 반영

- [upbit_ma_crossover_bot.py](upbit_ma_crossover_bot.py)
  - 업비트 알트 단타 전략
  - 1분봉 MA 돌파
  - 부분 익절 / 부분 손절 / 순익 보호 익절 / 브레이크이븐 가드
  - 업비트 전용 주문 버퍼 / 재시도 반영

### BTC 전략

- [okx_btc_ema_trend_bot.py](okx_btc_ema_trend_bot.py)
  - OKX BTC EMA 추세추종 전략
  - 5분봉 + 15분봉 확인
  - 부분 익절 / 순익 보호 / 트레일링 / 강한 상방 조정 보유

- [upbit_btc_ema_trend_bot.py](upbit_btc_ema_trend_bot.py)
  - 업비트 BTC EMA 추세추종 전략
  - 5분봉 + 15분봉 확인
  - 업비트 전용 주문 버퍼 / 재시도 반영
  - 부분 익절 / 순익 보호 / 트레일링 / 강한 상방 조정 보유

## 7. 로그/운영 보조 스크립트

- [migrate_logs_to_dated_dirs.py](migrate_logs_to_dated_dirs.py)
  - 기존 로그를 날짜별 폴더 구조로 이동

- [log_archive_manager.py](log_archive_manager.py)
  - 오래된 로그 압축 보관

## 8. 현재 구조에서 기억할 점

- 주문 API 차이, 거래소별 캐시 처리, 실행 순서가 중요한 코드는 의도적으로 각 봇 또는 거래소 실행 모듈에 남깁니다.
- 반복 로직은 `core/strategy`, `core/risk`, `core/positions`, `core/execution` helper 로 분리했고, 문서화된 리팩토링 후보는 현재 남아 있지 않습니다.

## 9. 리팩토링 진행 현황

2026-05-14 기준으로 문서화된 P1, P2, P3 후보는 운영 전략 값을 바꾸지 않는 범위에서 모두 공통 helper 로 반영했습니다.

| 우선순위 | 완료 항목 | 대상 | 기준 |
| --- | --- | --- | --- |
| P1 | 알트 매수/매도 체결 상태 갱신 공통화 | [core/positions/lifecycle.py](core/positions/lifecycle.py) | 매수 평균가/고저가, 매도 잔량/진입 카운트/부분청산 플래그를 helper 로 갱신 |
| P1 | 체결 알림 문구 formatter 공통화 | [core/notifications/trade_messages.py](core/notifications/trade_messages.py) | OKX/업비트 메시지 구조를 공유하고 숫자 자리수만 거래소별 설정 |
| P2 | 주문 요청/체결 로그 공통화 | [core/execution/order_logging.py](core/execution/order_logging.py) | 알트/BTC `order_requested`, `filled`, `log_trade_event` 입력 조립을 표준화 |
| P2 | 실주문 API 호출 어댑터 정리 | [core/execution/order_adapters.py](core/execution/order_adapters.py) | OKX `tgtCcy`, 업비트 private 이벤트 보강/캐시 무효화, 주문 타이밍 기록을 어댑터로 표준화 |
| P2 | 매도 주문 최소금액/최소수량 fallback 정책 분리 | [core/risk/alt_exit.py](core/risk/alt_exit.py) | OKX 수량 기준과 업비트 금액 기준을 별도 helper 로 처리 |
| P3 | 청산 퍼널 ready reason helper 적용 | [core/strategy/exit_reasons.py](core/strategy/exit_reasons.py) | 알트/BTC 청산 사유 우선순위를 공통 함수로 고정해 `run_bot()` 분기를 축소 |
| P3 | 알트 루프 진입/청산 퍼널 단계 helper 적용 | [core/strategy/alt_loop.py](core/strategy/alt_loop.py) | 알트 `run_bot()`의 `buy_ready`/`sell_ready` 퍼널 실행 코드를 공통화 |
| P3 | BTC 매수/추가매수 lifecycle helper 확대 | [core/positions/lifecycle.py](core/positions/lifecycle.py) | BTC 신규진입/추가매수 후 평균가, trailing 초기값, add-on count 계산을 공통화 |

현재 남은 리팩토링 후보:

- 없음. 새 후보는 실거래 로그, 테스트 중복, 또는 같은 파일을 반복 수정해야 하는 근거가 생길 때 추가합니다.

진행 원칙:

- 주문 API 호출, 업비트 private 이벤트 보강, 캐시 무효화, OKX/업비트 최소 주문 판정처럼 거래소별 차이가 명확한 부분은 봇 파일에 유지합니다.
- 평균 진입가, 진입/청산 카운트, reason key, 구조화 로그 입력처럼 같은 규칙이 반복되는 부분만 공통 모듈로 옮깁니다.
- 각 패스는 `tests/`에 동작 고정 테스트를 먼저 추가한 뒤, `py_compile`, `compileall`, 전체 `unittest discover`로 검증합니다.

## 10. 분석 지표 의미

### RSI

- 의미: 최근 상승/하락 힘의 강도를 `0 ~ 100` 범위로 보는 지표
- 일반 해석
  - `50` 근처: 중립
  - `70` 이상: 과열 가능성
  - `30` 이하: 과매도 가능성
- 현재 프로젝트 활용
  - `80` 이상이면 `EXHAUSTION_RISK` 후보
  - `90` 이상이면 `OVERHEATED` 후보

### 공개 준비

- 필드: `public_buy_ready`
- 의미: 분석 수집기 공개 기준으로 “겉으로 보기엔 매수 준비가 됐는가”
- 일반 해석
  - `True`: 공개 기준상 진입 후보
  - `False`: 아직 거래량, 변동성, 신호 강도, 상위 추세 등 뭔가 부족
- 현재 프로젝트 활용
  - 저에너지 장 판별에서 `ready_count == 0` 조건에 사용
  - `BREAKOUT_ATTEMPT` 후보 판단에도 사용

### 평균 절대 변화율

- 필드: `avg_abs_change_pct`
- 의미: 최근 캔들들이 평균적으로 몇 %씩 움직였는지 보는 지표
- 방향은 무시하고 “움직임 크기”만 봄
- 일반 해석
  - 낮음: 시장 에너지 약함
  - 높음: 변동성 큼
- 현재 프로젝트 활용
  - `LOW_ENERGY`, `TRENDING`, `OVERHEATED` 판별에 사용

## 10.1 자주 보는 거래 지표 용어

### `htf_bearish`

- 의미: 상위 타임프레임이 하락 추세 쪽에 있다는 뜻
- 해석
  - 짧은 봉에서는 반등처럼 보여도 큰 흐름은 아직 약한 상태일 수 있음
- 현재 프로젝트 활용
  - `XRP/KRW` 같은 특정 심볼은 `htf_bearish=True`일 때 신규 진입을 차단

### `MFE`

- 의미: `Maximum Favorable Excursion`
- 해석
  - 진입 후 청산 전까지 가장 유리했던 최대 수익 구간(%)
  - `MFE`가 매우 낮으면 진입 직후 거의 못 뻗은 거래로 해석 가능
- 현재 프로젝트 활용
  - 진입 품질 점검
  - 브레이크이븐 가드 발동 기준

### `MAE`

- 의미: `Maximum Adverse Excursion`
- 해석
  - 진입 후 청산 전까지 가장 불리했던 최대 손실 구간(%)
  - `MAE`가 크면 손절 전 흔들림이 큰 거래로 해석 가능
- 현재 프로젝트 활용
  - 손절 폭과 변동성 허용 범위 점검

## 11. 심볼별 레짐 기준표

현재 단타 프로젝트는 심볼별 최신 분석 로그 기준으로 아래 보수형 8단계 레짐을 분류합니다.

BTC 와 알트는 [core/strategy/regime_router.py](core/strategy/regime_router.py) 에서 먼저
- `skip`
- `breakout`
- `trend_follow`
중 하나로 전략 경로를 선택한 뒤, 기존 전략 엔진을 실행합니다.

### `LOW_ENERGY`

- 의미: 거래량과 변동성이 약해 추세추종 단타가 잘 안 먹히는 상태
- 대표 기준
  - 평균 거래량 배수 낮음
  - 평균 절대 변화율 낮음
  - `public_buy_ready == 0`
- 대응
  - 신규 진입 차단

### `CHOPPY_LOW_VOL`

- 의미: 방향성도 약하고 거래량도 약한 횡보 구간
- 대표 기준
  - `ADX` 낮음
  - 평균 절대 변화율 낮음
- 대응
  - 신규 진입 차단

### `CHOPPY_HIGH_VOL`

- 의미: 방향성은 약하지만 흔들림과 거래량은 살아 있는 혼조 구간
- 대표 기준
  - `ADX` 낮음
  - 평균 절대 변화율은 상대적으로 높음
- 대응
  - 강한 신호 + fresh cross + 더 긴 확인 루프만 허용

### `BREAKOUT_ATTEMPT`

- 의미: 거래량과 이격도가 붙으면서 돌파를 시도하는 구간
- 대표 기준
  - 거래량 증가
  - 이격도 확대
  - 또는 `public_buy_ready=True`
- 대응
  - 강한 신호만 허용

### `TRENDING_EARLY`

- 의미: 상위 추세 동의와 함께 막 추세가 뻗기 시작하는 초반 구간
- 대표 기준
  - 거래량 배수 적절
  - 평균 절대 변화율 적절
  - 상위 추세 동의
- 대응
  - 기본 전략 유지

### `TRENDING_MATURE`

- 의미: 추세는 강하지만 이미 상당 부분 진행된 구간
- 대표 기준
  - 상위 추세 동의
  - 거래량/이격도/RSI 중 일부가 확장 상태
- 대응
  - 신규 진입은 유지하되 추격은 보수화
  - 피라미딩은 제한적으로만 허용

### `EXHAUSTION_RISK`

- 의미: 많이 오른 뒤 힘이 빠질 위험이 큰 구간
- 대표 기준
  - `RSI` 높음
  - MA 위에 있지만 `public_buy_ready`는 없음
- 대응
  - 신규 진입 차단
  - 보유분은 순익 보호 우선

### `OVERHEATED`

- 의미: 과열/추격 위험이 큰 구간
- 대표 기준
  - `RSI` 매우 높음
  - 거래량도 높음
- 대응
  - 신규 진입 차단
  - 추격 금지

## 11.1 BTC 진입 확인 루프

BTC 는 단발 신호에 바로 진입하지 않고, 같은 방향 후보가 연속 확인될 때만 `READY` 로 승격합니다.

- 현재 기본 확인 횟수: `3회`
- 현재 루프 주기: `10초`
- 첫 후보 감지 뒤 추가 지연: 보통 `약 20초`
- 실제 체감 지연: 장이 막 기준을 만족한 시점부터 보면 `약 20~30초`

레짐별로는 다음처럼 보수적으로 운영합니다.

- `LOW_ENERGY`, `CHOPPY_LOW_VOL`, `EXHAUSTION_RISK`, `OVERHEATED`
  - 신규 진입 차단
- `CHOPPY_HIGH_VOL`
  - `4회` 확인, trend-follow 금지, 피라미딩 금지
- `BREAKOUT_ATTEMPT`
  - `3회` 확인, fresh cross 필수, trend-follow 금지
- `TRENDING_EARLY`
  - `3회` 확인, trend-follow 허용, 피라미딩 허용
- `TRENDING_MATURE`
  - `3회` 확인, trend-follow 허용, 피라미딩은 제한적으로 허용
