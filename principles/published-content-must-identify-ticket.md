---
description: "发布到 GitHub、forge PR/comment、release notes 或其他外部内容面时，必须显式标注对应 ticket"
triggers:
  - "publish content"
  - "GitHub"
  - "PR description"
  - "PR comment"
  - "issue comment"
  - "release notes"
  - "发布内容"
  - "发布文档"
  - "发布 PR"
  - "文档页面"
  - "ticket attribution"
  - "反向记录"
  - "更新文档"
  - "修改已有文件"
  - "published results"
  - "formal report"
  - "source commit"
  - "commit pin"
  - "commit id"
  - "正式结论"
---

# 发布内容必须标注对应 ticket

凡是 agent 把工作结果发布到 GitHub、forge PR/comment、release notes、文档页面或其他对话外的内容面，都必须在发布物里显式标注对应 ticket。

## 为什么

- **反查上下文**：读者能从发布物回到 `TICKET.md`，看到 goal、short-context、work log、artifacts 和决策依据
- **审计链完整**：PR、issue comment、release notes 和文档页面不应脱离 ticket 工作单元单独存在
- **跨 agent 交接**：后续 agent 只看到外部发布物时，也能定位到原始工作容器继续查证

## 何时触发

- 创建或更新 GitHub PR description / PR comment / issue comment
- 发布 release notes、runbook、报告、benchmark 结论、review 结果
- 任何会被对话外读者消费、转发或长期引用的 agent 产物

发布前还要判断这次发布是否已经形成新的 handoff unit。新 PR、外部文档族、多轮文档页面或正式 benchmark 结论经常不只是“给当前 ticket 加一个链接”，而是新的 workstream；按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 先做边界检查。

## 如何应用

发布物中至少包含当前 ticket 的一个稳定引用：

- ticket 目录路径：`/home/tsshi/agent-tickets/tickets/<ticket-name>`
- ticket URI：`file:///home/tsshi/agent-tickets/tickets/<ticket-name>`
- 在空间受限的标题/短评论中，至少写 ticket 名称，并在正文或后续评论补全完整路径

推荐写法：

```text
Ticket: file:///home/tsshi/agent-tickets/tickets/2026-06-06-example-123456
```

如果发布面不支持 `file://` 链接，写纯文本绝对路径；不要只写“见 ticket”或“本次 ticket”，因为这些描述离开对话 context 后不可解析。

发布前必须检查草稿，而不是发布后再补想：

- PR description / comment / release notes / 文档页面正文里已经有 `Ticket: ...`
- 如果正文由 markdown 转换或模板生成，检查最终会提交给工具的内容，不只检查源笔记
- 如果发布命令和正文生成分两步，发布命令前重新确认最终 body/description 包含 ticket 引用

## 对称记录

发布完成后，还要把发布物反向记录回 ticket。资源入口只用 `add-item` 记录；需要说明资源语义时写进 `short-context` 或 `log`，不要再使用旧 Artifacts 写法为同一个 URL 维护第二份事实源：

```bash
aticket-cli ticket "$TICKET_DIR" add-item "https://github.com/example-org/example-repo/pull/456"
aticket-cli ticket "$TICKET_DIR" add-item "https://github.com/example-org/example-repo/issues/789#issuecomment-123"
```

这样外部发布物和 ticket 之间形成双向链接：发布物能找到 ticket，ticket 也能找到发布物。

如果发布成功后发现发布物缺少 ticket 引用，先更新发布物补齐引用，再把补救动作写入 ticket log；不要只在 ticket 里登记外部 URL 后就结束。

## 更新已有文档

更新已有文档时优先做局部编辑，不要凭记忆全量重写。全量覆盖要求 agent 重构整个文件，容易静默丢失这次没有关注的段落、链接和边界条件。

判断口径：

| 场景 | 做法 |
|---|---|
| 新建文件 | 直接写新文件 |
| 修改几个段落 | 局部替换 / 插入 |
| 文件结构大幅重组 | 先读完整文件，写完后逐段比对原文，确认删除是有意的 |

## 正式技术结论和 benchmark

性能、correctness、数据修复、迁移结果、benchmark 结论这类会被反复引用或据此决策的发布材料，必须固定到可追溯的源码状态。

发布正式技术结论前：

1. 在发布材料里写明目标 repo、source commit sha 和 commit title。
2. 写清执行命令、artifacts 入口、关键环境和数据版本。
3. 如果结论声称代表主线 / release / 线上默认状态，才需要在对应 `master` / release commit 上复核，并写明这个复核 commit。

PR 合并前也可以发布正式结论，但正文必须清楚说明结论绑定的是 PR 分支或实验分支的具体 commit；合并后若 source commit 改变或需要代表主线状态，再补做复核并更新 commit pin。

## 相关原则

- [work-must-belong-to-a-ticket](work-must-belong-to-a-ticket.md) — 每次工作必须归属到一个 ticket
- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — 新 PR / 外部文档族 / benchmark 报告可能需要拆成新 ticket
- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录
