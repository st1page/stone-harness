from __future__ import annotations

import argparse
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
