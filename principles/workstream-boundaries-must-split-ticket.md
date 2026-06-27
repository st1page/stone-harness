---
description: "同一领域的连续讨论不等于同一个 ticket；新 repo、PR、外部文档族、benchmark 环境、外部运行态或 source repo 切换必须触发 ticket 边界检查并按 handoff unit 拆分"
triggers:
  - "workstream boundary"
  - "handoff unit"
  - "new repo"
  - "new PR"
  - "new external docs family"
  - "benchmark workstream"
  - "external runtime state"
  - "source repo switch"
  - "deferred TODO"
  - "follow-up"
  - "长 ticket"
  - "ticket 太长"
  - "large ticket"
  - "large archive"
  - "workspace too large"
  - "toolchain install"
  - "fork ticket"
---

# 工作流边界必须拆分 Ticket

Ticket 的边界是 **handoff unit**，不是主题关键词。即使仍在同一个大讨论 / 大 ticket 下，只要交付物、owner、外部状态或恢复入口不同，就拆成新 ticket 或 fork ticket。

## 核心判断

问一句：如果现在 context 丢失，后续 agent 是否应该从同一个 `TICKET.md`、同一个 `workspace/`、同一组外部链接和同一个 next action 恢复？如果答案是否定的，就拆。

边界检查的输出必须同时回答：

- 继续复用当前 ticket，还是创建 child ticket？
- 如果创建 child，是 `ticket new` 还是 `ticket "$TICKET_DIR" fork`？
- child 应保持 ACTIVE、用 `--backlog` 创建，还是创建后 `release`？
- parent 是继续协调、release，还是 archive？

## 必须触发边界检查的事件

遇到以下任一事件，先运行 `aticket-cli ticket "$TICKET_DIR" brief`，再写一条边界决策到当前 ticket：

- 新 repo 或 repo workstream。
- 新 PR / PR 线，或 PR merged / declined 后走另一个方向。
- 新外部文档族 / 外部文档线。
- 新 benchmark / 实验环境 / 远端运行态。
- source repo / ownership 切换。
- 目标从实现切到研究，或从研究切到产品化。
- 发现 deferred TODO / follow-up work，且它有独立 owner、外部状态、workspace 或 first action。
- ticket 规模告警：链接过多、跨多个公开 repo、`short-context` 已难以恢复 first action，或 `workspace/` 混入多个独立 workstream。
- ticket 进入“长票”形态：跨度超过一天且仍在新增不同类型工作，或 work log / item 数量已经让 `TICKET.md` 难以快速恢复当前 first action。
- ticket 目录进入“大目录”形态：安装了工具链 / package manager / model cache，保留多个 build tree / perf raw dump，或 `workspace/` / `artifacts/` 的大小已经成为 archive 前需要解释的状态。

长票和大目录不是单纯 hygiene 问题，它们通常说明当前 ticket 同时承载了实现、实验、发布、工具链和 cleanup 等多个 handoff unit。触发后先拆 child ticket 或把 source ticket 降级为 parent/index，不要继续把新 workstream 塞进同一个 ACTIVE ticket。

## 边界决策格式

每次触发边界检查，都把结果写进 ticket；即使决定不拆，也说明理由：

```bash
aticket-cli ticket "$TICKET_DIR" log \
  "Boundary check: user requested new repo hft-crypto-lab; this is a new handoff unit, not a continuation of current PR. Creating child ticket and linking both directions."
```

## 拆分方式

### 新建独立 ticket

适用于新 repo、新 PR 线、新 benchmark 环境、新外部文档线：

```bash
FOLLOWUP_DIR=$(aticket-cli ticket new \
  --topic "<new-workstream>" \
  --goal "<这个 handoff unit 要完成什么>" \
  --short-context "Split from $TICKET_DIR after boundary check: <why>. First action: <next command or inspection>.")
aticket-cli ticket "$TICKET_DIR" add-item "file://$FOLLOWUP_DIR"
aticket-cli ticket "$FOLLOWUP_DIR" add-item "file://$TICKET_DIR"
```

上面的 `ticket new` 形态只适用于当前 agent 立即切到 child 推进。只是记录 follow-up / handoff 时，必须加 `--backlog`；如果已经创建并 claim 但不继续推进，应写清 context 后 `release`。

### Fork 派生 ticket

适用于需要继承父 ticket 快照、`Must remember` 和上下文的研究 / monitor / publish / cleanup，也适用于同一个大 ticket 下的不同 branch / PR / benchmark / docs 分支任务：

同一个 parent ticket 可以代表 human-level intent / coordination thread；child/fork ticket 代表某个 branch-specific handoff unit。

```bash
FORK_DIR=$(aticket-cli ticket "$TICKET_DIR" fork \
  --topic "<derived-workstream>" \
  --goal "<fork ticket 要完成什么>")
aticket-cli ticket "$FORK_DIR" context \
  "Forked because <boundary>. First action: <next step>. Parent remains <active/archive/release decision>."
aticket-cli ticket "$TICKET_DIR" add-item "file://$FORK_DIR"
aticket-cli ticket "$FORK_DIR" add-item "file://$TICKET_DIR"
```

`fork` 后必须在对话里确认 source / forked ticket、fork goal，以及后续是否切到 forked ticket 推进。不立即切到 child 时，写清 child context 和双向链接后 `release` 成 BACKLOG。切到 child 后，repo 写操作必须先在 child ticket 的 `workspace/` 下创建或验证 linked worktree；不要让 parent 和 child 共用 checkout、branch 或 uncommitted worktree state。

### Parent ticket 收口

拆出 child 后，source ticket 不能无限作为 active index：

- 如果 source goal 已完成：写 final `short-context`，archive。
- 如果 source 还负责协调：保留 ACTIVE，但 `short-context` 必须写清它仍负责什么、child ticket 负责什么，以及 next coordination action。
- 如果 source 只剩纯索引功能，且没有 owner 要推进的下一步：archive source，让 child ticket 作为继续入口。
- 如果 source 仍在协调多个 branch-specific child/fork ticket，可以继续保持 ACTIVE；但每个 child 应该有自己的 owner、workspace、first action 和 recovery context。

长票 parent 收口前应优先写一个 `final-rollup` / `index` artifact：列出最终 PR / 页面 / benchmark / follow-up child ticket 的入口，说明哪些历史实验已经被 supersede。后续 agent 应该先读 rollup，而不是从数百行 item / log 里恢复状态。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 所有工作必须归属到 ticket，且 repo 写操作归属当前 ticket workspace
- [ticket-lifecycle-boundary-check](ticket-lifecycle-boundary-check.md) — 外部发布、阶段切换和最终回复前做 lifecycle decision
- [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) — 独立后续工作必须进入 backlog / fork ticket
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 长讨论中的意图变化和实现前状态必须 checkpoint
- [experiment-tickets-must-capture-minimum-contract](experiment-tickets-must-capture-minimum-contract.md) — benchmark / 实验 ticket 必须记录最小可复现合同
