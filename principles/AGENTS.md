# 控制面知识（principles）

本目录收敛“agent 如何做事”的控制面知识：协作规范、工具链、工作流和原则。入口仍以仓库根 `AGENTS.md` 为准（always-on）。

## 快速加载分组

### Ticket 生命周期

- [work-must-belong-to-a-ticket.md](work-must-belong-to-a-ticket.md) — ticket 归属、无当前 ticket 时的 discover/new/claim 启动流程、`brief` 字段、显示当前 ticket、只开 backlog ticket、ticket lifecycle 命令确认和 release handoff 细则；**开始 / 恢复 / ticket 生命周期操作后**
- [workstream-boundaries-must-split-ticket.md](workstream-boundaries-must-split-ticket.md) — 工作流边界变化、deferred / follow-up、长 ticket 或不相干目标需要拆 ticket / fork ticket 时读取；**new repo / new PR / 外部文档族 / benchmark / source repo 切换 / 长 ticket**
- [persistent-state-must-be-externalized.md](persistent-state-must-be-externalized.md) — 记录命令输出、决策、产物、恢复状态或长讨论 checkpoint；**执行命令 / 做决策 / 产生产物 / 更新状态 / 用户意图变化 / 实现前 checkpoint**
- [ticket-lifecycle-boundary-check.md](ticket-lifecycle-boundary-check.md) — 最终回复、外部发布、阶段切换前判断 archive / release / fork follow-up / 继续 ACTIVE，并在收口前写清 final state；**最终回复 / 外部发布 / 阶段切换 / archive 前**
- [deferred-work-must-become-ticket.md](deferred-work-must-become-ticket.md) — deferred / follow-up work 进入当前 ticket，或创建 backlog / fork ticket；**deferred TODO / follow-up / 依赖以后再做**

### 代码工作

- [code-work-preflight.md](code-work-preflight.md) — repo 写操作、提交、推送和 PR 必须在 ticket-owned worktree/topic branch 中进行，禁止直推远端 `master`；phase/worker 边界 dirty set 变宽时先解释或隔离；repo-wide formatter / bulk rewrite 运行后必须 commit-or-isolate；**任何代码工作 / repo 写操作 / git add / git commit / git push / create PR / dirty worktree / partial commit / worker handoff / repo-wide formatter 前后**
- [write-ops-must-verify-linked-worktree-before-first-edit.md](write-ops-must-verify-linked-worktree-before-first-edit.md) — 第一次正式 repo 写操作前验证 cwd、git-dir、common-dir、branch 和 ticket `workspace` 路径；**第一次编辑前 / apply_patch 前**

### P0 / 通用默认

- [verify-cli-args-before-invocation.md](verify-cli-args-before-invocation.md) — 首次调用不熟悉的 CLI 子命令先跑 `--help`，不要猜参数名；**首次调用 repo-local helper / 不熟悉的 CLI 子命令时**

### 文档写作 / 发布

- [published-content-must-identify-ticket.md](published-content-must-identify-ticket.md) — 发布到 GitHub PR / issue / comment、release notes、benchmark 结论或文档页面前，正文必须标注当前 ticket；正式技术结论必须 pin 可追溯 source commit；发布后反向记录 URL；**改已有文档 / 发布 PR description / 文档页面 / benchmark 结论前**

### PR review / subagent review

- [pr-review-subagents-must-use-aticket.md](pr-review-subagents-must-use-aticket.md) — PR review subagent 必须接受 sts-harness 控制面上下文，先有 review ticket，搜索历史 ticket 获取背景，在 ticket workspace 里做实验，并把 review 证据、结论和发布物双向链接；**review PR / subagent review / PR comment 前**

### 验证 / 实验

- [experiment-tickets-must-capture-minimum-contract.md](experiment-tickets-must-capture-minimum-contract.md) — 实验、benchmark、smoke ticket 必须记录假设、环境、命令、结果、结论和可复现入口；**experiment / benchmark / smoke / 跑实验 / validation**
- [agent-experiments-use-ticket-local-data-plane.md](agent-experiments-use-ticket-local-data-plane.md) — 多 run 实验/benchmark 使用 ticket-local Aim/JSON/CSV 数据面，aticket 保持控制面，避免 hot-loop logging，并在验证后再汇总到中央数据面；**Aim / experiment tracking / benchmark tracking / agent workspace / central Aim**
- [validators-must-not-false-green.md](validators-must-not-false-green.md) — 验证类工具必须避免没有真正检查输入却输出 OK 的假绿；**写校验脚本 / 检查流程时**

## 全量索引

| 文件 | 内容 |
|---|---|
| [agent-experiments-use-ticket-local-data-plane.md](agent-experiments-use-ticket-local-data-plane.md) | agent 实验 ticket-local 数据面 |
| [code-work-preflight.md](code-work-preflight.md) | 代码工作 preflight |
| [deferred-work-must-become-ticket.md](deferred-work-must-become-ticket.md) | deferred / follow-up work 处理 |
| [experiment-tickets-must-capture-minimum-contract.md](experiment-tickets-must-capture-minimum-contract.md) | 实验 / benchmark / smoke 最小可复现合同 |
| [persistent-state-must-be-externalized.md](persistent-state-must-be-externalized.md) | 持久化状态外部化 |
| [pr-review-subagents-must-use-aticket.md](pr-review-subagents-must-use-aticket.md) | PR review subagent 的 ticket / workspace / 证据链规则 |
| [published-content-must-identify-ticket.md](published-content-must-identify-ticket.md) | 发布内容必须标注对应 ticket |
| [ticket-lifecycle-boundary-check.md](ticket-lifecycle-boundary-check.md) | ticket lifecycle 边界检查 |
| [validators-must-not-false-green.md](validators-must-not-false-green.md) | 验证工具避免假绿 |
| [verify-cli-args-before-invocation.md](verify-cli-args-before-invocation.md) | 不熟悉 CLI 子命令先查 `--help` |
| [work-must-belong-to-a-ticket.md](work-must-belong-to-a-ticket.md) | 所有工作必须归属 ticket |
| [workstream-boundaries-must-split-ticket.md](workstream-boundaries-must-split-ticket.md) | workstream 边界和拆票 |
| [write-ops-must-verify-linked-worktree-before-first-edit.md](write-ops-must-verify-linked-worktree-before-first-edit.md) | repo 写操作前验证 linked worktree |
