---
description: "PR review subagent 必须接受 sts-harness 控制面上下文，并把 review 归属到 aticket：先搜历史 ticket，再用 ticket workspace 做实验，并把结论、证据和发布物双向链接"
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
- wrapper 自动运行 reviewer 并准备发布 GitHub 或其他 forge review 结果
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

6. **review 过程结论必须持久化。**
   关键命令、测试结果、重要推理、被排除的 false positive、候选 finding 和最终 finding 都要写入 ticket log、notes，或写成文件后用 `add-item` 登记。不要只把结论留在 subagent 的最终消息里。

7. **发布物和 ticket 双向链接。**
   PR comment、PR description 更新、review note 等外部发布物必须标注 ticket；发布后把外部 URL 用 `add-item` 反向登记到 ticket。

8. **review child ticket 产出 review artifact 后应收口归档。**
   独立 review / subagent review ticket 的目标是产出 review 证据和结论，而不是继续拥有被审 PR 的修复动作。`notes/review-findings.md`、review dump、PR comment 或父 ticket summary 已经落地后，review child ticket 应写清 final result 并 `archive`。如果 finding 需要修复，由 parent implementation ticket、作者、human，或新 follow-up ticket 接手；不要把已完成的 review child ticket `release` 回 BACKLOG 只为等待 parent 处理 finding。

## 推荐工作流

### 1. 创建或继承 review ticket

普通父 agent 自己 review：

```bash
TICKET_DIR=$(aticket-cli ticket new \
  --topic "review-<repo>-pr-<id>" \
  --goal "Review <repo> PR <id> and publish actionable findings" \
  --short-context "Start by searching historical tickets for repo/module/branch context, then inspect PR diff.")
```

父 agent 派独立 subagent：

```bash
SUB_REVIEW_DIR=$(aticket-cli ticket new \
  --topic "review-<repo>-pr-<id>-<focus>" \
  --goal "Review <repo> PR <id> for <focus>" \
  --short-context "Spawned from $TICKET_DIR; first search historical tickets, then inspect PR diff for <focus>.")
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
Launch mode: yolo; experiments must stay inside the claimed ticket workspace and notes/artifacts.
```

如果 subagent 的运行环境不能读本地文件，父 agent 必须把 sts-harness 的必要规则摘要内联到 subagent prompt：ticket ownership、历史 ticket search、ticket `workspace/` 实验隔离、持久化 findings、发布物回链。否则这个 subagent 不能被当作符合 sts-harness 的 reviewer。

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

`<verified-pr-ref>` 必须来自实际 forge / CLI / remote 信息。如果本地已有 PR source branch，按实际 PR branch checkout；不要猜 forge-specific refspec，首次使用前先查对应 CLI / remote 的真实形态。

### 5. 持久化 review 证据

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
- 最终 findings：severity、文件行号、证据、建议修法
- 被排除的候选问题和排除理由
- 如果需要后续工作，应该留在本 ticket 还是新建 / fork ticket

### 6. 发布 review 并回链

PR comment 或 review summary 中必须包含 ticket 引用：

```text
Ticket: file:///home/tsshi/agent-tickets/tickets/<ticket-name>
```

发布后回写：

```bash
aticket-cli ticket "$TICKET_DIR" add-item \
  "https://github.com/<owner>/<repo>/pull/<id>"
aticket-cli ticket "$TICKET_DIR" context \
  "Review published; next owner: parent ticket / PR author. Key evidence in notes/review-findings.md."
```

### 7. 收口 review child ticket

review child ticket 在 review artifact 已产出后应归档。归档前写清：

- final result：无 findings、已发布 findings、或未发布但已交给 parent/human
- evidence entry：`notes/review-findings.md`、review dump、PR comment URL 或父 ticket summary 的 `add-item`
- next owner：parent ticket / PR author / human / follow-up ticket；不要写成 review child ticket 自己继续等
- residual risk：未覆盖的 diff 面、未跑的测试、需要 parent 特别处理的 finding

```bash
aticket-cli ticket "$TICKET_DIR" context \
  "Final result: review artifact produced; next owner: parent ticket / PR author. Residual risk: <...>. Workspace state: <...>."
aticket-cli ticket "$TICKET_DIR" archive
```

如果 review 过程中发现一个独立后续工作，先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 和 [deferred-work-must-become-ticket](deferred-work-must-become-ticket.md) 新建 / fork follow-up，并双向链接；然后归档 review child ticket。不要让 review child ticket 变成“等待修复”的 backlog 票。

## 多 subagent 模式

如果父 agent 同时派多个 subagent：

- **不同 focus 用不同 ticket**：例如 `api-contract`、`migration-risk`、`test-coverage`。每个 ticket 有自己的 lease 和 workspace。
- **父 ticket 做汇总**：父 ticket 记录 subagent ticket 链接、合并后的最终 finding 列表和发布状态。
- **不要共享实验 worktree**：并行 subagent 不能写同一个 checkout；需要同一 PR 代码时，各自在自己的 ticket `workspace/` 下建 worktree。
- **需要补充给别人的 active ticket 时用 message**：不接管对方 ticket，只用 `aticket-cli message send --ticket "$TARGET" ...` 投递短消息或资源链接。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 每次工作必须归属到一个 ticket
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录
- [code-work-preflight](code-work-preflight.md) — ticket owns `workspace/`，repo 写操作仍必须使用并验证 linked git worktree
- [write-ops-must-verify-linked-worktree-before-first-edit](write-ops-must-verify-linked-worktree-before-first-edit.md) — repo 写操作前必须验证实际写路径已经是 linked worktree
- [published-content-must-identify-ticket](published-content-must-identify-ticket.md) — 外部发布物必须标注对应 ticket，并反向登记到 ticket
