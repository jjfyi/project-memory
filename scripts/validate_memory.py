#!/usr/bin/env python3
"""Read-only structural validation for one configured hub-memory namespace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None  # type: ignore[assignment]

EXIT_VALID, EXIT_INVALID, EXIT_INVOCATION, EXIT_INCONCLUSIVE = 0, 1, 2, 3
SCHEMA_ID = "hub-memory/memory-validation@1"
MAX_FINDINGS = 100
MAX_DETAIL_CHARS = 1_000
MAX_FILES = 5_000
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024

REQUIRED_RECORDS = {
    "CANDIDATES.md": ("hub-memory-candidates", ("Candidates",)),
    "CONTEXT.md": (
        "hub-memory-context",
        ("Current Focus", "Open Threads", "Blockers", "Next Steps", "Relevant Memory", "Active Handoff"),
    ),
    "DECISIONS.md": ("hub-memory-decisions", ("Decisions",)),
    "DIRECTION.md": ("hub-memory-direction", ("Goals", "Focuses")),
    "GUIDANCE.md": ("hub-memory-guidance", ("Guidance",)),
    "OUTCOMES.md": ("hub-memory-outcomes", ("Outcomes",)),
}
OPTIONAL_DIRS = {"handoffs", "archive"}
REMNANT_RE = re.compile(r"^\..+\.hub-memory-replace-[0-9a-f]{32}\.tmp$")
HANDOFF_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{4}-[a-z0-9-]{1,60}\.md$")
ARCHIVE_NAME_RE = re.compile(r"^(\d{4})\.md$")
ID_HEADING_RE = re.compile(r"^### (GOAL|FOCUS|OUT|DEC|GUIDE|CAND|TASTE)-(\d{4,}) — (.+)$")
FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z ]*):\s*(.*)$")
HANDOFF_FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z -]*):\s*(.*)$")
ID_RE = re.compile(r"\b(GOAL|FOCUS|OUT|DEC|GUIDE|CAND|TASTE)-(\d+)\b")
QUALIFIED_ID_RE = re.compile(r"\b[a-z][a-z0-9-]*:(?:GOAL|FOCUS|OUT|DEC|GUIDE|CAND|TASTE)-\d+\b")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WORKSPACE_ANCHOR = "- Workspace anchor:"
HANDOFF_REQUIRED_FIELDS = {
    "Objective": ("Objective", "Success condition"),
    "Exact State": ("Trusted state", "Uncertainty", "Stopping point"),
    "Unresolved Reasoning": (
        "Open questions",
        "Unverified assumptions",
        "Rejected paths",
        "Conversation-only continuity",
    ),
    "Artifacts": (
        "Authoritative resources",
        "Repository state",
        "Environment constraints",
        "Hazards",
    ),
    "Next Actions": ("Acceptance check",),
    "Validation": ("Checks run", "Material failures", "Cold-resume self-check"),
}


@dataclass(frozen=True)
class EntrySpec:
    required: tuple[str, ...]
    optional: tuple[str, ...]
    choices: dict[str, set[str]] = field(default_factory=dict)


SPECS = {
    "GOAL": EntrySpec(("Status", "Outcome", "Completion", "Progress", "Next"), ("Related",), {"Status": {"active", "completed", "parked"}}),
    "FOCUS": EntrySpec(("Status", "Purpose", "Current state", "Open questions"), ("Related",), {"Status": {"active", "parked"}}),
    "OUT": EntrySpec(("Date", "Type", "Result", "Effect"), ("Related direction", "Artifacts", "Rolls up", "Rolls up from"), {"Type": {"goal-progress", "goal-completion", "opportunistic", "maintenance"}}),
    "DEC": EntrySpec(("Status", "Date", "Applies to", "Decision", "Rationale", "Consequence"), ("Supersedes", "Superseded by", "Evidence"), {"Status": {"active", "superseded"}}),
    "GUIDE": EntrySpec(("Status", "Approved", "Scope", "Trigger", "Behavior", "Exceptions", "Evidence"), ("Supersedes", "Superseded by"), {"Status": {"active", "superseded"}}),
    "CAND": EntrySpec(("Status", "Scope", "Trigger", "Desired behavior", "Exceptions or uncertainty", "Evidence", "Proposed destination"), ("Disposition date", "Destination", "Rejection reason"), {"Status": {"watching", "proposed", "promoted", "rejected"}, "Proposed destination": {"guidance", "taste"}}),
    "TASTE": EntrySpec(("Status", "Approved", "Scope", "Example", "Preferred qualities", "Improvement", "Limits", "Evidence"), ("Supersedes", "Superseded by"), {"Status": {"active", "superseded"}}),
}
SECTION_PREFIXES = {
    "Goals": {"GOAL"}, "Focuses": {"FOCUS"}, "Outcomes": {"OUT"},
    "Decisions": {"DEC"}, "Guidance": {"GUIDE"}, "Candidates": {"CAND"},
    "Taste": {"TASTE"}, "Direction": {"GOAL", "FOCUS"},
}
COUNTERS = {
    "GOAL": ("DIRECTION.md", "next_goal_id"), "FOCUS": ("DIRECTION.md", "next_focus_id"),
    "OUT": ("OUTCOMES.md", "next_id"), "DEC": ("DECISIONS.md", "next_id"),
    "GUIDE": ("GUIDANCE.md", "next_id"), "CAND": ("CANDIDATES.md", "next_id"),
    "TASTE": ("TASTE.md", "next_id"),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "code": self.code, "path": self.path, "message": self.message}


@dataclass
class Entry:
    prefix: str
    number: int
    raw_id: str
    path: str
    section: str
    fields: dict[str, str]
    archived: bool

    @property
    def key(self) -> tuple[str, int]:
        return self.prefix, self.number


@dataclass
class Snapshot:
    inventory: dict[str, tuple[str, int, str]]
    data: dict[Path, bytes]


@dataclass
class ValidationResult:
    exit_code: int
    payload: dict[str, object]


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _timestamp(value: str) -> bool:
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def _ids(value: str) -> list[tuple[str, int]]:
    return [(match.group(1), int(match.group(2))) for match in ID_RE.finditer(value)]


def _bounded(value: str) -> str:
    if len(value) <= MAX_DETAIL_CHARS:
        return value
    return value[: MAX_DETAIL_CHARS - 16] + "...[truncated]"


class MemoryValidator:
    def __init__(self, owner: Path, config: Path, *, before_recheck: Callable[[], None] | None = None) -> None:
        self.owner = owner
        self.config = config
        self.before_recheck = before_recheck
        self.memory: Path | None = None
        self.namespace: str | None = None
        self.findings: list[Finding] = []
        self.entries: dict[tuple[str, int], list[Entry]] = {}
        self.counters: dict[tuple[str, str], int] = {}
        self.handoffs: dict[str, dict[str, str]] = {}
        self.handoff_edges: dict[str, str] = {}
        self.active_handoff: str | None = None
        self.captured_files = 0
        self.captured_bytes = 0

    def add(self, severity: str, code: str, path: str, message: str) -> None:
        self.findings.append(Finding(severity, code, _bounded(path), _bounded(message)))

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.owner).as_posix()
        except ValueError:
            return str(path)

    def run(self) -> ValidationResult:
        config_snap = self._capture_config()
        raw = config_snap.data.get(self.config)
        if raw is None:
            return self._finish_recheck(config_snap)
        parsed = self._parse_config(raw)
        if parsed is None:
            return self._finish_recheck(config_snap)
        memory = self._resolve_memory(parsed)
        if memory is None:
            return self._finish_recheck(config_snap)
        self.memory = memory
        memory_snap = self._capture_memory()
        snapshot = Snapshot(
            {**config_snap.inventory, **memory_snap.inventory},
            {**config_snap.data, **memory_snap.data},
        )
        self._validate_documents(memory_snap)
        self._validate_relationships()
        self._validate_handoffs()
        return self._finish_recheck(snapshot)

    def _capture_config(self) -> Snapshot:
        relative = self.rel(self.config)
        if not self.config.exists():
            self.add("error", "config-missing", relative, "hub-memory config is missing")
            return Snapshot({relative: ("missing", 0, "")}, {})
        if _reparse(self.config) or not self.config.is_file():
            self.add("error", "config-not-regular", relative, "config must be a regular non-reparse file")
        for ancestor in (self.config.parent.parent, self.config.parent):
            if ancestor.exists() and _reparse(ancestor):
                self.add("error", "config-ancestor-reparse", self.rel(ancestor), "config ancestor must not be a reparse point")
        return self._capture([self.config])

    def _capture(self, paths: list[Path]) -> Snapshot:
        inventory: dict[str, tuple[str, int, str]] = {}
        data: dict[Path, bytes] = {}
        for path in sorted(set(paths), key=self.rel):
            relative = self.rel(path)
            try:
                before = path.lstat()
            except FileNotFoundError:
                inventory[relative] = ("missing", 0, "")
                continue
            except OSError as exc:
                self.add("inconclusive", "stat-failed", relative, f"cannot inspect path: {exc}")
                continue
            if _reparse(path):
                inventory[relative] = ("reparse", before.st_size, "")
                continue
            if stat.S_ISDIR(before.st_mode):
                inventory[relative] = ("directory", 0, "")
                continue
            if not stat.S_ISREG(before.st_mode):
                inventory[relative] = ("other", before.st_size, "")
                continue
            self.captured_files += 1
            if self.captured_files > MAX_FILES:
                self.add("inconclusive", "file-limit", relative, f"file limit exceeded ({MAX_FILES})")
                break
            if before.st_size > MAX_FILE_BYTES:
                self.add("inconclusive", "file-size-limit", relative, f"file exceeds {MAX_FILE_BYTES} bytes")
                continue
            self.captured_bytes += before.st_size
            if self.captured_bytes > MAX_TOTAL_BYTES:
                self.add("inconclusive", "total-size-limit", relative, f"total bytes exceed {MAX_TOTAL_BYTES}")
                break
            try:
                raw = path.read_bytes()
                after = path.lstat()
            except OSError as exc:
                self.add("inconclusive", "read-failed", relative, f"cannot read file: {exc}")
                continue
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                self.add("inconclusive", "snapshot-changed", relative, "file changed during initial snapshot")
            inventory[relative] = ("file", len(raw), hashlib.sha256(raw).hexdigest())
            data[path] = raw
        return Snapshot(inventory, data)

    def _parse_config(self, raw: bytes) -> dict[str, object] | None:
        relative = self.rel(self.config)
        if raw.startswith(b"\xef\xbb\xbf"):
            self.add("error", "config-bom", relative, "config must be UTF-8 without BOM")
            return None
        if tomllib is None:
            self.add("inconclusive", "python-version", relative, "Python 3.11 or newer is required")
            return None
        try:
            config = tomllib.loads(raw.decode("utf-8"))
        except (UnicodeError, tomllib.TOMLDecodeError) as exc:
            self.add("error", "config-invalid", relative, f"invalid TOML: {exc}")
            return None
        version = config.get("schema_version")
        if version not in {"1.0", "1.1"}:
            self.add("error", "config-schema", relative, f"unsupported config schema: {version!r}")
            return None
        allowed = {"schema_version", "skill", "timezone", "paths"}
        if version == "1.1":
            allowed.add("namespace")
        unknown = sorted(set(config) - allowed)
        missing = sorted(allowed - set(config))
        if unknown:
            self.add("error", "config-unknown-key", relative, f"unknown config keys: {', '.join(unknown)}")
        if missing:
            self.add("error", "config-missing-key", relative, f"missing config keys: {', '.join(missing)}")
        if config.get("skill") != "hub-memory":
            self.add("error", "config-skill", relative, "skill must equal hub-memory")
        if not isinstance(config.get("timezone"), str) or not str(config.get("timezone", "")).strip():
            self.add("error", "config-timezone", relative, "timezone must be a non-empty string")
        if version == "1.0":
            if "namespace" in config:
                self.add("error", "config-namespace", relative, "namespace is invalid under config 1.0")
            self.namespace = "hub"
        else:
            if config.get("namespace") != "hub":
                self.add("error", "config-namespace", relative, 'config 1.1 requires namespace = "hub"')
            else:
                self.namespace = "hub"
        paths = config.get("paths")
        if not isinstance(paths, dict):
            self.add("error", "config-paths", relative, "paths must be a table")
            return None
        unknown_paths = sorted(set(paths) - {"memory"})
        if unknown_paths:
            self.add("error", "config-unknown-key", relative, f"unknown paths keys: {', '.join(unknown_paths)}")
        memory = paths.get("memory")
        if not isinstance(memory, str) or not memory.strip():
            self.add("error", "config-memory", relative, "paths.memory must be a non-empty string")
            return None
        return config

    def _resolve_memory(self, config: dict[str, object]) -> Path | None:
        paths = config["paths"]
        assert isinstance(paths, dict)
        value = paths["memory"]
        assert isinstance(value, str)
        relative = Path(value)
        if relative.is_absolute():
            self.add("error", "memory-absolute", self.rel(self.config), "paths.memory must be relative")
            return None
        candidate = self.owner / relative
        resolved = candidate.resolve(strict=False)
        if not _inside(resolved, self.owner):
            self.add("error", "memory-escape", self.rel(self.config), "configured memory path escapes owner root")
            return None
        current = self.owner
        for part in relative.parts:
            if part in {"", "."}:
                continue
            current /= part
            if current.exists() and _reparse(current):
                self.add("error", "memory-reparse", self.rel(current), "memory path must not cross a reparse point")
                return None
        return resolved

    def _capture_memory(self) -> Snapshot:
        assert self.memory is not None
        root = self.memory
        relative = self.rel(root)
        if not root.exists():
            self.add("error", "memory-missing", relative, "configured memory root is missing")
            return Snapshot({relative: ("missing", 0, "")}, {})
        if _reparse(root) or not root.is_dir():
            self.add("error", "memory-not-directory", relative, "memory root must be a regular non-reparse directory")
            return self._capture([root])
        try:
            root_items = sorted(root.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            self.add("inconclusive", "list-failed", relative, f"cannot list memory root: {exc}")
            return Snapshot({}, {})
        paths = [root]
        allowed_files = set(REQUIRED_RECORDS) | {"TASTE.md"}
        for item in root_items:
            paths.append(item)
            item_rel = self.rel(item)
            if REMNANT_RE.fullmatch(item.name):
                self.add("error", "replacement-remnant", item_rel, "interrupted replacement remnant")
            elif item.name in allowed_files:
                if _reparse(item) or not item.is_file():
                    self.add("error", "record-not-regular", item_rel, "record must be a regular non-reparse file")
            elif item.name in OPTIONAL_DIRS:
                if _reparse(item) or not item.is_dir():
                    self.add("error", "directory-not-regular", item_rel, "optional directory must be a regular non-reparse directory")
                    continue
                try:
                    children = sorted(item.iterdir(), key=lambda child: child.name)
                except OSError as exc:
                    self.add("inconclusive", "list-failed", item_rel, f"cannot list directory: {exc}")
                    continue
                for child in children:
                    paths.append(child)
                    child_rel = self.rel(child)
                    if REMNANT_RE.fullmatch(child.name):
                        self.add("error", "replacement-remnant", child_rel, "interrupted replacement remnant")
                    elif _reparse(child):
                        self.add("error", "item-reparse", child_rel, "memory item must not be a reparse point")
                    elif not child.is_file():
                        self.add("error", "nested-item", child_rel, "only direct files are allowed")
                    elif item.name == "handoffs" and not HANDOFF_NAME_RE.fullmatch(child.name):
                        self.add("error", "handoff-name", child_rel, "invalid handoff filename")
                    elif item.name == "archive" and not ARCHIVE_NAME_RE.fullmatch(child.name):
                        self.add("error", "archive-name", child_rel, "invalid archive filename")
            else:
                self.add("error", "foreign-item", item_rel, "foreign item in memory root")
        return self._capture(paths)

    def _frontmatter(
        self, path: Path, raw: bytes, allowed: set[str], required: set[str]
    ) -> tuple[dict[str, str], list[str]] | None:
        relative = self.rel(path)
        if raw.startswith(b"\xef\xbb\xbf"):
            self.add("error", "frontmatter-bom", relative, "UTF-8 BOM is not allowed")
            return None
        normalized = raw.replace(b"\r\n", b"\n")
        if b"\r" in normalized:
            self.add("error", "bare-cr", relative, "bare CR line endings are invalid")
            return None
        try:
            lines = normalized.decode("utf-8").split("\n")
        except UnicodeDecodeError as exc:
            self.add("error", "utf8", relative, f"invalid UTF-8: {exc}")
            return None
        if not lines or lines[0] != "---":
            self.add("error", "frontmatter-open", relative, "frontmatter must begin with exact ---")
            return None
        try:
            close = lines.index("---", 1)
        except ValueError:
            self.add("error", "frontmatter-close", relative, "frontmatter closing --- is missing")
            return None
        metadata: dict[str, str] = {}
        for number, line in enumerate(lines[1:close], 2):
            if not line or line[:1].isspace() or ":" not in line:
                self.add("error", "frontmatter-line", relative, f"invalid flat frontmatter line {number}")
                continue
            key, value = line.split(":", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
                self.add("error", "frontmatter-key", relative, f"invalid key on line {number}")
                continue
            if key in metadata:
                self.add("error", "frontmatter-duplicate", relative, f"duplicate key: {key}")
                continue
            scalar = value.strip()
            if scalar.startswith(("[", "{")):
                self.add("error", "frontmatter-collection", relative, f"collections are not allowed: {key}")
            metadata[key] = scalar
        for key in sorted(required - set(metadata)):
            self.add("error", "frontmatter-missing", relative, f"missing key: {key}")
        if metadata.get("schema_version") == '"1.0"':
            for key in sorted(set(metadata) - allowed):
                self.add("warning", "frontmatter-unknown", relative, f"unknown key: {key}")
        return metadata, lines[close + 1 :]

    def _common(self, path: Path, metadata: dict[str, str], expected_type: str) -> None:
        relative = self.rel(path)
        if metadata.get("type") != expected_type:
            self.add("error", "record-type", relative, f"type must equal {expected_type}")
        if metadata.get("schema_version") != '"1.0"':
            self.add("error", "record-schema", relative, 'schema_version must equal "1.0"')
        if "updated" in metadata and not DATE_RE.fullmatch(metadata["updated"]):
            self.add("error", "record-date", relative, "updated must be YYYY-MM-DD")

    def _sections(self, path: Path, body: list[str], required: tuple[str, ...]) -> dict[str, list[str]]:
        relative = self.rel(path)
        found: dict[str, list[int]] = {}
        for index, line in enumerate(body):
            if line.startswith("## "):
                found.setdefault(line[3:], []).append(index)
        for heading in required:
            count = len(found.get(heading, []))
            if count != 1:
                self.add("error", "heading-count", relative, f"## {heading} must occur once; found {count}")
        for heading in sorted(set(found) - set(required)):
            self.add("warning", "heading-unknown", relative, f"unknown section: ## {heading}")
        ordered = sorted((positions[0], heading) for heading, positions in found.items())
        result: dict[str, list[str]] = {}
        for offset, (start, heading) in enumerate(ordered):
            end = ordered[offset + 1][0] if offset + 1 < len(ordered) else len(body)
            result[heading] = body[start + 1 : end]
        return result

    def _validate_documents(self, snapshot: Snapshot) -> None:
        assert self.memory is not None
        for name, (expected_type, headings) in REQUIRED_RECORDS.items():
            path = self.memory / name
            raw = snapshot.data.get(path)
            if raw is None:
                self.add("error", "record-missing", self.rel(path), "required record is missing or unreadable")
                continue
            allowed = {"type", "schema_version", "updated", "next_id", "next_goal_id", "next_focus_id"}
            required = {"type", "schema_version", "updated"}
            if name == "DIRECTION.md":
                required.update({"next_goal_id", "next_focus_id"})
            elif name in {"OUTCOMES.md", "DECISIONS.md", "GUIDANCE.md", "CANDIDATES.md"}:
                required.add("next_id")
            parsed = self._frontmatter(path, raw, allowed, required)
            if parsed is None:
                continue
            metadata, body = parsed
            self._common(path, metadata, expected_type)
            self._read_counters(path, metadata)
            sections = self._sections(path, body, headings)
            if name == "CONTEXT.md":
                self._active_pointer(path, sections.get("Active Handoff", []))
            for section, prefixes in SECTION_PREFIXES.items():
                if section in sections:
                    self._entry_section(path, section, sections[section], prefixes, False)

        taste = self.memory / "TASTE.md"
        if taste in snapshot.data:
            parsed = self._frontmatter(
                taste,
                snapshot.data[taste],
                {"type", "schema_version", "updated", "next_id"},
                {"type", "schema_version", "updated", "next_id"},
            )
            if parsed:
                metadata, body = parsed
                self._common(taste, metadata, "hub-memory-taste")
                self._read_counters(taste, metadata)
                sections = self._sections(taste, body, ("Taste",))
                self._entry_section(taste, "Taste", sections.get("Taste", []), {"TASTE"}, False)

        archive_dir = self.memory / "archive"
        for path in sorted((path for path in snapshot.data if path.parent == archive_dir), key=lambda item: item.name):
            self._archive(path, snapshot.data[path])
        handoff_dir = self.memory / "handoffs"
        for path in sorted((path for path in snapshot.data if path.parent == handoff_dir), key=lambda item: item.name):
            self._handoff(path, snapshot.data[path])
        self._ids_and_counters()

    def _read_counters(self, path: Path, metadata: dict[str, str]) -> None:
        for key in {"next_id", "next_goal_id", "next_focus_id"} & set(metadata):
            try:
                value = int(metadata[key])
            except ValueError:
                self.add("error", "counter-type", self.rel(path), f"{key} must be an integer")
                continue
            if value < 1:
                self.add("error", "counter-value", self.rel(path), f"{key} must be positive")
            self.counters[(path.name, key)] = value

    def _entry_section(
        self,
        path: Path,
        section: str,
        lines: list[str],
        prefixes: set[str],
        archived: bool,
    ) -> None:
        relative = self.rel(path)
        starts = [index for index, line in enumerate(lines) if line.startswith("### ")]
        meaningful = [line for line in lines if line.strip()]
        if not starts:
            if meaningful not in ([], ["_None._"]):
                self.add("error", "section-body", relative, f"{section} contains non-entry content")
            return
        if any(line.strip() for line in lines[: starts[0]]):
            self.add("error", "section-prefix", relative, f"{section} has content before its first entry")
        last: dict[str, int] = {}
        for offset, start in enumerate(starts):
            end = starts[offset + 1] if offset + 1 < len(starts) else len(lines)
            heading = lines[start]
            match = ID_HEADING_RE.fullmatch(heading)
            if match is None:
                self.add("error", "id-heading", relative, f"invalid entry heading: {heading}")
                continue
            prefix, digits, title = match.groups()
            number = int(digits)
            raw_id = f"{prefix}-{digits}"
            if prefix not in prefixes:
                self.add("error", "id-prefix", relative, f"{raw_id} is invalid in {section}")
            if number <= last.get(prefix, -1):
                self.add("error", "id-order", relative, f"{raw_id} is not ascending")
            last[prefix] = number
            if not title.strip():
                self.add("error", "id-title", relative, f"{raw_id} requires a title")
            fields: dict[str, str] = {}
            for line in lines[start + 1 : end]:
                if not line.strip():
                    continue
                field_match = FIELD_RE.fullmatch(line)
                if not field_match:
                    self.add("error", "entry-line", relative, f"{raw_id} has invalid line: {line}")
                    continue
                label, value = field_match.groups()
                if label in fields:
                    self.add("error", "field-duplicate", relative, f"{raw_id} duplicates {label}")
                else:
                    fields[label] = value.strip()
            spec = SPECS[prefix]
            known = set(spec.required) | set(spec.optional)
            for label in spec.required:
                if not fields.get(label):
                    self.add("error", "field-missing", relative, f"{raw_id} requires {label}")
            for label in sorted(set(fields) - known):
                self.add("warning", "field-unknown", relative, f"{raw_id} has unknown field {label}")
            for label, choices in spec.choices.items():
                if label in fields and fields[label] not in choices:
                    self.add("error", "field-value", relative, f"{raw_id} has invalid {label}: {fields[label]}")
            if any(QUALIFIED_ID_RE.search(value) for value in fields.values()):
                self.add("error", "qualified-id", relative, f"{raw_id} uses a reserved qualified ID")
            entry = Entry(prefix, number, raw_id, relative, section, fields, archived)
            self.entries.setdefault(entry.key, []).append(entry)

    def _archive(self, path: Path, raw: bytes) -> None:
        allowed = {"type", "schema_version", "year", "updated"}
        parsed = self._frontmatter(path, raw, allowed, allowed)
        if not parsed:
            return
        metadata, body = parsed
        self._common(path, metadata, "hub-memory-archive")
        match = ARCHIVE_NAME_RE.fullmatch(path.name)
        if not match or metadata.get("year") != match.group(1):
            self.add("error", "archive-year", self.rel(path), "archive year must match filename")
        headings = ("Direction", "Outcomes", "Decisions", "Guidance", "Candidates", "Taste")
        sections = self._sections(path, body, headings)
        for section, prefixes in SECTION_PREFIXES.items():
            if section in sections:
                self._entry_section(path, section, sections[section], prefixes, True)

    def _handoff(self, path: Path, raw: bytes) -> None:
        allowed = {"type", "schema_version", "created", "objective", "supersedes", "retired"}
        required = {"type", "schema_version", "created", "objective"}
        parsed = self._frontmatter(path, raw, allowed, required)
        if not parsed:
            return
        metadata, body = parsed
        self._common(path, metadata, "hub-memory-handoff")
        relative = self.rel(path)
        if not _timestamp(metadata.get("created", "")):
            self.add("error", "handoff-created", relative, "created must be timezone-aware")
        if not metadata.get("objective", ""):
            self.add("error", "handoff-objective", relative, "objective must be non-empty")
        if "retired" in metadata and not _timestamp(metadata["retired"]):
            self.add("error", "handoff-retired", relative, "retired must be timezone-aware")
        sections = self._sections(
            path,
            body,
            (
                "Objective",
                "Exact State",
                "Completed",
                "Unresolved Reasoning",
                "Artifacts",
                "Next Actions",
                "Validation",
            ),
        )
        self._handoff_content(path, sections)
        self._workspace_anchor(path, sections.get("Exact State", []))
        self.handoffs[path.name] = metadata
        supersedes = metadata.get("supersedes")
        if not supersedes:
            return
        if LINK_RE.search(supersedes):
            self.add("error", "handoff-supersedes-format", relative, "supersedes must be a plain relative path")
            return
        target = (path.parent / supersedes).resolve(strict=False)
        if target.parent != path.parent.resolve() or target.name == path.name:
            self.add("error", "handoff-supersedes-path", relative, "supersedes must name another direct packet")
            return
        self.handoff_edges[path.name] = target.name

    def _handoff_content(self, path: Path, sections: dict[str, list[str]]) -> None:
        relative = self.rel(path)
        for heading in (
            "Objective",
            "Exact State",
            "Completed",
            "Unresolved Reasoning",
            "Artifacts",
            "Next Actions",
            "Validation",
        ):
            meaningful = [line.strip() for line in sections.get(heading, []) if line.strip()]
            if not meaningful:
                self.add(
                    "error",
                    "handoff-section-empty",
                    relative,
                    f"{heading} requires content",
                )

        for heading, required in HANDOFF_REQUIRED_FIELDS.items():
            fields: dict[str, list[str]] = {}
            for line in sections.get(heading, []):
                match = HANDOFF_FIELD_RE.fullmatch(line)
                if match:
                    label, value = match.groups()
                    fields.setdefault(label, []).append(value.strip())
            for label in required:
                values = fields.get(label, [])
                if len(values) != 1 or not values[0]:
                    self.add(
                        "error",
                        "handoff-field",
                        relative,
                        f"{heading} requires one nonempty {label} field",
                    )

        next_lines = [
            line.strip() for line in sections.get("Next Actions", []) if line.strip()
        ]
        if next_lines and not re.fullmatch(r"1[.]\s+.+", next_lines[0]):
            self.add(
                "error",
                "handoff-first-action",
                relative,
                "Next Actions must begin with one exact numbered first action",
            )

        validation_fields: dict[str, str] = {}
        for line in sections.get("Validation", []):
            match = HANDOFF_FIELD_RE.fullmatch(line)
            if match:
                validation_fields.setdefault(match.group(1), match.group(2).strip())
        self_check = validation_fields.get("Cold-resume self-check", "")
        if self_check and not self_check.casefold().startswith("passed"):
            self.add(
                "error",
                "handoff-self-check",
                relative,
                "cold-resume self-check must pass before packet creation",
            )

    def _workspace_anchor(self, path: Path, lines: list[str]) -> None:
        relative = self.rel(path)
        candidates = [
            line for line in lines if line.lstrip().startswith(WORKSPACE_ANCHOR)
        ]
        if len(candidates) > 1:
            self.add(
                "error",
                "workspace-anchor-count",
                relative,
                "Exact State permits at most one workspace anchor",
            )
        for line in candidates:
            if not line.startswith(WORKSPACE_ANCHOR):
                self.add(
                    "error",
                    "workspace-anchor-format",
                    relative,
                    "workspace anchor line must be unindented with the exact label",
                )
                continue
            value = line[len(WORKSPACE_ANCHOR) :].strip()
            posix = PurePosixPath(value)
            windows = PureWindowsPath(value)
            invalid = (
                not value
                or chr(92) in value
                or "://" in value
                or value.startswith(("[", "<"))
                or posix.is_absolute()
                or windows.is_absolute()
                or bool(windows.drive)
                or ".." in posix.parts
            )
            if invalid:
                self.add(
                    "error",
                    "workspace-anchor-path",
                    relative,
                    "workspace anchor must be one portable owner-relative path",
                )

    def _active_pointer(self, path: Path, lines: list[str]) -> None:
        meaningful = [line.strip() for line in lines if line.strip()]
        if meaningful in ([], ["_None._"]):
            return
        links = [link for line in meaningful for link in LINK_RE.findall(line)]
        if len(meaningful) != 1 or len(links) != 1:
            self.add("error", "active-handoff-count", self.rel(path), "Active Handoff requires exactly one link")
            return
        assert self.memory is not None
        target = (self.memory / links[0][1]).resolve(strict=False)
        handoff_root = (self.memory / "handoffs").resolve(strict=False)
        if target.parent != handoff_root or not HANDOFF_NAME_RE.fullmatch(target.name):
            self.add("error", "active-handoff-path", self.rel(path), "active handoff must be one direct handoffs/ packet")
            return
        self.active_handoff = target.name

    def _ids_and_counters(self) -> None:
        for key, entries in sorted(self.entries.items()):
            if len(entries) > 1:
                self.add("error", "id-duplicate", ", ".join(sorted(entry.path for entry in entries)), f"{key[0]}-{key[1]:04d} is duplicated")
        maxima: dict[str, int] = {}
        for prefix, number in self.entries:
            maxima[prefix] = max(maxima.get(prefix, 0), number)
        for prefix, maximum in sorted(maxima.items()):
            filename, key = COUNTERS[prefix]
            counter = self.counters.get((filename, key))
            if counter is None:
                self.add("error", "counter-missing", filename, f"{key} is required for {prefix} IDs")
            elif counter <= maximum:
                self.add("error", "counter-regression", filename, f"{key} must exceed {prefix}-{maximum:04d}")

    def _one(self, key: tuple[str, int]) -> Entry | None:
        entries = self.entries.get(key, [])
        return entries[0] if len(entries) == 1 else None

    def _target(self, source: Entry, key: tuple[str, int], label: str) -> Entry | None:
        target = self._one(key)
        if target is None:
            self.add("error", "id-target", source.path, f"{source.raw_id} {label} references missing {key[0]}-{key[1]:04d}")
        return target

    def _validate_relationships(self) -> None:
        unique = [entries[0] for _, entries in sorted(self.entries.items()) if len(entries) == 1]
        for entry in unique:
            if entry.prefix == "OUT":
                for key in _ids(entry.fields.get("Rolls up", "")):
                    if key[0] == "OUT":
                        parent = self._target(entry, key, "Rolls up")
                        if parent and entry.key not in _ids(parent.fields.get("Rolls up from", "")):
                            self.add("error", "rollup-reciprocal", entry.path, f"{entry.raw_id} is not reciprocated by {parent.raw_id}")
                for key in _ids(entry.fields.get("Rolls up from", "")):
                    if key[0] == "OUT":
                        child = self._target(entry, key, "Rolls up from")
                        if child and entry.key not in _ids(child.fields.get("Rolls up", "")):
                            self.add("error", "rollup-reciprocal", entry.path, f"{entry.raw_id} child {child.raw_id} does not point back")
            if entry.prefix in {"DEC", "GUIDE", "TASTE"}:
                for key in _ids(entry.fields.get("Supersedes", "")):
                    if key[0] == entry.prefix:
                        old = self._target(entry, key, "Supersedes")
                        if old and entry.key not in _ids(old.fields.get("Superseded by", "")):
                            self.add("error", "supersession-reciprocal", entry.path, f"{old.raw_id} does not point back to {entry.raw_id}")
                for key in _ids(entry.fields.get("Superseded by", "")):
                    if key[0] == entry.prefix:
                        new = self._target(entry, key, "Superseded by")
                        if new and entry.key not in _ids(new.fields.get("Supersedes", "")):
                            self.add("error", "supersession-reciprocal", entry.path, f"{new.raw_id} does not supersede {entry.raw_id}")
            if entry.prefix == "CAND" and entry.fields.get("Status") == "promoted":
                targets = _ids(entry.fields.get("Destination", ""))
                if len(targets) != 1 or targets[0][0] not in {"GUIDE", "TASTE"} or self._one(targets[0]) is None:
                    self.add("error", "candidate-destination", entry.path, f"{entry.raw_id} requires one resolving GUIDE or TASTE destination")

    def _validate_handoffs(self) -> None:
        for source, target in sorted(self.handoff_edges.items()):
            if target not in self.handoffs:
                self.add("error", "handoff-supersedes-missing", source, f"missing supersedes target: {target}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                self.add("error", "handoff-cycle", node, "handoff supersedes chain is cyclic")
                return
            if node in visited:
                return
            visiting.add(node)
            target = self.handoff_edges.get(node)
            if target in self.handoffs:
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for node in sorted(self.handoffs):
            visit(node)
        if self.active_handoff:
            metadata = self.handoffs.get(self.active_handoff)
            if metadata is None:
                self.add("error", "active-handoff-missing", "CONTEXT.md", f"active handoff does not resolve: {self.active_handoff}")
            elif "retired" in metadata:
                self.add("error", "active-handoff-retired", self.active_handoff, "active handoff must not be retired")

    def _current_inventory(self) -> dict[str, tuple[str, int, str]] | None:
        paths = [self.config]
        if self.memory is not None:
            paths.append(self.memory)
            try:
                items = sorted(self.memory.iterdir(), key=lambda item: item.name)
            except OSError:
                return None
            for item in items:
                paths.append(item)
                if item.name in OPTIONAL_DIRS and item.is_dir() and not _reparse(item):
                    try:
                        paths.extend(sorted(item.iterdir(), key=lambda child: child.name))
                    except OSError:
                        return None
        probe = MemoryValidator(self.owner, self.config)
        snapshot = probe._capture(paths)
        if any(item.severity == "inconclusive" for item in probe.findings):
            return None
        return snapshot.inventory

    def _finish_recheck(self, snapshot: Snapshot) -> ValidationResult:
        if self.before_recheck:
            self.before_recheck()
        current = self._current_inventory()
        if current is None:
            self.add("inconclusive", "snapshot-recheck-failed", self.rel(self.memory or self.config), "could not recheck snapshot")
        elif current != snapshot.inventory:
            self.add("inconclusive", "snapshot-changed", self.rel(self.memory or self.config), "inventory or hashes changed during validation")
        return self._finish()

    def _finish(self) -> ValidationResult:
        rank = {"inconclusive": 0, "error": 1, "warning": 2}
        ordered = sorted(self.findings, key=lambda item: (rank[item.severity], item.path, item.code, item.message))
        omitted = max(0, len(ordered) - MAX_FINDINGS)
        shown = ordered[:MAX_FINDINGS]
        if any(item.severity == "inconclusive" for item in ordered):
            code, status_value = EXIT_INCONCLUSIVE, "inconclusive"
        elif any(item.severity == "error" for item in ordered):
            code, status_value = EXIT_INVALID, "invalid"
        else:
            code, status_value = EXIT_VALID, "valid"
        payload: dict[str, object] = {
            "schema": SCHEMA_ID,
            "status": status_value,
            "owner_root": str(self.owner),
            "config": str(self.config),
            "memory_root": str(self.memory) if self.memory else None,
            "namespace": self.namespace,
            "limits": {
                "max_findings": MAX_FINDINGS,
                "max_detail_chars": MAX_DETAIL_CHARS,
                "max_files": MAX_FILES,
                "max_file_bytes": MAX_FILE_BYTES,
                "max_total_bytes": MAX_TOTAL_BYTES,
            },
            "findings": [item.as_dict() for item in shown],
            "omitted_findings": omitted,
        }
        return ValidationResult(code, payload)


def invocation_result(message: str, owner: Path | None = None) -> ValidationResult:
    payload: dict[str, object] = {
        "schema": SCHEMA_ID,
        "status": "invocation-error",
        "owner_root": str(owner) if owner else None,
        "config": None,
        "memory_root": None,
        "namespace": None,
        "limits": {
            "max_findings": MAX_FINDINGS,
            "max_detail_chars": MAX_DETAIL_CHARS,
            "max_files": MAX_FILES,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_total_bytes": MAX_TOTAL_BYTES,
        },
        "findings": [Finding("error", "invocation", "", message).as_dict()],
        "omitted_findings": 0,
    }
    return ValidationResult(EXIT_INVOCATION, payload)


def validate_memory(
    owner_root: Path,
    config_path: Path | None = None,
    *,
    before_recheck: Callable[[], None] | None = None,
) -> ValidationResult:
    if sys.version_info < (3, 11):
        return invocation_result("validate_memory.py requires Python 3.11 or newer")
    try:
        owner = owner_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return invocation_result("owner root does not exist", owner_root)
    if not owner.is_dir():
        return invocation_result("owner root must be a directory", owner)
    expected_parent = owner / ".agents" / "config"
    expected = expected_parent / "hub-memory.toml"
    if config_path is None:
        config = expected
    else:
        supplied = config_path if config_path.is_absolute() else Path.cwd() / config_path
        supplied = supplied.absolute()
        if supplied.name != "hub-memory.toml" or supplied.parent != expected_parent:
            return invocation_result("explicit config must be named hub-memory.toml directly beneath <owner-root>/.agents/config/", owner)
        try:
            if supplied.resolve(strict=False).parent != expected_parent.resolve(strict=False):
                return invocation_result("explicit config escapes <owner-root>/.agents/config/", owner)
        except (OSError, RuntimeError):
            return invocation_result("explicit config path cannot be resolved", owner)
        config = supplied
    return MemoryValidator(owner, config, before_recheck=before_recheck).run()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only structural validation for one configured hub-memory namespace.",
        epilog="Exit codes: 0 valid, 1 stable invalid namespace, 2 invocation error, 3 runtime or inconclusive.",
    )
    parser.add_argument(
        "--owner-root",
        required=True,
        type=Path,
        help="Owner (hub) root containing .agents/config/hub-memory.toml.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional exact <owner-root>/.agents/config/hub-memory.toml path.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Bounded output format (default: text).",
    )
    return parser.parse_args(argv)


def render_text(payload: dict[str, object]) -> str:
    lines = [f"{str(payload['status']).upper()} hub-memory", f"owner: {payload['owner_root']}"]
    if payload.get("memory_root"):
        lines.append(f"memory: {payload['memory_root']}")
    findings = payload.get("findings", [])
    assert isinstance(findings, list)
    for raw in findings:
        assert isinstance(raw, dict)
        location = f" {raw['path']}:" if raw.get("path") else ""
        lines.append(f"- {str(raw['severity']).upper()} {raw['code']}:{location} {raw['message']}")
    omitted = int(payload.get("omitted_findings", 0))
    if omitted:
        lines.append(f"- {omitted} additional finding(s) omitted")
    if not findings:
        lines.append("- no structural findings")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate_memory(args.owner_root, args.config)
    print(json.dumps(result.payload, indent=2, sort_keys=True) if args.format == "json" else render_text(result.payload))
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
