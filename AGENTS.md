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

**来源 / 文档**：[`aticket-cli`](https://github.com/st1page/aticket-cli)

**用途**：管理工作生命周期（ticket 创建、claim/release、fork、archive、状态外部化，以及 ticket `workspace/` 下的 repo worktree 归属）

**P0 / 所有命令任务必看**：
- **环境 skill**：`ticket-workdir`（aticket-cli skill）必须已安装并可用；未安装或版本不匹配时，不要继续命令任务，先让 human 安装 / 更新 aticket-cli skill
- 所有命令任务必须归属到 ticket；无当前 ticket 时，agent 不能继续实质工作，但必须自己先做只读 discover（`aticket-cli tickets search` / 顶层 ticket 扫描），找不到可复用 ticket 就用 `aticket-cli ticket new --topic ... --goal ...` 新建并 claim，再 `brief` 后继续；这不是要求 human 先提供 ticket
- 阶段边界先运行 `aticket-cli ticket "$TICKET_DIR" brief`：开始 / 恢复、claim / fork 后、repo 写操作前、外部发布前、最终回复前、release / archive 前
- repo 写操作必须在当前 ticket 的 `workspace/` linked worktree 下进行
- 新目标、新 repo、新 PR、外部文档族、benchmark 环境、source repo 切换、长票、大目录 / 工具链缓存，或 ticket 范围变宽时，必须判断是否拆 ticket / fork ticket
- 有命令输出、决策、产物、外部 URL、等待外部反馈、长任务或其他可恢复状态时，必须写入 ticket
- 发现 deferred / follow-up 时，必须判断是当前 ticket 尾巴还是新 BACKLOG / fork ticket
- 用户意图、约束或关键事实变化，或进入实现 / 执行前，必须 checkpoint
- 最终回复、外部发布或阶段切换前，必须判断当前 ticket 应 archive、release、fork follow-up 还是继续 ACTIVE；收口前必须写清 final result、外部状态、next owner、剩余风险和 workspace 状态
- `--human-confirm-*` / `--confirm-*` 这类绕过保护的确认参数必须得到 human 对该具体异常操作的明确批准；不能从“结束 / 继续 / 可以”等邻近意图推断
- ticket 生命周期操作后必须在对话里确认

**ticket 相关文档路径（P1 / 按场景加载）**：
- **基础 ticket 归属 / brief / lifecycle 命令确认**：`principles/work-must-belong-to-a-ticket.md`
- **工作流边界 / 拆 ticket / fork ticket**：`principles/workstream-boundaries-must-split-ticket.md`
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
  - **文档写作 / 发布必看**：改已有文档、发布到 GitHub PR / issue / comment、release notes 或其他外部内容面前读 `principles/published-content-must-identify-ticket.md`
  - **验证 / 实验必看**：跑 experiment / benchmark / smoke 时读 `principles/experiment-tickets-must-capture-minimum-contract.md`；写验证脚本时读 `principles/validators-must-not-false-green.md`
  - **PR review / subagent review 必看**：review PR、启动 review subagent 或发布 review comment 前读 `principles/pr-review-subagents-must-use-aticket.md`
  - 详细分组与完整索引见 `principles/AGENTS.md`
- **索引入口**：长期控制面知识只按 principle 处理，入口是 `principles/AGENTS.md`；ticket 生命周期规则从 `principles/AGENTS.md` 读取。
