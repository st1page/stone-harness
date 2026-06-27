---
description: "最终回复前、外部发布后、阶段切换前必须判断当前 ticket 应 archive、release、fork follow-up，还是继续 ACTIVE 并写清 next action"
triggers:
  - "final response"
  - "最终回复"
  - "PR created"
  - "PR updated"
  - "PR merged"
  - "documentation page published"
  - "page created"
  - "page updated"
  - "lifecycle boundary"
  - "阶段切换"
  - "keep active"
  - "release to backlog"
  - "ticket closeout"
  - "closeout"
  - "archive ticket"
  - "large archive"
  - "human-confirm"
  - "--human-confirm"
  - "--confirm"
  - "final result"
  - "next owner"
  - "parent ticket"
  - "index ticket"
---

# ticket-lifecycle-boundary-check

Ticket 生命周期边界检查解决的是"这一步之后当前工作单元应该处于什么状态"。它不是 PR / 文档页面的发布格式规则，也不是归档前的详细 closeout 模板；它是在关键边界上强制 agent 做一次 lifecycle decision，避免完成、等待、发布、后台运行这些状态都混在 `ACTIVE` 里。

## 何时触发

在这些节点先做一次判断，再进入下一步：

- 准备给用户最终回复前
- 创建 / 更新 PR 后，或确认 PR 已合并后
- 创建 / 更新文档页面、release notes 或长期文档后
- 发布任何文档页面、benchmark 结论、review comment 后
- 启动长后台任务后，或后台任务结束后
- 从探索进入实现、实现进入验证、验证进入发布 / 交接时
- 创建新 repo、切到另一个 source repo、开启新 PR 线、创建外部文档族、或进入新的 benchmark / remote runtime workstream 时
- 准备切到另一个 ticket、release、archive 前

## 四个问题

每次边界检查只问四件事：

1. **目标状态**：这个 ticket 的 goal 是否已经完成？是完成、部分完成、取消、阻塞，还是仍在推进？收口前要写清 final result，不要只写“done”。
2. **外部状态**：PR / 文档页面 / job / 数据产物 / 安装状态是什么？如果有 URL、commit、文档 id、tmux session 或输出目录，是否已经写回 ticket？
3. **下一任 owner**：下一步由谁负责？无人、human、reviewer、当前 agent、未来 agent，还是另一个 follow-up ticket？
4. **生命周期动作**：现在应该 `archive`、`release` 成 BACKLOG、fork / new follow-up，还是继续保持 ACTIVE 并写清 first action？

## 决策口径

| 边界状态 | 动作 |
|---|---|
| 准备给最终答复，目标完成且无后续 | 写 final `short-context`，用 `add-item` 记录资源入口，`archive` |
| PR 已创建但还等 review / merge | 保持 ACTIVE 并写清 next action，或当前 agent 不再持有时 `release` 成 BACKLOG |
| PR 已合并 | 回到发布 / 实现 ticket 做 closeout：记录 PR、merged commit、master 同步状态和验证结果；如果原 goal 已完成则 `archive`；如果只剩独立尾巴，先 fork / new backlog ticket 再 `archive` 原票 |
| 文档页面 / release notes 已发布且无后续 | 记录 URL / 文档 id / version；无后续则 `archive` |
| review child ticket 已产出 review artifact / finding summary | 写清 final result、evidence entry、next owner 和 residual risk 后 `archive`；finding 的修复由 parent / author / human / follow-up ticket 接手，不把 review child `release` 回 BACKLOG 等修复 |
| 后台 job / tmux 仍在跑 | 保持 ACTIVE；`short-context` 必须写 session 名、输出目录、停止条件和下一次检查方式 |
| 后续是独立工作单元 | fork 或新建 BACKLOG ticket，双向链接；source ticket 若目标已完成则 `archive` |
| parent ticket 仍负责协调，某个 branch-specific 任务需要独立推进 | fork child ticket；parent 保持 ACTIVE 并写清 coordination role、child link 和 next coordination action；child 若不是当前立即推进则 release/BACKLOG |
| 只是等 human 回答或 reviewer 反馈 | 明确 next owner 和 first action；如果当前 agent 不继续占有推进权，`release` 成 BACKLOG |
| 新 repo / PR 线 / 外部文档族 / benchmark 环境 / source repo 切换 | 先按 handoff unit 判断；通常 fork 或新建 ticket，并把 repo worktree / docs / benchmark artifacts 放进新 ticket workspace |
| ticket 已跨多个公开 repo、链接过多或 short-context 难以恢复 | 立即做 split review；不要继续把相关领域的新工作塞进同一个 ACTIVE ticket |

## 归档前最小收口字段

归档前必须让下一个 agent 不读对话历史也能判断工作是否真正结束。`short-context` 至少写清：

- **Final result**：完成、部分完成、取消、阻塞，具体是哪一种。
- **External state**：PR / commit / documentation page / job / data file / install 状态；资源入口用 `add-item` 登记。
- **Next owner**：无人接手、human 接手、reviewer 接手、另一个 ticket 接手，或当前 ticket 后续仍需保持 active。
- **Residual risk**：未验证范围、已知缺口、需要 reviewer 特别看的点；没有也写 none known。
- **Workspace state**：repo worktree 是否干净、是否已推分支、是否需要保留 workspace。
- **Storage state**：ticket `workspace/` / `artifacts/` 是否包含可再生 build、toolchain、package cache、raw trace/perf dump；如果保留，为什么需要保留。

完成的 parent / index ticket 也要收口：child tickets 都已结束时，parent 写 final rollup 后 archive；如果 child 仍 open，parent 要说明自己是否仍有协调 owner。如果 parent 只剩索引功能，archive parent，并在 child ticket 里保留反链。

归档或 release 前还要检查当前 ticket 链接的 BACKLOG tickets：如果本 ticket 已经完成、取消或废弃了某个 linked backlog follow-up，必须明确处理那个 follow-up 的 lifecycle：archive 它、fork / new replacement，或写清为什么仍然 open。不要只在当前 ticket 里链接旧 backlog 后收口，留下已经被完成或 supersede 的原票无人回收。

## 大目录归档检查

归档前如果 ticket 目录明显变大，或 archive 命令拒绝并提示目录超过阈值，不能直接绕过。先按已有 closeout cleanup / worktree cleanup 规则处理；本原则只要求在 lifecycle 边界上写清 cleanup 后的 storage state、仍保留大文件的原因，以及是否需要 human confirm。

如果清理本身已经是独立工作单元，先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) fork / new cleanup ticket；source ticket 已归档时不要继续写入 source，使用 cleanup ticket 并用 archived message / item 反链。

## Human Confirm 参数

任何 `--human-confirm-*`、`--confirm-*`、`--confirm-human-*` 这类绕过保护、接管、强制删除、强制归档或改变生命周期安全边界的参数，都要求 human 对**同一个具体异常操作**给出明确批准。

执行前必须在对话里说明：

- 将要执行的命令和确认参数名。
- 工具为什么要求确认，或该操作绕过了哪条保护。
- 影响范围，例如 ticket 路径、目录大小、将删除/保留的内容、要接管的 owner、要归档的 lifecycle。
- 不执行确认参数时的安全替代方案，例如先 cleanup、fork ticket、release/backlog 或等待 human。

不要从邻近意图推断确认。比如“结束”“继续”“可以”“按你说的做”只能说明用户希望推进目标，不能自动授权 `--human-confirm-archive-large-dir`、`--confirm-human-approved-takeover` 或类似强制参数。没有明确批准时，停下并询问，或选择不需要绕过保护的安全路径。

## 记录要求

边界检查的结果必须外部化到 ticket，不能只写在对话里：

```bash
aticket-cli ticket "$TICKET_DIR" context \
  "PR is open; next owner: reviewer/current agent. First action: check feedback, then rerun smoke. Residual risk: migration not tested on prod data."
```

如果边界动作产出新的 ticket 或外部发布物，必须双向链接。资源入口只用 `add-item` 记录；需要说明语义时写进 `short-context` 或 `log`，不要再使用旧 Artifacts 写法为同一个 URL 维护第二份事实源：

```bash
aticket-cli ticket "$TICKET_DIR" add-item "https://..."
aticket-cli ticket "$TICKET_DIR" add-item "file://$FOLLOWUP_DIR"
```

## 与发布规则的关系

- [published-content-must-identify-ticket](published-content-must-identify-ticket.md) 管"发布物正文能否反查 ticket，以及发布后反链是否记录"。
- 本原则管"发布完成后当前 ticket 生命周期该怎么走"。

不要把 PR / 文档页面的具体发布格式细节复制到这里；也不要把本原则的 lifecycle 决策表塞回发布专项规则里。外部发布规则保持窄，生命周期判断保持通用。

## 相关原则

- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — 同一领域连续讨论不等于同一个 ticket，按 handoff unit 拆分 workstream
- [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) — 独立后续工作必须进入 backlog / fork ticket
- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 所有工作必须归属到 ticket，ticket 生命周期操作后要向 human 确认
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 边界检查结论必须写进 ticket
