from __future__ import annotations

import hashlib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = PACKAGE_ROOT / "templates"
RECORD_NAMES = (
    "CANDIDATES.md",
    "CONTEXT.md",
    "DECISIONS.md",
    "DIRECTION.md",
    "GUIDANCE.md",
    "OUTCOMES.md",
)


def make_hub(
    base: Path,
    *,
    config_version: str = "1.1",
    memory_path: str = ".ai-hub/memory",
    namespace: str | None = "hub",
) -> tuple[Path, Path]:
    owner = base / "hub"
    config_dir = owner / ".agents" / "config"
    config_dir.mkdir(parents=True)
    write_config(
        owner,
        config_version=config_version,
        memory_path=memory_path,
        namespace=namespace,
    )
    memory = owner / memory_path
    memory.mkdir(parents=True)
    for name in RECORD_NAMES:
        text = (TEMPLATE_ROOT / name).read_text(encoding="utf-8")
        (memory / name).write_text(
            text.replace("YYYY-MM-DD", "2026-08-31"),
            encoding="utf-8",
            newline="",
        )
    return owner, memory


def write_config(
    owner: Path,
    *,
    config_version: str,
    memory_path: str,
    namespace: str | None,
    extra: str = "",
) -> Path:
    config = owner / ".agents" / "config" / "hub-memory.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'schema_version = "{config_version}"',
        'skill = "hub-memory"',
    ]
    if namespace is not None:
        lines.append(f'namespace = "{namespace}"')
    lines.extend(
        [
            'timezone = "America/Los_Angeles"',
            "",
            "[paths]",
            f'memory = "{memory_path}"',
        ]
    )
    if extra:
        lines.extend(["", extra])
    config.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="")
    return config


def replace_section(path: Path, heading: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.index(heading) + len(heading)
    next_heading = text.find("\n## ", start)
    end = len(text) if next_heading == -1 else next_heading
    replacement = f"{heading}\n\n{content.rstrip()}\n"
    path.write_text(text[: start - len(heading)] + replacement + text[end:], encoding="utf-8", newline="")


def set_counter(path: Path, key: str, value: int) -> None:
    text = path.read_text(encoding="utf-8")
    old = next(line for line in text.splitlines() if line.startswith(f"{key}:"))
    path.write_text(text.replace(old, f"{key}: {value}", 1), encoding="utf-8", newline="")


def outcome_entry(
    number: int,
    *,
    rolls_up: str = "",
    rolls_up_from: str = "",
) -> str:
    optional = ""
    if rolls_up:
        optional += f"\n- Rolls up: {rolls_up}"
    if rolls_up_from:
        optional += f"\n- Rolls up from: {rolls_up_from}"
    return (
        f"### OUT-{number:04d} — result {number}\n"
        "- Date: 2026-08-31\n"
        "- Type: opportunistic\n"
        f"- Result: result {number}\n"
        "- Effect: useful"
        f"{optional}"
    )


def decision_entry(
    number: int,
    *,
    supersedes: str = "",
    superseded_by: str = "",
) -> str:
    optional = ""
    if supersedes:
        optional += f"\n- Supersedes: {supersedes}"
    if superseded_by:
        optional += f"\n- Superseded by: {superseded_by}"
    return (
        f"### DEC-{number:04d} — decision {number}\n"
        "- Status: active\n"
        "- Date: 2026-08-31\n"
        "- Applies to: hub\n"
        f"- Decision: choice {number}\n"
        "- Rationale: reason\n"
        "- Consequence: follow it"
        f"{optional}"
    )


def handoff_text(
    *,
    objective: str = "Continue",
    supersedes: str = "",
    retired: bool = False,
    workspace_anchor: str = "",
) -> str:
    optional = ""
    if supersedes:
        optional += f"supersedes: {supersedes}\n"
    if retired:
        optional += "retired: 2026-08-31T11:00:00-07:00\n"
    exact_state = (
        "- Trusted state: Ready.\n"
        "- Uncertainty: None\n"
        "- Stopping point: Ready to continue."
    )
    if workspace_anchor:
        exact_state += f"\n- Workspace anchor: {workspace_anchor}"
    return (
        "---\n"
        "type: hub-memory-handoff\n"
        'schema_version: "1.0"\n'
        "created: 2026-08-31T10:00:00-07:00\n"
        f"objective: {objective}\n"
        f"{optional}"
        "---\n\n"
        "# Handoff\n\n"
        "## Objective\n\n"
        "- Objective: Continue.\n"
        "- Success condition: The continuation is complete.\n\n"
        f"## Exact State\n\n{exact_state}\n\n"
        "## Completed\n\n_None._\n\n"
        "## Unresolved Reasoning\n\n"
        "- Open questions: None\n"
        "- Unverified assumptions: None\n"
        "- Rejected paths: None\n"
        "- Conversation-only continuity: None\n\n"
        "## Artifacts\n\n"
        "- Authoritative resources: None\n"
        "- Repository state: None\n"
        "- Environment constraints: None\n"
        "- Hazards: None\n\n"
        "## Next Actions\n\n"
        "1. Continue.\n"
        "- Acceptance check: The continuation succeeds.\n\n"
        "## Validation\n\n"
        "- Checks run: Structural fixture check.\n"
        "- Material failures: None\n"
        "- Cold-resume self-check: passed — the required continuation facts are present.\n"
    )


def archive_text(year: str = "2025", content: str = "") -> str:
    sections = []
    for heading in ("Direction", "Outcomes", "Decisions", "Guidance", "Candidates", "Taste"):
        body = content if heading == "Outcomes" and content else "_None._"
        sections.append(f"## {heading}\n\n{body}")
    return (
        "---\n"
        "type: hub-memory-archive\n"
        'schema_version: "1.0"\n'
        f"year: {year}\n"
        "updated: 2026-08-31\n"
        "---\n\n"
        "# Archive\n\n"
        + "\n\n".join(sections)
        + "\n"
    )


def content_snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    result: dict[str, tuple[bytes, int]] = {}
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        result[path.relative_to(root).as_posix()] = (path.read_bytes(), path.stat().st_mtime_ns)
    return result


def digest_snapshot(root: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256(raw).hexdigest()
        for relative, (raw, _) in content_snapshot(root).items()
    }
