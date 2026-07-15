---
description: "PR review subagent 必须接受 sts-harness 控制面上下文，并把 review 归属到 aticket：先搜历史 ticket，先独立发现问题，再复核已知问题，用 ticket workspace 做实验，并把结论、证据和发布物双向链接"
triggers:
  - "review PR"
  - "PR review"
  - "subagent review"
  - "review subagent"
  - "code review"
  - "review-agent-cli"
  - "GitHub comment"
  - "PR comment"
---

# PR Review Subagent 必须使用 aticket

PR review 不是纯读对话任务。只要 agent 或 subagent 要判断一个 PR 是否有 bug、跑实验、发布 review comment，review 本身就是一个需要恢复、审计和交接的工作单元，必须归属到 aticket。

## 为什么

- **review 结论需要证据链**：最终 comment 通常很短，但判断过程包含 diff 理解、历史背景、实验命令、被排除的假设和风险取舍。
- **subagent context 更容易丢**：父 agent 只看到摘要时，后续很难复原 subagent 为什么认为某处有问题或没问题。
- **历史 ticket 是 review 背景库**：过去的 bug、PR、rollback、benchmark 和 runbook 常常能解释当前 PR 的真实约束。
- **review 也需要实验隔离**：checkout PR 分支、跑测试、改临时代码或复现问题时，必须有 ticket-owned workspace，不能污染主 checkout。

## 适用边界

适用：

- 人工请求 agent / subagent review 一个 PR
- 父 agent 派多个 subagent 分别 review diff、测试、设计或风险面
- wrapper 自动运行 reviewer 并准备发布 GitHub / forge / 文档页面 review 结果
- review 期间需要搜索历史 ticket、checkout PR、跑测试、写 notes 或发布 comment

不适用：

- 只在当前对话里回答一个很小的代码片段问题，且不执行命令、不产生产物、不发布外部内容
- 由 review-agent-cli wrapper 明确托管持久化的 automated reviewer；此时 reviewer 本体可以声明 `Session: inherited (reviewer-wrapper-managed)`，由 wrapper 或父 ticket 负责落 notes / add-item / PR comment

## 核心规则

1. **review 开始前先有 review ticket。**
   如果父 agent 直接做 review，就复用或新建自己的当前 ticket；如果要派独立 subagent，每个独立推进的 subagent 应有自己的 ticket，或由 wrapper 创建并传入 wrapper-managed session。不要让多个并行 subagent 直接 claim 同一个 ticket。

2. **subagent 必须接受 sts-harness 控制面上下文。**
   父 agent 派 review subagent 时，必须把 `/home/tsshi/sts-harness/AGENTS.md` 和本原则路径传给 subagent；如果 subagent 有文件读取能力，启动后先读 sts-harness 入口和相关原则，再读目标 repo 的本地 `AGENTS.md` / `CLAUDE.md`。不要假设 subagent 自动继承父 agent 的 system prompt、已加载控制面上下文或当前 ticket 状态。

3. **subagent 应用 yolo 模式启动。**
   PR review subagent 的价值在于能快速 checkout、运行测试、写复现脚本和收集证据；父 agent / wrapper 应用 yolo 模式启动它，避免每个实验命令都被交互式确认阻塞。yolo 模式不放宽工作边界：subagent 仍必须先 claim 自己的 review ticket，实验写入限制在该 ticket `workspace/` 和 notes/artifacts 内，不能污染主 checkout 或无关路径。

4. **先搜历史 ticket，再读 PR。**
   用 repo 名、PR id、branch、关键文件、模块名、错误码、策略名、功能关键词搜索历史 ticket。找到 ACTIVE 别人持有的 ticket 只读参考，不默认 claim；ARCHIVED ticket 可直接作为背景读取。

5. **实验环境放在 ticket `workspace/`。**
   需要 checkout PR 分支、跑测试、写 scratch patch 或复现脚本时，在当前 review ticket 的 `workspace/` 下创建 linked worktree。只写 ticket 内 scratch 文件不需要 git worktree，但不能写进主 checkout。

6. **已知问题不能替代独立 review。**
   父 agent / wrapper 可以把已经发现的问题传给 subagent，但这些问题只能作为背景和后续复核项，不能成为唯一 review 目标。subagent 必须先按自己的 focus 做一轮独立问题发现：建立 changed-surface inventory、选择高风险路径、搜索跨文件影响，并记录未覆盖范围；然后再回到已知问题，确认是否复现、是否还有变体、是否存在同类遗漏。父 agent 不应要求 subagent “只看这个 finding 是否成立”，除非任务明确是单点复核且不声称完成 PR review。

7. **先做 compact review inventory，再展开细节。**
   review 的慢点通常不是 shell 命令，而是把大块 `git diff` / `rg` 输出塞进模型上下文。先用 `git diff --stat`、`git diff --name-status`、`git diff --unified=0`、`rg -l` 或 `rg --count-matches` 建立紧凑 inventory；只对候选 finding、关键文件和命中项展开带上下文的 diff / search 输出。不要默认用大 `--unified` diff 或全仓 `rg -n` dump 作为第一轮输入。

8. **review 过程结论必须持久化。**
   关键命令、测试结果、重要推理、被排除的 false positive、候选 finding 和最终 finding 都要写入 ticket log、notes，或写成文件后用 `add-item` 登记。不要只把结论留在 subagent 的最终消息里。

9. **review ticket 必须维护可判定的收口状态。**
   `aticket-cli` 的 goal、short-context 和 item 是通用字段；不要假设存在未实现的 review 专属 CLI schema。每个独立 review child 应在 short-context 中用稳定、可检索的标签写清：`Review status: IN_PROGRESS|READY_TO_CLOSE|CLOSED_BLOCKED`、`Outcome: PENDING|CLEAN|FINDINGS|INCOMPLETE`、`Parent ticket:`、`Evidence:`、`Fix owner:`，以及预期完成时间或下一次 check-in。`CLOSED_BLOCKED` 必须同时写明具体 blocker、owner 和解除条件，不能只写“waiting”。这些标签既让人能快速判断，也为将来的只读检查保留可靠输入。

10. **发布物和 ticket 双向链接。**
   PR comment、PR description 更新、文档页面 review note 等外部发布物必须标注 ticket；发布后把外部 URL 用 `add-item` 反向登记到 ticket。

11. **review child ticket 产出 review artifact 后必须执行收口 epilogue。**
   独立 review / subagent review ticket 的目标是产出 review 证据和结论，而不是继续拥有被审 PR 的修复动作。`notes/review-findings.md`、review dump、PR comment 或父 ticket summary 已经落地后，child 必须：(a) 写入 `READY_TO_CLOSE`、outcome、evidence、fix owner 和 residual risk；(b) 向 parent ticket 发送简洁的 closure message；(c) 清理已安全清理的 review worktree；(d) `archive`。如果 finding 需要修复，由 parent implementation ticket、作者、human，或新 follow-up ticket 接手；不要把已完成的 review child ticket `release` 回 BACKLOG 只为等待 parent 处理 finding。

   只有明确的 lifecycle guard（例如仍在运行的 job，或 archive 工具要求的 human confirmation）可以阻止 archive。唯一 review 证据必须保留并登记，但它本身不是阻塞理由；只有具体的 size/tool guard 要求 human action 时才使用 `CLOSED_BLOCKED`，并记录 blocker、next owner 和 first action。“等待作者修复”“等 parent 看结果”不是阻塞理由。

## 推荐工作流

### 1. 创建或继承 review ticket

普通父 agent 自己 review：

```bash
TICKET_DIR=$(aticket-cli ticket new \
  --topic "review-<repo>-pr-<id>" \
  --goal "Review <repo> PR <id> and publish actionable findings" \
  --short-context "Review status: IN_PROGRESS. Outcome: PENDING. Parent ticket: none. Evidence: pending. Fix owner: pending. Next check-in: <time>. Start by searching historical tickets for repo/module/branch context, then inspect PR diff.")
```

父 agent 派独立 subagent：

```bash
SUB_REVIEW_DIR=$(aticket-cli ticket new \
  --topic "review-<repo>-pr-<id>-<focus>" \
  --goal "Review <repo> PR <id> for <focus>" \
  --short-context "Review status: IN_PROGRESS. Outcome: PENDING. Parent ticket: $TICKET_DIR. Evidence: pending. Fix owner: pending. Next check-in: <time>. First search historical tickets, then inspect PR diff for <focus>.")
aticket-cli ticket "$SUB_REVIEW_DIR" log "Spawned by source ticket: $TICKET_DIR"
aticket-cli ticket "$TICKET_DIR" add-item "file://$SUB_REVIEW_DIR"
aticket-cli ticket "$SUB_REVIEW_DIR" add-item "file://$TICKET_DIR"
aticket-cli ticket "$SUB_REVIEW_DIR" release
```

父 agent 创建 subagent ticket 后应 release，让真正执行 review 的 subagent claim。subagent 启动后第一步：

```bash
TICKET_DIR="<sub-review-ticket-dir>"
aticket-cli ticket "$TICKET_DIR" claim
```

wrapper-managed reviewer：

```text
Session: inherited (reviewer-wrapper-managed)
```

这种模式下 reviewer 本体不直接 `ticket new` / `ticket log`；wrapper 必须把 reviewer dump、实验输出和最终 comment 落到父 ticket 或 wrapper-created ticket。

### 2. 传入 sts-harness 控制面上下文

父 agent 给 subagent 的任务输入至少包含：

```text
Read /home/tsshi/sts-harness/AGENTS.md first.
Then read /home/tsshi/sts-harness/principles/pr-review-subagents-must-use-aticket.md.
Use ticket: <sub-review-ticket-dir>
Review target: <repo> PR <id> / <branch> / <commit>
Focus: <focus>
Relevant historical tickets already found: <ticket paths or none>
Known findings to verify after independent pass: <none or finding ids/summaries>
Review process: first do independent issue discovery with compact review inventory; expand only candidate finding areas. After that, verify known findings and search for nearby variants.
Launch mode: yolo; experiments must stay inside the claimed ticket workspace and notes/artifacts.
```

如果 subagent 的运行环境不能读本地文件，父 agent 必须把 sts-harness 的必要规则摘要内联到 subagent prompt：ticket ownership、历史 ticket search、ticket `workspace/` 实验隔离、独立发现优先、持久化 findings、发布物回链。否则这个 subagent 不能被当作符合 sts-harness 的 reviewer。

已知 finding 的传递要保持克制：给足文件、症状、复现线索即可，不要把父 agent 的完整推理链写成 subagent 的结论。需要多 subagent 评审时，优先按风险面或代码区域分配 focus；不要把所有 subagent 都锚定到同一条已知 finding 上反复确认。

sts-harness 控制面规则和目标 repo 本地规则都要加载，职责不同：

- **sts-harness**：定义 agent 怎么工作、怎么用 ticket、怎么隔离 workspace、怎么持久化 review 证据。
- **目标 repo AGENTS / CLAUDE**：定义该 repo 的代码规范、测试命令、领域约束和发布流程。

### 3. 搜索历史背景

```bash
ROOT="${AGENT_TICKETS_ROOT:-/home/tsshi/agent-tickets}"
rg -n "<repo>|PR-<id>|<branch>|<module>|<keyword>" "$ROOT"/tickets/*/TICKET.md 2>/dev/null
aticket-cli tickets search --query "<repo> <module> <keyword> <branch>" --limit 20
```

记录搜索口径和有用结果：

```bash
aticket-cli ticket "$TICKET_DIR" log \
  "Historical ticket search: query='<repo> <module> <keyword>'; relevant: <ticket-a>, <ticket-b>; no active same-review ticket found."
aticket-cli ticket "$TICKET_DIR" add-item "file://<relevant-ticket-dir>"
```

只扫 `$ROOT/tickets/*/TICKET.md` 或用 `aticket-cli tickets search`。不要递归扫整个 tickets 树，否则会误命中历史 ticket 的 `workspace/` checkout、fixture 和临时输出。

### 4. 建立实验 worktree

```bash
REPO_ROOT=/home/tsshi/<repo>
REVIEW_SLUG="<focus-or-ticket-slug>"
WORKTREE_DIR="$TICKET_DIR/workspace/<repo>-review-pr-<id>-$REVIEW_SLUG"

git -C "$REPO_ROOT" fetch origin
git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" -b <agent>/review-pr-<id>-$REVIEW_SLUG origin/master
cd "$WORKTREE_DIR"
git fetch origin <verified-pr-ref>:pr-<id>-$REVIEW_SLUG
git checkout pr-<id>-$REVIEW_SLUG

git rev-parse --git-dir
git rev-parse --git-common-dir
pwd
git branch --show-current
```

`REVIEW_SLUG` 必须对每个并行 review subagent 唯一，优先使用 focus 名或 ticket slug。不要让多个 subagent 为同一个 PR 复用相同 local branch 名；Git 会拒绝同一 branch 被多个 worktree checkout。

`<verified-pr-ref>` 必须来自实际 forge / CLI / remote 信息。若本地已有 PR source branch，按实际 PR branch checkout；不要猜 forge-specific refspec，首次使用前先查对应 CLI / remote 的真实形态。

### 5. 先生成 compact review inventory

先用低输出命令确定 review 面，再决定哪些文件需要展开读取：

```bash
git diff --stat <base>...<head>
git diff --name-status <base>...<head>
git diff --unified=0 <base>...<head> -- <focus-files>
rg -l "<broad-risk-pattern>" .
rg --count-matches "<broad-risk-pattern>" .
```

inventory 应记录到 ticket log 或 `notes/review-findings.md`，至少包含：

- changed files / diffstat
- 高风险文件或目录
- broad search 的匹配文件和匹配数量
- 需要展开 full diff / file read 的候选文件
- 暂不展开的文件及理由
- 独立发现阶段完成后，再复核的已知 finding 列表

展开规则：

- 只有候选 finding、API/contract 变更、索引/路由入口、迁移逻辑、测试覆盖缺口等需要带上下文 diff。
- broad internal-reference、stale-link、关键词泄漏类检查先看 `rg -l` / count；只有命中文件再跑 `rg -n`，必要时限制到路径或 pattern。
- 如果需要保留大 raw output，把它放进 ticket `artifacts/`，再把精简摘要喂给模型；不要让全量 raw output 成为默认 review 输入。
- 同一个大 diff 不要按不同分组重复 dump。已经分类为低风险的文件，只在 focus 改变或出现新证据时重新展开。

### 6. 持久化 review 证据

短记录用 log：

```bash
aticket-cli ticket "$TICKET_DIR" log \
  "Review experiment: ran <command>; result=<pass/fail>; key output in artifacts/<file>."
```

较长分析写 notes，再用 `add-item` 登记入口：

```bash
mkdir -p "$TICKET_DIR/notes"
$EDITOR "$TICKET_DIR/notes/review-findings.md"
aticket-cli ticket "$TICKET_DIR" add-item \
  "file://$TICKET_DIR/notes/review-findings.md"
```

`notes/review-findings.md` 应至少覆盖：

- PR / repo / branch / commit
- 历史 ticket 搜索关键词和相关结果
- 已检查的 diff 面和未检查的面
- 执行过的命令、测试和关键输出位置
- 独立发现的新 findings：severity、文件行号、证据、建议修法
- 已知 findings 的复核结果：confirmed / rejected / related variant found，并写明证据
- 被排除的候选问题和排除理由
- 如果需要后续工作，应该留在本 ticket 还是新建 / fork ticket

### 7. 发布 review 并回链

PR comment 或 review summary 中必须包含 ticket 引用：

```text
Ticket: file:///home/tsshi/agent-tickets/tickets/<ticket-name>
```

发布后回写：

```bash
aticket-cli ticket "$TICKET_DIR" add-item \
  "https://<forge>/<repo>/pull-requests/<id>"
aticket-cli ticket "$TICKET_DIR" context \
  "Review published; next owner: parent ticket / PR author. Key evidence in notes/review-findings.md."
```

### 8. 收口 review child ticket

review child ticket 在 review artifact 已产出后应归档。归档前写清：

- final result：无 findings、已发布 findings、或未发布但已交给 parent/human
- evidence entry：`notes/review-findings.md`、review dump、PR comment URL 或父 ticket summary 的 `add-item`
- next owner：parent ticket / PR author / human / follow-up ticket；不要写成 review child ticket 自己继续等
- residual risk：未覆盖的 diff 面、未跑的测试、需要 parent 特别处理的 finding

先把结论投递给仍 ACTIVE 的 parent；这样 child archive 后，parent 仍有可见的 fan-in 入口：

```bash
aticket-cli message send --ticket "$PARENT_TICKET_DIR" \
  "Review closure: status=READY_TO_CLOSE outcome=<CLEAN|FINDINGS|INCOMPLETE>; evidence=file://$TICKET_DIR/notes/review-findings.md; fix owner=<parent|author|human|follow-up>; residual risk=<...>."
```

parent holder 收到 message 后，必须把 child 的 outcome、evidence 和 fix owner 汇总到 parent 的 short-context 或 log，并标记 message 已读。child 不应为了等待这个汇总而继续占有 ACTIVE lease；parent 已 archived 或不存在时，在 child 的 final context 里明确写出替代 owner 和为什么无法回传。

```bash
aticket-cli ticket "$TICKET_DIR" context \
  "Review status: READY_TO_CLOSE. Outcome: <CLEAN|FINDINGS|INCOMPLETE>. Parent ticket: $PARENT_TICKET_DIR. Evidence: file://$TICKET_DIR/notes/review-findings.md. Fix owner: <parent|author|human|follow-up>. Final result: review artifact produced. Residual risk: <...>. Workspace state: <...>."
aticket-cli ticket "$TICKET_DIR" archive
```

如果 review 过程中发现一个独立后续工作，先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 和 [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) 新建 / fork follow-up，并双向链接；然后归档 review child ticket。不要让 review child ticket 变成“等待修复”的 backlog 票。

### 9. review ticket 的 stale lifecycle signal

`ACTIVE` lease 只表示曾经有人认领，不能证明 review 仍在推进。出现以下任一情况时，parent / wrapper / 后续协调者应把它当作 lifecycle-debt signal：

- child 已有 review artifact 或明确 outcome，却仍是 ACTIVE；
- 超过声明的完成时间或 check-in 时间仍无 ticket log / context 更新；若未声明时间，默认以 24 小时无更新作为提示阈值；
- child 的 short-context 只剩“waiting for parent/author/review”而没有具体 first action。

signal 只触发交接检查，**不**授权自动 archive、force claim 或根据时间戳断定 owner 已失活。先给该 ticket 发送 message，parent 检查自己的 fan-in 状态；仍无响应时由 human 决定接管、开新的 review ticket，还是保留原 lease。确认 review 已完成时，应由当前 holder 完成上述 epilogue；确认未完成但当前 holder 不再推进时，写清 first action 后 release 为 BACKLOG。

## 多 subagent 模式

如果父 agent 同时派多个 subagent：

- **不同 focus 用不同 ticket**：例如 `api-contract`、`migration-risk`、`test-coverage`。每个 ticket 有自己的 lease 和 workspace。
- **避免重复锚定已知问题**：已知 finding 可以分配给一个 subagent 做复核，其他 subagent 应按独立风险面寻找新问题。确实需要多人复核同一 finding 时，父 ticket 必须说明原因，例如高风险结论需要独立验证。
- **父 ticket 做汇总和 fan-in**：父 ticket 记录 subagent ticket 链接、合并后的最终 finding 列表和发布状态，并区分 new findings、known-finding confirmations 和 no-new-finding evidence。对每个 child，parent 还必须能指出 closure message 是否收到、outcome/evidence/fix owner 是什么，以及 child 已 archive 还是有具体 `CLOSED_BLOCKED` 理由；不要把“child 仍 ACTIVE”当作汇总状态。
- **不要共享实验 worktree**：并行 subagent 不能写同一个 checkout；需要同一 PR 代码时，各自在自己的 ticket `workspace/` 下建 worktree。
- **需要补充给别人的 active ticket 时用 message**：不接管对方 ticket，只用 `aticket-cli message send --ticket "$TARGET" ...` 投递短消息或资源链接。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 每次工作必须归属到一个 ticket
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录
- [code-work-preflight](code-work-preflight.md) — ticket owns `workspace/`，repo 写操作仍必须使用并验证 linked git worktree
- [write-ops-must-verify-linked-worktree-before-first-edit](write-ops-must-verify-linked-worktree-before-first-edit.md) — repo 写操作前必须验证实际写路径已经是 linked worktree
- [published-content-must-identify-ticket](published-content-must-identify-ticket.md) — 外部发布物必须标注对应 ticket，并反向登记到 ticket
