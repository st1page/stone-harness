---
description: "agent 跑实验/benchmark 时优先在自己的 ticket workspace 中维护本地数据面；Aim/JSON/CSV 只承接性能数据，aticket 继续承接控制面"
triggers:
  - "Aim"
  - "experiment tracking"
  - "benchmark tracking"
  - "实验管理"
  - "ticket-local Aim"
  - "agent workspace"
  - "JSON spool"
  - "CSV spool"
  - "central Aim"
  - "performance data plane"
---

# agent 实验应使用 ticket-local 数据面

当实验、benchmark 或 profiling 产生多轮 run、多个 variant、多个 compiler / CPU / perf group，或需要后续 agent 继续检索对比时，agent 应把结构化性能数据放在自己的 ticket workspace 中管理。Aim、JSON spool、CSV spool 都是**数据面**；aticket 仍是**控制面**。

## 原则

- aticket 负责 goal、owner、handoff、生命周期、最终结论和证据入口。
- ticket-local 数据面负责 run、metric、variant、compiler、CPU、噪声标记和可查询字段。
- 原始 CSV/JSON/log/summary 仍是审计证据；Aim repo 不能成为唯一事实源。
- 多 agent 并发时，默认各写各的 ticket workspace，不直接并发写中央 Aim repo。
- 数据确认干净后，再把已验证 run 汇总到中央 TSU / 项目级 Aim repo。

## 推荐布局

```text
$TICKET_DIR/
├── artifacts/
│   └── experiments/
│       └── <run-id>/
│           ├── summary.md
│           ├── results.csv
│           └── raw.jsonl
└── workspace/
    ├── aim-repo/              # 可选：ticket-local Aim repo
    ├── import_runs.py         # 可选：把 CSV/JSON spool 导入 Aim
    └── query_runs.py          # 可选：固定常用 agent 查询
```

如果实验很小，只产生一个 pass/fail smoke，不需要 Aim。按 [experiment-tickets-must-capture-minimum-contract.md](experiment-tickets-must-capture-minimum-contract.md) 写 summary/log 即可。

## 什么时候使用 Aim

适合使用 Aim：

- 同一个问题跨多个版本、compiler、CPU、perf group 或参数组合。
- 需要查询“clean 样本”“被拒绝变体”“同 compiler 下 vA vs vB”等结构化问题。
- 后续 agent 需要从 run schema 直接恢复比较上下文。
- 指标很多，Markdown 表格开始不够用。

不适合使用 Aim：

- 单次 smoke 或只有一个结论数字。
- 还没有稳定 schema，只是在临时探索输出。
- 需要在 measured hot loop 内打点。
- 多 agent 要直接并发写同一个中央 repo。

## 写入边界

不要在 measured hot loop 内写 Aim、SQLite、JSON、CSV 或网络日志。benchmark wrapper 可以在每次 run、进程或 perf group 结束后写一条完整记录。

推荐流程：

1. hot loop 只做测量。
2. wrapper 收集本次 run 的 metrics、environment、artifact path 和噪声状态。
3. run 结束后写入 JSON/CSV spool，或写入 ticket-local Aim repo。
4. batch 完成后执行查询/校验，确认 run count、clean 过滤和关键结论。
5. 把 summary、manifest、query report 登记到 ticket items。

## 最小 run schema

每条结构化 run 至少应包含：

- `ticket_id`
- `source_ticket_path`
- `hypothesis`
- `change_summary`
- `variant`
- `compiler`
- `commit`
- `cpu`
- `smt_clean`
- `hugepage` 或其他关键 runtime config
- `metrics`
- `decision`
- `reason`
- `artifact_paths`

建议额外包含：

- `dataset`
- `source_csv`
- `source_run`
- `perf_group`
- `machine`
- `warmup_iters`
- `measure_iters`
- `toolchain_path`

## 噪声和决策

不要把噪声样本删到不可追溯。更好的做法是保留样本，并显式标注：

- `smt_clean=true/false`
- `decision=clean_sample`
- `decision=discard_sibling_interference`
- `decision=caveated_memory_pressure`
- `decision=reject`
- `reason=<具体原因>`

最终报告只用 clean 或明确 caveated 的样本，但被丢弃样本仍能解释为什么没采纳。

## ticket-local 到中央 repo

中央 Aim repo 只接收已经验证过的数据。晋升前至少检查：

1. ticket-local run count 与 manifest / CSV 行数一致。
2. 常用查询能复现 summary 中的关键数字。
3. 每条 run 都能反链到原始 artifact。
4. `decision` 和 `reason` 不为空。
5. 噪声过滤字段能区分 clean 与 discarded/caveated 样本。

如果多个 agent 同时跑 benchmark，优先让每个 agent 写自己的 ticket-local repo 或 spool 文件，再由一个明确 owner 合并。

## Aim 使用注意

Aim 是实现选择，不是控制面契约。不同版本的 Aim SDK 可能有兼容问题；agent 使用前应先做最小 smoke：

```bash
python3.12 -m venv "$TICKET_DIR/workspace/aim-venv"
"$TICKET_DIR/workspace/aim-venv/bin/python" -m pip install aim
"$TICKET_DIR/workspace/aim-venv/bin/python" - "$TICKET_DIR/workspace/aim-smoke" <<'PY'
import sys
from aim import Run
repo = sys.argv[1]
run = Run(repo=repo, experiment="smoke", system_tracking_interval=None, log_system_params=False)
run["ticket_id"] = "smoke"
run.track(1.0, name="latency_us", step=0)
run.close()
PY
```

如果 batch 写入后查询看不到 run，先按当前 Aim 版本的 CLI 帮助确认是否需要 reindex。不要把“写入命令成功”当成查询可用的证明。

## 与实验最小合同的关系

本原则补充的是“多 run 数据面怎么管理”。每个实验仍必须满足 [experiment-tickets-must-capture-minimum-contract.md](experiment-tickets-must-capture-minimum-contract.md)：

- Question / hypothesis
- Environment
- Command / procedure
- Raw evidence
- Result
- Conclusion
- Next action

Aim repo、manifest、query report 都只是 raw evidence / result 的入口之一；ticket summary 和 final context 仍要写清结论、限制和下一步。

## 反模式

- 直接让多个 agent 写同一个中央 Aim repo。
- 只保存 Aim repo，不保存原始 CSV/JSON/log/summary。
- run 里只有 metric，没有 hypothesis、decision、reason、artifact path。
- 把 Aim 当成 ticket lifecycle、handoff 或 final decision 的替代品。
- 在热循环内调用 Aim logging。
- 导入后不做 run count / 查询校验，就把数据发布成正式结论。

## 相关原则

- [experiment-tickets-must-capture-minimum-contract.md](experiment-tickets-must-capture-minimum-contract.md) — 实验 / benchmark / smoke 最小可复现合同
- [work-must-belong-to-a-ticket.md](work-must-belong-to-a-ticket.md) — 所有工作必须归属 ticket
- [persistent-state-must-be-externalized.md](persistent-state-must-be-externalized.md) — 持久化状态必须外部化
- [workstream-boundaries-must-split-ticket.md](workstream-boundaries-must-split-ticket.md) — benchmark workstream 边界和拆票
