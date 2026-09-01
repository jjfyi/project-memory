---
name: hub-memory
description: Maintain a progressive filesystem-first memory namespace for one knowledge-worker hub. Use when the user asks to resume, reground, load context, or asks "where were we"; save session, update session, save work, save progress, or checkpoint; create a handoff; or maintain or review memory. Do not use for saving a particular file, draft, document, image, artifact, or named path.
metadata:
  version: "0.4.0"
---

# hub-memory

Maintain one concise, durable memory namespace that helps future sessions continue correctly without preserving routine activity.

## Scope

Use this skill for:

- `init` — initialize a new hub memory namespace;
- `resume` — recover current direction and continuation state;
- `save` — preserve meaningful state changes and replace expired working detail;
- `handoff` — create an explicit high-fidelity continuation packet;
- `maintain` — check, reconcile, compact, archive, or review candidate learning.

Do not use it to create or manage tasks, workstreams, projects, daily, weekly, or monthly notes or reports, migrations from an existing memory system, or cross-namespace routing or roll-up.

## Route the request

These rules select an operation after the skill has loaded. They do not make skill discovery deterministic across every agent harness.

Match intent case-insensitively and allow ordinary polite or temporal framing. Apply this precedence:

1. Suppress negated or genuinely hypothetical, explanatory, or deliberative language. “Don't save yet” does nothing. “What would save session do?”, “Would saving now be useful?”, and “Should we save?” receive an explanation or offer only.
2. Honor an explicitly named operation when it is a request to perform it. Conventional requests such as “Can you save our progress?” and “Could you update the session?” execute; their polite question form is not hypothetical.
3. Otherwise infer session-level intent from the object and context. Saving the session, work, or progress invokes `save`. Saving a particular file, draft, document, image, artifact, or named path does not.

If object-save intent caused this skill to load, exit immediately without a memory preamble or hub-memory completion report.

Read only the references required for the selected operation:

| Request | Required references |
|---|---|
| Initialize or set up memory | [config](references/config.md), [schema](references/schema.md), [init](references/init.md) |
| Resume, reground, load context, or ask where work stands | [config](references/config.md), [schema](references/schema.md), [resume](references/resume.md) |
| Save session, update session, save work/progress, or checkpoint | [config](references/config.md), [schema](references/schema.md), [save](references/save.md) |
| Create or use a handoff | [config](references/config.md), [schema](references/schema.md), [save](references/save.md), [handoff](references/handoff.md) |
| Review learning, check drift, compact, repair, or archive | [config](references/config.md), [schema](references/schema.md), [maintain](references/maintain.md) |

If the request combines operations, read each selected operation reference once.

Every handoff request, including a combined save plus handoff, uses the reconciliation-embedded save mode defined in [handoff](references/handoff.md). That mode applies save classification and guards while preserving the current pointer until activation. Standalone save applies only when no handoff is requested. It absorbs, clears, and retires an active packet only when bounded evidence establishes consumption and accounts for every live item; otherwise it preserves the active handoff and reports that disposition.

## Shared operating rules

For every operation except `init`:

1. Resolve and validate configuration before reading or writing memory.
2. Treat config schema 1.0 as the implicit `hub` namespace and config schema 1.1 as valid only with `namespace = "hub"`; both supported states are fully read/write.
3. Reject unknown config keys, unsupported config versions, invalid namespace identity, and unsupported or mixed record schemas before writing.
4. Canonicalize the hub and memory paths and refuse any path outside the hub root.
5. Treat namespace identity as config-only. Records, handoffs, and archives remain schema 1.0 and contain no namespace field.
6. Load active approved guidance and apply only entries whose scope, trigger, and exceptions match the operation.
7. Read every target immediately before editing it and stop on unexpected changes.

Remember state changes, not activity. Point to canonical artifacts instead of copying their detail. One real correction, comparison, or feedback instance starts a candidate as `watching`; `proposed` requires two distinct supporting instances or an explicit request to review it as reusable guidance. A polite operation request is not guidance approval. Never let candidates govern execution. Never create tasks, reports, or workstreams as hidden side effects.

Use the validated same-directory atomic replacement contract in [schema](references/schema.md) for every existing memory file. Prefer `scripts/replace_record.py` only when a supported Python runtime is available. A helper refusal or nonzero result is final for that attempt and may not be bypassed manually. The instruction-level fallback is allowed only when a known same-directory atomic replacement primitive is available; otherwise stop without writing.

Never hard-delete durable memory files or records in version 1. Stop on ambiguity that could discard live state, duplicate an ID, broaden guidance, or change meaning without approval.

## Completion report

Report concisely:

- the operation performed;
- files created or changed;
- meaningful state changes preserved or removed;
- validation performed;
- approval still needed or ambiguity left unresolved.

Do not turn the report into another memory record.

## Full reference

See [man.hub-memory.md](man.hub-memory.md).
