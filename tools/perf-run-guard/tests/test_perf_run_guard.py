from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "perf_run_guard.py"
SPEC = importlib.util.spec_from_file_location("vendored_perf_run_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GUARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUARD
SPEC.loader.exec_module(GUARD)


class ArgumentValidationTests(unittest.TestCase):
    def test_min_samples_must_be_positive(self) -> None:
        self.assertEqual(GUARD.positive_int("1"), 1)
        for value in ("0", "-1", "not-an-int"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    GUARD.positive_int(value)

    def test_float_arguments_must_be_finite_and_in_range(self) -> None:
        self.assertEqual(GUARD.positive_finite_float("0.1"), 0.1)
        self.assertEqual(GUARD.percentage_float("100"), 100.0)
        for value in ("nan", "inf", "-inf", "0", "-1"):
            with self.subTest(kind="positive", value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    GUARD.positive_finite_float(value)
        for value in ("nan", "inf", "-inf", "-1", "101"):
            with self.subTest(kind="percentage", value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    GUARD.percentage_float(value)

    def test_invalid_float_is_rejected_before_output_creation(self) -> None:
        parser = GUARD.build_parser()
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "run"
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parser.parse_args(
                        [
                            "run",
                            "--output-dir",
                            str(output_dir),
                            "--target-min-busy-pct",
                            "nan",
                            "--",
                            "/bin/true",
                        ]
                    )
            self.assertFalse(output_dir.exists())


class ArtifactSafetyTests(unittest.TestCase):
    def test_existing_output_directory_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "run"
            output_dir.mkdir()
            sentinel = output_dir / "manifest.json"
            sentinel.write_text("prior evidence\n", encoding="utf-8")

            with self.assertRaises(GUARD.GuardError):
                GUARD.create_output_dir(output_dir)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "prior evidence\n")

    def test_new_output_directory_is_created_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "new" / "run"
            GUARD.create_output_dir(output_dir)
            self.assertTrue(output_dir.is_dir())
            with self.assertRaises(GUARD.GuardError):
                GUARD.create_output_dir(output_dir)

    def test_summary_requires_explicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / "manifest.json"
            summary = Path(temp) / "summary.md"
            manifest.write_text("{}\n", encoding="utf-8")
            summary.write_text("prior summary\n", encoding="utf-8")
            args = argparse.Namespace(manifest=str(manifest), overwrite=False)

            with self.assertRaises(GUARD.GuardError):
                GUARD.summarize_guard(args)

            self.assertEqual(summary.read_text(encoding="utf-8"), "prior summary\n")


class TopologySafetyTests(unittest.TestCase):
    def test_missing_topology_fails_closed(self) -> None:
        with mock.patch.object(GUARD.Path, "read_text", side_effect=FileNotFoundError("missing")):
            with self.assertRaisesRegex(GUARD.GuardError, "cannot read SMT topology"):
                GUARD.thread_siblings(7)

    def test_empty_topology_fails_closed(self) -> None:
        with mock.patch.object(GUARD.Path, "read_text", return_value="\n"):
            with self.assertRaisesRegex(GUARD.GuardError, "SMT topology.*is empty"):
                GUARD.thread_siblings(7)

    def test_topology_must_contain_target_cpu(self) -> None:
        with mock.patch.object(GUARD.Path, "read_text", return_value="8\n"):
            with self.assertRaisesRegex(GUARD.GuardError, "does not include the target CPU"):
                GUARD.thread_siblings(7)

    def test_explicit_single_cpu_topology_has_no_sibling(self) -> None:
        with mock.patch.object(GUARD.Path, "read_text", return_value="7\n"):
            self.assertIsNone(GUARD.primary_sibling(7))

    def test_multiple_siblings_fail_closed(self) -> None:
        with mock.patch.object(GUARD, "thread_siblings", return_value={0, 1, 2}):
            with self.assertRaisesRegex(GUARD.GuardError, "multiple SMT siblings"):
                GUARD.primary_sibling(0)

    def test_single_sibling_is_supported(self) -> None:
        with mock.patch.object(GUARD, "thread_siblings", return_value={0, 4}):
            self.assertEqual(GUARD.primary_sibling(0), 4)


class ScanSafetyTests(unittest.TestCase):
    @staticmethod
    def scan(intervals: list[tuple[dict[int, object], list[dict[str, object]]]]):
        monotonic_values = [0.0, 0.0, 0.0, 1.0, 1.0, 2.0]
        with (
            mock.patch.object(GUARD, "primary_sibling", return_value=1),
            mock.patch.object(GUARD.time, "monotonic", side_effect=monotonic_values),
            mock.patch.object(GUARD, "collect_interval", side_effect=intervals),
        ):
            return GUARD.scan_candidates({0}, 2.0, 1.0, 5.0, 5.0)

    def test_partial_sibling_telemetry_is_rejected(self) -> None:
        target = GUARD.CpuSample(cpu=0, busy_pct=0.0, freq_mhz=3000.0)
        sibling = GUARD.CpuSample(cpu=1, busy_pct=0.0, freq_mhz=3000.0)

        candidates, summary = self.scan(
            [({0: target, 1: sibling}, []), ({0: target}, [])]
        )

        self.assertEqual(candidates, [])
        self.assertEqual(summary["intervals"], 2)
        self.assertEqual(summary["incomplete_sibling_telemetry"], 1)

    def test_partial_target_telemetry_is_rejected(self) -> None:
        target = GUARD.CpuSample(cpu=0, busy_pct=0.0, freq_mhz=3000.0)
        sibling = GUARD.CpuSample(cpu=1, busy_pct=0.0, freq_mhz=3000.0)

        candidates, summary = self.scan(
            [({0: target, 1: sibling}, []), ({1: sibling}, [])]
        )

        self.assertEqual(candidates, [])
        self.assertEqual(summary["incomplete_target_telemetry"], 1)

    def test_complete_paired_telemetry_is_accepted(self) -> None:
        target = GUARD.CpuSample(cpu=0, busy_pct=0.0, freq_mhz=3000.0)
        sibling = GUARD.CpuSample(cpu=1, busy_pct=0.0, freq_mhz=3000.0)

        candidates, summary = self.scan(
            [({0: target, 1: sibling}, []), ({0: target, 1: sibling}, [])]
        )

        self.assertEqual([candidate.cpu for candidate in candidates], [0])
        self.assertEqual(summary["incomplete_sibling_telemetry"], 0)


class DecisionSafetyTests(unittest.TestCase):
    @staticmethod
    def args(**overrides: object) -> argparse.Namespace:
        values = {
            "min_samples": 1,
            "sibling_threshold_pct": 5.0,
            "target_min_busy_pct": 20.0,
            "no_affinity": False,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_missing_sibling_telemetry_is_rejected(self) -> None:
        candidate = GUARD.CleanCandidate(0, 1, 0.0, 0.0, None)
        decision, _ = GUARD.decide_run(
            self.args(), candidate, 1, 0, [50.0], []
        )
        self.assertEqual(decision, "reject_incomplete_sibling_telemetry")

    def test_no_affinity_is_never_clean(self) -> None:
        candidate = GUARD.CleanCandidate(0, None, 0.0, None, None)
        decision, _ = GUARD.decide_run(
            self.args(no_affinity=True), candidate, 1, 0, [50.0], []
        )
        self.assertEqual(decision, "caveated_no_affinity")

    def test_complete_pinned_sample_can_be_clean(self) -> None:
        candidate = GUARD.CleanCandidate(0, 1, 0.0, 0.0, None)
        decision, _ = GUARD.decide_run(
            self.args(), candidate, 1, 1, [50.0], [0.0]
        )
        self.assertEqual(decision, "clean_sample")


if __name__ == "__main__":
    unittest.main()
