from __future__ import annotations

import errno
import hashlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = PACKAGE_ROOT / "scripts" / "replace_record.py"
SPEC = importlib.util.spec_from_file_location("project_memory_replace_record", HELPER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load replacement helper")
replace_record = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replace_record)


class ReplaceRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.owner = Path(self.temporary.name) / "hub"
        self.memory = self.owner / ".project-memory"
        self.memory.mkdir(parents=True)
        self.target = self.memory / "CONTEXT.md"
        self.original = b"---\nupdated: 2026-01-01\n---\n\nold\n"
        self.target.write_bytes(self.original)
        self.proposed = Path(self.temporary.name) / "proposed.bin"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def expected_hash(self) -> str:
        return hashlib.sha256(self.target.read_bytes()).hexdigest()

    def call_helper(self, **overrides: object) -> tuple[int, dict[str, object]]:
        arguments: dict[str, object] = {
            "owner_root": self.owner,
            "memory_root": self.memory,
            "target": self.target,
            "expected_sha256": self.expected_hash(),
            "proposed_content": self.proposed,
        }
        arguments.update(overrides)
        return replace_record.replace_record(**arguments)

    def remnants(self) -> list[Path]:
        return list(self.memory.glob(".*.project-memory-replace-*.tmp"))

    def test_successful_byte_exact_replacement(self) -> None:
        proposed = "raw Ω bytes\r\nnext\n".encode("utf-8")
        self.proposed.write_bytes(proposed)

        code, result = self.call_helper()

        self.assertEqual(replace_record.EXIT_OK, code)
        self.assertEqual("replaced", result["status"])
        self.assertEqual(proposed, self.target.read_bytes())
        self.assertEqual(hashlib.sha256(proposed).hexdigest(), result["final_sha256"])
        self.assertEqual([], self.remnants())

    def test_proposed_content_requires_utf8_without_bom(self) -> None:
        for proposed in (b"\xef\xbb\xbftext\n", b"\xff\xfe"):
            with self.subTest(proposed=proposed):
                self.target.write_bytes(self.original)
                self.proposed.write_bytes(proposed)
                code, result = self.call_helper()
                self.assertEqual(replace_record.EXIT_REFUSED, code)
                self.assertEqual("refused", result["status"])
                self.assertEqual(self.original, self.target.read_bytes())
                self.assertEqual([], self.remnants())

    def test_lf_and_crlf_are_not_translated(self) -> None:
        for proposed in (b"one\ntwo\n", b"one\r\ntwo\r\n"):
            with self.subTest(proposed=proposed):
                self.target.write_bytes(self.original)
                self.proposed.write_bytes(proposed)
                code, _ = self.call_helper()
                self.assertEqual(replace_record.EXIT_OK, code)
                self.assertEqual(proposed, self.target.read_bytes())

    def test_dry_run_leaves_bytes_metadata_and_directory_unchanged(self) -> None:
        self.proposed.write_bytes(b"new\n")
        before_bytes = self.target.read_bytes()
        before_stat = self.target.stat()
        before_entries = {path.name for path in self.memory.iterdir()}

        code, result = self.call_helper(dry_run=True)

        after_stat = self.target.stat()
        self.assertEqual(replace_record.EXIT_OK, code)
        self.assertEqual("dry-run", result["status"])
        self.assertEqual(before_bytes, self.target.read_bytes())
        self.assertEqual(before_stat.st_mtime_ns, after_stat.st_mtime_ns)
        self.assertEqual(before_entries, {path.name for path in self.memory.iterdir()})

    def test_stale_hash_refuses_without_change(self) -> None:
        self.proposed.write_bytes(b"new\n")
        stale = hashlib.sha256(b"different").hexdigest()

        code, result = self.call_helper(expected_sha256=stale)

        self.assertEqual(replace_record.EXIT_STALE, code)
        self.assertEqual("stale", result["status"])
        self.assertEqual(self.original, self.target.read_bytes())
        self.assertEqual([], self.remnants())

    def test_expected_hash_is_rechecked_before_retry(self) -> None:
        self.proposed.write_bytes(b"new\n")
        calls = 0

        def locked_after_concurrent_change(source: str, destination: str) -> None:
            nonlocal calls
            calls += 1
            Path(destination).write_bytes(b"concurrent\n")
            raise PermissionError(errno.EACCES, "temporarily locked", destination)

        code, result = self.call_helper(
            replace_func=locked_after_concurrent_change,
            sleep_func=lambda _: None,
            monotonic_func=lambda: 0.0,
        )

        self.assertEqual(1, calls)
        self.assertEqual(replace_record.EXIT_STALE, code)
        self.assertEqual("stale", result["status"])
        self.assertEqual(b"concurrent\n", self.target.read_bytes())
        self.assertEqual([], self.remnants())

    def test_owner_and_memory_escapes_are_refused(self) -> None:
        self.proposed.write_bytes(b"new\n")
        with tempfile.TemporaryDirectory() as external_name:
            external = Path(external_name)
            outside_target = external / "OUTSIDE.md"
            outside_target.write_bytes(self.original)

            code, result = self.call_helper(target=outside_target)
            self.assertEqual(replace_record.EXIT_REFUSED, code)
            self.assertEqual("refused", result["status"])
            self.assertEqual(self.original, outside_target.read_bytes())

            code, result = self.call_helper(memory_root=external, target=outside_target)
            self.assertEqual(replace_record.EXIT_REFUSED, code)
            self.assertEqual("refused", result["status"])

    def test_target_symlink_or_reparse_point_is_refused_when_supported(self) -> None:
        self.proposed.write_bytes(b"new\n")
        link = self.memory / "LINK.md"
        try:
            os.symlink(self.target, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")

        code, result = self.call_helper(target=link)

        self.assertEqual(replace_record.EXIT_REFUSED, code)
        self.assertEqual("refused", result["status"])
        self.assertEqual(self.original, self.target.read_bytes())

    def test_nontransient_failure_preserves_original_and_cleans_temp(self) -> None:
        self.proposed.write_bytes(b"new\n")

        def fail_replace(source: str, destination: str) -> None:
            raise OSError(errno.EIO, "simulated I/O failure", destination)

        code, result = self.call_helper(replace_func=fail_replace)

        self.assertEqual(replace_record.EXIT_IO_ERROR, code)
        self.assertEqual("io-error", result["status"])
        self.assertEqual(self.original, self.target.read_bytes())
        self.assertEqual([], self.remnants())

    def test_lock_retry_is_bounded_and_cleans_temp(self) -> None:
        self.proposed.write_bytes(b"new\n")
        calls = 0

        def locked(source: str, destination: str) -> None:
            nonlocal calls
            calls += 1
            raise PermissionError(errno.EACCES, "temporarily locked", destination)

        code, result = self.call_helper(
            replace_func=locked,
            sleep_func=lambda _: None,
            monotonic_func=lambda: 0.0,
        )

        self.assertEqual(replace_record.MAX_REPLACE_ATTEMPTS, calls)
        self.assertEqual(replace_record.EXIT_LOCKED, code)
        self.assertEqual("locked", result["status"])
        self.assertEqual(self.original, self.target.read_bytes())
        self.assertEqual([], self.remnants())

    @unittest.skipUnless(os.name == "nt", "live Windows replacement")
    def test_live_windows_atomic_replacement(self) -> None:
        proposed = b"windows\r\nreplacement\r\n"
        self.proposed.write_bytes(proposed)

        code, result = self.call_helper()

        self.assertEqual(replace_record.EXIT_OK, code)
        self.assertEqual("replaced", result["status"])
        self.assertEqual(proposed, self.target.read_bytes())
        self.assertEqual([], self.remnants())


if __name__ == "__main__":
    unittest.main()
