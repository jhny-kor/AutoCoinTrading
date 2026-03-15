#!/bin/zsh
set -euo pipefail

cd /Users/plo/Documents/auto_coin_bot
mkdir -p logs

timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$timestamp] launchd auto start requested" >> logs/launchd_autostart.out

./.venv/bin/python bot_manager.py start all >> logs/launchd_autostart.out 2>> logs/launchd_autostart.err
