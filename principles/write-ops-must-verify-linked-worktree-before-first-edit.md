---
description: "正式 repo 写操作前必须先确认写路径根已经是 linked worktree；ticket workspace scratch 写入不需要 git worktree"
triggers:
  - "first edit"
  - "linked worktree"
  - "verify cwd"
  - "cwd drift"
  - "apply_patch"
  - "main worktree"
---

# Repo 写操作前必须先验证写路径根已在 linked worktree

## 背景

`code-work-preflight.md` 已经规定“任何 repo 写操作必须在独立 worktree 中进行”，且 worktree 应放在当前 aticket 的 `workspace/` 下。但真实事故表明，这条规则如果只停留在计划、ticket、或作者记忆里，仍然会失效：

- agent 线程常常从 repo root 启动；Codex 的 `AGENTS.md` 发现链和 hooks 都与 session cwd 有关
- agent 可能先声明“会去某个 worktree”，但第一次 `apply_patch` 发生时其实还没切过去
- shell 命令的 `workdir` 校验不等于 `apply_patch` 的写路径校验；`apply_patch` 的相对路径会按 Codex session cwd 解析
- 同一条 rollout 也可能先在 worktree 写，后续回合又漂回 root

因此，**“已经计划使用 worktree”不是有效条件；只有“第一次 repo 写之前，实际写路径根已被验证为 linked worktree”才算满足规则。**

## 适用边界

本原则约束的是**目标 repo 内的文件写入**，例如代码、脚本、文档、原则、索引、测试 fixture 等会进入 git status / commit / PR 的内容。

不要求 git worktree 的写入：

- 当前 ticket 目录下的 `notes/`、`artifacts/`、`workspace/` scratch 文件
- 为验证临时生成的脚本、数据、日志、图片、缓存
- 不属于目标 repo 的外部工具输出

这些非 repo 写入仍必须归属当前 ticket：默认写在当前 ticket 目录下，必要时用 `aticket-cli ticket "$TICKET_DIR" log` / `aticket-cli ticket "$TICKET_DIR" add-item` 记录。不要因为不需要 git worktree，就把临时文件写进主 checkout 或无法追溯的位置。

## 规则

1. **任何正式 repo 写操作前，先验证实际写路径根。**
   正式 repo 写操作包括代码、脚本、文档、原则、索引、session 之外的 repo 文件编辑；不要把“只是文档改动”当成例外。
2. **如果当前目录仍是 main worktree，先停下，创建或切入当前 ticket `workspace/` 下的 linked worktree，再开始编辑。**
3. **如果任务后续还会继续多轮推进，也不要先在 root 写、之后再搬。**
4. **当 rollout / wrapper / 子工具 会跨回合或跨 cwd 运行时，每次重新进入写阶段都应重新确认 cwd，没有“只验一次就永久安全”这回事。**
5. **Codex `apply_patch` 不能只靠 shell `workdir` 证明安全。**
   - 最佳做法：启动 / resume / handoff 后让 Codex session cwd 本身就在当前 ticket worktree，然后 `apply_patch` 才可使用 repo-relative 路径。
   - 如果当前 session cwd 仍是主 checkout、且本轮无法把 session cwd 对齐到 worktree，`apply_patch` 必须使用当前 ticket worktree 下的绝对路径。
   - 禁止在主 checkout session cwd 下用 repo-relative `apply_patch`，再靠事后复制 / 清理补救。

## 最小检查

在目标仓库的候选 worktree 里执行：

```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
pwd
git branch --show-current
```

判定方法：

- `--git-dir` 与 `--git-common-dir` 不同，通常表示当前在 linked worktree
- `pwd` 应落在当前 ticket 的 worktree 路径下，例如 `$TICKET_DIR/workspace/<repo>-<topic>`
- 当前分支应是 topic branch，而不是 `master`

### Codex `apply_patch` 专项判定

当 `apply_patch` 目标是 repo 文件时，它是 repo 写操作，但它不像 shell command 那样有每次调用的 `workdir`。因此，检查 shell command 的 `workdir` 只能证明那个 shell command 安全，不能证明下一次 `apply_patch` 安全。

使用 `apply_patch` 前必须满足二选一：

1. **session cwd 已对齐到 worktree**：`pwd` / `git rev-parse --show-toplevel` 都指向当前 ticket worktree，此时可以用 repo-relative patch 路径。
2. **patch path 自带绝对 worktree 根**：patch 文件名写成 `$TICKET_DIR/workspace/<repo>-<topic>/...` 下的绝对路径，此时即使 session cwd 仍是主 checkout，也不会写错仓库。

不满足任一条件时，先不要 patch；切换 / resume 到 worktree，或改用绝对路径 patch。

编辑后还要同时检查目标 worktree 和主 checkout：

```bash
git -C "$WORKTREE_DIR" status --short
git -C "$REPO_ROOT" status --short
git -C "$REPO_ROOT" ls-files -o --directory --exclude-standard
```

最后一条用于发现 Git status 不显示的空 untracked 目录。

若检查不通过：

先判断是“还没建 worktree”，还是“正确 worktree 其实已经存在，但 cwd 漂回了 repo root”。

### 情况 A：worktree 已存在，只是要切回去

典型症状：

- 你知道本轮 topic / branch 已经存在
- 之前某个回合已经在 linked worktree 中成功编辑过
- `git worktree add ... -b ...` 很可能会因为 branch/worktree 已存在而失败

先找回现有 worktree，再 `cd` 回去：

```bash
git worktree list
cd "$TICKET_DIR/workspace/<repo>-<topic>"
```

### 情况 B：还没创建 worktree，才执行创建

确认不存在可复用 worktree 后，再执行：

```bash
git fetch origin
WORKTREE_DIR="$TICKET_DIR/workspace/<repo>-<topic>"
git worktree add "$WORKTREE_DIR" -b <agent>/<topic> origin/master
cd "$WORKTREE_DIR"
```

核心点：

- “创建或切入 linked worktree”是两个分支，不是永远重新 `git worktree add`
- 对 `cwd drift` 场景，重进现有 worktree 必须是 retry-safe 的；否则恢复步骤本身又会失败

## 反模式

- 在 session 里写了目标 worktree，就直接开始 `apply_patch`
- 在主 checkout session cwd 下执行 repo-relative `apply_patch`
- 验证了 shell command 的 `workdir`，就认为 `apply_patch` 也会写到同一个目录
- 把 ticket workspace 下的 scratch 脚本误判为 repo 写操作，强行先建 git worktree
- 反过来把会进入 PR 的文档文件当成 scratch，写到 ticket workspace 后忘记纳入 repo worktree
- 先在 repo root 改文档，等用户要求 PR 时再补建 worktree
- 把 worktree 建在 repo-local `.claude/worktrees/`，导致 ticket owner 看不到当前实际工作面
- 同一条 rollout 早期已经在 worktree 成功写过，就默认后续回合不会漂回 root
- 只给某几个 wrapper 加 guard，却让普通编辑路径继续裸奔

## 与 `code-work-preflight.md` 的关系

- `code-work-preflight.md` 说明的是“所有 repo 写操作必须在独立 worktree 中进行”的总体协作规范
- 本文补的是执行面约束：**如何在第一次编辑前把这条规范真正落地**

两者要同时满足。只读过规范、不做运行时验证，等价于没有 guard。
