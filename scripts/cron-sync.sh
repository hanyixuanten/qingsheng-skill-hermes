#!/usr/bin/env bash
# 定时任务入口（Hermes cron no_agent 模式）：只在「真的同步了」或「出错」时有输出。
# 输出为空 = 上游没更新 = 不打扰。
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# cron 环境不一定带 HERMES_HOME；本机 profile 家目录是 /opt/data
: "${HERMES_HOME:=/opt/data}"
export HERMES_HOME

OUT="$(GIT_TERMINAL_PROMPT=0 bash "$REPO_DIR/scripts/sync-upstream.sh" 2>&1)"
RC=$?

if [ "$RC" -ne 0 ]; then
  echo "❌ 情圣 skill 同步失败（退出码 $RC）"
  echo
  echo '```'
  echo "$OUT"
  echo '```'
  exit 0
fi

case "$OUT" in
  UP_TO_DATE*) exit 0 ;;
  *)
    echo "✅ 情圣 skill 已同步上游更新"
    echo
    echo '```'
    echo "$OUT"
    echo '```'
    ;;
esac
