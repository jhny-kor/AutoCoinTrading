# Auto Coin Bot

이 저장소는 OKX와 업비트에서 각각 현물 자동매매를 테스트하기 위한 초기 버전 프로젝트입니다.
전략 값을 바꿔가며 테스트할 수 있도록, 구조화 로그와 `trade_history.jsonl`에는 `strategy_version`도 함께 남기도록 구성했습니다.  

<div align="center">  
<a href="https://www.instagram.com/_k.jhny" target="_blank"><img src="https://img.shields.io/badge/Instagram-E4405F?style=flat-square&logo=Instagram&logoColor=white"/></a>  
</div>  

## 문서 역할

- `README.md`: 현재 운영 기준과 현재 구조를 설명합니다.
- `STRATEGY_DECISIONS.md`: 왜 값을 바꿨는지, 어떤 버전과 로그를 근거로 바꿨는지 이력 중심으로 기록합니다.
- `PLANS.md`: 현재 적용 상태, 과거 검토안, 앞으로 볼 후보안을 함께 정리합니다.

즉 현재 상태를 빠르게 확인할 때는 `README.md`, 변경 이력을 추적할 때는 `STRATEGY_DECISIONS.md`, 아직 확정되지 않은 아이디어와 과거 검토 흐름은 `PLANS.md`를 우선 참고하면 됩니다.

## 대화 요약

- OKX 봇에서 `Parameter sz error`가 발생해 주문 파라미터를 수정했습니다.
- OKX 시장가 매수는 코인 수량이 아니라 사용 금액 기준으로 보내도록 바꿨습니다.
- OKX와 업비트 봇 모두 분할 매수/분할 매도 구조로 변경했습니다.
- 두 봇 모두 평균 진입가보다 더 낮아질 때만 추가 매수하도록 바꿨습니다.
- 두 봇 모두 최소 익절률 이상일 때만 매도하도록 바꿨습니다.
- 두 봇 모두 손절률을 넘기면 즉시 전량 청산하도록 손절 규칙을 추가했습니다.
- 과매매를 줄이기 위해 쿨다운, 최소 이격도 조건을 추가했습니다.
- 상위 타임프레임 추세 필터를 추가해 큰 흐름과 같은 방향일 때만 신규 진입하도록 바꿨습니다.
- 거래량 필터와 변동성 필터를 추가해 신규 진입 품질을 높였습니다.
- 일일 최대 손실 제한을 추가해 손실이 커지면 신규 매수를 중단하도록 바꿨습니다.
- 업비트는 편도 수수료 0.05%를 반영해 왕복 수수료보다 낮은 구간에서 성급히 매도하지 않도록 보완했습니다.
- 전략 공통값은 `.env`에서 같이 관리하도록 정리했습니다.
- 코인별 이격도, 익절률, 손절률을 다르게 설정할 수 있도록 정리했습니다.
- 심볼별 최소 주문 수량도 `.env`에서 다르게 관리할 수 있도록 정리했습니다.
- 알트 감시 심볼 목록도 `.env`에서 관리해 종목 추가 시 코드 수정 범위를 줄였습니다.
- BTC 전용 봇은 익절 구간 도달 후 최고가 대비 되돌림으로 전량 청산하는 트레일링 익절을 적용했습니다.
- BTC 전용 봇은 수수료를 제하고도 순익이 남는 상태에서 추세가 약해지면 빠르게 잠그는 순익 보호 익절을 추가했습니다.
- BTC 전용 봇은 트레일링 익절/순익 보호 익절 직후 재진입과 추가매수를 잠시 막는 전용 쿨다운을 추가했습니다.
- BTC 전용 봇은 익절가 도달 시 1회 부분 익절 후 잔량을 트레일링/순익 보호로 관리하는 구조를 추가했습니다.
- BTC 전용 봇은 진입 필터를 조금 더 보수적으로 강화하고, 강한 다중 상승 추세에서는 짧은 조정을 일시 보유로 처리하도록 조정했습니다.
- BTC 전용 봇은 약한 추세 구간 진입을 줄이기 위해 EMA 스프레드와 거래량 기준을 소폭 강화했습니다.
- 알트 봇도 수수료를 제하고도 순익이 남는 상태에서 메인 추세가 꺾이면 전량 순익 보호 익절을 실행하도록 보강했습니다.
- 알트 부분 익절 직후에는 같은 코인 재진입과 추가 매수를 잠시 막는 전용 쿨다운을 추가했습니다.
- 포트폴리오 배분은 `현재 가용 현금`만이 아니라 `코인별 누적 투입 원가`까지 함께 계산해 목표 비중을 넘는 신규 매수를 제한하도록 확장했습니다.
- 거래량과 추세 품질이 아주 강한 코인만 목표 비중을 보수적으로 `+5%`까지 일시 확대하는 동적 오버웨이트 구조를 추가했습니다.
- 체결 로그에는 주문 ID, API 지연, 슬리피지, 체결 비율 같은 주문 실행 품질 지표도 함께 남기도록 확장했습니다.
- 분석 수집기에는 호가창 상위 누적 잔량, 누적 금액, 깊이 비대칭 같은 미시구조 지표도 함께 남기도록 확장했습니다.
- 알트 봇은 최근 로그 기준으로 거래량 필터와 이격도 기준을 조금 완화해 실제 진입 기회를 늘려보는 테스트로 조정했습니다.
- 로그는 날짜별 폴더 아래에 종류별로 분리해 저장하도록 변경했습니다.
- 터미널에서는 매수 신호를 빨간색, 매도 신호를 파란색으로 보여주고, 실제 주문은 강조 배너로 표시하도록 바꿨습니다.
- 여러 번 실행돼 있던 봇 프로세스는 모두 중지했습니다.

## 현재 파일 구성

- `ma_crossover_bot.py`: OKX 알트 현물용 봇
- `upbit_ma_crossover_bot.py`: 업비트 알트 원화마켓용 봇
- `strategy_settings.py`: `.env`에서 공통 전략 값을 읽는 모듈
- `bot_logger.py`: 터미널 출력과 파일 로그를 함께 처리하는 모듈
- `bot_manager.py`: 실행 중인 봇 상태 확인 및 전체 중지 도구
- `analysis_log_collector.py`: 분석용 구조화 로그 수집기
- `analyze_logs.py`: 수집된 분석 로그 요약 도구
- `telegram_notifier.py`: 텔레그램 메시지 전송 유틸
- `telegram_command_listener.py`: 텔레그램 명령 수신 및 상태 응답 리스너
- `trade_history_logger.py`: 체결 결과를 JSONL 로 구조화 저장하는 로거
- `structured_log_manager.py`: system / strategy / trade 구조화 로그와 퍼널 요약을 관리하는 로거
- `analyze_strategy_logs.py`: 구조화 전략 로그의 퍼널 병목과 차단 사유를 집계하는 도구
- `log_path_utils.py`: 일자별 로그 경로와 탐색을 공통으로 처리하는 유틸
- `migrate_logs_to_dated_dirs.py`: 기존 평면 로그를 날짜별 폴더 구조로 옮기는 마이그레이션 도구
- `log_archive_manager.py`: 최근 7일 원본 유지 후 오래된 로그를 날짜별 `tar.gz`로 압축하는 도구
- `btc_trend_settings.py`: BTC 전용 EMA 추세추종 설정 로더
- `okx_btc_ema_trend_bot.py`: OKX BTC 전용 EMA+ATR 추세추종 실험 봇
- `upbit_btc_ema_trend_bot.py`: 업비트 BTC 전용 EMA+ATR 추세추종 실험 봇
- `.env`: API 키, 거래소별 설정, 공통 전략 설정

## 로그 파일

- `logs/YYYY-MM-DD/<program>.log`
- `logs/YYYY-MM-DD/<program>.launcher.log`
- `analysis_logs/YYYY-MM-DD/<exchange>__<symbol>.jsonl`
- `trade_logs/YYYY-MM-DD/trade_history.jsonl`
- `structured_logs/live/YYYY-MM-DD/<program>/system.jsonl`
- `structured_logs/live/YYYY-MM-DD/<program>/strategy.jsonl`
- `structured_logs/live/YYYY-MM-DD/<program>/trade.jsonl`
- `structured_logs/live/YYYY-MM-DD/<program>/summary_1h/*.json`

프로그램을 실행하면 위 파일들이 자동으로 생성되고 누적 기록됩니다. `trade_logs/YYYY-MM-DD/trade_history.jsonl` 에는 매수/익절/손절 체결 결과가 거래소/심볼/수량/금액/손익/원본 주문 응답과 함께 구조화되어 저장됩니다. 최근에는 주문 실행 품질 분석용으로 주문 ID, API 지연, 평균 체결가, 슬리피지, 체결 비율 같은 필드도 함께 남기도록 확장했습니다. 구조화 로그는 장애 분석은 `system.jsonl`, 전략 병목 분석은 `strategy.jsonl`, 체결 분석은 `trade.jsonl` 로 바로 나눠서 볼 수 있게 해줍니다.

기존 평면 로그가 남아 있는 경우에는 아래 명령으로 날짜별 폴더 구조로 옮길 수 있습니다.

- 미리보기: `.venv/bin/python migrate_logs_to_dated_dirs.py --dry-run`
- 실제 이동: `.venv/bin/python migrate_logs_to_dated_dirs.py`

오래된 로그 보관 정책은 다음과 같습니다.

- 최근 7일 로그는 원본 유지
- 7일 초과 로그는 날짜별 `tar.gz` 압축
- 압축 점검: `.venv/bin/python log_archive_manager.py status`
- 수동 압축: `.venv/bin/python log_archive_manager.py compress`

## 알트 심볼 추가 방법

- `.env`의 `OKX_ALT_SYMBOLS`, `UPBIT_ALT_SYMBOLS` 에 감시할 알트 심볼을 쉼표로 추가합니다.
- 텔레그램 `/positions`, `/analysis`, 분석 수집기는 위 알트 목록에 BTC 전용 심볼을 자동으로 합쳐서 사용합니다.
- 운영 알트 외에 추가 관찰만 하고 싶은 심볼이 있으면 `.env`의 `ANALYSIS_OKX_SYMBOLS`, `ANALYSIS_UPBIT_SYMBOLS` 에만 별도로 넣을 수 있습니다.
- 심볼별 이격도, 익절률, 손절률, 최소 주문 수량은 `.env`의 `STRATEGY_*_MAP` 항목에 함께 추가해 두는 것이 안전합니다.

## 봇 상태 확인, 시작, 중지

- 상태 확인: `.venv/bin/python bot_manager.py status`
- 전체 시작: `.venv/bin/python bot_manager.py start all`
- OKX 봇만 시작: `.venv/bin/python bot_manager.py start okx`
- 업비트 봇만 시작: `.venv/bin/python bot_manager.py start upbit`
- OKX BTC EMA 봇만 시작: `.venv/bin/python bot_manager.py start okx_btc`
- 업비트 BTC EMA 봇만 시작: `.venv/bin/python bot_manager.py start upbit_btc`
- 분석 수집기만 시작: `.venv/bin/python bot_manager.py start collector`
- 텔레그램 명령 리스너만 시작: `.venv/bin/python bot_manager.py start telegram`
- 전체 중지: `.venv/bin/python bot_manager.py stop`
- 텔레그램 리스너만 중지: `.venv/bin/python bot_manager.py stop telegram`
- 강제 종료: `.venv/bin/python bot_manager.py stop --force`

위 도구는 `ma_crossover_bot.py`, `upbit_ma_crossover_bot.py`, `okx_btc_ema_trend_bot.py`, `upbit_btc_ema_trend_bot.py`, `analysis_log_collector.py`, `telegram_command_listener.py` 상태를 함께 확인하고 관리합니다.
현재 기준으로 `start all`은 매일 돌려야 하는 프로그램 전체를 모두 시작하고, `stop all`은 이 관리 대상 전체를 모두 중지합니다.

## 운영 루틴 정리

### 항상 실행

- `.venv/bin/python bot_manager.py start all`

여기에는 아래 프로그램이 모두 포함됩니다.

- OKX 알트 봇: `ma_crossover_bot.py`
- 업비트 알트 봇: `upbit_ma_crossover_bot.py`
- OKX BTC 봇: `okx_btc_ema_trend_bot.py`
- 업비트 BTC 봇: `upbit_btc_ema_trend_bot.py`
- 시장 분석 수집기: `analysis_log_collector.py`
- 텔레그램 명령 리스너: `telegram_command_listener.py`

### 수시 확인

- 텔레그램에서 `/status`
- 텔레그램에서 `/pnl`
- 텔레그램에서 `/analysis`
- 텔레그램에서 `/weekly`
- 필요할 때 `.venv/bin/python bot_manager.py status`

### 정기 분석

- 전략 병목 분석: `.venv/bin/python analyze_strategy_logs.py`
- 시장 특성 분석: `.venv/bin/python analyze_logs.py`
- CSV 저장 분석: `.venv/bin/python analyze_strategy_logs.py --csv reports/strategy_funnel.csv`

즉 운영 흐름은 `항상 실행 = start all`, `상태 확인 = 텔레그램/ status`, `정기 분석 = analyze_* 스크립트`로 생각하시면 됩니다.

## 포트폴리오 배분

현재 포트폴리오 배분은 `평가금액 강제 리밸런싱`이 아니라, `신규 매수 허용 금액 제한` 방식으로 동작합니다.

- 기준 목표 비중
  - BTC `60%`
  - ETH `30%`
  - XRP `10%`
- 지갑 총액 계산
  - 현재 가용 현금
  - 코인별 현재 평가금액이 아니라 `남아 있는 누적 투입 원가`
- 신규 매수 허용 금액
  - `목표 비중 금액 - 현재 남아 있는 누적 투입 원가`
  - 이 값이 0 이하이면 해당 코인은 신규 매수를 막습니다.
  - 이 값이 양수이면 기존 전략 주문 금액과 비교해 더 작은 값만 사용합니다.

즉 현재는 “이미 많이 넣은 코인은 더 안 사고, 부족한 코인만 채운다”는 구조입니다. 손절이나 일반 매도로 인해 잔고가 줄어들면 누적 투입 원가도 함께 줄어, 이후 다시 목표 비중 안에서 신규 진입이 가능해집니다.

거래소별 적용은 다음처럼 해석합니다.

- 기본 목표 비중은 `BTC 60 / ETH 30 / XRP 10`
- 해당 거래소에서 실제로 운용하는 자산만 남겨 다시 정규화합니다.
- 예를 들어 OKX 는 현재 `BTC`, `ETH` 위주로 운용하므로 `BTC/ETH`만 대상으로 다시 나눕니다.

### 보수적 동적 오버웨이트

기본 비중 외에 특정 코인의 거래량과 추세 품질이 아주 좋을 때만, 해당 코인의 목표 비중을 일시적으로 `+5%` 확대할 수 있습니다.

- 현재 단계는 보수형으로 설계합니다.
- 추가 비중 최대치: `+5%`
- 적용 조건 예시
  - 거래량 배수 충분
  - 상위 추세 동의
  - 신호 강도 통과
  - 과열 구간 아님

동적 오버웨이트는 “가장 강한 코인에 약간 더 싣는 보조 장치”로만 쓰고, 기본 목표 비중을 크게 흔들지 않도록 유지합니다.

## 로그 수집, 분석, 확인 프로세스

평소에는 `.venv/bin/python bot_manager.py start all` 로 매매 봇 4개, 시장 분석 수집기, 텔레그램 리스너를 항상 켜두고 로그를 계속 쌓습니다. 이렇게 하면 운영용 텍스트 로그는 `logs/YYYY-MM-DD/*.log`, 시장 상태 로그는 `analysis_logs/YYYY-MM-DD/*.jsonl`, 전략 판단 로그는 `structured_logs/live/YYYY-MM-DD/*/strategy.jsonl`, 체결 로그는 `trade_logs/YYYY-MM-DD/trade_history.jsonl` 과 `structured_logs/live/YYYY-MM-DD/*/trade.jsonl` 에 함께 기록됩니다. 수시 상태 확인은 텔레그램에서 `/status`, `/pnl`, `/analysis`, `/weekly` 로 하고, 며칠 간 로그가 쌓이면 `.venv/bin/python analyze_strategy_logs.py` 로 퍼널 병목과 차단 사유를 보고, `.venv/bin/python analyze_logs.py` 로 코인별 이격도/변동성/거래량 특성을 확인하면 됩니다. 즉 순서는 `항상 수집 -> 텔레그램으로 수시 확인 -> analyze_strategy_logs.py 로 전략 병목 분석 -> analyze_logs.py 로 시장 특성 분석` 으로 보시면 됩니다.

전략 값을 왜 바꿨는지와 어떤 로그를 근거로 조정했는지는 `STRATEGY_DECISIONS.md` 에 계속 누적 기록합니다.

| 수집 항목 | 어디에 쌓이는지 | 이걸로 답하는 질문 | 전략 조정 포인트 |
| --- | --- | --- | --- |
| 시장 상태 로그 | `analysis_logs/YYYY-MM-DD/*.jsonl` | 이 코인이 원래 잔잔한지, 변동성이 큰지, 거래량이 붙는지 | 코인별 이격도, 거래량 기준, 변동성 기준 조정 |
| 전략 퍼널 로그 | `structured_logs/live/YYYY-MM-DD/*/strategy.jsonl` | 왜 안 샀는지, 어느 단계에서 가장 많이 막히는지 | 진입 신호 정의, 상위 타임프레임 필터, 쿨다운, 추가매수 조건 조정 |
| 체결 로그 | `trade_logs/YYYY-MM-DD/trade_history.jsonl` | 실제로 돈이 되는지, 손절/익절이 적절한지 | 손절률, 익절률, 트레일링, 부분 익절, 브레이크이븐, 순익 보호 익절 조정 |
| 거래 품질 지표 | `trade_history.jsonl` 의 `mfe_pct`, `mae_pct`, `holding_seconds`, `trailing_armed_seconds`, `api_latency_ms`, `slippage_bps`, `fill_ratio` | 들어간 거래가 얼마나 잘 갔고 왜 못 먹었는지, 주문이 얼마나 불리하게 체결됐는지 | 익절 활성화 가격, 트레일링 폭, 손절 간격, 주문 방식 조정 |
| 시간대 성과 | `analyze_strategy_logs.py` 시간대 요약 | 몇 시에 손절이 많고 몇 시에 성과가 좋은지 | 시간대 필터, 거래 시간 제한 검토 |
| 전략 버전 정보 | 구조화 로그 `metrics.strategy_version`, 체결 로그 `strategy_version` | 어떤 버전이 실제로 더 나은지 | 버전별 A/B 비교, 보수형/중간형/공격형 유지 여부 판단 |

## 분석용 로그 수집

- 실행: `.venv/bin/python analysis_log_collector.py`
- 저장 위치: `analysis_logs/YYYY-MM-DD/*.jsonl`

이 수집기는 거래를 하지 않고, 시세/이동평균/신호 상태를 구조화된 JSONL 형식으로 저장합니다.
나중에 코인별 신호 빈도, 평균 이격도, 변동성, 전략 적합성 분석에 활용할 수 있습니다.
현재는 기본 OHLCV 외에도 거래량 배수, 변동성, RSI, 최근 범위 위치, 상위 타임프레임 상태, 호가 스프레드, 상위 호가 누적 잔량/금액, 깊이 비대칭, 공개 기준 필터 통과 여부까지 함께 저장합니다.

## 분석 로그 요약

- 전체 요약: `.venv/bin/python analyze_logs.py`
- 거래소별 요약: `.venv/bin/python analyze_logs.py --exchange okx`
- 심볼별 요약: `.venv/bin/python analyze_logs.py --symbol BTC/USDT`

이 도구는 수집된 분석 로그를 읽어 신호 빈도, 평균 이격도, 변동성, MA 위 체류 비율 등을 요약합니다.
확장 로그가 쌓이면 평균 거래량 배수, 평균 RSI, 평균 스프레드, 대표 매수 차단 사유도 함께 보여줍니다.

## 구조화 전략 로그 분석

- 전체 퍼널 요약: `.venv/bin/python analyze_strategy_logs.py`
- CSV 저장: `.venv/bin/python analyze_strategy_logs.py --csv reports/strategy_funnel.csv`

이 도구는 `structured_logs/live/YYYY-MM-DD/*/strategy.jsonl` 과 `trade.jsonl` 을 읽어
심볼별 `scan -> ready -> requested -> filled` 흐름과 주요 차단 사유를 집계합니다.
즉 이제는 “왜 안 샀는지 / 왜 샀는지 / 왜 팔렸는지”를 문장 로그가 아니라 코드값과 단계별 숫자로 볼 수 있습니다.
추가로 체결 로그 기준 평균 보유시간, MFE/MAE, 트레일링 활성화 비율, 시간대별 성과, 필터 기준 부족 폭뿐 아니라 API 지연, 슬리피지, 체결 비율 같은 주문 실행 품질도 함께 볼 수 있습니다.

## 텔레그램 알림

- `.env`에서 `TELEGRAM_ENABLED=true` 로 켭니다.
- `TELEGRAM_BOT_TOKEN` 에 BotFather 에서 받은 토큰을 넣습니다.
- `TELEGRAM_CHAT_ID` 에 메시지를 받을 chat id 를 넣습니다.

현재 지원하는 알림:
- 매수 체결
- 일반 매도 체결
- 손절 발생
- 에러 발생
- 일일 손실 제한 도달
- 즉시 확인이 필요한 운영 알림
- 승인형 버튼이 붙은 에러 인시던트 알림

알림은 `ma_crossover_bot.py`, `upbit_ma_crossover_bot.py`, `okx_btc_ema_trend_bot.py`, `upbit_btc_ema_trend_bot.py` 실행 중 자동으로 전송됩니다.
즉시 확인 요청을 수동으로 보내고 싶으면 아래 명령을 사용할 수 있습니다.

- 일반 메시지: `.venv/bin/python telegram_notifier.py --message "운영 점검 시작"`
- 확인 요청: `.venv/bin/python telegram_notifier.py --attention "권한 확인이 필요합니다." --source "Codex"`

## 텔레그램 명령 조회

- 텔레그램 명령 리스너 시작: `.venv/bin/python bot_manager.py start telegram`
- 전체 서비스 시작: `.venv/bin/python bot_manager.py start all`

리너서가 실행 중이면 텔레그램 채팅창에서 아래 명령으로 현재 상태를 바로 조회할 수 있습니다.

- `/test`: 텔레그램 응답 테스트
- `/status`: 현재 OKX/업비트/분석 수집기/텔레그램 리스너 실행 상태
- `/positions`: 현재 거래소 잔고와 보유 포지션 평가 금액 요약
- `/pnl`: 오늘 누적 실현 손익 요약
- `/analysis`: 최근 분석 로그 요약
- `/weekly`: 최근 7일 기준 주간 리포트
- `/last`: 최근 운영 로그 끝부분 확인
- `/help`: 명령 도움말

현재 에러 인시던트 알림에는 아래 승인형 버튼도 함께 붙일 수 있습니다.

- `재기동`: 해당 봇을 stop/start 순서로 재기동
- `상세 보기`: 인시던트 ID, 반복 횟수, 상세 에러 내용 확인
- `수정 요청`: 수정 필요 인시던트로 기록하고 확인 메시지 전송
- `무시`: 이번 인시던트를 무시 상태로 표시

현재 구현 범위에서 `수정 요청`은 요청 기록과 알림까지 자동화하고, 실제 코드 패치/커밋/푸시는 별도 Codex 세션에서 진행합니다.

텔레그램 명령 리스너는 `.env`의 `TELEGRAM_CHAT_ID`와 일치하는 채팅에서 온 메시지에만 응답합니다.

즉시 테스트 메시지를 터미널에서 보내고 싶으면 아래 명령을 사용할 수 있습니다.

- `.venv/bin/python telegram_command_listener.py --send-test`

## 텔레그램 일일 리포트

텔레그램 명령 리스너가 실행 중이면 `.env` 설정에 따라 일일 리포트도 자동으로 전송됩니다.

- 아침 리포트: `TELEGRAM_DAILY_REPORT_MORNING_HOUR=8`
- 점심 리포트: `TELEGRAM_DAILY_REPORT_NOON_HOUR=12`
- 저녁 리포트: `TELEGRAM_DAILY_REPORT_EVENING_HOUR=18`
- 야간 리포트: `TELEGRAM_DAILY_REPORT_NIGHT_HOUR=21`
- 사용 여부: `TELEGRAM_DAILY_REPORT_ENABLED=true`

현재 리포트에는 아래 내용이 함께 들어갑니다.

- 오늘 누적 실현 손익
- 현재 잔고와 포지션 요약
- 시장 로그 분석 요약
- 전략 퍼널 분석 요약
- 거래 품질 요약(MFE/MAE, 보유시간, 트레일링 활성화 비율)
- 순익 보호 익절 요약
- 필터 기준 부족 폭 요약
- 시간대 성과 요약
- 최근 1주 거래량 기준 신규 후보 코인 3개씩
- 최근 체결 내역
- 오늘 스킵 사유 요약

## 텔레그램 주간 리포트

텔레그램 명령 리스너가 실행 중이면 `.env` 설정에 따라 최근 7일 기준 주간 리포트도 자동으로 전송됩니다.

- 사용 여부: `TELEGRAM_WEEKLY_REPORT_ENABLED=true`
- 기본 전송 요일: `TELEGRAM_WEEKLY_REPORT_WEEKDAY=MON`
- 기본 전송 시각: `TELEGRAM_WEEKLY_REPORT_HOUR=9`

현재 주간 리포트에는 아래 내용이 함께 들어갑니다.

- 최근 7일 누적 실현 손익
- 최근 7일 거래 품질 요약
- 최근 7일 순익 보호 익절 요약
- 최근 7일 전략 퍼널 요약
- 최근 7일 시간대 성과 요약
- 최근 1주 거래량 기준 신규 후보 코인

## 현재 운영 방향

- 당분간은 낮은 시드머니로 전략을 테스트합니다.
- 전략은 수익률보다도 진입/청산 조건의 안정성과 과매매 방지에 더 초점을 두고 있습니다.
- 현재는 분할 진입, 코인별 이격도/익절/손절, 상위 타임프레임, 거래량, 변동성, 일일 손실 제한까지 포함한 보수형 전략을 테스트 중입니다.
- BTC 전용 봇은 ATR 기반 손절, 약한 추세 구간 진입 필터, 익절 구간 진입 후 전량 트레일링, 수수료 반영 순익 보호 익절 구조를 함께 테스트 중입니다.
- 알트 봇은 기존 부분익절/부분손절 구조에 더해, 수수료를 넘긴 순익 구간에서 메인 추세가 꺾이면 전량 순익 보호 익절을 우선 실행하도록 테스트 중입니다.
- 알트 봇은 `.env`의 알트 심볼 목록 기준으로 여러 종목을 순회하며, 최근 로그 기준으로 일부 종목의 거래량 필터와 이격도 기준을 완화해 테스트 중입니다.
- 앞으로는 현재 전략을 충분히 관찰한 뒤 코인별 필터 값을 더 세밀하게 조정하고, 필요하면 RSI나 거래 횟수 제한 같은 보조 필터를 추가 검토할 수 있습니다.

## 현재 역할 분리

- 기존 OKX 봇: `.env`의 `OKX_ALT_SYMBOLS`
- 기존 업비트 봇: `.env`의 `UPBIT_ALT_SYMBOLS`
- OKX BTC 전용 봇: `BTC/USDT`
- 업비트 BTC 전용 봇: `BTC/KRW`

즉 현재는 `BTC는 전용 EMA+ATR 봇`, `알트는 기존 1분봉 전략 봇`으로 나누어 운영하는 구조입니다.

## BTC 전용 실험 전략

BTC는 현재 1분봉 다중코인 전략보다 더 느린 추세형 접근이 맞을 수 있어서 별도 실험 파일을 추가했습니다.

- OKX: `.venv/bin/python okx_btc_ema_trend_bot.py`
- 업비트: `.venv/bin/python upbit_btc_ema_trend_bot.py`

이 전략은 `5분봉/15분봉`, `EMA`, `거래량 확인`, `ATR 기반 변동성 필터`, `보수적 1회 추가매수 허용`, `ATR 또는 최근 스윙 기반 손절`, `익절 구간 도달 후 전량 트레일링 청산`, `수수료 반영 순익 보호 익절` 구조를 사용합니다.
기존 BTC 포함 봇과 동시에 실행하면 같은 BTC 심볼을 중복 매매할 수 있으니 함께 실행하지 않는 것이 안전합니다.

## 다음 전략 후보

- BTC 전용 봇
  - 현재 적용: 익절 구간 도달 후 전량 트레일링 청산
  - 다음 후보: 부분 익절 + 잔량 트레일링
- 알트 봇
  - 현재 적용: 거래량 필터, 이격도 필터를 최근 로그 기준으로 소폭 완화
  - 다음 후보: 필터 재강화, 레짐(시장 상태) 기준 ON/OFF
- 공통 후보
  - 더 강한 신호만 선택하는 필터 튜닝
  - 레짐 상태별 전략 ON/OFF
  - 부분 익절, 트레일링, 시그널 품질 비교를 trade/strategy 로그 기준으로 성과 분석
