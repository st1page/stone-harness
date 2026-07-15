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
- 创建 / 更新文档页面后
- 发布任何外部报告、benchmark 结论、review comment 后
- 启动长后台任务后，或后台任务结束后
- 从探索进入实现、实现进入验证、验证进入发布 / 交接时
- 创建新 repo、切到另一个 source repo、开启新 PR 线、创建文档页面族、或进入新的 benchmark / remote runtime workstream 时
- 准备切到另一个 ticket、release、archive 前

## 四个问题

每次边界检查只问四件事：

1. **目标状态**：这个 ticket 的 goal 是否已经完成？是完成、部分完成、取消、阻塞，还是仍在推进？收口前要写清 final result，不要只写“done”。
2. **外部状态**：PR / 文档页面 / job / 数据产物 / 安装状态是什么？如果有 URL、commit、page id、tmux session 或输出目录，是否已经写回 ticket？
3. **下一任 owner**：下一步由谁负责？无人、human、reviewer、当前 agent、未来 agent，还是另一个 follow-up ticket？
4. **生命周期动作**：现在应该 `archive`、`release` 成 BACKLOG、fork / new follow-up，还是继续保持 ACTIVE 并写清 first action？

## 决策口径

| 边界状态 | 动作 |
|---|---|
| 准备给最终答复，目标完成且无后续 | 写 final `short-context`，用 `add-item` 记录资源入口，`archive` |
| 有可用 remote 的 repo 保留了代码改动，但 topic branch / PR 尚未发布 | 默认交付尚未完成，保持 ACTIVE；确有 blocker 或明确下一 owner 时可 `release` 成 BACKLOG。“没有另行要求 PR”不能作为 archive 理由 |
| PR 已创建但还等 review / merge | 普通 implementation / code-delivery goal 保持 ACTIVE 并写清 next action，或已由 human / reviewer 接手时 `release` 成 BACKLOG；只有 goal 明确止于 PR publication 且交接已成立时才可 `archive` |
| PR 已合并 | 回到发布 / 实现 ticket 做 closeout：记录 PR、merged commit、master 同步状态和验证结果；如果原 goal 已完成则 `archive`；如果只剩独立尾巴，先 fork / new backlog ticket 再 `archive` 原票 |
| human 明确要求暂停 / 停止 / 暂时别 push，delivery 尚未终结 | 停止外部发布，记录 branch / commit 和 first action；保持 ACTIVE 或 `release` 成 BACKLOG，不当作 local-only 终态 archive |
| human 肯定说明本地产物就是最终交付且以后不再 push / 发 PR、repo 无 remote、改动已丢弃 / supersede、或采用明确替代交付 | 记录具体依据和 commit / patch / artifact 等恢复入口；目标无后续时可 `archive` |
| 文档页面 / 外部报告已发布且无后续 | 记录 URL / page id / version；无后续则 `archive` |
| review child ticket 已产出 review artifact / finding summary | 写清 final result、evidence entry、next owner 和 residual risk 后 `archive`；finding 的修复由 parent / author / human / follow-up ticket 接手，不把 review child `release` 回 BACKLOG 等修复 |
| 后台 job / tmux 仍在跑 | 保持 ACTIVE；`short-context` 必须写 session 名、输出目录、停止条件和下一次检查方式 |
| 后续是独立工作单元 | fork 或新建 BACKLOG ticket，双向链接；source ticket 若目标已完成则 `archive` |
| parent ticket 仍负责协调，某个 branch-specific 任务需要独立推进 | fork child ticket；parent 保持 ACTIVE 并写清 coordination role、child link 和 next coordination action；child 若不是当前立即推进则 release/BACKLOG |
| 只是等 human 回答或 reviewer 反馈 | 明确 next owner 和 first action；如果当前 agent 不继续占有推进权，`release` 成 BACKLOG |
| 新 repo / PR 线 / 页面族 / benchmark 环境 / source repo 切换 | 先按 handoff unit 判断；通常 fork 或新建 ticket，并把 repo worktree / docs / benchmark artifacts 放进新 ticket workspace |
| ticket 已跨多个公开 repo、链接过多或 short-context 难以恢复 | 立即做 split review；不要继续把相关领域的新工作塞进同一个 ACTIVE ticket |

## 归档前最小收口字段

归档前必须让下一个 agent 不读对话历史也能判断工作是否真正结束。`short-context` 至少写清：

- **Final result**：完成、部分完成、取消、阻塞，具体是哪一种。
- **External state**：PR / commit / 文档页面 / job / data file / install 状态；资源入口用 `add-item` 登记。
- **Next owner**：无人接手、human 接手、reviewer 接手、另一个 ticket 接手，或当前 ticket 后续仍需保持 active。
- **Residual risk**：未验证范围、已知缺口、需要 reviewer 特别看的点；没有也写 none known。
- **Workspace state**：repo worktree 是否干净、是否已推分支、是否需要保留 workspace。
- **Storage state**：ticket `workspace/` / `artifacts/` 是否包含可再生 build、toolchain、package cache、raw trace/perf dump；如果保留，为什么需要保留。

对 repo 代码工作，以上字段还必须语义一致。以下组合不能作为正常归档终态：

- retained code + no PR + complete + `Next owner: none`，除非记录了 human 肯定说明本地产物是最终交付且以后不再 push / 发 PR，或 no-remote / discarded / superseded / alternative-delivery 依据；
- 普通 implementation / code-delivery goal 的 PR OPEN + archive，即使已有 next owner；只有 goal 明确止于 PR publication 且交接已成立时例外；
- PR MERGED / DECLINED / SUPERSEDED + ACTIVE / BACKLOG + 没有剩余 goal。

不要靠全局猜测任意 git worktree 来决定 lifecycle；依据当前 ticket 明确记录的 repo、branch、commit、PR state 和 delivery disposition 判断。exception 是普通、可解释的终态，不应依赖泛化的 `--confirm-*` 绕过。

### 代码交付回归矩阵

| 场景 | 预期动作 |
|---|---|
| remote-backed 新实现 / 修复 | 同一 ticket 推送 branch 并创建 PR；未发布时不算完成 |
| 已有 PR / review finding | 更新现有 branch / PR，不新建 publication ticket 或重复 PR |
| 发布前 review 发现问题 | 当前 ticket 保持 ACTIVE，修复并验证后再发布 / 更新 PR |
| PR OPEN，当前 agent 仍负责 | 保持 ACTIVE |
| PR OPEN，human / reviewer 已接手 | 普通代码 goal release 成 BACKLOG；publication-only goal 交接成立后可 archive |
| human 明确暂停 / 先到这里 / 暂时别 push，代码尚未发布 | 停止外部发布，记录恢复点；保持 ACTIVE 或 release 成 BACKLOG，不 archive |
| human 肯定说明本地产物是最终交付且以后不再 push / 发 PR、repo 无 remote 或明确替代交付 | 记录依据和 durable recovery pointer；无剩余 goal 时可 archive |
| 改动 discarded / superseded，或无 repo change | 记录终态；无剩余 goal 时可 archive |
| PR 已 MERGED / DECLINED / SUPERSEDED 但 ticket 仍 ACTIVE / BACKLOG | 完成 closeout；无剩余 goal 时 archive |

完成的 parent / index ticket 也要收口：child tickets 都已结束时，parent 写 final rollup 后 archive；如果 child 仍 open，parent 要说明自己是否仍有协调 owner。如果 parent 只剩索引功能，archive parent，并在 child ticket 里保留反链。

归档或 release 前还要检查当前 ticket 链接的 BACKLOG tickets：如果本 ticket 已经完成、取消或废弃了某个 linked backlog follow-up，必须明确处理那个 follow-up 的 lifecycle：archive 它、fork / new replacement，或写清为什么仍然 open。不要只在当前 ticket 里链接旧 backlog 后收口，留下已经被完成或 supersede 的原票无人回收。

## 大目录归档检查

归档前如果 ticket 目录明显变大，或 archive 命令拒绝并提示目录超过阈值，不能直接绕过。先按已有 closeout cleanup / worktree cleanup 规则处理；本原则只要求在 lifecycle 边界上写清 cleanup 后的 storage state、仍保留大文件的原因，以及是否需要 human confirm。

### Archive preflight cleanup hints

先逐项盘点 `workspace/`、`artifacts/` 和 ticket 根下的临时输出，再按下面三类处理。分类的目的只是减少可解释的冗余存储；它**不能**把尚未满足交付条件的 ticket 变成可 archive，也不能替代任何 `--human-confirm-*` 保护。

| 分类 | 可处理的内容 | 必须先记录 / 验证的证据 | 动作 |
|---|---|---|---|
| 可安全删除 | 已提交且已推送的 linked worktree；可由已记录命令从 commit / 输入重新生成的 build、package cache、coverage 或派生输出；无交接价值的 scratch | 对 worktree：`git status --short` 为空，目标 commit 在已推送的 topic branch / PR 上；对再生内容：记录生成命令、输入位置和 commit，且不把唯一测试证据或唯一结果当作 cache | 删除前把恢复入口写入 ticket；用正常 `git worktree remove` 清理 worktree，删除再生目录后更新 Storage state |
| 需要人工决定 | 内容是否再生不清楚的 cache / 下载物；未确认已被外部系统保存的报告、截图、原始数据；仍可能用于 reviewer、复现或下一个 owner 的大文件 | 列出路径、大小、可能用途、可否从何处重建，以及不删除的成本；没有充分依据时不要把它标成可安全删除 | 保留并在 ticket 请求具体处置，或先 fork / new 一个独立 cleanup ticket |
| 必须保留 | 未提交或未推送的工作；唯一的实验/验证证据、原始数据、错误日志或决策记录；恢复工作所需的 PR、commit、输入、脚本和说明 | 将证据入口和保留理由写入 ticket；若内容大，说明留存位置、owner 和后续保留期限 | 不删除；若 archive 阈值仍受阻，按工具提示向 human 说明具体范围并请求针对该异常操作的确认 |

判断 worktree 是否可清理时，`git status --short` 为空只是必要条件，不是充分条件：还要确认提交已经在远端可恢复，且当前 ticket 不再需要本地 checkout 来完成 review、修复、验证或交接。不要用删除本地 worktree 来掩盖未发布改动，也不要因为清掉 workspace 就把 PR OPEN 的普通代码交付 ticket archive。

“可以现场生成”也必须是可审计的再生路径：至少记录命令或脚本、输入来源、对应 commit 和输出的用途。不能只凭文件名（例如 `*.npz`、`cache/` 或 `dist/`）推断可删除；同类文件可能是唯一结果或验证证据。

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

不要把 PR / 文档页面的具体发布格式细节复制到这里；也不要把本原则的 lifecycle 决策表塞回 PR / 文档发布专项规则里。外部发布规则保持窄，生命周期判断保持通用。

## 相关原则

- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — 同一领域连续讨论不等于同一个 ticket，按 handoff unit 拆分 workstream
- [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) — 独立后续工作必须进入 backlog / fork ticket
- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 所有工作必须归属到 ticket；生命周期操作后报告结果，只有旧票归属不明或安全保护要求时才向 human 确认
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 边界检查结论必须写进 ticket
