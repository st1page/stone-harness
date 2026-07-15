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
    def test_multiple_siblings_fail_closed(self) -> None:
        with mock.patch.object(GUARD, "thread_siblings", return_value={0, 1, 2}):
            with self.assertRaisesRegex(GUARD.GuardError, "multiple SMT siblings"):
                GUARD.primary_sibling(0)

    def test_single_sibling_is_supported(self) -> None:
        with mock.patch.object(GUARD, "thread_siblings", return_value={0, 4}):
            self.assertEqual(GUARD.primary_sibling(0), 4)


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
