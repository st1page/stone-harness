---
description: "延迟工作必须进入当前 ticket，或创建 backlog / fork ticket 让后续 agent 接手"
triggers:
  - "deferred TODO"
  - "follow-up"
  - "延迟工作"
  - "后续再做"
  - "等待依赖"
  - "fork ticket"
---

# deferred-work-must-become-ticket

延迟工作（deferred TODO）不要留在对话里，也不要写入单独待办池。`aticket-cli` 当前的基本工作单元就是 ticket：如果一个事项未来需要有人接手，就把它记录到当前 ticket，或创建 backlog / fork ticket。

## 为什么

- **可接手**：新的 backlog ticket 自带 goal、short-context 和来源，后续 agent 可以直接 claim 后推进。
- **避免重复机制**：没有单独待办 schema，也不需要 agent 理解两套生命周期。
- **保持边界清楚**：属于当前 ticket 尾巴的事项留在当前 ticket；独立工作单元用新 ticket 或 fork。

## 何时触发

- 发现需要做的工作，但当前 ticket 的目标不包含这个工作
- 需要把工作交给另一个 agent（或未来的自己）
- 需要等某个前置条件满足后再做这个工作

## 如何应用

创建新 follow-up ticket 前，先用 `ls` / `rg` 扫 ACTIVE/BACKLOG ticket，或用 `aticket-cli tickets search --query "<keywords>" --lifecycle-state ALL` 做关键词检索，查是否已有同目标 ticket。若已有可复用 BACKLOG ticket，claim 它；若已有其他 agent 持有的 ACTIVE ticket，先按 [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) 的接管规则处理；若只找到 archived ticket，则不要继续写入，应该新建或 fork。

`aticket-cli` 的 ticket lease 保护单个 ticket 的 `workspace/` 和当前推进权，但不会阻止两个 agent 创建两个不同 ticket。`ls` / `rg` / `aticket-cli tickets search --query "<keywords>"` 查重再 `aticket-cli ticket new` 不是原子操作；并发下重复 ticket 是已知限制，后续 owner 或人工需要通过链接、archive 或合并上下文收口。

### 仍属于当前 ticket

如果 deferred TODO 只是当前 ticket 的尾巴，写进当前 ticket：

```bash
aticket-cli ticket "$TICKET_DIR" context \
  "当前状态；等待 PR 合入后跑 smoke；如果失败先看 artifacts/smoke.log。"
aticket-cli ticket "$TICKET_DIR" log "Deferred follow-up remains in this ticket: run smoke after PR merge."
```

适合：
- 等用户反馈后继续修
- 本 PR 合入后跑一次 smoke
- 当前工作尚未完成但暂时切走

### 独立工作单元：backlog ticket

如果 follow-up 是独立工作，不需要继承父 ticket 快照，创建 backlog ticket：

```bash
ROOT="${AGENT_TICKETS_ROOT:-/home/tsshi/agent-tickets}"
rg -n "backfill jp10|utop2-token|2024-Q4" "$ROOT"/tickets/*/TICKET.md 2>/dev/null
aticket-cli tickets search --query "backfill jp10 utop2-token 2024-Q4" --lifecycle-state ALL

FOLLOWUP_DIR=$(aticket-cli ticket new \
  --topic "backfill-jp10-utop2-token" \
  --goal "Backfill jp10 utop2-token for 2024-Q4 data" \
  --short-context "Created as follow-up from $TICKET_DIR; first step is to inspect PR-123 merge status." \
  --backlog)
aticket-cli ticket "$TICKET_DIR" add-item "file://$FOLLOWUP_DIR"
aticket-cli ticket "$FOLLOWUP_DIR" add-item "file://$TICKET_DIR"
```

### 派生工作：fork ticket

如果 follow-up 需要父 ticket 当时状态，用 fork：

```bash
FORKED_TICKET_DIR=$(aticket-cli ticket "$SOURCE_TICKET_DIR" fork \
  --topic "monitor-jp10-backfill" \
  --goal "Monitor jp10 backfill after PR-123 merge")
aticket-cli ticket "$FORKED_TICKET_DIR" context \
  "Start from artifacts/source-ticket-snapshot.md; first check backfill job state."
aticket-cli ticket "$SOURCE_TICKET_DIR" add-item "file://$FORKED_TICKET_DIR"
aticket-cli ticket "$FORKED_TICKET_DIR" add-item "file://$SOURCE_TICKET_DIR"
aticket-cli ticket "$FORKED_TICKET_DIR" release
```

fork 默认创建 ACTIVE child ticket。deferred follow-up 不是当前 agent 立即推进的工作，所以写清 context 和双向链接后必须 `release` 成 BACKLOG；如果当前 agent 要立即切到 forked ticket 推进，就不要 release，但要把后续 repo 写操作切到 forked ticket 的 `workspace/` linked worktree。

forked ticket 有自己的 lease。它可以读 source ticket 和 source artifacts/state，但拿到的是 fork 时刻的 source snapshot；source 不会自动回写，也不会自动 archive。

派生目的写进 `--goal` / `short-context` / `log`；source 是否需要额外补充决策日志，由 source owner 显式决定。`fork` / `release` 后仍要按 [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) 在对话里向 human 确认 ticket 路径、lifecycle 和 handoff 语义。

## 后续票被完成或废弃时

后来的大票、实现票或发布票可能会完成、合并、取消或 supersede 早先创建的 backlog follow-up。这个后续 closeout 不能只在新票里留下旧票链接；当前 owner 必须处理旧 follow-up 的 lifecycle。

收口前检查当前 ticket item URI 里链接的 BACKLOG tickets：

- 如果本 ticket 已经完成那个 follow-up，claim 旧票，写清完成来源和证据，然后 `archive`。
- 如果本 ticket 的决策让旧 follow-up 不再成立，claim 旧票，写清 superseded / obsolete 的原因，然后 `archive`。
- 如果旧 follow-up 仍然需要独立推进，保留 BACKLOG，但在当前 ticket `short-context` / `log` 写清为什么仍 open，以及下一 owner 的 first action。
- 如果旧 follow-up 需要改目标，fork / new replacement ticket，并把旧票作为历史证据收口。

这条规则只要求处理明确由当前 workstream 完成或废弃的 linked backlog；不要为了整理 backlog 去接管无关 ticket。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 每次工作必须归属到一个 ticket
- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — 新 repo / PR / 外部文档族 / benchmark / source repo 切换等独立 handoff unit 必须拆票并双向链接
- [ticket-lifecycle-boundary-check](ticket-lifecycle-boundary-check.md) — 边界动作后判断 source / child ticket 应 ACTIVE、release/BACKLOG 还是 archive
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录

## 工具来源

本原则依赖的 `aticket-cli` 命令来自 `aticket-cli` 仓库。详见 `aticket-cli/SKILL.md`（ticket-workdir skill）。
