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

完整的实验合同、canary 和结果解释见 [性能 benchmark 使用 perf-run-guard](../../principles/performance-benchmarks-use-perf-run-guard.md)。

本目录内容遵循 stone-harness 仓库的 MIT License。
