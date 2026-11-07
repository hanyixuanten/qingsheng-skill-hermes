# 情圣 skill · Hermes Agent 适配版

[`tomwong001/qingsheng-skill`](https://github.com/tomwong001/qingsheng-skill) 的 **Hermes Agent 适配 fork**。
上游是 Claude Code 技能，直接用会有几处跑不通（Claude 专属路径、`AskUserQuestion`、`WebSearch`、
`/急` `/挽回` 这类独立斜杠命令）。这个仓库把 `skill/` 自动改造成 Hermes 能直接加载的版本，并保持与上游同步。

- 当前上游版本：见 `VERSION`
- 适配逻辑：`scripts/adapt-hermes.py`（幂等，可重复运行）
- 同步脚本：`scripts/sync-upstream.sh`（拉上游 → 重新适配 → 提交 → 推送 → 刷新本机安装）

## 安装到 Hermes

```bash
# 方式一：直接从这个 fork 安装（skill/ 目录已是适配版）
hermes skills install hanyixuanten/qingsheng-skill-hermes/skill

# 方式二：本地目录直接放进 skills
cp -a skill "${HERMES_HOME:-$HOME/.hermes}/skills/social-media/qingsheng"
```

装好后聊天即可触发（「帮我看看这段聊天」「她这话什么意思」），或 `/qingsheng` 手动进入。
档案存在 `~/.qingsheng/`，与 Claude Code 版共用。

## 适配做了什么

`scripts/adapt-hermes.py` 对上游 `skill/` 执行以下改动，全部幂等：

| 改动 | 说明 |
|---|---|
| 路径 | `~/.claude/skills/qingsheng-skill/` → `${HERMES_HOME:-$HOME/.hermes}/skills/social-media/qingsheng/` |
| 提问 | `AskUserQuestion` → `clarify`（Hermes 的选项式提问工具） |
| 搜索 | `WebSearch` → `web_search` |
| 主技能引用 | 子命令里的「读取情圣主技能文件 SKILL.md」→ `skill_view(name='qingsheng')` |
| 新增章节 | `SKILL.md` 开头插入「Hermes 运行环境适配」，含快捷指令映射、`vision_analyze` 看图、computer-use 降级等 |
| 分发文件 | 把根目录 `VERSION` / `CHANGELOG.md` 复制进 `skill/`（版本检查 preamble 需要） |

关键锚点消失（上游大改结构）时脚本会 **报错退出**，不会静默推出一个没适配好的技能。

## 与上游同步

```bash
scripts/sync-upstream.sh            # 有新提交就同步并推送
scripts/sync-upstream.sh --force    # 强制重新适配一遍
scripts/sync-upstream.sh --no-push  # 只本地提交，不推送
scripts/sync-upstream.sh --no-install  # 不动本机已安装的技能
```

流程：`git fetch upstream` → 比对 `.sync-state/upstream-sha` → 用上游文件覆盖工作区
（`git checkout upstream/main -- .`，不会删掉 `scripts/` 和本文件）→ 重新跑适配 →
提交 `sync: upstream vX @ sha` → 推送到 `origin/main` → 刷新本机
`${HERMES_HOME}/skills/social-media/qingsheng`。

已配置定时任务（Hermes cron，每 6 小时一次，**无 LLM 参与**）：上游没更新时脚本零输出、不打扰；
同步成功或失败才发一条消息。

| 项 | 值 |
|---|---|
| Job ID | `718310bfad8f`（`hermes cron list` 可查） |
| 计划 | `0 */6 * * *` |
| 入口 | `/opt/data/scripts/qingsheng-sync.sh` → 转发到本目录 `scripts/cron-sync.sh` |
| 静默条件 | 输出 `UP_TO_DATE` 时退出码 0 且无 stdout |

手动管理：`hermes cron pause|resume|remove 718310bfad8f`。想立刻跑一次用 `--force` 直接执行
`scripts/sync-upstream.sh`。

## 目录

```
skill/                  Hermes 适配版技能（由 adapt-hermes.py 生成，不要手改）
scripts/adapt-hermes.py 适配器
scripts/sync-upstream.sh 同步脚本
.sync-state/            上次同步的上游 commit
VERSION CHANGELOG.md docs/ evals/ demos/ setup ...  上游原样内容
```

## 注意

- `skill/` 是生成产物：改它请改 `scripts/adapt-hermes.py`，否则下次同步会被覆盖。
- 用 `hermes skills update` 更新本机安装会按上游覆盖，适配会丢；用 `scripts/sync-upstream.sh` 更新才保留适配。
- 上游 MIT License，见 `LICENSE`。
