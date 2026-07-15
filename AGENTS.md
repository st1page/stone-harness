# Agent Notes

每个 agent 在开始任何任务前，**必须先通读本文件**（Claude Code 中本文件已通过 `CLAUDE.md` 的 `@AGENTS.md` 内联到 system prompt，等价于已读）。

## 仓库结构

```
sts-harness/
├── principles/                 # 控制面知识（原则与 ticket 生命周期文档）
│   ├── AGENTS.md               # principles/ 统一索引
│   ├── work-must-belong-to-a-ticket.md
│   ├── code-work-preflight.md
│   └── ...
└── AGENTS.md                   # 本文件（入口）
```

## 知识入口

本仓库只保留**控制面（principles/）**知识：描述「agent 怎么做事」的协作规范、工具链和工作流。详细索引见 **`principles/AGENTS.md`**。

不在本仓库存放领域工具知识；具体系统/工具的 runbook 应放在对应项目或独立工具文档仓库。

## 依赖：aticket-cli

**来源 / 文档**：[`st1page/aticket-cli`](https://github.com/st1page/aticket-cli)

**用途**：管理工作生命周期（ticket 创建、claim/release、fork、archive、状态外部化，以及 ticket `workspace/` 下的 repo worktree 归属）

**P0 / 所有命令任务必看**：
- **环境 skill**：`ticket-workdir`（aticket-cli skill）必须已安装并可用；未安装或版本不匹配时，不要继续命令任务，先让 human 安装 / 更新 aticket-cli skill
- 所有命令任务必须归属到 ticket；无当前 ticket 时，agent 不能继续实质工作，但必须自己先做只读 discover（`aticket-cli tickets search` / 顶层 ticket 扫描），找不到可复用 ticket 就用 `aticket-cli ticket new --topic ... --goal ...` 新建并 claim，再 `brief` 后继续；这不是要求 human 先提供 ticket
- **rename 是物理迁移**：需要更正 ticket topic / 目录名时，只能使用 `aticket-cli ticket <ticket-ref> rename --topic <topic>`；不得用 `mv`、`rename(1)` 或手工 SQLite 编辑。CLI 返回的路径才是 canonical path；旧路径可能是指向它的 symlink alias，不能把 alias 当成另一张 ticket 或让 search/reindex 重复登记。
- **历史路径恢复**：接收 ticket ref 的操作应交给 CLI resolver。路径不存在时，只有请求中包含完整 UUID，或命中 SQLite 中的精确 path history，才允许定位当前 canonical path；不得按 topic、日期或模糊搜索猜路径。rename/recovery 正在进行时遵循 CLI 的 gate / retry 诊断，不要手工清 journal、alias 或锁文件。
- 同一会话的连续追问、解释延伸和同一环境下的参数 sweep 默认复用当前 ACTIVE ticket；只有独立 handoff unit 才能 `new` / `fork`。fork 前先判断能否改 source ticket 的 goal/context/log；普通独立 fork 可用单行 `--boundary-reason` 留下审计依据，source 本身还是短 fork 时 CLI 会在创建 child 前强制要求；“下一题”“继续”“再跑一个参数”不是有效理由
- 有可用 remote 的 repo 代码任务，普通的实现 / 修复 / 修改目标默认交付到 topic branch 已推送且 ticket-attributed PR 已创建；“用户没有另行要求 push / PR”不是 local-only 例外。同一 goal / branch 从实现进入 PR 通常继续当前 ticket，只有独立 PR 线、owner、workspace 或验收才拆票；human 明确要求暂停 / 停止 / 暂时别 push 时不得继续外部发布，记录恢复点后保持 ACTIVE 或 release BACKLOG，只有 human 肯定说明本地产物就是最终交付且以后不再 push / 发 PR、repo 无 remote、变更已丢弃 / supersede 或显式替代交付时才允许无 PR 收口
- 阶段边界先运行 `aticket-cli ticket "$TICKET_DIR" brief`：开始 / 恢复、claim / fork 后、repo 写操作前、外部发布前、最终回复前、release / archive 前
- repo 写操作必须在当前 ticket 的 `workspace/` linked worktree 下进行
- 新目标、新 repo、新 PR、外部页面族、benchmark 环境、source repo 切换、长票、大目录 / 工具链缓存，或 ticket 范围变宽时，必须判断是否拆 ticket / fork ticket
- 有命令输出、决策、产物、外部 URL、等待外部反馈、长任务或其他可恢复状态时，必须写入 ticket
- 发现 deferred / follow-up 时，必须判断是当前 ticket 尾巴还是新 BACKLOG / fork ticket
- 用户意图、约束或关键事实变化，或进入实现 / 执行前，必须 checkpoint
- 最终回复、外部发布或阶段切换前，必须判断当前 ticket 应 archive、release、fork follow-up 还是继续 ACTIVE；收口前必须写清 final result、外部状态、next owner、剩余风险和 workspace 状态
- `--human-confirm-*` / `--confirm-*` 这类绕过保护的确认参数必须得到 human 对该具体异常操作的明确批准；不能从“结束 / 继续 / 可以”等邻近意图推断
- ticket 的 `new` / `fork` / `release` / `archive` 完成后，以陈述句报告 ticket 路径、状态和下一步；下一步已经确定时立即执行。只有在 **操作前** 的 discover 后仍无法判断是否应继续某张旧 ticket 时才询问 human。接管他人 ACTIVE ticket 或使用 `--confirm-*` 等保护绕过参数仍必须取得明确批准

**ticket 相关文档路径（P1 / 按场景加载）**：
- **基础 ticket 归属 / brief / 自主选择旧票或新票**：`principles/work-must-belong-to-a-ticket.md`
- **工作流边界 / 判断是否拆 ticket / fork ticket**：`principles/workstream-boundaries-must-split-ticket.md`
- **状态外部化 / 命令输出 / 决策 / 产物 / checkpoint**：`principles/persistent-state-must-be-externalized.md`
- **最终回复 / 外部发布 / 阶段切换 / 收口 final state**：`principles/ticket-lifecycle-boundary-check.md`
- **deferred / follow-up work 处理细则**：`principles/deferred-work-must-become-ticket.md`
- **长讨论 / 意图变化 / 实现前 checkpoint 细则**：`principles/persistent-state-must-be-externalized.md`

## 控制面知识加载

- **Always-on**：
  - `AGENTS.md`（本文件）；进入任务、续接长 ticket、context 压缩后都要先回到这里
  - **知识加载常驻行为**：不确定名字、缩写、代号或概念指什么时，先 `aticket-cli tickets search --query "<term>"`，搜不到就问用户，不要自行扩散检索或猜；context 压缩 / 恢复后先回到 `AGENTS.md` 和当前 ticket `brief` / `TICKET.md`
  - **Python P0**：直接调用 Python 解释器时默认用 `python3.12`，不要用裸 `python` 或 `python3`；若项目明确要求 `.venv/bin/python`、`uv run`、`poetry run`、`tox`、`nox`、`make test` 等封装入口，则遵循项目契约并在必要时记录原因。
  - **环境默认**：本地代码 checkout 通常在 `/home/tsshi/<repo>`，根 checkout 日常保持 `master`。细则见 `principles/code-work-preflight.md` 和 `principles/verify-cli-args-before-invocation.md`
- **按场景加载**：
  - **代码工作必看**：`principles/code-work-preflight.md`、`principles/write-ops-must-verify-linked-worktree-before-first-edit.md`
  - **文档写作 / 发布必看**：改已有文档、发布到 GitHub、PR description/comment、文档页面或其他外部内容面前读 `principles/published-content-must-identify-ticket.md`
  - **验证 / 实验必看**：跑 experiment / benchmark / smoke 时读 `principles/experiment-tickets-must-capture-minimum-contract.md`；跑性能 benchmark 时读 `principles/performance-benchmarks-use-perf-run-guard.md`；写验证脚本时读 `principles/validators-must-not-false-green.md`
  - **PR review / subagent review 必看**：review PR、启动 review subagent 或发布 review comment 前读 `principles/pr-review-subagents-must-use-aticket.md`
  - 详细分组与完整索引见 `principles/AGENTS.md`
- **索引入口**：长期控制面知识只按 principle 处理，入口是 `principles/AGENTS.md`；ticket 生命周期规则从 `principles/AGENTS.md` 读取。
