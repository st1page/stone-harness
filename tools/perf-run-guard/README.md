# perf-run-guard

`perf_run_guard.py` 为 Linux 单核性能实验提供运行前 CPU/SMT sibling 干净度检查、运行期 CPU busy/frequency 采样，以及可审计的 manifest 和 Markdown summary。

脚本只依赖 Linux `/proc`、`/sys` 和 Python 3.12 标准库，不需要安装第三方 Python 包。

## 使用

从 stone-harness checkout 中定位脚本：

```bash
STONE_HARNESS_ROOT="${STONE_HARNESS_ROOT:-$(git rev-parse --show-toplevel)}"
PERF_RUN_GUARD="$STONE_HARNESS_ROOT/tools/perf-run-guard/perf_run_guard.py"

python3.12 "$PERF_RUN_GUARD" --help
python3.12 "$PERF_RUN_GUARD" scan --duration 2 --interval 0.2
```

运行 benchmark：

```bash
python3.12 "$PERF_RUN_GUARD" run \
  --output-dir "$TICKET_DIR/artifacts/experiments/<run-id>/perf_guard" \
  --pre-scan 2 \
  --interval 0.2 \
  -- <benchmark command>
```

每次 run 必须使用尚不存在的唯一 output directory；脚本会原子创建目录，并在路径已存在时拒绝运行，以免覆盖既有证据。`--min-samples` 必须大于等于 1。

当前版本支持无 SMT 或每个 core 只有一个 sibling 的拓扑。如果 Linux 报告目标 CPU 有多个 sibling，脚本会 fail closed；它不会忽略额外 sibling 后继续生成 clean 结论。

如需从既有 manifest 重新生成 `summary.md`，已有 summary 时必须显式确认覆盖：

```bash
python3.12 "$PERF_RUN_GUARD" summary --overwrite "<run-dir>/manifest.json"
```

完整的实验合同、canary 和结果解释见 [性能 benchmark 使用 perf-run-guard](../../principles/performance-benchmarks-use-perf-run-guard.md)。

本目录内容遵循 stone-harness 仓库的 MIT License。
