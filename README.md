# stone-harness

`stone-harness` 需要和 [`aticket-cli`](https://github.com/st1page/aticket-cli) 配合使用：本仓库提供 agent 控制面示例基座，`aticket-cli` 提供 ticket / workspace 生命周期命令。

新项目的 agent 工作基座。仓库自包含，**唯一外部依赖是 [`aticket-cli`](https://github.com/st1page/aticket-cli) 的 `aticket-cli` 命令**（用于工作单元归属、claim/release、fork、archive、状态外部化等）。

本仓库只保留控制面知识：描述「agent 怎么做事」的协作规范、工作流、原则。

## 目录结构

```
sts-harness/
├── principles/                 # 控制面知识（原则与 ticket 生命周期文档）
│   ├── AGENTS.md               # principles/ 统一索引
│   ├── work-must-belong-to-a-ticket.md
│   ├── code-work-preflight.md
│   └── ...
├── AGENTS.md                   # 入口（Claude Code 通过 CLAUDE.md 内联）
└── CLAUDE.md                   # @AGENTS.md import
```

## 入口

每个 agent 进入仓库前先读 `AGENTS.md`（Claude Code 通过 `CLAUDE.md` 的 `@AGENTS.md` 内联到 system prompt）。后续按需沿 `principles/AGENTS.md` 索引加载具体文件。

## 外部依赖

- **`aticket-cli`**：所有 substantive work 必须归属到一个 ticket（见 `principles/work-must-belong-to-a-ticket.md`）。安装后 `which aticket-cli` 应返回有效路径。
- **不依赖任何其他工作仓库**：sts-harness 在新机器上单独 clone 即可使用，不需要预先准备其他知识库或脚本仓库。
