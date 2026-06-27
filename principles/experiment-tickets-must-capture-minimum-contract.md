---
description: "实验/benchmark/smoke ticket 必须记录假设、环境、命令、结果、结论和可复现文件入口；不要只留下运行痕迹或口头结论"
triggers:
  - "experiment"
  - "benchmark"
  - "smoke"
  - "实验"
  - "跑实验"
  - "结果"
  - "measurement"
  - "validation"
---

# experiment-tickets-must-capture-minimum-contract

实验 ticket 的价值在于让后续 agent 能复核结论，而不是证明“我跑过”。每个实验、benchmark、smoke 或验证性 ticket 都要记录最小可复现合同。

## 最小合同

实验结束前至少记录：

1. **Question / hypothesis**：要验证什么，成功/失败标准是什么。
2. **Environment**：机器、repo commit、分支、关键配置、数据版本、随机种子或时间窗口。
3. **Command / procedure**：实际跑了什么命令、脚本或人工步骤。
4. **Raw evidence**：日志、输出、截图、CSV、job URL、commit hash；大文件可压缩或只保留摘要加路径。
5. **Result**：关键数字或 pass/fail，不要只写“看起来可以”。
6. **Conclusion**：这个结果支持/反驳什么，能否外推，有哪些限制。
7. **Next action**：需要 merge、rerun、扩大样本、交给 human，还是没有后续。

## 推荐 artifacts/ 结构

```text
artifacts/
└── experiments/
    └── 2026-06-18-run-01/
        ├── summary.md
        ├── command-output.log
        └── results.csv
```

`artifacts/` 下的实验输出是不可变证据。只有确认这个 run / version 需要被恢复、审计或发布引用时才放进去；如果还会反复编辑，先放 `notes/` 或 `workspace/`。预计会多次实验时，先按 run id、日期、样本、参数或 reviewer round 设计目录，不要让后一次实验覆盖前一次实验的文件。

`summary.md` 可以很短，但要 standalone：

```markdown
# Experiment Summary

Question: Does m4approx beat baseline on cp30 NUMA0 for sample S?
Environment: repo abc123, cp30, NUMA0, dataset S 2026-06-12.
Procedure: `./bench --mode m4approx --dataset S --runs 5`
Result: median 12.3ms vs baseline 15.8ms; 5/5 runs completed.
Conclusion: m4approx is faster on this sample; not yet validated on full data.
Next: run full-data benchmark before publishing.
```

登记到 ticket：

```bash
aticket-cli ticket "$TICKET_DIR" add-item \
  "file://$TICKET_DIR/artifacts/experiments/2026-06-18-run-01/summary.md"
aticket-cli ticket "$TICKET_DIR" context \
  "Experiment complete; result supports m4approx on sample S. Next: full-data benchmark before publish."
```

## 边界

- 小 smoke 也要有 pass/fail、命令和环境；可以只写一条 log。
- 大实验不要把所有 raw 数据塞进 `TICKET.md`；把文件放进带 run/version 语义的 `artifacts/` 路径，ticket 里写摘要并用 `add-item` 登记入口。
- 不要为了“更新结果”覆盖已登记的 artifact；新结果用新路径，旧结果保留为审计证据。
- 如果结果会被正式发布，发布材料还必须固定到可追溯的 source commit，并引用 commit sha/title、执行命令和 artifacts 入口；只有当结论声称代表主线 / release / 线上默认状态时，才需要在对应 `master` / release commit 上复核。
- 如果实验切到新的机器 / runtime / 数据环境 / benchmark 目标，或从附带 smoke 变成独立研究线，先按 [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) 判断是否需要新 ticket / fork ticket。不要把长期 benchmark 线附着在原实现 ticket 下，尤其是结果会驱动 PR、文档页面或后续优化时。

## 相关原则

- [persistent-state-must-be-externalized](persistent-state-must-be-externalized.md) — 持久化状态必须外部化到 ticket 目录
- [workstream-boundaries-must-split-ticket](workstream-boundaries-must-split-ticket.md) — benchmark workstream 是常见 handoff unit 边界
- [published-content-must-identify-ticket](published-content-must-identify-ticket.md) — 正式 benchmark / 技术结论发布前必须 pin 可追溯 source commit
