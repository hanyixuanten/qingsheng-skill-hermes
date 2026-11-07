#!/usr/bin/env bash
# 把上游 tomwong001/qingsheng-skill 的更新同步进 Hermes 适配版 fork。
#
#   upstream（原仓库）有新提交 → 拉取上游文件 → 重新套用 scripts/adapt-hermes.py
#   → 提交 → 推送到 origin（hanyixuanten/qingsheng-skill-hermes）
#   → 顺带刷新本机已安装的 Hermes 技能
#
# 用法：scripts/sync-upstream.sh [--force] [--no-install] [--no-push]
# 退出码：0 = 已是最新或同步成功；非 0 = 失败（需要有人的地方）
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

UPSTREAM_URL="${QS_UPSTREAM_URL:-https://github.com/tomwong001/qingsheng-skill.git}"
SKILL_DEST="${HERMES_HOME:-$HOME/.hermes}/skills/social-media/qingsheng"
STATE_FILE="$REPO_DIR/.sync-state/upstream-sha"

FORCE=0
DO_INSTALL=1
DO_PUSH=1
for arg in "$@"; do
  case "$arg" in
    --force)      FORCE=1 ;;
    --no-install) DO_INSTALL=0 ;;
    --no-push)    DO_PUSH=0 ;;
    *) echo "未知参数: $arg" >&2; exit 2 ;;
  esac
done

# 自愈：远端配置不在 .git/config 里时补上（换机器 / 重新 clone 后依然能跑）
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream "$UPSTREAM_URL"
[ "$(git remote get-url upstream)" = "$UPSTREAM_URL" ] || git remote set-url upstream "$UPSTREAM_URL"

git fetch upstream --quiet
SHA="$(git rev-parse upstream/main)"
LAST="$(cat "$STATE_FILE" 2>/dev/null || true)"
VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || echo '?')"

install_local() {
  [ "$DO_INSTALL" -eq 1 ] || return 0
  [ -d "$SKILL_DEST" ] || { echo "→ 本机未安装该技能，跳过刷新（$SKILL_DEST）"; return 0; }
  rm -rf "$SKILL_DEST.new"
  cp -a skill "$SKILL_DEST.new"
  rm -rf "$SKILL_DEST"
  mv "$SKILL_DEST.new" "$SKILL_DEST"
  echo "→ 已刷新本机技能：$SKILL_DEST"
}

if [ "$SHA" = "$LAST" ] && [ "$FORCE" -eq 0 ]; then
  echo "UP_TO_DATE 上游无新提交（v$VERSION @ ${SHA:0:7}）"
  install_local
  exit 0
fi

echo "→ 上游有新提交（${SHA:0:7}），开始同步（本地记录：${LAST:0:7}）"

# 用上游文件覆盖工作区：不会删除我们自己的 scripts/、README-HERMES.md
git checkout upstream/main -- .
python3 scripts/adapt-hermes.py

NEW_VERSION="$(tr -d '[:space:]' < VERSION)"
mkdir -p "$(dirname "$STATE_FILE")"
echo "$SHA" > "$STATE_FILE"

git add -A
if git diff --cached --quiet; then
  echo "NO_FILE_CHANGES 上游提交没有改动文件内容（v$NEW_VERSION @ ${SHA:0:7}）"
else
  git -c user.name="${GIT_AUTHOR_NAME:-qingsheng-hermes-sync}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-qingsheng-hermes-sync@users.noreply.github.com}" \
      commit -q -m "sync: upstream v$NEW_VERSION @ ${SHA:0:7}"
  echo "→ 已提交 $(git rev-parse --short HEAD)"
  if [ "$DO_PUSH" -eq 1 ]; then
    git push --quiet origin HEAD:main
    echo "→ 已推送到 origin/main"
  else
    echo "→ 跳过推送（--no-push）"
  fi
fi

install_local
echo "SYNCED v$NEW_VERSION @ ${SHA:0:7}"
