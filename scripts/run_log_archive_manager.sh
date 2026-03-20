#!/bin/zsh
# 수정 요약
# - 로그 아카이브 매니저를 .venv/bin/python 우선, python3 대체 순서로 실행하는 래퍼 추가

set -euo pipefail

SCRIPT_DIR=${0:A:h}
PROJECT_ROOT=${SCRIPT_DIR:h}

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

exec "${PYTHON_BIN}" "${PROJECT_ROOT}/log_archive_manager.py" "$@"
