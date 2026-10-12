#!/usr/bin/env python3
"""Validate the public project-memory skill package using only the standard library."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path


REQUIRED_ROOT_FILES = {"README.md", "SKILL.md", "man.project-memory.md", "LICENSE"}
REQUIRED_REFERENCES = {
    "config.md",
    "identity.md",
    "handoff.md",
    "init.md",
    "maintain.md",
    "resume.md",
    "save.md",
    "schema.md",
}
REQUIRED_TEMPLATES = {
    "CANDIDATES.md",
    "CONTEXT.md",
    "DECISIONS.md",
    "DIRECTION.md",
    "GUIDANCE.md",
    "OUTCOMES.md",
}
REQUIRED_SCRIPTS = {"replace_record.py", "validate_memory.py", "validate_package.py"}
REQUIRED_TESTS = {"memory_fixtures.py", "test_replace_record.py", "test_validate_memory.py"}
REQUIRED_ROOT_DIRECTORIES = {"references", "scripts", "templates", "tests"}
ALLOWED_ROOT_ENTRIES = REQUIRED_ROOT_FILES | REQUIRED_ROOT_DIRECTORIES | {".gitignore", "CHANGELOG.md", "jjfyi-readme-mark.svg"}
PROHIBITED_ROOT_FILES = {
    "BUILD_PLAN.md",
    "DESIGN.md",
    "config.example.toml",
    "config.schema.toml",
}
TEMPLATE_RULES = {
    "CONTEXT.md": (
        "project-memory-context",
        (),
        (
            "## Current Focus",
            "## Open Threads",
            "## Blockers",
            "## Next Steps",
            "## Relevant Memory",
            "## Active Handoff",
        ),
    ),
    "DIRECTION.md": (
        "project-memory-direction",
        ("next_goal_id: 1", "next_focus_id: 1"),
        ("## Goals", "## Focuses"),
    ),
    "OUTCOMES.md": ("project-memory-outcomes", ("next_id: 1",), ("## Outcomes",)),
    "DECISIONS.md": ("project-memory-decisions", ("next_id: 1",), ("## Decisions",)),
    "GUIDANCE.md": ("project-memory-guidance", ("next_id: 1",), ("## Guidance",)),
    "CANDIDATES.md": ("project-memory-candidates", ("next_id: 1",), ("## Candidates",)),
}
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DRIVE_PATH = re.compile(r"(?i)\b[a-z]:[\\/]")
PRIVATE_PRODUCT = re.compile(r"(?i)\bai[.]hub\b")
PRIVATE_LAYOUT = re.compile(r"(?i)(?:[.]homebase|[.]scratch)")
SCAFFOLD = re.compile(
    r"(?i)(?:\b" + "TO" + r"DO\b|\b" + "FIX" + r"ME\b|\b" + "T" + r"BD\b|\[MISSING\])"
)
MAX_REPORTED_ERRORS = 100
PACKAGE_VERSION = "0.5.1"
LEGACY_PACKAGE_VERSIONS = ("0.2" + ".0",)
STALE_PACKAGE_ASSERTIONS = (
    'version: "' + "0.3.0" + '"',
    "Version `" + "0.3.0" + "` is",
)
DEFAULT_MEMORY_PATH = ".project-memory"
CONFIG_SCHEMA_VERSION = "1.2"
LEGACY_CONFIG_SCHEMA_VERSION = "1.0"
RECORD_SCHEMA_VERSION = "1.0"

BEHAVIOR_CONTRACT = {
    "references/identity.md": ("quick unrelated prompt", "ordinary subsequent asks", "Initialization interview", "config last"),
    "SKILL.md": (
        "resume, reground, load context",
        "save session, update session, save work, save progress, or checkpoint",
        "Saving a particular file, draft, document, image, artifact, or named path does not",
        "These rules select an operation after the skill has loaded",
        "Can you save our progress?",
        "Should we save?",
        "Every handoff request, including a combined save plus handoff",
        "Standalone save applies only when no handoff is requested",
        "only when bounded evidence establishes consumption and accounts for every live item",
        "A polite operation request is not guidance approval",
        "known same-directory atomic replacement primitive is available; otherwise stop without writing",
        "cross-namespace routing or roll-up",
    ),
    "README.md": ("PROJECT.md",),
    "man.project-memory.md": ("PROJECT.md",),
    "references/config.md": ("PROJECT.md",),
    "references/init.md": ("PROJECT.md",),
    "references/resume.md": (
        "at most once per fresh conversation",
        "continue the substantive task",
        "create no suppression marker",
        "This list is complete.",
        "the immediate local artifact named for the next action",
        "one owner-relative",
        "a local artifact whose existence is asserted as the current stopping point",
        "direct stat or existence checks only",
        "saved claim and the observed state separately",
        "writes nothing, including when it detects continuation drift",
    ),
    "references/save.md": (
        "installation, initialization, or evaluation alone does not create an adoption decision",
        "an active evaluation updates a `FOCUS` current state",
        "later adoption creates a new decision citing prior evidence",
        "smallest relevant closed evidence set",
        "Do not recursively enumerate the repository",
        "Immediately before writing any memory file",
        "must not be marked complete when its required artifact cannot be verified",
        "names-and-ID-headings inventory is confined to the configured memory root",
        "Reconciliation-embedded save is used by every handoff request",
        "never changes the `Active Handoff` section",
        "sole authority for its ordering, activation, retry, and old-packet retirement",
        "Unrelated completed work alone never establishes absorption",
        "preserve the pointer and packet unchanged",
        "at least two distinct supporting instances",
        "ordinary or polite request to save, update, checkpoint, or continue work is not a request to review or approve reusable guidance",
        "never promotes or rejects a candidate",
        "Do not run this standalone procedure before a handoff",
    ),
    "references/handoff.md": (
        "including a combined save plus handoff, uses reconciliation-embedded save",
        "Report every durable record created during reconciliation",
        "explicitly requests a packet-only handoff",
        "requires the explicit non-absorption supersession choice",
        "write and validate durable records first",
        "update only the non-pointer continuation sections",
        "Prevalidate the exact bytes",
        "reliable current instant from the host or runtime clock",
        "never invent a time of day",
        "same converted instant as `created`",
        "Never invent the retirement time",
        "Re-read the created raw bytes",
        "Hash the post-reconciliation `CONTEXT.md` raw bytes",
        "The pointer alone activates the new packet",
        "add its retirement timestamp exactly once",
        "fresh with no `supersedes`",
        "one post-activation retirement is never repeated",
        "Reuse a uniquely identified inactive packet",
        "attempt pointer activation only",
        "Require explicit approval before creating a suffixed packet",
        "Do not claim that a fresh-session behavioral cold resume was tested",
    ),
    "references/maintain.md": (
        "Reserved replacement remnants are never silently ignored or deleted",
        "stale-continuation finding",
        "inspect only the closed continuation-anchor set",
        "requires explicit approval before changing the meaning",
    ),
    "references/schema.md": ("PROJECT.md",),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a project-memory skill package without modifying it.",
        epilog="Exit codes: 0 valid, 1 validation errors, 2 invalid invocation.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Package root; defaults to the parent of this script's directory.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser.parse_args()


def read_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read UTF-8 text: {path}: {exc}")
        return ""


def frontmatter(text: str) -> str | None:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return None
    marker = normalized.find("\n---\n", 4)
    if marker == -1:
        return None
    return normalized[4:marker]


def strip_code(text: str) -> str:
    text = re.sub(r"(?s)```.*?```", "", text)
    return re.sub(r"`[^`]*`", "", text)


def closed_entries(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {
        path.name
        for path in directory.iterdir()
        if not (
            path.is_dir()
            and (path.name == "__pycache__" or path.name.startswith("."))
        )
    }


def validate_structure(root: Path, errors: list[str]) -> None:
    if not root.is_dir():
        errors.append(f"package root is not a directory: {root}")
        return

    root_entries = closed_entries(root)
    for name in sorted(REQUIRED_ROOT_FILES - root_entries):
        errors.append(f"missing required root file: {name}")
    for name in sorted(root_entries - ALLOWED_ROOT_ENTRIES):
        errors.append(f"unexpected root entry: {name}")
    for name in sorted(PROHIBITED_ROOT_FILES & root_entries):
        errors.append(f"prohibited root file: {name}")

    reference_dir = root / "references"
    template_dir = root / "templates"
    script_dir = root / "scripts"
    test_dir = root / "tests"

    actual_references = closed_entries(reference_dir)
    actual_templates = closed_entries(template_dir)
    actual_scripts = closed_entries(script_dir)
    actual_tests = closed_entries(test_dir)
    for name in sorted(REQUIRED_REFERENCES - actual_references):
        errors.append(f"missing required reference: references/{name}")
    for name in sorted(REQUIRED_TEMPLATES - actual_templates):
        errors.append(f"missing required template: templates/{name}")
    for name in sorted(REQUIRED_SCRIPTS - actual_scripts):
        errors.append(f"missing required script: scripts/{name}")
    for name in sorted(REQUIRED_TESTS - actual_tests):
        errors.append(f"missing required test: tests/{name}")
    for name in sorted(actual_references - REQUIRED_REFERENCES):
        errors.append(f"unexpected reference entry: references/{name}")
    for name in sorted(actual_templates - REQUIRED_TEMPLATES):
        errors.append(f"unexpected template entry: templates/{name}")
    for name in sorted(actual_scripts - REQUIRED_SCRIPTS):
        errors.append(f"unexpected script entry: scripts/{name}")
    for name in sorted(actual_tests - REQUIRED_TESTS):
        errors.append(f"unexpected test entry: tests/{name}")


def validate_skill(root: Path, errors: list[str]) -> None:
    path = root / "SKILL.md"
    text = read_text(path, errors)
    metadata = frontmatter(text)
    if metadata is None:
        errors.append("SKILL.md has missing or malformed YAML frontmatter")
        return

    name_match = re.search(r"(?m)^name:\s*([^\s]+)\s*$", metadata)
    description_match = re.search(r"(?m)^description:\s*(.+?)\s*$", metadata)
    if not name_match or name_match.group(1) != "project-memory":
        errors.append("SKILL.md name must be project-memory")
    if root.name != "project-memory":
        errors.append(f"package directory must be named project-memory, found {root.name}")
    if not description_match:
        errors.append("SKILL.md description is missing")
    elif len(description_match.group(1)) > 1024:
        errors.append("SKILL.md description exceeds 1024 characters")
    expected_version = f'version: "{PACKAGE_VERSION}"'
    if expected_version not in metadata:
        errors.append(f"SKILL.md metadata version must be {PACKAGE_VERSION}")
    if "man.project-memory.md" not in text:
        errors.append("SKILL.md does not link man.project-memory.md")
    for reference in sorted(REQUIRED_REFERENCES):
        if f"references/{reference}" not in text:
            errors.append(f"SKILL.md does not route to references/{reference}")


def validate_templates(root: Path, errors: list[str]) -> None:
    for name, (expected_type, counters, headings) in TEMPLATE_RULES.items():
        path = root / "templates" / name
        text = read_text(path, errors)
        metadata = frontmatter(text)
        if metadata is None:
            errors.append(f"template has missing or malformed frontmatter: {name}")
            continue
        if f"type: {expected_type}" not in metadata:
            errors.append(f"template type mismatch: {name}")
        if f'schema_version: "{RECORD_SCHEMA_VERSION}"' not in metadata:
            errors.append(f"template schema_version mismatch: {name}")
        if re.search(r"(?m)^namespace\s*:", metadata):
            errors.append(f"template must not contain namespace field: {name}")
        if "updated: YYYY-MM-DD" not in metadata:
            errors.append(f"template updated placeholder missing: {name}")
        for counter in counters:
            if counter not in metadata:
                errors.append(f"template counter missing in {name}: {counter}")
        for heading in headings:
            if text.count(heading) != 1:
                errors.append(f"template heading must occur once in {name}: {heading}")


def validate_markdown(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        text = read_text(path, errors)
        visible_text = strip_code(text)

        if DRIVE_PATH.search(visible_text):
            errors.append(f"local drive path found: {relative}")
        if PRIVATE_PRODUCT.search(visible_text) or PRIVATE_LAYOUT.search(visible_text):
            errors.append(f"private product assumption found: {relative}")
        if SCAFFOLD.search(visible_text):
            errors.append(f"unfinished scaffold marker found: {relative}")

        for match in MARKDOWN_LINK.finditer(visible_text):
            target = match.group(1).strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_part = target.split("#", 1)[0]
            resolved = (path.parent / path_part).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"link escapes package: {relative} -> {target}")
                continue
            if not resolved.exists():
                errors.append(f"missing link target: {relative} -> {target}")

    if any(path.name in PROHIBITED_ROOT_FILES for path in root.rglob("*")):
        errors.append("private design or build artifact found in package")
    for state_name in (".project-memory", ".memory"):
        state_path = root / state_name
        if state_path.exists() or state_path.is_symlink():
            errors.append(f"generated memory state found in package: {state_name}")


def validate_python(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        text = read_text(path, errors)
        try:
            ast.parse(text, filename=str(relative))
        except SyntaxError as exc:
            errors.append(f"invalid Python syntax: {relative}:{exc.lineno}: {exc.msg}")
        if DRIVE_PATH.search(text):
            errors.append(f"local drive path found in Python source: {relative}")
        if PRIVATE_PRODUCT.search(text) or PRIVATE_LAYOUT.search(text):
            errors.append(f"private product assumption found in Python source: {relative}")
        if SCAFFOLD.search(text):
            errors.append(f"unfinished scaffold marker found in Python source: {relative}")


def validate_behavior_contract(root: Path, errors: list[str]) -> None:
    for relative, required_phrases in BEHAVIOR_CONTRACT.items():
        text = read_text(root / relative, errors)
        for phrase in required_phrases:
            if phrase not in text:
                errors.append(f"behavior contract missing from {relative}: {phrase}")


def validate_release_contract(root: Path, errors: list[str]) -> None:
    public_sources = sorted(root.rglob("*.md")) + sorted(root.rglob("*.py"))
    for path in public_sources:
        text = read_text(path, errors)
        for legacy_version in LEGACY_PACKAGE_VERSIONS:
            if legacy_version in text:
                errors.append(
                    f"stale package version {legacy_version} found: {path.relative_to(root)}"
                )
        for assertion in STALE_PACKAGE_ASSERTIONS:
            if assertion in text:
                errors.append(
                    f"stale package assertion found: {path.relative_to(root)}: {assertion}"
                )

    config_text = read_text(root / "references" / "config.md", errors)
    if f'schema_version = "{CONFIG_SCHEMA_VERSION}"' not in config_text:
        errors.append(
            f"fresh config example schema_version must be {CONFIG_SCHEMA_VERSION}"
        )
    if 'identity = "PROJECT.md"' not in config_text:
        errors.append("fresh config must reference PROJECT.md")
    if f"Config {LEGACY_CONFIG_SCHEMA_VERSION} permits exactly" not in config_text:
        errors.append(
            f"legacy config schema {LEGACY_CONFIG_SCHEMA_VERSION} closed field set is missing"
        )
    if f'memory = "{DEFAULT_MEMORY_PATH}"' not in config_text:
        errors.append(
            f"config example memory path must default to {DEFAULT_MEMORY_PATH}"
        )

    schema_text = read_text(root / "references" / "schema.md", errors)
    if f'schema_version: "{RECORD_SCHEMA_VERSION}"' not in schema_text:
        errors.append(
            f"record schema documentation must remain {RECORD_SCHEMA_VERSION}"
        )
    if schema_text.count(f'schema_version: "{RECORD_SCHEMA_VERSION}"') != 3:
        errors.append(
            "record, handoff, and archive schema examples must all remain 1.0"
        )
    if re.search(r"(?m)^namespace\s*:", schema_text):
        errors.append(
            "record, handoff, and archive schema examples must not contain namespace"
        )

    validator_text = read_text(root / "scripts" / "validate_memory.py", errors)
    validator_contract = (
        'SCHEMA_ID = "project-memory/memory-validation@1"',
        "MAX_FINDINGS = 100",
        "MAX_DETAIL_CHARS = 1_000",
        "MAX_FILES = 5_000",
        "MAX_FILE_BYTES = 8 * 1024 * 1024",
        "MAX_TOTAL_BYTES = 64 * 1024 * 1024",
        "WORKSPACE_ANCHOR =",
        "HANDOFF_REQUIRED_FIELDS =",
        '"--owner-root",',
        '"--config",',
        'choices=("text", "json")',
        "sys.version_info < (3, 11)",
        "EXIT_VALID, EXIT_INVALID, EXIT_INVOCATION, EXIT_INCONCLUSIVE = 0, 1, 2, 3",
        "def _workspace_anchor(",
        "def _handoff_content(",
        "Owner (hub) root containing .project-memory/project-memory.toml.",
        "Bounded output format (default: text).",
    )
    for assertion in validator_contract:
        if assertion not in validator_text:
            errors.append(f"live-memory validator contract missing: {assertion}")
    if "replace_record" in validator_text:
        errors.append("live-memory validator must remain self-contained")

    replacement_text = read_text(root / "scripts" / "replace_record.py", errors)
    replacement_help = (
        "Owner (hub) root containing the configured memory namespace.",
        "relative paths resolve from --owner-root.",
        "relative paths resolve from --memory-root.",
        "Expected SHA-256 of the target's current raw bytes.",
        "Separate UTF-8 file whose raw bytes will replace the target.",
        "Validate without creating files, replacing the target, or changing metadata.",
    )
    for assertion in replacement_help:
        if assertion not in replacement_text:
            errors.append(f"replacement helper help missing: {assertion}")

    authority_sources = (
        read_text(root / "SKILL.md", errors)
        + read_text(root / "references" / "save.md", errors)
        + read_text(root / "references" / "handoff.md", errors)
        + read_text(root / "man.project-memory.md", errors)
    )
    authority_marker = "sole authority for its ordering, activation, retry, and old-packet retirement"
    if authority_sources.count(authority_marker) != 1:
        errors.append("reconciliation-embedded save must name exactly one ordering authority")
    stale_handoff_orders = (
        "combined save plus handoff runs `save` first",
        "When requested with `save`, complete save first",
    )
    for stale in stale_handoff_orders:
        if stale in authority_sources:
            errors.append(f"stale standalone-save handoff ordering found: {stale}")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    validate_structure(root, errors)
    if root.is_dir():
        validate_skill(root, errors)
        validate_templates(root, errors)
        validate_markdown(root, errors)
        validate_python(root, errors)
        validate_behavior_contract(root, errors)
        validate_release_contract(root, errors)

    if len(errors) > MAX_REPORTED_ERRORS:
        omitted = len(errors) - MAX_REPORTED_ERRORS
        errors = errors[:MAX_REPORTED_ERRORS] + [f"{omitted} additional error(s) omitted"]

    result = {
        "schema": "project-memory/package-validation@1",
        "status": "pass" if not errors else "fail",
        "root": str(root),
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif errors:
        print(f"FAIL project-memory ({len(errors)} error(s))")
        for error in errors:
            print(f"- {error}")
    else:
        print("PASS project-memory")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
