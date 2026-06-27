---
description: "所有工作必须归属到一个 ticket；ticket 是工作单元、状态容器、workspace 和产物归档点"
triggers:
  - "开始工作"
  - "substantive work"
  - "ticket"
  - "开新ticket"
  - "开新 ticket"
  - "aticket"
  - "工作归属"
  - "claim"
  - "fork ticket"
---

# work-must-belong-to-a-ticket

每次工作必须**归属到一个 ticket**，把命令输出、日志、决策与产物落到文件里，而不是只留在对话 context。

## 可见性要求：定期显示当前 ticket

agent 不能只在内部记住当前 ticket。只要进入 substantive work，就要把当前 ticket 作为可见工作状态暴露给 human：

1. **开始工作 / 复用 ticket / 新建 ticket / fork ticket / context 压缩后恢复时**，明确说出当前 ticket 路径、goal 摘要，以及是否已 claim。
2. **长任务推进中**，至少在阶段切换时再次显示当前 ticket：从探索到实现、实现到验证、准备发 PR / 交接 / archive 前。
3. **如果 cwd、worktree 或工作目标发生切换**，同时显示当前 ticket 和当前 worktree 路径，避免 human 只能从对话上下文猜 agent 在操作哪个工作单元。

推荐的简短格式：

```text
当前 ticket: /home/tsshi/agent-tickets/tickets/<ticket> (ACTIVE, claimed by this agent)
当前 worktree: /home/tsshi/agent-tickets/tickets/<ticket>/workspace/<repo>-<topic>
```

## Must remember 读路径

`Must remember` 是 ticket 里不能只埋在流水日志中的 principle、preflight、invariant 和 human instruction。agent 不能只依赖“写进 ticket 了”来保证自己会遵守这些内容；必须把它们放进阶段边界的主动读路径。

在以下节点，先运行：

```bash
aticket-cli ticket "$TICKET_DIR" brief
```

- 开始工作 / 复用 ticket / context 压缩后恢复时
- `claim`、`fork` 后切入该 ticket 工作前
- 从探索进入实现、从实现进入验证、准备 release/archive 前
- repo 写操作前，和 linked worktree 校验一起做
- human 明确新增或修改约束后

`brief` 会集中显示 goal、short-context、`Must remember`、unread messages 和关键计数。普通 ticket 命令成功后，如果该 ticket 有 `Must remember` 条目，也会在 stderr 主动提醒；agent 看到提醒后要把这些条目当作当前 preflight 约束，而不是把它们当作普通日志。维护 `Must remember` 使用 `aticket-cli ticket "$TICKET_DIR" remember "<constraint>"` 添加一条，使用 `aticket-cli ticket "$TICKET_DIR" forget <index>` 删除一条；每个 ticket 最多 16 条，满了先删除过时条目。

## 为什么

- **中断恢复**：agent session 可能被 API 400 / timeout / 用户中断打断，ticket 目录是唯一可靠的恢复点
- **跨 agent 交接**：Claude / Codex / 人工接手时，`TICKET.md` 是 canonical handoff 文档
- **审计链**：事后追溯"为什么做这个决策"时，对话 context 已不可达，只有 ticket 目录留存

## 何时触发

- 开始任何 substantive work（探索、实现、验证、补查）前
- 发现当前没有可复用 ticket 时
- 工作目标切换成新的独立交付物 / 审计链时

## 如何应用

### Preflight 判定：复用 / 新建 / fork

决定开始工作前先做这个判断：

- **无当前 ticket 时的启动流程**：`无 ticket 不能继续` 的含义是不能直接进入实质命令 / repo 写操作；agent 仍然要自己执行只读 discover（`aticket-cli tickets search --query "<keywords>"` 或顶层 `tickets/*/TICKET.md` 扫描），判断是否有可复用 ticket。没有可复用 ticket 时，agent 应自己 `aticket-cli ticket new --topic "<topic>" --goal "<goal>"` 新建并默认 claim，随后立刻 `aticket-cli ticket "$TICKET_DIR" brief`，再继续工作。不要把这条规则理解成必须等待 human 先提供 ticket。
- **复用当前 ticket**：同一工作目标、同一 repo、同一 handoff 单元里的探索 / 实现 / 验证 / 补查 → 继续用现有 `TICKET_DIR`
- **新建 ticket**：没有可复用 ticket，或工作目标已切换成新的独立交付物 / 审计链
- **fork 独立 ticket**：source ticket 已形成可恢复状态，后续工作是 monitor / publish / sediment / cleanup 这类派生任务；同一个大 ticket 下不同 branch / PR / benchmark / docs 分支任务，如果需要继承父上下文，也属于 fork 语义

**经验口径**：`same goal, same repo, same handoff unit => reuse`。不要把 ticket 的边界退化成「一个命令一个 ticket」。

同时也不要把 ticket 边界退化成「同一个大领域一个 ticket」。如果出现新 repo、PR、外部文档族、benchmark 环境、外部运行态、source repo 切换，或 `Links` / workspace 规模明显膨胀，先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 做 handoff unit 边界检查。相关领域连续讨论只能说明需要互相链接，不能自动说明应该继续写同一个 ticket。

大 ticket 可以保留为 coordination / index ticket；同一大 ticket 下的 branch-specific 小 ticket 不是偏离 parent，而是把某条分支的 workspace、owner、PR/review 状态和 next action 独立化。需要继承 parent 当前上下文时优先 `fork`，不需要继承时再 `ticket new`。

如果开小 ticket 只是为了记录未来分支任务或交给后续 agent，创建时用 `--backlog`，或在写清 context 后 `release`；只有当前 agent 立即切换过去推进时，child ticket 才应保持 ACTIVE。切换到 child 后，repo 写路径也随之切换到 child 的 `workspace/`。

找现有 ticket：

```bash
ROOT="${AGENT_TICKETS_ROOT:-/home/tsshi/agent-tickets}"
ls -td "$ROOT"/tickets/* 2>/dev/null | head
rg -n '^Lifecycle:|^Owner:|^## Goal|^## Short context|^## Must remember|jp10|signal|backfill' "$ROOT"/tickets/*/TICKET.md 2>/dev/null
aticket-cli tickets search --query "jp10 signal backfill" --lifecycle-state ALL
```

简单读取直接读顶层 ticket 目录和 `TICKET.md`；跨 ticket 全文检索才使用 `aticket-cli tickets search --query "<keywords>"`。不要递归扫整个 `tickets/` 树，否则会命中 ticket `workspace/` 里的模板、fixture 或 cloned repo 文件。创建新 ticket 前先查是否已有同目标 BACKLOG/ACTIVE ticket；如果只搜到 ARCHIVED ticket，不要继续写入，应该新建或 fork。找到可复用 BACKLOG ticket 后，先 `aticket-cli ticket "$TICKET_DIR" claim`；找到其他 agent 持有的 ACTIVE ticket 时先确认接管/并行语义。

### 用户只要求开新 ticket 时

如果用户的请求语义是“给后续工作开一个新 ticket / 记录一个 follow-up / 准备转手给其他 agent”，但没有明确要求**当前 agent**继续做，agent 只能：

1. 用 `aticket-cli ticket new --backlog` 创建新 ticket，写清 goal / short-context / 来源。
2. 在对话里展示新 ticket 路径、goal、lifecycle=`BACKLOG`，确认这是 handoff ticket。
3. 停止推进该 ticket 内的实质工作；不要 claim、不要创建 repo worktree、不要实现、不要验证目标任务。

这是 handoff 语义，不是执行授权。常见表述包括“开个新 ticket”“给这个开 ticket”“记录一个后续 ticket”“开新 ticket 让别人做”。

只有当用户明确说当前 agent 要做，例如“开新 ticket 去做”“新建 ticket 然后你继续修”“用新 ticket 做完这个”，才把新 ticket 作为当前工作 ticket claim 后继续推进。

### Ticket 生命周期操作后的 human 确认

`aticket-cli ticket new` / `aticket-cli ticket "$TICKET_DIR" fork` / `aticket-cli ticket "$TICKET_DIR" release` / `aticket-cli ticket "$TICKET_DIR" archive` 会改变工作边界或生命周期，执行后必须立刻向 human 明确确认结果，再继续后续推进：

- **new 之后**：展示新 ticket 路径、goal、claim 状态，并确认后续工作将归属到这个 ticket。
- **只开 ticket 的 new 之后**：使用 `--backlog`，展示新 ticket 路径、goal、BACKLOG 状态；确认这是 handoff ticket，不继续执行目标任务。
- **fork 之后**：展示 source ticket、forked ticket、fork goal，并确认后续是否切到 forked ticket 推进，还是只把 forked ticket 作为 follow-up 记录。
- **release 之后**：展示 released ticket、当前状态、下一步 owner/first action，并明确这是让出推进权 / handoff 语义；如果当前 agent 仍负责 parent 协调、回写或收口，不要因为切到 forked child ticket 就自动 release parent。
- **archive 之后**：展示 archived ticket，并确认当前工作已收口；如果还要继续，必须经 human 确认后新建或 fork 新 ticket，不能继续写 archived ticket。

确认必须发生在对话里，不能只写进 `TICKET.md`。如果 human 没有确认，不要把工作边界切到新 ticket / forked ticket，不要把 release 误表达成“仍由当前 agent 持有”，也不要在 archive 后继续追加实质工作。

### 创建 ticket

```bash
TICKET_DIR=$(aticket-cli ticket new \
  --topic "fix-jp10-signal-mapping" \
  --goal "Fix jp10 wrong deploy-key signal mapping" \
  --short-context "Need inspect jp10 deploy-key mapping; first verify live query output.")
```

- `--topic` 必须给，出现在目录名里
- `--goal` 必须给且不能为空；如果后续目标变化，用 `aticket-cli ticket "$TICKET_DIR" goal`
- owner/lease 默认从 provider 环境推断；必要时可显式传 `--agent-type claude|codex --session-id <uuid>`
- `--short-context` 可选；如果创建时已经知道当前状态和下一步，可以直接写入

### Claim 已有 ticket

复用已有 ACTIVE ticket 前，先 claim 它，确保当前 ticket 的 `workspace/` 和当前推进权归属于自己：

```bash
TICKET_DIR="$EXISTING_TICKET_DIR"
aticket-cli ticket "$TICKET_DIR" claim
aticket-cli ticket "$TICKET_DIR" brief
```

不在 provider 工具子进程中运行时，可显式传 owner 身份：

```bash
aticket-cli ticket "$TICKET_DIR" claim --agent-type codex --session-id "<uuid>"
```

如果已有其他 active holder，不要默认 `--force` 接管；先和 human 确认是接管、合并进去，还是开新 ticket 只把它当参考。只有 human 明确同意接管时，才允许：

```bash
aticket-cli ticket "$TICKET_DIR" claim --force --confirm-human-approved-takeover
```

如果要并行推进，不要接管同一个 ticket/workspace；fork 或新建 ticket，并在自己的 ticket `workspace/` 下使用独立 worktree/branch。

### Fork 独立 ticket

当 source ticket 已形成可恢复状态，后续工作是派生任务（monitor / publish / sediment / cleanup）时：

```bash
FORKED_TICKET_DIR=$(aticket-cli ticket "$SOURCE_TICKET_DIR" fork \
  --topic "monitor-jp10-backfill" \
  --goal "Monitor jp10 backfill after merge")
aticket-cli ticket "$FORKED_TICKET_DIR" brief
```

- `fork` 是带 `forked-from` 和 source 快照的特殊 `new`
- 派生类型和来源语义写进 `--goal`、`short-context` 或 `log`
- forked ticket 有自己的 lease；source ticket 不会被自动回写，也不会自动 archive
- forked ticket 可以读 source ticket 当时的 snapshot，以及 source ticket 目录中的产物；但不操作 source ticket

### Repo worktree 归属

ticket 解决证据链、lease 和工作容器；git worktree 解决仓库写路径隔离。repo 写操作的 worktree 必须放在当前 ticket 的 `workspace/` 下，不要放在 repo-local `.claude/worktrees/`。

具体创建、同步和验证步骤见 [code-work-preflight](code-work-preflight.md) 与 [write-ops-must-verify-linked-worktree-before-first-edit](write-ops-must-verify-linked-worktree-before-first-edit.md)，不要在本文件重复维护命令块。

### 最小写实合同（不要停在 scaffold）

`aticket-cli ticket new` 已要求 `--goal`，但如果会执行命令、产生产物或改文件，仍至少补齐：

1. 一条真实的 `log`，或用 `add-item` 记录产出的资源入口
2. 必要时维护精简的 `short-context`
3. 必要时维护 `Must remember`，把不能忘的 principle / preflight / invariant / human instruction 写成最多 16 条的 list；满了先删除过时条目
4. 对 `aticket-cli ticket new` / `aticket-cli ticket "$TICKET_DIR" fork` / `aticket-cli ticket "$TICKET_DIR" release` / `aticket-cli ticket "$TICKET_DIR" archive` 操作，在对话里完成 human 确认，并把确认结论作为 `log` 记录到相关 ticket

```bash
aticket-cli ticket "$TICKET_DIR" log "$(date +%H:%M): Confirmed utop2-token mismatch in live query"
aticket-cli ticket "$TICKET_DIR" add-item "https://github.com/example-org/example-repo/pull/123"
aticket-cli ticket "$TICKET_DIR" context "PR is open; next check feedback, then monitor backfill if merged."
aticket-cli ticket "$TICKET_DIR" remember "Preflight: verify linked worktree before repo edits"
aticket-cli ticket "$TICKET_DIR" forget 2
```

如果 substantive work 已经开始，但 `TICKET.md` 仍接近初始 scaffold（没有真实 `Work log`、`Links` 或可恢复的 `Short context`），视为 ticket hygiene 失败——先补齐再继续。

短任务完成后直接 archive；archive 后这个 ticket 不再继续修改，新的变更应 fork 或新建 ticket：

```bash
aticket-cli ticket "$TICKET_DIR" archive
```

## 相关原则

- [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) — 延迟工作必须进入当前 ticket 或创建 backlog/fork ticket
- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — 新 repo / PR / 外部文档族 / benchmark / source repo 切换等独立 handoff unit 必须拆票
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录
- [ticket-lifecycle-boundary-check](ticket-lifecycle-boundary-check.md) — ticket 收口前必须写清 final result、external state、next owner、剩余风险和 workspace 状态
- [code-work-preflight](code-work-preflight.md) — ticket owns `workspace/`，repo 写操作仍必须使用并验证 linked git worktree

## 工具来源

本原则依赖的 `aticket-cli` 命令来自 `aticket-cli` 仓库。详见 `aticket-cli/SKILL.md`（ticket-workdir skill）。
