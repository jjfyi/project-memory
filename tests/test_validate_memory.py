from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from memory_fixtures import (
    archive_text,
    content_snapshot,
    decision_entry,
    handoff_text,
    make_hub,
    outcome_entry,
    replace_section,
    set_counter,
    write_config,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE_ROOT / "scripts" / "validate_memory.py"
SPEC = importlib.util.spec_from_file_location("project_memory_validate_memory", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load live-memory validator")
validate_memory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_memory
SPEC.loader.exec_module(validate_memory)


@unittest.skipUnless(sys.version_info >= (3, 11), "validate_memory requires Python 3.11+")
class ValidateMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.owner, self.memory = make_hub(self.base)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, **kwargs: object):
        return validate_memory.validate_memory(self.owner, **kwargs)

    def codes(self, result) -> list[str]:
        return [finding["code"] for finding in result.payload["findings"]]

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=PACKAGE_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def project_identity(self, namespace="sample-project"):
        config = self.owner / ".project-memory/project-memory.toml"
        config.write_text('schema_version = "1.2"\nskill = "project-memory"\ntimezone = "America/Los_Angeles"\n[paths]\nmemory = ".project-memory"\nidentity = "PROJECT.md"\n', encoding="utf-8")
        identity = self.owner / "PROJECT.md"
        identity.write_text(f"---\nnamespace: {namespace}\nname: Sample Project\n---\n\n# Project\n\n## Purpose\nBuild a useful deliverable.\n\n## Scope\nResearch and delivery.\n", encoding="utf-8")
        return identity

    def test_project_identity_12_valid(self):
        self.project_identity()
        result = self.validate()
        self.assertEqual(0, result.exit_code, result.payload)
        self.assertEqual("sample-project", result.payload["namespace"])

    def test_project_identity_missing(self):
        self.project_identity().unlink()
        self.assertIn("identity-missing", self.codes(self.validate()))

    def test_project_identity_invalid_namespace(self):
        self.project_identity("Bad Namespace")
        self.assertIn("identity-invalid", self.codes(self.validate()))

    def test_project_identity_empty_scope(self):
        path = self.project_identity()
        path.write_text(path.read_text().replace("Research and delivery.", ""), encoding="utf-8")
        self.assertIn("identity-invalid", self.codes(self.validate()))

    def test_project_identity_duplicate_field(self):
        path = self.project_identity()
        path.write_text(path.read_text().replace("name: Sample Project", "name: Sample Project\nname: Other"), encoding="utf-8")
        self.assertIn("identity-invalid", self.codes(self.validate()))

    def test_project_identity_rejects_config_namespace(self):
        self.project_identity()
        path = self.owner / ".project-memory/project-memory.toml"
        path.write_text(path.read_text().replace('[paths]', 'namespace = "sample-project"\n[paths]'), encoding="utf-8")
        self.assertIn("config-unknown-key", self.codes(self.validate()))

    def test_project_identity_concurrent_change(self):
        path = self.project_identity()
        result = self.validate(before_recheck=lambda: path.write_text(path.read_text().replace("Sample Project", "Changed Project"), encoding="utf-8"))
        self.assertEqual(validate_memory.EXIT_INCONCLUSIVE, result.exit_code)

    def test_project_identity_legacy_conflict(self):
        path = self.project_identity()
        write_config(self.owner, config_version="1.1", memory_path=".project-memory", namespace="hub")
        self.assertIn("identity-conflict", self.codes(self.validate()))

    def test_project_identity_symlink_refused(self):
        path = self.project_identity()
        target = self.owner / "identity-copy.md"
        path.rename(target)
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest("symlink unavailable")
        self.assertIn("identity-missing", self.codes(self.validate()))

    def test_valid_fresh_config_11_text_and_json(self) -> None:
        result = self.validate()
        self.assertEqual(validate_memory.EXIT_VALID, result.exit_code)
        self.assertEqual("project-memory/memory-validation@1", result.payload["schema"])
        self.assertEqual("hub", result.payload["namespace"])

        text = self.cli("--owner-root", str(self.owner))
        self.assertEqual(0, text.returncode)
        self.assertIn("VALID project-memory", text.stdout)

        structured = self.cli("--owner-root", str(self.owner), "--format", "json")
        self.assertEqual(0, structured.returncode)
        payload = json.loads(structured.stdout)
        self.assertEqual("project-memory/memory-validation@1", payload["schema"])
        self.assertEqual("valid", payload["status"])

    def test_help_and_invocation_exit_2(self) -> None:
        help_result = self.cli("--help")
        self.assertEqual(0, help_result.returncode)
        self.assertIn("--owner-root", help_result.stdout)
        self.assertIn("--config", help_result.stdout)

        missing = self.cli("--owner-root", str(self.base / "missing"))
        self.assertEqual(2, missing.returncode)
        bad_config = self.cli(
            "--owner-root",
            str(self.owner),
            "--config",
            str(self.owner / "wrong.toml"),
        )
        self.assertEqual(2, bad_config.returncode)

    def test_valid_complete_legacy_config_10(self) -> None:
        write_config(
            self.owner,
            config_version="1.0",
            memory_path=".project-memory",
            namespace=None,
        )
        result = self.validate()
        self.assertEqual(0, result.exit_code)
        self.assertEqual("hub", result.payload["namespace"])

    def test_legacy_memory_location_requires_migration(self) -> None:
        legacy_owner, _ = make_hub(
            self.base / "legacy-path",
            config_version="1.1",
            memory_path=".memory",
            namespace="hub",
        )
        result = validate_memory.validate_memory(legacy_owner)
        self.assertIn("config-memory-location", self.codes(result))

    def test_valid_optional_resources_under_legacy_config(self) -> None:
        write_config(
            self.owner,
            config_version="1.0",
            memory_path=".project-memory",
            namespace=None,
        )
        (self.memory / "TASTE.md").write_text(
            "---\ntype: project-memory-taste\nschema_version: \"1.0\"\n"
            "updated: 2026-08-31\nnext_id: 1\n---\n\n# Taste\n\n## Taste\n\n_None._\n",
            encoding="utf-8",
            newline="",
        )
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        (handoffs / "2026-08-31-1000-continue.md").write_text(
            handoff_text(), encoding="utf-8", newline=""
        )
        archive = self.memory / "archive"
        archive.mkdir()
        (archive / "2025.md").write_text(
            archive_text(), encoding="utf-8", newline=""
        )
        self.assertEqual(0, self.validate().exit_code)

    def test_malformed_toml_and_unknown_config_keys_are_invalid(self) -> None:
        config = self.owner / ".project-memory" / "project-memory.toml"
        config.write_text("not = [valid\n", encoding="utf-8")
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("config-invalid", self.codes(result))

        write_config(
            self.owner,
            config_version="1.1",
            memory_path=".project-memory",
            namespace="hub",
            extra="unexpected = true",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("config-unknown-key", self.codes(result))

    def test_namespace_version_matrix(self) -> None:
        cases = [
            ("1.0", "hub"),
            ("1.1", None),
            ("1.1", "project"),
        ]
        for version, namespace in cases:
            with self.subTest(version=version, namespace=namespace):
                write_config(
                    self.owner,
                    config_version=version,
                    memory_path=".project-memory",
                    namespace=namespace,
                )
                result = self.validate()
                self.assertEqual(1, result.exit_code)
                self.assertIn("config-namespace", self.codes(result))

    def test_path_escape_is_invalid(self) -> None:
        write_config(
            self.owner,
            config_version="1.1",
            memory_path="../outside",
            namespace="hub",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("memory-escape", self.codes(result))

    def test_memory_path_reparse_is_invalid_when_supported(self) -> None:
        other = self.base / "outside"
        other.mkdir()
        link = self.owner / "linked-memory"
        try:
            os.symlink(other, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"directory symlink unavailable: {exc}")
        write_config(
            self.owner,
            config_version="1.1",
            memory_path="linked-memory",
            namespace="hub",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertTrue(
            {"memory-reparse", "memory-escape"}.intersection(self.codes(result))
        )

    def test_missing_record_heading_and_wrong_type_are_invalid(self) -> None:
        (self.memory / "GUIDANCE.md").unlink()
        context = self.memory / "CONTEXT.md"
        context.write_text(
            context.read_text(encoding="utf-8").replace("## Blockers", "## Missing Blockers"),
            encoding="utf-8",
            newline="",
        )
        decisions = self.memory / "DECISIONS.md"
        decisions.write_text(
            decisions.read_text(encoding="utf-8").replace(
                "type: project-memory-decisions", "type: project-memory-outcomes"
            ),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("record-missing", self.codes(result))
        self.assertIn("heading-count", self.codes(result))
        self.assertIn("record-type", self.codes(result))

    def test_duplicate_frontmatter_and_unsupported_record_schema(self) -> None:
        context = self.memory / "CONTEXT.md"
        text = context.read_text(encoding="utf-8")
        context.write_text(
            text.replace("updated: 2026-08-31", "updated: 2026-08-31\nupdated: 2026-08-31"),
            encoding="utf-8",
            newline="",
        )
        outcomes = self.memory / "OUTCOMES.md"
        outcomes.write_text(
            outcomes.read_text(encoding="utf-8").replace(
                'schema_version: "1.0"', 'schema_version: "1.1"'
            ),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("frontmatter-duplicate", self.codes(result))
        self.assertIn("record-schema", self.codes(result))

    def test_required_counter_is_present_even_without_entries(self) -> None:
        outcomes = self.memory / "OUTCOMES.md"
        outcomes.write_text(
            outcomes.read_text(encoding="utf-8").replace("next_id: 1\n", ""),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("frontmatter-missing", self.codes(result))

    def test_counter_regression_and_duplicate_id_across_archive(self) -> None:
        outcomes = self.memory / "OUTCOMES.md"
        replace_section(outcomes, "## Outcomes", outcome_entry(2))
        set_counter(outcomes, "next_id", 2)
        archive = self.memory / "archive"
        archive.mkdir()
        (archive / "2025.md").write_text(
            archive_text(content=outcome_entry(2)), encoding="utf-8", newline=""
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("counter-regression", self.codes(result))
        self.assertIn("id-duplicate", self.codes(result))

    def test_outcome_rollup_must_be_reciprocal(self) -> None:
        outcomes = self.memory / "OUTCOMES.md"
        replace_section(
            outcomes,
            "## Outcomes",
            outcome_entry(1, rolls_up="OUT-0002") + "\n" + outcome_entry(2),
        )
        set_counter(outcomes, "next_id", 3)
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("rollup-reciprocal", self.codes(result))

    def test_decision_supersession_must_be_reciprocal(self) -> None:
        decisions = self.memory / "DECISIONS.md"
        replace_section(
            decisions,
            "## Decisions",
            decision_entry(1, superseded_by="DEC-0002").replace(
                "- Status: active", "- Status: superseded"
            )
            + "\n"
            + decision_entry(2),
        )
        set_counter(decisions, "next_id", 3)
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("supersession-reciprocal", self.codes(result))

    def test_handoff_pointer_and_retirement_rules(self) -> None:
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        name = "2026-08-31-1000-continue.md"
        (handoffs / name).write_text(
            handoff_text(retired=True), encoding="utf-8", newline=""
        )
        replace_section(
            self.memory / "CONTEXT.md",
            "## Active Handoff",
            f"[Continue](handoffs/{name})",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("active-handoff-retired", self.codes(result))

    def test_valid_owner_relative_workspace_anchor(self) -> None:
        workspace = self.owner / "work" / "next.txt"
        workspace.parent.mkdir()
        workspace.write_text("ready", encoding="utf-8")
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        (handoffs / "2026-08-31-1000-anchor.md").write_text(
            handoff_text(workspace_anchor="work/next.txt"),
            encoding="utf-8",
            newline="",
        )
        self.assertEqual(0, self.validate().exit_code)

    def test_invalid_workspace_anchor_forms(self) -> None:
        cases = (
            ("escape", "../outside", "workspace-anchor-path"),
            ("absolute", "/outside", "workspace-anchor-path"),
            ("drive", "C" + chr(58) + "/outside", "workspace-anchor-path"),
            ("backslash", "work\\next.txt", "workspace-anchor-path"),
            ("link", "[next](work/next.txt)", "workspace-anchor-path"),
        )
        for name, anchor, expected in cases:
            with self.subTest(name=name):
                owner, memory = make_hub(self.base / name)
                handoffs = memory / "handoffs"
                handoffs.mkdir()
                (handoffs / "2026-08-31-1000-anchor.md").write_text(
                    handoff_text(workspace_anchor=anchor),
                    encoding="utf-8",
                    newline="",
                )
                result = validate_memory.validate_memory(owner)
                self.assertEqual(1, result.exit_code)
                self.assertIn(expected, self.codes(result))

    def test_multiple_or_indented_workspace_anchors_are_invalid(self) -> None:
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        packet = handoffs / "2026-08-31-1000-anchor.md"
        packet.write_text(
            handoff_text(workspace_anchor="work/one").replace(
                "- Workspace anchor: work/one",
                "- Workspace anchor: work/one\n- Workspace anchor: work/two",
            ),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("workspace-anchor-count", self.codes(result))

        packet.write_text(
            handoff_text(workspace_anchor="work/one").replace(
                "- Workspace anchor:", "  - Workspace anchor:"
            ),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("workspace-anchor-format", self.codes(result))

    def test_handoff_packet_content_contract(self) -> None:
        cases = (
            (
                "missing-success",
                lambda text: text.replace(
                    "- Success condition: The continuation is complete.\n", ""
                ),
                "handoff-field",
            ),
            (
                "empty-completed",
                lambda text: text.replace(
                    "## Completed\n\n_None._",
                    "## Completed\n",
                    1,
                ),
                "handoff-section-empty",
            ),
            (
                "first-action",
                lambda text: text.replace("1. Continue.", "Continue."),
                "handoff-first-action",
            ),
            (
                "failed-self-check",
                lambda text: text.replace(
                    "Cold-resume self-check: passed",
                    "Cold-resume self-check: failed",
                ),
                "handoff-self-check",
            ),
        )
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                owner, memory = make_hub(self.base / name)
                handoffs = memory / "handoffs"
                handoffs.mkdir()
                packet = handoffs / "2026-08-31-1000-contract.md"
                packet.write_text(
                    mutate(handoff_text()), encoding="utf-8", newline=""
                )
                result = validate_memory.validate_memory(owner)
                self.assertEqual(1, result.exit_code)
                self.assertIn(expected, self.codes(result))

    def test_valid_active_retired_and_one_way_supersedes_state(self) -> None:
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        first = "2026-08-31-1000-first.md"
        second = "2026-08-31-1100-second.md"
        (handoffs / first).write_text(
            handoff_text(retired=True), encoding="utf-8", newline=""
        )
        (handoffs / second).write_text(
            handoff_text(supersedes=first), encoding="utf-8", newline=""
        )
        replace_section(
            self.memory / "CONTEXT.md",
            "## Active Handoff",
            f"[Second](handoffs/{second})",
        )
        self.assertEqual(0, self.validate().exit_code)

    def test_inactive_retry_candidates_are_structurally_valid(self) -> None:
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        packet = handoff_text()
        for name in (
            "2026-08-31-1000-retry.md",
            "2026-08-31-1000-retry-2.md",
        ):
            (handoffs / name).write_text(packet, encoding="utf-8", newline="")
        result = self.validate()
        self.assertEqual(0, result.exit_code)
        self.assertEqual("valid", result.payload["status"])

    def test_dangling_and_multiple_handoff_pointers_are_invalid(self) -> None:
        context = self.memory / "CONTEXT.md"
        missing = "2026-08-31-1000-missing.md"
        replace_section(
            context,
            "## Active Handoff",
            f"[Absent packet](handoffs/{missing})",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("active-handoff-missing", self.codes(result))

        replace_section(
            context,
            "## Active Handoff",
            f"[First](handoffs/{missing}) [Second](handoffs/{missing})",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("active-handoff-count", self.codes(result))

    def test_handoff_supersedes_is_one_way_resolving_and_acyclic(self) -> None:
        handoffs = self.memory / "handoffs"
        handoffs.mkdir()
        first = "2026-08-31-1000-first.md"
        second = "2026-08-31-1100-second.md"
        (handoffs / first).write_text(
            handoff_text(retired=True, supersedes=second),
            encoding="utf-8",
            newline="",
        )
        (handoffs / second).write_text(
            handoff_text(retired=True, supersedes=first),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("handoff-cycle", self.codes(result))

    def test_archive_identity_and_replacement_remnant(self) -> None:
        archive = self.memory / "archive"
        archive.mkdir()
        (archive / "2025.md").write_text(
            archive_text(year="2024"), encoding="utf-8", newline=""
        )
        (self.memory / ".CONTEXT.md.project-memory-replace-0123456789abcdef0123456789abcdef.tmp").write_bytes(b"pending")
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("archive-year", self.codes(result))
        self.assertIn("replacement-remnant", self.codes(result))

    def test_sibling_capability_directory_is_ignored(self) -> None:
        sibling = self.owner / "another-capability"
        sibling.mkdir()
        (sibling / "data.txt").write_text("opaque", encoding="utf-8")
        self.assertEqual(0, self.validate().exit_code)

    def test_foreign_file_and_nested_directory_are_invalid(self) -> None:
        (self.memory / "notes.txt").write_text("foreign", encoding="utf-8")
        nested = self.memory / "handoffs" / "nested"
        nested.mkdir(parents=True)
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("foreign-item", self.codes(result))
        self.assertIn("nested-item", self.codes(result))

    def test_crlf_is_accepted_but_bom_and_bare_cr_are_invalid(self) -> None:
        context = self.memory / "CONTEXT.md"
        raw = context.read_bytes()
        context.write_bytes(raw.replace(b"\n", b"\r\n"))
        self.assertEqual(0, self.validate().exit_code)

        other_owner, other_memory = make_hub(self.base / "bom")
        other_context = other_memory / "CONTEXT.md"
        other_context.write_bytes(b"\xef\xbb\xbf" + other_context.read_bytes())
        result = validate_memory.validate_memory(other_owner)
        self.assertEqual(1, result.exit_code)
        self.assertIn("frontmatter-bom", self.codes(result))

        third_owner, third_memory = make_hub(self.base / "bare-cr")
        third_context = third_memory / "CONTEXT.md"
        third_context.write_bytes(third_context.read_bytes().replace(b"\n", b"\r", 1))
        result = validate_memory.validate_memory(third_owner)
        self.assertEqual(1, result.exit_code)
        self.assertIn("bare-cr", self.codes(result))

    def test_id_padding_order_and_qualified_id_are_invalid(self) -> None:
        outcomes = self.memory / "OUTCOMES.md"
        replace_section(
            outcomes,
            "## Outcomes",
            outcome_entry(2)
            + "\n- Artifacts: project:DEC-0001"
            + "\n"
            + outcome_entry(1),
        )
        set_counter(outcomes, "next_id", 3)
        guidance = self.memory / "GUIDANCE.md"
        guidance.write_text(
            guidance.read_text(encoding="utf-8").replace(
                "## Guidance", "## Guidance\n\n### GUIDE-001  Short\n- status: active"
            ),
            encoding="utf-8",
            newline="",
        )
        result = self.validate()
        self.assertEqual(1, result.exit_code)
        self.assertIn("id-order", self.codes(result))
        self.assertIn("id-heading", self.codes(result))
        self.assertIn("qualified-id", self.codes(result))

    def test_unknown_frontmatter_and_entry_fields_are_warnings(self) -> None:
        outcomes = self.memory / "OUTCOMES.md"
        replace_section(outcomes, "## Outcomes", outcome_entry(1) + "\n- future: value")
        text = outcomes.read_text(encoding="utf-8")
        text = text.replace("updated: 2026-08-31", "updated: 2026-08-31\nfuture: value")
        outcomes.write_text(text, encoding="utf-8", newline="")
        set_counter(outcomes, "next_id", 2)
        result = self.validate()
        self.assertEqual(0, result.exit_code)
        self.assertIn("frontmatter-unknown", self.codes(result))
        self.assertIn("field-unknown", self.codes(result))

    def test_concurrent_change_is_inconclusive_exit_3(self) -> None:
        context = self.memory / "CONTEXT.md"

        def mutate() -> None:
            context.write_text(
                context.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
                newline="",
            )

        result = self.validate(before_recheck=mutate)
        self.assertEqual(3, result.exit_code)
        self.assertIn("snapshot-changed", self.codes(result))

    def test_resource_limit_is_inconclusive_exit_3(self) -> None:
        with mock.patch.object(validate_memory, "MAX_FILES", 2):
            result = self.validate()
        self.assertEqual(3, result.exit_code)
        self.assertIn("file-limit", self.codes(result))

    def test_findings_are_bounded_and_deterministic(self) -> None:
        for name in ("one.txt", "two.txt", "three.txt"):
            (self.memory / name).write_text(name, encoding="utf-8")
        with mock.patch.object(validate_memory, "MAX_FINDINGS", 2):
            first = self.validate()
            second = self.validate()
        self.assertEqual(first.payload["findings"], second.payload["findings"])
        self.assertEqual(2, len(first.payload["findings"]))
        self.assertGreater(first.payload["omitted_findings"], 0)

        replace_section(
            self.memory / "OUTCOMES.md",
            "## Outcomes",
            "### " + ("x" * 2_000),
        )
        detailed = self.validate()
        self.assertTrue(
            any(finding["code"] == "id-heading" for finding in detailed.payload["findings"])
        )
        self.assertTrue(
            all(
                len(finding["path"]) <= validate_memory.MAX_DETAIL_CHARS
                and len(finding["message"]) <= validate_memory.MAX_DETAIL_CHARS
                for finding in detailed.payload["findings"]
            )
        )

    def test_validation_does_not_modify_content_or_mtime(self) -> None:
        before = content_snapshot(self.owner)
        entries_before = sorted(
            path.relative_to(self.owner).as_posix()
            for path in self.owner.rglob("*")
        )
        self.assertEqual(0, self.validate().exit_code)
        after = content_snapshot(self.owner)
        entries_after = sorted(
            path.relative_to(self.owner).as_posix()
            for path in self.owner.rglob("*")
        )
        self.assertEqual(before, after)
        self.assertEqual(entries_before, entries_after)

    def test_file_size_limit_is_inconclusive(self) -> None:
        with mock.patch.object(validate_memory, "MAX_FILE_BYTES", 8):
            result = self.validate()
        self.assertEqual(3, result.exit_code)
        self.assertIn("file-size-limit", self.codes(result))


if __name__ == "__main__":
    unittest.main()
