# hub-memory

`hub-memory` is a portable Agent Skill for progressive, filesystem-first memory in a knowledge-worker hub.

It helps an agent preserve the state needed to continue work, record meaningful outcomes and decisions, learn cautiously from correction evidence, create deliberate high-fidelity handoffs, and periodically reconcile or compact its records.

## Memory model scope

The version 1 memory model manages one contained, fixed `hub` namespace. It does not provide workstream or project orchestration, task management, daily, weekly, or monthly notes or reporting, migration of an existing memory system, or cross-namespace routing or roll-up.

The package is instruction-first and human-readable. It does not require a database, background service, embeddings, retained chat history, or Git history.

## Package contents

- `SKILL.md` — agent entrypoint and operation router.
- `man.hub-memory.md` — human-facing reference.
- `references/` — configuration, schema, and operation contracts.
- `scripts/` — read-only package/live-memory validation and optional safe existing-record replacement.
- `templates/` — the six required empty memory records.
- `tests/` — focused standard-library tests and disposable live-memory fixtures.

## Installation

Install or clone this repository root as:

```text
<hub>/.agents/skills/hub-memory/
```

Then ask the agent to initialize `hub-memory` for the hub. Initialization creates `.agents/config/hub-memory.toml` and the configured memory namespace only after showing the proposed targets and receiving confirmation.

For a new hub, initialization writes config schema 1.1 with `namespace = "hub"` and defaults memory to `.ai-hub/memory`. This is an initialization default, not the only valid configured value: an existing valid config may continue to use `.memory` or another contained relative path. Version 1 performs no automatic migration.

Config schema 1.1 requires hub-memory package 0.4.0 or newer. Existing config schema 1.0 remains fully read/write under 0.4.0 as the implicit `hub` namespace; it is never upgraded automatically. Record, handoff, archive, and template schemas remain 1.0 and do not contain a namespace field. Package and data-schema versions are independent.

An optional manual config upgrade changes only `schema_version` from `"1.0"` to `"1.1"` and adds `namespace = "hub"`. The skill must show and validate that exact edit before applying it. Memory records and paths remain unchanged.

`.ai-hub/` is a shared container for durable, human-readable data owned by future `hub-*` capabilities. `hub-memory` owns only `.ai-hub/memory/`; it does not inspect, validate, reject, create, modify, or govern sibling capability directories merely because they exist. Runtime state, caches, and secrets remain under `.agents/config/state/` and `.agents/config/secrets/`, not `.ai-hub/`.

Do not initialize over an existing or competing memory system. Version 1 intentionally has no migration workflow.

### Recommended automatic resume

For harnesses that support repository instructions, the hub may add this optional line to `AGENTS.md`:

```text
At the start of each new agent session, before substantive work, use hub-memory to resume.
```

This means once per fresh conversation, not once per user turn. It is a recommended adapter, not a portable-skill dependency. `hub-memory` never creates or edits `AGENTS.md` automatically; initialization reports when the line is absent and requires a separate explicit request and approval before changing agent instructions.

Automatic resume degrades gracefully. If memory is missing, invalid, or ambiguous, the memory operation reports once for that session, performs no writes, continues the substantive task, and offers initialization afterward.

## Save and handoff

A standalone save reconciles meaningful session state. It absorbs, clears, and retires an active handoff only when bounded evidence establishes that the packet was consumed and every live item is resolved or durably represented; otherwise the unrelated save may proceed while the handoff remains active. Every handoff request, including “save and handoff,” instead uses reconciliation-embedded save: it applies the same classification and adoption guards while preserving the current pointer until durable records, non-pointer context, and the new packet validate.

An explicit packet-only handoff skips progressive-record reconciliation except for the required pointer mutation and reports that limitation. Detailed ordering and retry behavior remain normative in [references/handoff.md](references/handoff.md).

## Status

Package version `0.4.0` is under pre-stable contract hardening. It is independent of config and record schema versions. Acceptance is reported separately as structurally valid, behaviorally tested, and live accepted; one level does not imply the next.

## Python support

The package remains instruction-first. Python is optional and the bundled scripts use only the standard library. `scripts/validate_package.py` and `scripts/replace_record.py` require Python 3.10 or newer. The separate live-memory validator, `scripts/validate_memory.py`, requires Python 3.11 or newer so it can parse configuration with `tomllib`.

When Python is unavailable, existing records may be replaced only through the normative validated same-directory atomic replacement procedure in [references/schema.md](references/schema.md). If no known atomic primitive is available, stop without writing. A refusal or nonzero result from `scripts/replace_record.py` may not be bypassed manually.

## Structural validation

Run the bundled read-only validator with Python 3:

```text
python scripts/validate_package.py --root .
python scripts/validate_package.py --root . --format json
```

The package validator checks the public package structure, skill frontmatter, required references and templates, internal links, template schemas, private-artifact exclusions, and common unfinished scaffolding. It does not prove behavioral correctness.

Package validation reports schema `hub-memory/package-validation@1` and exits 0 for a valid package, 1 for validation errors, or 2 for invalid invocation.

To check one configured live namespace without writing to it, run:

```text
python scripts/validate_memory.py --owner-root <hub-root>
python scripts/validate_memory.py --owner-root <hub-root> --format json
```

An explicit config may be supplied only as `<hub-root>/.agents/config/hub-memory.toml` with `--config`. The validator supports config schema 1.0 as implicit `hub` and config schema 1.1 with `namespace = "hub"`; record, handoff, and archive schema remain 1.0.

Live-memory validation reports schema `hub-memory/memory-validation@1` and exits 0 for valid memory, 1 for a stable invalid namespace, 2 for an invocation error, or 3 when validation is inconclusive. Findings are deterministic and bounded. Public read limits are 5,000 files, 8 MiB per file, and 64 MiB total. It inventories and hashes the config and checked memory files before validation, then rechecks them; concurrent change is inconclusive rather than an invalid-memory finding.
