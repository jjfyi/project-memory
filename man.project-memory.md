# project-memory(7)

## Name

`project-memory` — progressive filesystem-first memory for one independent project workspace.

## Synopsis

Invoke the skill in natural language:

```text
Initialize project memory here.
Resume the project context.
Save our progress.
Create a detailed handoff.
Check and maintain the memory records.
Review the learning candidates.
```

## Description

`project-memory` keeps current continuation state short while preserving durable direction, outcomes, decisions, approved guidance, and evidence awaiting review. It records completed state changes at the useful level rather than searches, retries, draft iterations, or transcripts.

The version 1 memory model manages one independent project namespace. Task management, workstream orchestration, daily, weekly, or monthly notes or reporting, migration, and cross-namespace routing or roll-up are outside its scope.

Operation routing is intent-based after the skill loads. Matching is case-insensitive and permits ordinary polite or temporal framing. Negated, genuinely hypothetical, explanatory, and deliberative language is handled before explicit operation names and inferred session-level intent. “Can you save our progress?” executes; “Should we save?” offers only. Saving a particular file, draft, document, image, artifact, or named path is not a memory operation.

## Operations

| Operation | Purpose | Typical request |
|---|---|---|
| `init` | Safely create config and six empty records | “Set up project memory.” |
| `resume` | Recover current direction and next action | “Where were we?” |
| `save` | Preserve meaningful progress and condense working state | “Save our progress.” |
| `handoff` | Create a detailed explicit continuation packet | “Create a handoff for a new session.” |
| `maintain` | Check drift, repair structure, review learning, compact, or archive | “Clean up and maintain memory.” |

`maintain` supports a read-only check. Meaning-changing compaction, archival, promotion, rejection, supersession, and uncertain completion require approval.

Every handoff, including a combined save plus handoff, uses a reconciliation-embedded save mode. It applies ordinary save classification and guards, but preserves the old active pointer until durable records, non-pointer context, and the new inactive packet validate. Pointer activation makes the new packet active; the uniquely replaced packet is then retired once. Standalone save absorbs, clears, and retires an active packet only when bounded evidence establishes consumption and accounts for every live item; otherwise it preserves the pointer and packet while allowing unrelated saving to proceed.

An explicit packet-only request skips progressive-record reconciliation except for the required context-pointer mutation and reports that limitation. Replacing an existing active packet still requires explicit supersession authority. A failed activation leaves the new packet inactive for a byte-matching retry rather than silently creating another packet.

## Files

The configured memory root contains six required files:

| File | Responsibility |
|---|---|
| `CONTEXT.md` | Current continuation state only |
| `DIRECTION.md` | Goals, focuses, criteria, and progress frontiers |
| `OUTCOMES.md` | Meaningful completed state changes |
| `DECISIONS.md` | Durable choices, requirements, and constraints |
| `GUIDANCE.md` | Explicitly approved reusable behavior |
| `CANDIDATES.md` | Correction evidence awaiting review |

Optional resources appear only when needed: `TASTE.md`, `handoffs/`, and `archive/`.

## Configuration

Active configuration is repo-local at `.project-memory/project-memory.toml`. Ordinary operations stop if it is absent; `init` is the only bootstrap operation. See [references/config.md](references/config.md) for the field catalog and copy-ready example.

Config and all memory records live directly in `.project-memory/`. The config is `.project-memory/project-memory.toml`; paths.memory must equal `.project-memory`. PROJECT.md stays at the project root. Old locations require explicit migration; the skill creates no runtime state, caches, or secrets.

Package version 0.5.1 is independent of data-schema versions. Fresh initialization uses config schema 1.2 and root PROJECT.md identity; an existing complete config schema 1.0 remains fully read/write as implicit `hub`. Required records, optional taste, handoffs, and archives remain record schema 1.0 with no namespace field.

For optional automatic startup, a hub can place this recommended line in its agent instructions:

```text
At the start of each new agent session, before substantive work, use project-memory to resume.
```

It runs once per fresh conversation. Missing, invalid, ambiguous, or structurally drifting memory never blocks the substantive task and never causes automatic initialization or instruction-file edits.

## Core behavior

- Working detail remains only while it helps finish or safely resume work.
- Progress frontiers replace sequential progress narration.
- Completion creates an outcome, not an activity transcript.
- Artifacts retain their own detailed content; memory links to them.
- Unplanned completed work may be recorded without inventing a goal.
- One real correction, comparison, or feedback instance creates a `watching` candidate. `proposed` requires two distinct supporting instances or an explicit request to review the candidate as reusable guidance. A polite operation request is not approval, and candidates never govern execution. Guidance or taste requires explicit approval.
- A single pointer in `CONTEXT.md` determines the active handoff.
- Stable IDs are never reused, including after archival.
- Installing, initializing, or evaluating the skill does not by itself create an adoption decision.

## Safety

The skill validates paths on every operation, reads before editing, refuses unexpected concurrent changes, uses atomic per-file replacement, and never hard-deletes durable memory in version 1. Ambiguous semantic cleanup stops for user direction.

With Python 3.10 or newer, `scripts/replace_record.py` is the preferred portable helper for replacing existing records. It uses an expected raw-byte SHA-256 as optimistic concurrency protection, writes proposed bytes without newline translation, and fails closed on path escapes, stale content, target reparse points, or bounded lock exhaustion. Instruction-level same-directory atomic replacement remains normative and is the only fallback when Python is unavailable.

## Validation

Package validation and safe replacement require Python 3.10 or newer. Validate the package from its root:

```text
python scripts/validate_package.py --root .
python scripts/validate_package.py --root . --format json
```

The package validator reports schema `project-memory/package-validation@1` and exits 0 for a valid package, 1 for validation errors, or 2 for invalid invocation.

The separate read-only live-memory validator requires Python 3.11 or newer and only the standard library:

```text
python scripts/validate_memory.py --owner-root <hub-root>
python scripts/validate_memory.py --owner-root <hub-root> --format json
```

Use `--config <hub-root>/.project-memory/project-memory.toml` only to name that exact owner-root config explicitly. The validator supports config schema 1.2 through PROJECT.md, config schema 1.0 as implicit `hub` and config schema 1.1 as explicit `hub`, while record, handoff, and archive schema remain 1.0. It returns 0 for valid memory, 1 for stable invalid memory, 2 for invocation errors, and 3 for runtime or inconclusive checks such as concurrent change or resource exhaustion. Findings and output are bounded; validation does not write to the namespace.

Each selected project owns one memory namespace. Nearest-owner discovery, project routing, cross-namespace roll-up, qualified IDs, and multiple namespaces are future work.

A future project owner may independently use its own `.project-memory/`, but version 1 implements no project-owner discovery, precedence, or roll-up.

## See also

- [Configuration](references/config.md)
- [Memory schema](references/schema.md)
- [Initialization](references/init.md)
- [Resume](references/resume.md)
- [Save](references/save.md)
- [Handoff](references/handoff.md)
- [Maintenance](references/maintain.md)


## Project identity and session behavior



Read identity when an explicit resume or reground starts memory use in a conversation. Keep the validated identity in conversation context; ordinary subsequent asks do not invoke memory or reread PROJECT.md. A quick unrelated prompt never invokes project-memory merely because identity or memory exists. Automatic startup is optional and requires an explicit project instruction.

Every later explicit memory operation rereads identity as preflight before relying on it or writing. Switching the selected root requires loading its identity. If identity changes during a write operation, stop and reconcile. Do not persist a session-loaded marker. Legacy config 1.0/1.1 retains its fixed hub identity; if PROJECT.md exists, its namespace must be hub. Init or an explicitly approved upgrade establishes project identity under config 1.2.


Read [project identity](references/identity.md) for the interview and record contract. Config schema 1.2 references PROJECT.md; legacy 1.0/1.1 preserves its existing semantics. Current initialization uses 1.2. Historical 0.4.0 documentation describes the earlier baseline.

## License

Skill source, scripts, templates, and documentation are MIT licensed. See [LICENSE](LICENSE). The JJFYI name and brand assets are excluded; all rights are reserved for those materials.
