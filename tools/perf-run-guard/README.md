# perf-run-guard

`perf_run_guard.py` 为 Linux 单核性能实验提供运行前 CPU/SMT sibling 干净度检查、运行期 CPU busy/frequency 采样，以及可审计的 manifest 和 Markdown summary。

脚本只依赖 Linux `/proc`、`/sys` 和 Python 3.12 标准库，不需要安装第三方 Python 包。

## 使用

显式指定 stone-harness checkout，再验证脚本入口。不要用当前 benchmark 仓库的
`git rev-parse --show-toplevel` 猜 stone-harness 的位置：

```bash
: "${STONE_HARNESS_ROOT:?set STONE_HARNESS_ROOT to the stone-harness checkout}"
PERF_RUN_GUARD="$STONE_HARNESS_ROOT/tools/perf-run-guard/perf_run_guard.py"
test -x "$PERF_RUN_GUARD" || {
  echo "perf-run-guard not found or not executable: $PERF_RUN_GUARD" >&2
  exit 1
}

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

当前版本支持无 SMT 或每个 core 只有一个 sibling 的拓扑。只有成功读取且明确仅包含
目标 CPU 的 `thread_siblings_list` 才能证明无 SMT；拓扑文件缺失、为空、不包含目标
CPU，或报告多个 sibling 时，脚本都会 fail closed。

pre-scan 和运行期如果目标 CPU 的任一采样 interval 缺少对应 sibling 遥测，guard
都会拒绝该候选或 run，避免把部分遥测覆盖当成 sibling 干净。所有数值参数必须有限
并处于各自允许范围；`NaN`、`Inf`、非正采样间隔以及超出 `0..100` 的百分比会在
创建输出目录前被拒绝。

`--no-affinity` 是探索性逃生口：它无法证明命令运行在被采样 CPU 上，因此即使其他
检查通过也只会生成 `caveated_no_affinity`，不会生成 `clean_sample`。

如需从既有 manifest 重新生成 `summary.md`，已有 summary 时必须显式确认覆盖：

```bash
python3.12 "$PERF_RUN_GUARD" summary --overwrite "<run-dir>/manifest.json"
```

完整的实验合同、canary 和结果解释见 [性能 benchmark 使用 perf-run-guard](../../principles/performance-benchmarks-use-perf-run-guard.md)。

本目录内容遵循 stone-harness 仓库的 MIT License。
