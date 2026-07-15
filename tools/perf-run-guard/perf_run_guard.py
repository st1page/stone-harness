#!/usr/bin/env python3.12
"""Guard and record single-core benchmark runs.

This tool intentionally uses only Linux procfs/sysfs plus the Python standard
library so it can be copied into benchmark tickets without bootstrapping a
separate environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CPU_RE = re.compile(r"^cpu(\d+)$")
PROC_STAT_RE = re.compile(r"^cpu(\d+)\s+(.+)$")


class GuardError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True)
class CpuTimes:
    idle: int
    total: int


@dataclass(frozen=True)
class CpuSample:
    cpu: int
    busy_pct: float
    freq_mhz: float | None


@dataclass(frozen=True)
class ProcessSample:
    pid: int
    comm: str
    state: str
    processor: int | None
    cpu_ticks: int
    allowed_cpus: set[int]


@dataclass(frozen=True)
class CleanCandidate:
    cpu: int
    sibling: int | None
    cpu_busy_pct: float
    sibling_busy_pct: float | None
    freq_mhz: float | None


def parse_cpu_list(value: str) -> set[int]:
    cpus: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            try:
                start = int(start_s)
                end = int(end_s)
            except ValueError as exc:
                raise GuardError(f"invalid CPU range: {part}") from exc
            if end < start:
                raise GuardError(f"invalid CPU range: {part}")
            cpus.update(range(start, end + 1))
        else:
            try:
                cpus.add(int(part))
            except ValueError as exc:
                raise GuardError(f"invalid CPU id: {part}") from exc
    return cpus


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got: {value}") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"expected an integer >= 1, got: {value}")
    return parsed


def format_cpu_list(cpus: set[int]) -> str:
    if not cpus:
        return ""
    ordered = sorted(cpus)
    ranges: list[str] = []
    start = prev = ordered[0]
    for cpu in ordered[1:]:
        if cpu == prev + 1:
            prev = cpu
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = cpu
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)


def list_online_cpus() -> set[int]:
    online = Path("/sys/devices/system/cpu/online")
    if online.exists():
        text = online.read_text(encoding="utf-8").strip()
        if text:
            return parse_cpu_list(text)
    cpus: set[int] = set()
    for path in Path("/sys/devices/system/cpu").iterdir():
        match = CPU_RE.match(path.name)
        if match:
            cpus.add(int(match.group(1)))
    if not cpus:
        raise GuardError("could not discover online CPUs from /sys/devices/system/cpu")
    return cpus


def thread_siblings(cpu: int) -> set[int]:
    path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
    if not path.exists():
        return {cpu}
    text = path.read_text(encoding="utf-8").strip()
    return parse_cpu_list(text) if text else {cpu}


def primary_sibling(cpu: int) -> int | None:
    siblings = sorted(thread_siblings(cpu) - {cpu})
    if len(siblings) > 1:
        raise GuardError(
            f"CPU {cpu} has multiple SMT siblings ({format_cpu_list(set(siblings))}); "
            "perf-run-guard currently supports at most one sibling and refuses to continue"
        )
    return siblings[0] if siblings else None


def read_cpu_times() -> dict[int, CpuTimes]:
    stat = Path("/proc/stat")
    if not stat.exists():
        raise GuardError("/proc/stat is not available")
    out: dict[int, CpuTimes] = {}
    with stat.open(encoding="utf-8") as handle:
        for line in handle:
            match = PROC_STAT_RE.match(line)
            if not match:
                continue
            cpu = int(match.group(1))
            fields = [int(x) for x in match.group(2).split()]
            if len(fields) < 4:
                continue
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            out[cpu] = CpuTimes(idle=idle, total=sum(fields))
    if not out:
        raise GuardError("could not read per-CPU counters from /proc/stat")
    return out


def busy_between(before: CpuTimes, after: CpuTimes) -> float:
    total_delta = after.total - before.total
    idle_delta = after.idle - before.idle
    if total_delta <= 0:
        return 0.0
    busy = max(0, total_delta - max(0, idle_delta))
    return busy * 100.0 / total_delta


def read_freq_mhz(cpu: int) -> float | None:
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq")
    for name in ("scaling_cur_freq", "cpuinfo_cur_freq"):
        path = base / name
        if path.exists():
            try:
                value_khz = float(path.read_text(encoding="utf-8").strip())
            except ValueError:
                continue
            return value_khz / 1000.0
    return None


def read_meminfo() -> dict[str, int]:
    result: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, rest = line.partition(":")
        fields = rest.strip().split()
        if fields and fields[0].isdigit():
            result[key] = int(fields[0])
    return result


def parse_proc_stat(line: str) -> tuple[str, str, int, int | None] | None:
    left = line.find("(")
    right = line.rfind(")")
    if left < 0 or right < left:
        return None
    comm = line[left + 1 : right]
    fields = line[right + 2 :].split()
    if len(fields) < 37:
        return None
    state = fields[0]
    utime = int(fields[11])
    stime = int(fields[12])
    processor = int(fields[36]) if fields[36].lstrip("-").isdigit() else None
    return comm, state, utime + stime, processor


def read_process_samples() -> dict[int, ProcessSample]:
    samples: dict[int, ProcessSample] = {}
    proc = Path("/proc")
    for path in proc.iterdir():
        if not path.name.isdigit():
            continue
        pid = int(path.name)
        try:
            stat_line = (path / "stat").read_text(encoding="utf-8")
            parsed = parse_proc_stat(stat_line)
            if parsed is None:
                continue
            comm, state, cpu_ticks, processor = parsed
            allowed = set()
            for line in (path / "status").read_text(encoding="utf-8").splitlines():
                if line.startswith("Cpus_allowed_list:"):
                    allowed_text = line.split(":", 1)[1].strip()
                    allowed = parse_cpu_list(allowed_text) if allowed_text else set()
                    break
            samples[pid] = ProcessSample(
                pid=pid,
                comm=comm,
                state=state,
                processor=processor,
                cpu_ticks=cpu_ticks,
                allowed_cpus=allowed,
            )
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, GuardError):
            continue
    return samples


def process_deltas(
    before: dict[int, ProcessSample],
    after: dict[int, ProcessSample],
    watched_cpus: set[int],
    min_ticks: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, current in after.items():
        previous = before.get(pid)
        if previous is None:
            continue
        delta = current.cpu_ticks - previous.cpu_ticks
        if delta < min_ticks:
            continue
        affinity_overlap = bool(current.allowed_cpus & watched_cpus) if current.allowed_cpus else False
        last_seen_on_watched = current.processor in watched_cpus
        if not affinity_overlap and not last_seen_on_watched:
            continue
        rows.append(
            {
                "pid": pid,
                "comm": current.comm,
                "state": current.state,
                "processor": current.processor,
                "cpu_ticks_delta": delta,
                "allowed_cpus": format_cpu_list(current.allowed_cpus),
                "reason": "last_seen_on_watched_cpu" if last_seen_on_watched else "affinity_overlaps_watched_cpu",
            }
        )
    rows.sort(key=lambda row: row["cpu_ticks_delta"], reverse=True)
    return rows[:20]


def collect_interval(
    interval_s: float,
    cpus: set[int],
    include_processes: bool,
    min_proc_ticks: int,
) -> tuple[dict[int, CpuSample], list[dict[str, Any]]]:
    before_cpu = read_cpu_times()
    before_proc = read_process_samples() if include_processes else {}
    time.sleep(interval_s)
    after_cpu = read_cpu_times()
    after_proc = read_process_samples() if include_processes else {}

    samples: dict[int, CpuSample] = {}
    for cpu in cpus:
        if cpu not in before_cpu or cpu not in after_cpu:
            continue
        samples[cpu] = CpuSample(
            cpu=cpu,
            busy_pct=busy_between(before_cpu[cpu], after_cpu[cpu]),
            freq_mhz=read_freq_mhz(cpu),
        )
    proc_rows = process_deltas(before_proc, after_proc, cpus, min_proc_ticks) if include_processes else []
    return samples, proc_rows


def scan_candidates(
    target_cpus: set[int],
    duration_s: float,
    interval_s: float,
    busy_threshold_pct: float,
    sibling_threshold_pct: float,
) -> tuple[list[CleanCandidate], dict[str, Any]]:
    if duration_s <= 0 or interval_s <= 0:
        raise GuardError("--duration and --interval must be positive")
    sample_cpus = set(target_cpus)
    for cpu in target_cpus:
        sibling = primary_sibling(cpu)
        if sibling is not None:
            sample_cpus.add(sibling)
    observed: dict[int, list[CpuSample]] = {cpu: [] for cpu in sample_cpus}
    deadline = time.monotonic() + duration_s
    interval_count = 0
    while time.monotonic() < deadline:
        samples, _ = collect_interval(min(interval_s, max(0.01, deadline - time.monotonic())), sample_cpus, False, 0)
        interval_count += 1
        for cpu, sample in samples.items():
            observed.setdefault(cpu, []).append(sample)
    if interval_count == 0 or not any(observed.values()):
        raise GuardError("scan collected zero CPU samples; refusing to report OK")

    candidates: list[CleanCandidate] = []
    for cpu in sorted(target_cpus):
        cpu_samples = observed.get(cpu, [])
        if not cpu_samples:
            continue
        sibling = primary_sibling(cpu)
        cpu_max = max(sample.busy_pct for sample in cpu_samples)
        sibling_max: float | None = None
        if sibling is not None:
            sibling_samples = observed.get(sibling, [])
            if not sibling_samples:
                continue
            sibling_max = max(sample.busy_pct for sample in sibling_samples)
        freq_values = [sample.freq_mhz for sample in cpu_samples if sample.freq_mhz is not None]
        freq = statistics.mean(freq_values) if freq_values else None
        sibling_ok = sibling_max is None or sibling_max <= sibling_threshold_pct
        if cpu_max <= busy_threshold_pct and sibling_ok:
            candidates.append(
                CleanCandidate(
                    cpu=cpu,
                    sibling=sibling,
                    cpu_busy_pct=cpu_max,
                    sibling_busy_pct=sibling_max,
                    freq_mhz=freq,
                )
            )
    summary = {
        "target_cpus": len(target_cpus),
        "scanned_cpus": len(sample_cpus),
        "intervals": interval_count,
        "busy_threshold_pct": busy_threshold_pct,
        "sibling_threshold_pct": sibling_threshold_pct,
        "clean_candidates": len(candidates),
    }
    return candidates, summary


def candidate_to_json(candidate: CleanCandidate) -> dict[str, Any]:
    return {
        "cpu": candidate.cpu,
        "sibling": candidate.sibling,
        "cpu_busy_pct_max": round(candidate.cpu_busy_pct, 3),
        "sibling_busy_pct_max": None
        if candidate.sibling_busy_pct is None
        else round(candidate.sibling_busy_pct, 3),
        "freq_mhz_avg": None if candidate.freq_mhz is None else round(candidate.freq_mhz, 3),
    }


def summarize_values(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"avg": None, "max": None, "min": None}
    return {
        "avg": round(statistics.mean(values), 3),
        "max": round(max(values), 3),
        "min": round(min(values), 3),
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_summary_md(path: Path, manifest: dict[str, Any]) -> None:
    cpu = manifest["cpu"]
    sibling = manifest.get("sibling")
    decision = manifest["decision"]
    result = manifest["result"]
    lines = [
        "# Performance Run Guard Summary",
        "",
        f"Decision: `{decision}`",
        f"Command exit code: `{result['returncode']}`",
        f"CPU: `{cpu}`",
        f"SMT sibling: `{sibling}`",
        f"Samples: `{manifest['samples']}`",
        "",
        "## CPU State",
        "",
        f"- Target busy pct: `{manifest['target_busy_pct']}`",
        f"- Sibling busy pct: `{manifest['sibling_busy_pct']}`",
        f"- Target freq MHz: `{manifest['target_freq_mhz']}`",
        "",
        "## Reason",
        "",
        manifest["reason"],
        "",
        "## Command",
        "",
        "```text",
        " ".join(manifest["command"]),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def prelaunch_failure_manifest(
    command: list[str],
    output_dir: Path,
    raw_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    start: float,
    mem_start: dict[str, int],
    error: BaseException,
    args: argparse.Namespace,
    decision: str,
    candidate: CleanCandidate | None = None,
) -> dict[str, Any]:
    end = time.time()
    return {
        "tool": "perf_run_guard",
        "version": 1,
        "command": command,
        "cpu": None if candidate is None else candidate.cpu,
        "sibling": None if candidate is None else candidate.sibling,
        "affinity_applied": not args.no_affinity,
        "thresholds": {
            "busy_threshold_pct": args.busy_threshold_pct,
            "sibling_threshold_pct": args.sibling_threshold_pct,
            "target_min_busy_pct": args.target_min_busy_pct,
            "min_samples": args.min_samples,
        },
        "start_time": start,
        "end_time": end,
        "duration_s": round(end - start, 6),
        "samples": 0,
        "target_busy_pct": summarize_values([]),
        "sibling_busy_pct": summarize_values([]),
        "target_freq_mhz": summarize_values([]),
        "suspicious_processes": [],
        "meminfo_start_kb": mem_start,
        "meminfo_end_kb": read_meminfo(),
        "result": {
            "returncode": None,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        },
        "raw_samples": str(raw_path),
        "decision": decision,
        "reason": f"{decision} in {output_dir}: {error}",
    }


def select_cpu(args: argparse.Namespace, online: set[int]) -> CleanCandidate:
    cpus = set(online)
    if args.cpus:
        requested = parse_cpu_list(args.cpus)
        cpus &= requested
    if not cpus:
        raise GuardError("CPU selection is empty")
    if args.cpu is not None:
        if args.cpu not in online:
            raise GuardError(f"CPU {args.cpu} is not online")
        candidates, summary = scan_candidates(
            {args.cpu},
            args.pre_scan,
            args.interval,
            args.busy_threshold_pct,
            args.sibling_threshold_pct,
        )
        for candidate in candidates:
            if candidate.cpu == args.cpu:
                return candidate
        raise GuardError(f"selected CPU {args.cpu} was not clean in pre-scan: {summary}", 4)

    candidates, summary = scan_candidates(
        cpus,
        args.pre_scan,
        args.interval,
        args.busy_threshold_pct,
        args.sibling_threshold_pct,
    )
    if not candidates:
        raise GuardError(f"no clean CPU candidate found: {summary}", 4)
    return sorted(candidates, key=lambda item: (item.sibling_busy_pct or 0.0, item.cpu_busy_pct, item.cpu))[0]


def normalize_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise GuardError("run requires a command after --")
    return command


def set_child_affinity(cpu: int) -> None:
    os.sched_setaffinity(0, {cpu})


def create_output_dir(output_dir: Path) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise GuardError(
            f"output directory already exists: {output_dir}; choose a unique run directory "
            "to preserve prior evidence"
        ) from exc
    except OSError as exc:
        raise GuardError(f"could not create output directory {output_dir}: {exc}") from exc


def run_guard(args: argparse.Namespace) -> int:
    command = normalize_command(args.command)
    output_dir = Path(args.output_dir)
    create_output_dir(output_dir)
    raw_path = output_dir / "samples.jsonl"
    stdout_path = output_dir / "command.stdout"
    stderr_path = output_dir / "command.stderr"
    manifest_path = output_dir / "manifest.json"
    summary_path = output_dir / "summary.md"

    start = time.time()
    mem_start = read_meminfo()
    try:
        online = list_online_cpus()
        candidate = select_cpu(args, online)
    except GuardError as exc:
        raw_path.write_text(
            json.dumps({"time": time.time(), "event": "prelaunch_failed", "error": str(exc)}) + "\n",
            encoding="utf-8",
        )
        stdout_path.write_bytes(b"")
        stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
        manifest = prelaunch_failure_manifest(
            command,
            output_dir,
            raw_path,
            stdout_path,
            stderr_path,
            start,
            mem_start,
            exc,
            args,
            "prelaunch_failed",
        )
        write_json(manifest_path, manifest)
        write_summary_md(summary_path, manifest)
        raise

    watched = {candidate.cpu}
    if candidate.sibling is not None:
        watched.add(candidate.sibling)

    target_busy: list[float] = []
    sibling_busy: list[float] = []
    target_freq: list[float] = []
    suspicious: list[dict[str, Any]] = []
    samples = 0
    with (
        stdout_path.open("wb") as stdout_file,
        stderr_path.open("wb") as stderr_file,
        raw_path.open("w", encoding="utf-8") as raw,
    ):
        try:
            proc = subprocess.Popen(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                preexec_fn=None if args.no_affinity else lambda: set_child_affinity(candidate.cpu),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raw.write(json.dumps({"time": time.time(), "event": "launch_failed", "error": str(exc)}) + "\n")
            manifest = prelaunch_failure_manifest(
                command,
                output_dir,
                raw_path,
                stdout_path,
                stderr_path,
                start,
                mem_start,
                exc,
                args,
                "launch_failed",
                candidate,
            )
            write_json(manifest_path, manifest)
            write_summary_md(summary_path, manifest)
            raise GuardError(f"failed to launch command: {exc}", 6) from exc
        while proc.poll() is None:
            cpu_samples, proc_rows = collect_interval(
                args.interval,
                watched,
                True,
                args.process_min_ticks,
            )
            sample_time = time.time()
            target = cpu_samples.get(candidate.cpu)
            sibling = cpu_samples.get(candidate.sibling) if candidate.sibling is not None else None
            if target is not None:
                samples += 1
                target_busy.append(target.busy_pct)
                if target.freq_mhz is not None:
                    target_freq.append(target.freq_mhz)
            if sibling is not None:
                sibling_busy.append(sibling.busy_pct)
            suspicious.extend(proc_rows)
            raw.write(
                json.dumps(
                    {
                        "time": sample_time,
                        "target": None
                        if target is None
                        else {
                            "cpu": target.cpu,
                            "busy_pct": target.busy_pct,
                            "freq_mhz": target.freq_mhz,
                        },
                        "sibling": None
                        if sibling is None
                        else {
                            "cpu": sibling.cpu,
                            "busy_pct": sibling.busy_pct,
                            "freq_mhz": sibling.freq_mhz,
                        },
                        "processes": proc_rows,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            raw.flush()

        returncode = proc.wait()
    end = time.time()
    mem_end = read_meminfo()

    if samples < args.min_samples:
        reason = f"collected only {samples} samples; minimum is {args.min_samples}"
        decision = "reject_insufficient_samples"
    elif sibling_busy and max(sibling_busy) > args.sibling_threshold_pct:
        reason = (
            f"SMT sibling busy max {max(sibling_busy):.2f}% exceeded "
            f"{args.sibling_threshold_pct:.2f}% threshold"
        )
        decision = "discard_sibling_interference"
    elif target_busy and max(target_busy) < args.target_min_busy_pct:
        reason = (
            f"target CPU busy max {max(target_busy):.2f}% was below "
            f"{args.target_min_busy_pct:.2f}% minimum; benchmark may not have run on target CPU"
        )
        decision = "caveated_target_not_busy"
    else:
        reason = "target CPU was observed and SMT sibling stayed within threshold"
        decision = "clean_sample"

    manifest = {
        "tool": "perf_run_guard",
        "version": 1,
        "command": command,
        "cpu": candidate.cpu,
        "sibling": candidate.sibling,
        "affinity_applied": not args.no_affinity,
        "thresholds": {
            "busy_threshold_pct": args.busy_threshold_pct,
            "sibling_threshold_pct": args.sibling_threshold_pct,
            "target_min_busy_pct": args.target_min_busy_pct,
            "min_samples": args.min_samples,
        },
        "start_time": start,
        "end_time": end,
        "duration_s": round(end - start, 6),
        "samples": samples,
        "target_busy_pct": summarize_values(target_busy),
        "sibling_busy_pct": summarize_values(sibling_busy),
        "target_freq_mhz": summarize_values(target_freq),
        "suspicious_processes": suspicious[:50],
        "meminfo_start_kb": mem_start,
        "meminfo_end_kb": mem_end,
        "result": {
            "returncode": returncode,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        },
        "raw_samples": str(raw_path),
        "decision": decision,
        "reason": reason,
    }
    write_json(manifest_path, manifest)
    write_summary_md(summary_path, manifest)

    if returncode != 0:
        return returncode
    if decision != "clean_sample" and not args.allow_noisy:
        print(f"perf_run_guard: {decision}: {reason}", file=sys.stderr)
        return 5
    print(
        "perf_run_guard: "
        f"{decision}; summary={summary_path}; manifest={manifest_path}; "
        f"cpu={candidate.cpu}; sibling={candidate.sibling}; samples={samples}"
    )
    return 0


def scan_guard(args: argparse.Namespace) -> int:
    cpus = list_online_cpus()
    if args.cpus:
        cpus &= parse_cpu_list(args.cpus)
    candidates, summary = scan_candidates(
        cpus,
        args.duration,
        args.interval,
        args.busy_threshold_pct,
        args.sibling_threshold_pct,
    )
    payload = {
        "summary": summary,
        "candidates": [
            candidate_to_json(candidate)
            for candidate in sorted(
                candidates,
                key=lambda item: (item.sibling_busy_pct or 0.0, item.cpu_busy_pct, item.cpu),
            )[: args.limit or None]
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if candidates else 4


def summarize_guard(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    summary_path = manifest_path.with_name("summary.md")
    if summary_path.exists() and not args.overwrite:
        raise GuardError(
            f"summary already exists: {summary_path}; pass --overwrite only when replacing it is intentional"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    write_summary_md(summary_path, manifest)
    print(summary_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check clean CPU/SMT conditions and record CPU state around benchmark runs."
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    scan = subparsers.add_parser("scan", help="find currently clean CPU/SMT pairs")
    scan.add_argument("--cpus", help="CPU allow-list such as 0-15,24")
    scan.add_argument("--duration", type=float, default=1.0, help="scan duration in seconds")
    scan.add_argument("--interval", type=float, default=0.2, help="sampling interval in seconds")
    scan.add_argument("--busy-threshold-pct", type=float, default=5.0)
    scan.add_argument("--sibling-threshold-pct", type=float, default=5.0)
    scan.add_argument("--limit", type=int, default=32, help="maximum candidates to print; 0 means all")
    scan.set_defaults(func=scan_guard)

    run = subparsers.add_parser("run", help="run a command with CPU guard and sampling")
    run.add_argument("--cpu", type=int, help="specific target CPU; omit to auto-pick")
    run.add_argument("--cpus", help="CPU allow-list for auto-pick")
    run.add_argument("--output-dir", required=True, help="directory for manifest and raw samples")
    run.add_argument("--pre-scan", type=float, default=1.0, help="cleanliness scan before starting command")
    run.add_argument("--interval", type=float, default=0.2, help="sampling interval in seconds")
    run.add_argument("--busy-threshold-pct", type=float, default=5.0)
    run.add_argument("--sibling-threshold-pct", type=float, default=5.0)
    run.add_argument("--target-min-busy-pct", type=float, default=20.0)
    run.add_argument("--min-samples", type=positive_int, default=1)
    run.add_argument("--process-min-ticks", type=int, default=1)
    run.add_argument("--no-affinity", action="store_true", help="do not pin child command to target CPU")
    run.add_argument("--allow-noisy", action="store_true", help="return command exit code even if guard decision is not clean")
    run.add_argument("command", nargs=argparse.REMAINDER, help="benchmark command after --")
    run.set_defaults(func=run_guard)

    summary = subparsers.add_parser("summary", help="regenerate Markdown summary from manifest.json")
    summary.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing summary.md after explicit confirmation",
    )
    summary.add_argument("manifest")
    summary.set_defaults(func=summarize_guard)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GuardError as exc:
        print(f"perf_run_guard: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
