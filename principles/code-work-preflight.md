---
description: "代码工作 preflight：repo 写操作、提交、推送和 PR 必须在 ticket-owned worktree/topic branch 中进行，禁止直推远端 master"
triggers:
  - "worktree"
  - "环境约定"
  - "代码路径"
  - "/home/tsshi"
  - "master 路径"
  - "checkout"
  - "merge 后 pull"
  - "多 agent"
  - "并行开发"
  - "分支隔离"
  - "代码工作"
  - "repo 写操作"
  - "git add"
  - "git commit"
  - "git push"
  - "提交"
  - "推送"
  - "push master"
  - "origin/master"
  - "create PR"
  - "发布 PR"
  - "new repo bootstrap"
  - "first branch"
  - "default branch"
  - "unborn master"
  - "broken root checkout"
  - "initial commit"
  - "dirty worktree"
  - "partial commit"
  - "worker handoff"
  - "repo-wide formatter"
  - "formatter spillover"
  - "bulk rewrite"
  - "codemod"
---

# 代码工作 Preflight

## 边界

只读调查可以从主 checkout 开始；一旦准备编辑 repo 文件、运行会改写 repo 的 formatter/generator、`git add`、`git commit`、`git push` 或创建 PR，就进入代码工作 preflight。

这条原则管目标 repo 的写入和发布。当前 ticket 目录下的 scratch 脚本、临时数据、日志和 artifacts 可以直接写在 ticket `workspace/` / `notes/` / `artifacts/` 下，但不能误写进主 checkout，也不能冒充已经进入 PR 的 repo 内容。

## 三项检查

1. **Ticket**：当前工作已归属并 claim 一个 ticket，且已运行 `aticket-cli ticket "$TICKET_DIR" brief`
2. **Worktree**：目标 repo 从 `/home/tsshi/<repo>` 这类日常 `master` checkout 创建或复用当前 ticket `workspace/` 下的 linked worktree；第一次编辑前按 [write-ops-must-verify-linked-worktree-before-first-edit](write-ops-must-verify-linked-worktree-before-first-edit.md) 验证 `git-dir` / `common-dir` / `pwd` / branch
3. **Publish**：有 remote 的 repo 只 push topic branch 并通过 PR 合入 `master`；创建 PR 或其他外部发布物前，按 [published-content-must-identify-ticket](published-content-must-identify-ticket.md) 在正文里标注当前 ticket

human 明确要求直推远端 `master` 时才允许例外；执行前必须在对话中复述目标 repo、remote、source ref、target ref 和 commit 范围，并把例外记录到 ticket。

新建公开 repo 前先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 判断是否需要新 ticket / fork ticket。新 repo 的首个可写分支默认直接使用 `master`；如果确实必须先用 bootstrap/topic branch，必须在同一 session 内补齐真实 `master`、`origin/master`、default branch 和健康 root checkout。bootstrap session 结束前至少确认 `master` / `origin/master` 存在、`master...origin/master` 为 `0 0`、root status 干净且 `git ls-files` 非零；不要把这一步降级成 optional follow-up。

## 本地路径约定

1. **代码 checkout 通常放在 `/home/tsshi/<repo>`。**
   例如 `sts-harness` 的日常根 checkout 是 `/home/tsshi/sts-harness`。除非用户或现有 ticket 明确说明其他位置，查找、同步、创建 worktree 时优先以 `/home/tsshi/<repo>` 作为 repo root。

2. **`/home/tsshi/<repo>` 日常保持在 `master` 路径。**
   根 checkout 是只读检查、fetch/pull、查看基线和创建 linked worktree 的入口，不承载 feature 开发改动。不要在根 checkout 上直接做会进入 PR 的编辑。

3. **开发写操作在当前 ticket 的 `workspace/` worktree 下进行。**
   repo 写操作仍必须先 claim ticket，再从 `/home/tsshi/<repo>` 创建或复用 linked worktree。

4. **准备合并和确认合入后，都注意同步 `/home/tsshi/<repo>` 的 `master`。**
   准备合并前，先确认根 checkout 能代表最新主线；PR 合并后，或准备基于最新主线创建下一条 worktree 时，也要回到根 checkout 更新主线视角。如果根 checkout 有非预期 dirty 状态，不要强行 pull；先按本文件的 dirty state 规则说明或隔离现状。

## Dirty state 和 formatter

linked worktree 只能保证写在正确位置，不能保证当前 dirty set 仍然匹配本 phase / planned commit。每次 phase 边界、worker / subagent 返回、接手旧 worktree、或外部反馈修复后准备继续时，如果 `git status --short` 比当前意图更宽，必须先解释或隔离这些改动。

继续写或 commit 前，至少能说清：

1. 每个 dirty 文件为什么在这里。
2. 当前 planned commit / planned next phase 覆盖完整 dirty set。

只想 partial commit 其中几个文件时，不要把更宽的未提交状态留在同一 worktree 里继续推进；先把当前 dirty worktree 闭环成单一 scope，或切到新的干净 worktree。

repo-root formatter、`cargo fmt --all`、bulk rewrite、codemod 这类命令会主动扩宽 dirty set。只有当前任务明确接受 formatter 实际命中的文件进入交付 scope，才运行；运行后遵守 **run -> commit-or-isolate**：要么把 widened files 一起纳入当前 commit 并解释 scope，要么立刻隔离/收口，不要留下悬空 formatter 改动。

## 命令骨架

```bash
REPO_ROOT=/home/tsshi/<repo>
TOPIC=<topic>
WORKTREE_DIR="$TICKET_DIR/workspace/<repo>-$TOPIC"

git -C "$REPO_ROOT" fetch origin
git -C "$REPO_ROOT" worktree add "$WORKTREE_DIR" -b <agent>/<topic> origin/master
cd "$WORKTREE_DIR"

git rev-parse --git-dir
git rev-parse --git-common-dir
pwd
git branch --show-current

git add ...
git commit -m "..."
git push -u origin <agent>/<topic>
```

`git push` 目标必须是当前 topic branch。不要执行 `git push origin master`、`git push origin HEAD:master`、`git push origin HEAD:refs/heads/master`，也不要先在本地 merge 到 `master` 后再直推远端主线。

Codex 特别注意：shell 命令可以逐次指定 `workdir`，但 `apply_patch` 的 repo-relative 路径按 session cwd 解析。持续在 worktree cwd 中工作是首选；当 session cwd 无法实时对齐时，patch path 必须写成 `$WORKTREE_DIR/...` 绝对路径。

## 发布和收尾

创建 PR 前再次确认当前分支不是 `master`，要发布的提交范围是 `origin/master..HEAD`，PR description 按 [published-content-must-identify-ticket](published-content-must-identify-ticket.md) 标注当前 ticket。PR 合并后，同步 `/home/tsshi/<repo>` 的 `master` 根 checkout；如果要清理 worktree，用 `git -C "$REPO_ROOT" worktree remove "$WORKTREE_DIR"`。

需要把 worktree 更新到最新主线时：

```bash
git fetch origin
git rebase origin/master
```

如果你在非交互环境（无 TTY）里 resolve 冲突后 `git rebase --continue` 卡在编辑器（常见是 vim），可以用：

```bash
GIT_EDITOR=true git rebase --continue
```

## 注意事项

- 同一分支不能同时被多个 worktree checkout，git 会拒绝
- worktree 中的 submodule 需要单独初始化：`git submodule update --init`
- 完成工作后务必清理 ticket `workspace/` 下的 worktree，避免残留占用磁盘
- 如果 worktree 被意外删除（未用 `git worktree remove`），用 `git worktree prune` 清理记录
- **创建 worktree 前必须 `git fetch origin`**，基于 `origin/master` 而非本地 `master`，否则可能基于过时代码开发导致 PR 冲突
- **即使是「先探索一下」也应该在 worktree 里做**，因为探索很容易变成正式开发，事后再搬改动到 worktree 步骤繁琐且容易遗漏文件

## 相关原则

- [write-ops-must-verify-linked-worktree-before-first-edit](write-ops-must-verify-linked-worktree-before-first-edit.md) — 第一次编辑前验证实际写路径已经是 linked worktree
- [published-content-must-identify-ticket](published-content-must-identify-ticket.md) — PR description 等外部发布物必须标注当前 ticket
