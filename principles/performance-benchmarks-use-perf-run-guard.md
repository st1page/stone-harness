---
description: "性能 benchmark 应使用 perf-run-guard 固化 clean CPU/SMT sibling 检查、运行期 CPU 频率采样和 false-green-resistant artifacts"
triggers:
  - "perf-run-guard"
  - "$perf-run-guard"
  - "性能 benchmark"
  - "performance benchmark"
  - "CPU sibling"
  - "SMT sibling"
  - "frequency sampling"
  - "clean CPU"
  - "taskset"
---

# 性能 benchmark 使用 perf-run-guard

需要把性能结论用于比较、回归判断或对外发布时，agent 必须用 `perf-run-guard` 固化实验保护：运行前检查空核和 SMT sibling 干净，运行中采样目标 CPU 状态和频率，并把 accept / reject 决策与原始证据落到 ticket artifact。短小 smoke 只要不产出性能结论，可以不触发本原则。

## 何时触发

- 跑 benchmark、perf experiment、性能回归复核或性能 PR review
- 使用 `taskset`、绑核、隔离 CPU、SMT sibling 或 CPU frequency 作为实验条件
- 结论依赖“这次机器没有明显外部干扰”
- 需要把性能数据发布到 GitHub、文档页面、ticket summary 或其他外部报告

本原则补充 [experiment-tickets-must-capture-minimum-contract](experiment-tickets-must-capture-minimum-contract.md) 和 [validators-must-not-false-green](validators-must-not-false-green.md)：前者规定实验最小合同，后者规定验证不能假绿；`perf-run-guard` 是性能实验的默认 guard 工具。

## 工具入口

本仓库已经携带 `perf-run-guard`，不需要另行安装或依赖其他工作仓库。先从当前 checkout 定位脚本：

```bash
STONE_HARNESS_ROOT="${STONE_HARNESS_ROOT:-$(git rev-parse --show-toplevel)}"
PERF_RUN_GUARD="$STONE_HARNESS_ROOT/tools/perf-run-guard/perf_run_guard.py"
python3.12 "$PERF_RUN_GUARD" --help
```

如果当前环境还提供 `$perf-run-guard` skill，可以用它加载更完整的 runbook，但执行入口仍以上述仓库内脚本为准。如果脚本缺失或当前环境不是 Linux，不得把性能结果当作 clean run 发布；在 ticket 里记录缺失条件和结论降级口径。

## Artifact 位置

每个 guarded run 的输出必须落在当前 ticket 下，例如：

```bash
RUN_ID="$(date +%Y%m%d-%H%M%S)-<short-name>"
OUT="$TICKET_DIR/artifacts/experiments/$RUN_ID/perf_guard"
mkdir -p "$OUT"
```

不要把高频采样原始数据逐条写入 aticket work log。aticket 记录控制面摘要，`perf-run-guard` output dir 保存数据面证据。

## 新环境 canary

在新机器、新安装或工具升级后，先跑一个必须失败的 canary，确认 validator 不会假绿：

```bash
python3.12 "$PERF_RUN_GUARD" run \
  --output-dir "$OUT-canary" \
  --pre-scan 0.1 \
  --interval 0.1 \
  --busy-threshold-pct 100 \
  --sibling-threshold-pct 100 \
  --target-min-busy-pct 0 \
  --min-samples 2 \
  -- /bin/true
```

期望结果是命令非零退出，artifact 中能看到 `decision=reject_insufficient_samples` 或等价 reject 决策。canary 意外成功时，先停下修工具或修调用方式，不要继续发布性能结论。

## 标准运行

先用 scan 观察候选 CPU，再用 run 包住真实 benchmark：

```bash
python3.12 "$PERF_RUN_GUARD" scan --duration 2 --interval 0.2

python3.12 "$PERF_RUN_GUARD" run \
  --output-dir "$OUT" \
  --pre-scan 2 \
  --interval 0.2 \
  -- <benchmark command>
```

如果 benchmark 本身很短，必须延长 benchmark 迭代或提高 guard 的最小样本要求；不能因为运行过快没有样本，就把结果当作 clean。

## 解释结果

- 只有 benchmark 退出码为 0 且 guard 决策为 `clean_sample` 时，才能把该 run 作为 clean 性能样本引用。
- `reject_*`、prelaunch failure、样本不足、sibling busy 或目标 CPU busy 不达标时，该 run 只能作为失败证据或带 caveat 的探索数据。
- 如果放宽 busy、sibling、min-samples、pre-scan 或 interval 阈值，必须在 ticket 和发布物里写清具体参数。
- 发布正式性能结论时，写明 source commit、benchmark 命令、guard output dir、关键环境和 guard decision。

## Ticket 记录

完成 guarded run 后，向 ticket 记录摘要和 artifact 入口：

```bash
aticket-cli ticket "$TICKET_DIR" log \
  "perf-run-guard: decision=<decision>; command=<benchmark>; artifact=$OUT"
```

若结果会发布到 PR description、PR comment、文档页面或其他外部内容面，还必须遵守 [published-content-must-identify-ticket](published-content-must-identify-ticket.md)。
