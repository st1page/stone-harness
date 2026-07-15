---
description: "持久化状态必须外部化到 ticket 目录，不能只留在对话 context；资源入口统一用 add-item 记录"
triggers:
  - "持久化状态"
  - "short-context"
  - "work log"
  - "add-item"
  - "产生产物"
  - "更新状态"
  - "长讨论"
  - "实现前 checkpoint"
  - "handoff"
---

# persistent-state-must-be-externalized

持久化状态必须外部化到 ticket 目录（`aticket-cli ticket "$TICKET_DIR" log` / `aticket-cli ticket "$TICKET_DIR" add-item` / `aticket-cli ticket "$TICKET_DIR" context`），不能只留在对话 context。

## 为什么

- **对话 context 不可靠**：agent session 可能被 API 400 / timeout / 用户中断打断，对话 context 会丢失
- **跨 agent 交接**：下一个 agent（Claude / Codex / 人工）只能看到 `TICKET.md`，看不到你的对话 context
- **审计链**：事后追溯"为什么做这个决策"时，对话 context 已不可达，只有 ticket 目录留存

## 何时触发

- 执行了命令，产生了关键输出
- 做了决策（例如"选择方案 A 而不是方案 B"）
- 产生了产物（PR 链接、commit hash、文档链接、数据文件）
- 更新了可恢复上下文（当前状态、下一步、关键 note）
- 长讨论期间，用户意图、问题理解、约束、风险或关键事实发生变化
- 准备从讨论进入实现或执行前，需要写清最终理解和 first action

长讨论 / 实现前 checkpoint 的典型触发点包括：

- 用户明确新的目标、非目标、优先级或成功标准
- agent 对问题的理解从“以为要做 A”修正为“实际要做 B”
- 用户提供新的账号、机器、参数、数据来源、成本授权或风险边界
- 讨论选择了一个方案，同时放弃了其他有意义的候选方案
- 长讨论后准备写代码、跑远端命令、发 PR、发布文档页面或消耗外部资源

## 如何应用

### 记录命令输出和决策

```bash
aticket-cli ticket "$TICKET_DIR" log "$(date +%H:%M): Confirmed utop2-token mismatch in live query"
aticket-cli ticket "$TICKET_DIR" log "$(date +%H:%M): Chose approach A (direct SQL update) over approach B (backfill script) due to data volume"
```

- log 主内容是 positional argument；真实换行会写成字面量 `\n`，保证 rendered ticket 中是一行
- 建议加时间戳（`$(date +%H:%M)` 或 `$(date +%Y-%m-%d\ %H:%M:%S)`）
- 记录**关键结论**，不是流水账

### 记录资源入口

```bash
aticket-cli ticket "$TICKET_DIR" add-item "https://github.com/example-org/example-repo/pull/123"
aticket-cli ticket "$TICKET_DIR" add-item "https://docs.example.com/reports/jp10-signal-mapping-fix"
aticket-cli ticket "$TICKET_DIR" add-item "file:///home/tsshi/agent-tickets/tickets/2024-06-01-jp10-fix-123456/artifacts/backfill-results.csv"
```

`add-item` 是 ticket 的统一资源入口。需要说明资源语义、状态或结论时，写进 `short-context` 或 `log`；不要再使用旧 Artifacts 写法为同一个 URL / `file://` 路径维护第二份事实源。

### 管理 artifacts/ 文件

进入 `artifacts/` 的文件视为不可变证据。写入前先想清楚路径设计；一旦路径被 `add-item` 登记、PR/文档引用，或作为实验/审计依据被记录，就不要覆盖同一路径来表达新版本、新实验或修正结论。

- 如果内容还在反复编辑，先放 `notes/` 或 `workspace/`；定稿后再复制/写入 `artifacts/`。
- 如果需要修正，写新文件或新目录，并在 `log` / `short-context` 里说明 supersedes 关系。
- 如果预计会有多次实验、多轮 reviewer dump 或多个版本，先设计稳定路径，例如 `artifacts/experiments/2026-06-18-run-01/summary.md`、`artifacts/review/round-02/findings.md`，不要把所有结果覆盖到 `artifacts/results.csv`。
- `add-item` 登记的是具体不可变入口；“当前有效版本是哪一个”写进 `short-context` 或 final log。

### 维护目标和短上下文

```bash
aticket-cli ticket "$TICKET_DIR" goal "Fix jp10 wrong deploy-key signal mapping"
aticket-cli ticket "$TICKET_DIR" context "PR is open; next check feedback, then merge and monitor backfill."
aticket-cli ticket "$TICKET_DIR" archive
```

`short-context` 是快速恢复当前工作状态的一段精简文字：目前状态、下一步、关键 note、暂时想到但还不需要拆出去的事项。它可以反复修改，但不要高频刷写；通常保持几百字以内。

### 记录长讨论 checkpoint

如果讨论持续时间较长，或用户意图、约束、风险、关键事实发生变化，不能只把最新理解留在对话里。进入实现 / 执行前，先写一条 checkpoint，至少说明：

- 当前目标和不做什么
- 已确认的约束和风险
- 第一条执行动作
- 是否需要拆出 follow-up / fork ticket

如果 checkpoint 暴露出独立 handoff unit，按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 先做边界检查。

checkpoint 记录可恢复的实现依据，不复述聊天顺序。复杂讨论可以写 `notes/` 或 `artifacts/` 文件并用 `add-item` 登记；如果内容还在整理，先放 `notes/`，确认需要作为恢复/审计证据后再进入 `artifacts/`。后续讨论改变结论时，写新的 checkpoint，并在 `log` 或 `short-context` 里说明它 supersedes 哪个旧文件。

### 记录链接和引用

TICKET.md 的 `## Links` 部分用于存放工作相关的 URI（PR/文档/路径/agent thread 等）。

```bash
# 添加单个 URI（去重）
aticket-cli ticket "$TICKET_DIR" add-item "https://github.com/example-org/example-repo/pull/123"
aticket-cli ticket "$TICKET_DIR" add-item "file:///home/tsshi/sts-harness"
aticket-cli ticket "$TICKET_DIR" add-item "https://docs.example.com/reports/jp10-signal-mapping-fix"
```

读取链接时直接读 `TICKET.md` 或用文件系统工具过滤：

```bash
sed -n '/^## Links/,/^## /p' "$TICKET_DIR/TICKET.md"
rg -n "github|docs|^file://" "$TICKET_DIR/TICKET.md"
```

URI 格式：
- 本地路径：`file:///abs/path`
- Web 资源：`https://...`（GitHub / docs / 任意 HTTP 资源）
- Agent thread：`agents://codex/thread-id`

### 读取状态

`aticket-cli` 只保留跨 ticket 全文检索作为读接口；单个 ticket 的状态直接读 `TICKET.md`，目录扫描用 `ls` / `find` / `rg`：

```bash
sed -n '1,180p' "$TICKET_DIR/TICKET.md"
rg -n "feedback|backfill|blocked" "$TICKET_DIR/TICKET.md"
aticket-cli tickets search --query "jp10 backfill"
```

`TICKET.md` 会在写操作后自动更新；不要调用手工 render / freshness 检查命令。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 每次工作必须归属到一个 ticket
- [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) — 延迟工作必须进入当前 ticket 或创建 backlog/fork ticket

## 工具来源

本原则依赖的 `aticket-cli` 命令来自 `aticket-cli` 仓库。详见 `aticket-cli/SKILL.md`（ticket-workdir skill）。
