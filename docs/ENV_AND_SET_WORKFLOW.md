# 설정 파일 구조 한 페이지 정리

## English Summary

This document explains how runtime configuration is layered.

- The canonical runtime file is `config/runtime.toml`.
- Strategy presets live under `config/sets/*.toml`.
- Local active overrides live in `config/runtime.local.toml`.
- Secret values live in `.env.secrets`.
- Legacy `.env` is only a fallback when the split env/TOML files are not present.
- When a strategy appears not to change after editing `.env`, check the TOML runtime layers first.

## 핵심 결론

현재 구조에서 **canonical 운영 설정은 `config/runtime.toml`** 입니다.

전략 세트 canonical 파일은 아래입니다.

- `config/sets/conservative.toml`
- `config/sets/medium.toml`
- `config/sets/mixed.toml`

실제 런타임에서는 아래 레이어가 순서대로 합쳐집니다.

1. `config/runtime.toml`
2. `.env.settings`
3. `.env.secrets`
4. `.env.local`
5. `config/runtime.local.toml`

split env 가 없을 때만 아래 fallback 이 추가됩니다.

6. `.env` (legacy fallback)

즉 현재 관계는 아래와 같습니다.

- `config/runtime.toml` = canonical 운영 설정
- `config/sets/*.toml` = canonical 전략 세트
- `config/runtime.local.toml` = 현재 적용 세트를 담는 로컬 TOML override
- `.env.settings` = 선택적 env override 레이어
- `.env.secrets` = 비밀정보 레이어
- `.env.local` = 로컬 env override
- `.env` = legacy fallback

---

## 1. 각 파일 역할

### `config/runtime.toml`

- canonical 운영 설정 파일
- 전략, 리스크, 포트폴리오, 텔레그램 일반 설정의 기준값

### `config/sets/*.toml`

- canonical 전략 세트 파일
- 보수형/중간형/혼합형 같은 비교 세트를 구조화된 형태로 정의

예:

- `config/sets/conservative.toml`
- `config/sets/medium.toml`
- `config/sets/mixed.toml`

### `config/runtime.local.toml`

- 현재 적용 세트 또는 로컬 TOML override
- `tools/apply_strategy_set.py` 가 갱신하는 파일

### `.env.settings`

- env 기반 운영 override
- TOML 위에 덮어쓰는 값

### `.env.secrets`

- 비밀정보 파일
- 거래소 API 키
- 텔레그램 토큰 / chat id

### `.env.local`

- 로컬 env override

### `.env`

- legacy fallback
- split env / TOML 이 없을 때만 기준 역할

### `env_overrides/*`

- legacy / history 보관용
- 현재 canonical 세트 파일은 아님

---

## 2. 실제 적용 흐름

현재 전략 세트 적용 순서는 아래입니다.

1. `config/runtime.toml` 에 canonical 기본값 유지
2. `config/sets/*.toml` 에 비교 세트 정의
3. `tools/apply_strategy_set.py` 실행
4. 선택한 세트 내용을 `config/runtime.local.toml` 에 반영
5. 봇 재시작
6. 재시작 후 봇은 `config/runtime.toml` + env 레이어 + `config/runtime.local.toml` 을 함께 읽음

즉 전략 세트 변경은 이제 **`config/runtime.local.toml` 기준**으로 반영됩니다.

---

## 3. 사용 예시

혼합형 세트 적용:

```bash
.venv/bin/python tools/apply_strategy_set.py --set mixed
```

미리보기:

```bash
.venv/bin/python tools/apply_strategy_set.py --set mixed --dry-run
```

반영 후 알트 봇 재시작:

```bash
.venv/bin/python bot_manager.py stop okx
.venv/bin/python bot_manager.py stop upbit
.venv/bin/python bot_manager.py start okx
.venv/bin/python bot_manager.py start upbit
```

---

## 4. 왜 이렇게 바꿨나

장점

- canonical 운영 설정과 전략 세트 경로가 분명해짐
- 현재 적용 세트를 `config/runtime.local.toml` 에서 바로 확인 가능
- 전략 세트 비교가 쉬워짐
- 비밀정보와 운영 설정을 분리 가능
- env 기반 호환성도 유지 가능
- 장기적으로 typed config 시스템으로 확장하기 쉬움

---

## 5. 현재 단계 의미

현재는 “구조화된 설정 시스템 전환 3차 완료” 상태입니다.

완료된 것

- canonical TOML 운영 설정 도입
- canonical TOML 전략 세트 도입
- split env 도입
- 중앙 로더 도입
- 핵심 설정/실행 모듈을 중앙 로더로 전환
- 세트 적용 도구를 `runtime.local.toml` 기준으로 전환

아직 남은 것

- `env_overrides` legacy/history 정리 정책 확정
- `config/runtime.local.toml` 운용 규칙 문서화 보강
- typed config accessor 적용 범위를 실행/리포트 전역으로 더 넓히기

위 항목은 리팩토링 미완료가 아니라 후속 개선 메모로 봅니다.
현재 canonical 설정 구조 전환 자체는 완료된 상태입니다.

---

## 6. 한 줄 요약

현재 구조에서

- `config/runtime.toml` 이 canonical 운영 설정이고
- `config/sets/*.toml` 이 canonical 전략 세트이며
- `config/runtime.local.toml` 이 현재 적용 세트를 담는 override 파일이고
- `.env.settings` / `.env.secrets` 는 추가 override / secret 레이어입니다.
