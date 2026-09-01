# Memory schema

This file is the normative record schema for a version 1 `hub-memory` namespace.

## Config, namespace, and record versions

Config schema and record schema are independent exact strings. Config schema 1.0 selects the implicit `hub` namespace; config schema 1.1 selects the same namespace explicitly with `namespace = "hub"`. Namespace identity exists only in config.

Every required record, optional `TASTE.md`, handoff packet, and annual archive remains record schema 1.0 and contains no namespace field. A supported config 1.0 or 1.1 namespace may create and update these schema-1.0 resources. Unsupported or mixed record schemas stop before writes.

## Required namespace

```text
<memory-root>/
├── CONTEXT.md
├── DIRECTION.md
├── OUTCOMES.md
├── DECISIONS.md
├── GUIDANCE.md
└── CANDIDATES.md
```

Optional resources are created only when first needed:

```text
<memory-root>/
├── TASTE.md
├── handoffs/
└── archive/
```

The filenames are fixed in version 1.

## Reserved replacement remnants

An interrupted existing-record replacement may leave a same-directory sibling named:

```text
.<target-filename>.hub-memory-replace-<32-lowercase-hex>.tmp
```

This reserved pattern is a recognized non-record artifact. A remnant is inactive, is never loaded as memory, and is not a competing system. `init` and `maintain` report it as an interrupted write. If it might contain uncommitted state, stop and require content comparison plus explicit approval before recovery or removal; never silently ignore or delete it. Approved removal of a confirmed remnant is interrupted-write cleanup, not deletion of durable memory.

## Common metadata

Every required record begins with:

```yaml
---
type: hub-memory-<record-type>
schema_version: "1.0"
updated: YYYY-MM-DD
---
```

ID-bearing records also carry monotonic counters:

- `OUTCOMES.md`, `DECISIONS.md`, `GUIDANCE.md`, `CANDIDATES.md`, and optional `TASTE.md`: `next_id: 1`.
- `DIRECTION.md`: `next_goal_id: 1` and `next_focus_id: 1`.
- `CONTEXT.md`, handoff packets, and annual archives have no counter.

Use the configured timezone for dates and timestamps. Preserve unknown frontmatter keys and report them as warnings when the declared record schema is otherwise supported. Unsupported or mixed record schemas stop before writes.

### Flat frontmatter grammar

Package-produced record, handoff, and archive frontmatter is UTF-8 without a BOM. LF and CRLF line endings are accepted; bare CR is rejected.

Frontmatter begins and ends with a line exactly equal to `---`. Between those delimiters it is one unindented flat `key: scalar` mapping:

- split each field on its first colon;
- trim the scalar remainder, including free-text values such as handoff `objective`;
- allow no collections, nesting, or comment stripping;
- reject duplicate keys;
- type-check every required key;
- preserve unknown keys as warnings only when the declared record schema is otherwise supported.

Handoff `supersedes` is a plain relative path resolved from the current packet directory, not a Markdown link.

## IDs and links

Prefixes are fixed:

| Record | Prefix |
|---|---|
| Goal | `GOAL-` |
| Focus | `FOCUS-` |
| Outcome | `OUT-` |
| Decision | `DEC-` |
| Guidance | `GUIDE-` |
| Candidate | `CAND-` |
| Taste | `TASTE-` |

Format the initial numeric portion with at least four digits. Expand beyond four digits when necessary. Allocate the current counter value, then increment it. Archival never lowers a counter. IDs are never reused. Their identity is conceptually `(owner root, namespace, stable ID)`, and they are authoritative only within the one active namespace selected by config.

Validate ID uniqueness across active records and every annual archive. An identical active/archive duplicate may represent an interrupted approved move; maintenance may finish it only when content and intended destination agree uniquely.

Within a file, an ID may be referenced as plain code. Across files, use a relative Markdown link whose label is the stable ID, for example `[OUT-0042](OUTCOMES.md)`. The ID is authoritative; the file target is advisory. An approved archive move rewrites inbound targets. A uniquely resolvable stale target is a structural repair.

Qualified IDs and cross-namespace references are reserved for a future schema and are invalid in version 1.

Keep entries in ascending ID order inside their section.

## Empty sections

Every required heading exists exactly once. An empty section contains:

```markdown
_None._
```

Remove `_None._` when adding the first entry and restore it when an approved move leaves a section empty.

## `CONTEXT.md`

Frontmatter type: `hub-memory-context`.

Required headings:

```markdown
## Current Focus
## Open Threads
## Blockers
## Next Steps
## Relevant Memory
## Active Handoff
```

`Current Focus` contains a short `GOAL` or `FOCUS` pointer and the immediate objective. Canonical progress lives in `DIRECTION.md`.

Each open thread states its next action and resolution or transfer condition. Context contains only live continuation state; completed history belongs elsewhere unless it still affects continuation. Age never removes a live unresolved item.

`Active Handoff` contains `_None._` or exactly one relative Markdown link to a handoff packet. This pointer alone determines which packet is active.

## `DIRECTION.md`

Frontmatter type: `hub-memory-direction`; counters: `next_goal_id`, `next_focus_id`.

Required headings:

```markdown
## Goals
## Focuses
```

Goal:

```markdown
### GOAL-0001 — <title>
- Status: active | completed | parked
- Outcome: <desired state>
- Completion: <observable criteria>
- Progress: <current frontier or phase>
- Next: <next meaningful move>
- Related: <optional IDs or artifact links>
```

Focus:

```markdown
### FOCUS-0001 — <title>
- Status: active | parked
- Purpose: <why continuity matters>
- Current state: <compact durable state>
- Open questions: <bounded unresolved questions>
- Related: <optional IDs or artifact links>
```

A bounded initiative is a goal with phases, not a separate record type. Ordinary increments update `Progress`; create a progress outcome only when the result remains meaningful independently of the goal.

## `OUTCOMES.md`

Frontmatter type: `hub-memory-outcomes`; counter: `next_id`; required heading: `## Outcomes`.

```markdown
### OUT-0001 — <result>
- Date: YYYY-MM-DD
- Type: goal-progress | goal-completion | opportunistic | maintenance
- Result: <what became true>
- Effect: <why it matters>
- Related direction: <optional GOAL or FOCUS IDs>
- Artifacts: <optional canonical links>
- Rolls up: <optional later OUT ID>
- Rolls up from: <optional earlier OUT IDs>
```

Record completed state changes, not searches, attempts, iteration counts, consumed approvals, validation transcripts, or routine memory repairs. Only meaning-changing maintenance such as an approved roll-up or archival may be an outcome.

A roll-up child points forward with `Rolls up`; its milestone points back with `Rolls up from`. Both sides must agree.

## `DECISIONS.md`

Frontmatter type: `hub-memory-decisions`; counter: `next_id`; required heading: `## Decisions`.

```markdown
### DEC-0001 — <decision title>
- Status: active | superseded
- Date: YYYY-MM-DD
- Applies to: <scope>
- Decision: <accepted state>
- Rationale: <governing reason or constraint>
- Consequence: <what future work must do>
- Supersedes: <optional earlier DEC IDs>
- Superseded by: <optional later DEC ID>
- Evidence: <optional outcome or artifact links>
```

Preserve the accepted choice and useful rationale, not the proposal transcript. A successor's `Supersedes` and the earlier entry's `Superseded by` must agree.

## `GUIDANCE.md`

Frontmatter type: `hub-memory-guidance`; counter: `next_id`; required heading: `## Guidance`.

```markdown
### GUIDE-0001 — <behavior title>
- Status: active | superseded
- Approved: YYYY-MM-DD
- Scope: <where it applies>
- Trigger: <when to use it>
- Behavior: <what to do>
- Exceptions: <when it does not apply>
- Evidence: <candidate IDs and artifact links>
- Supersedes: <optional earlier GUIDE IDs>
- Superseded by: <optional later GUIDE ID>
```

Only explicitly approved reusable behavior belongs here. Guidance must change future behavior. A successor's `Supersedes` and the earlier entry's `Superseded by` must agree.

## `CANDIDATES.md`

Frontmatter type: `hub-memory-candidates`; counter: `next_id`; required heading: `## Candidates`.

```markdown
### CAND-0001 — <candidate title>
- Status: watching | proposed | promoted | rejected
- Scope: <current narrow scope>
- Trigger: <underlying situation>
- Desired behavior: <possible reusable rule>
- Exceptions or uncertainty: <why promotion is not automatic>
- Evidence: <distinct tasks, outcomes, or artifact links>
- Proposed destination: guidance | taste
- Disposition date: <optional YYYY-MM-DD>
- Destination: <optional GUIDE or TASTE ID>
- Rejection reason: <optional reason>
```

A fresh candidate supported by one real correction, comparison, or feedback instance starts as `watching`. A fresh or existing candidate becomes `proposed` only when the bounded evidence set contains at least two distinct supporting instances or the user explicitly requests review of that candidate as reusable guidance. An ordinary or polite request to save, update, checkpoint, or continue work is not a request to review or approve reusable guidance. Recurrence triggers review but does not prove a rule. `save` may surface a qualifying proposal but never promotes or rejects it. `promoted` and `rejected` are terminal maintenance dispositions. A promoted candidate remains as a compact disposition pointing to the approved destination. Candidates never govern execution.

## Optional `TASTE.md`

Created by approved maintenance after the first taste promotion.

Frontmatter type: `hub-memory-taste`; common metadata plus `next_id`; required heading: `## Taste`.

```markdown
### TASTE-0001 — <example title>
- Status: active | superseded
- Approved: YYYY-MM-DD
- Scope: <where this example applies>
- Example: <artifact or excerpt link>
- Preferred qualities: <observable traits>
- Improvement: <what changed from an earlier version>
- Limits: <where not to generalize>
- Evidence: <candidate or comparison links>
- Supersedes: <optional earlier TASTE IDs>
- Superseded by: <optional later TASTE ID>
```

Taste preserves approved concrete examples for subjective work. It does not replace observable guidance or expand beyond its approved scope.

## Optional handoffs

Directory owner: `handoff`.

Filename: `YYYY-MM-DD-HHMM-<slug>.md`. The slug matches `[a-z0-9-]{1,60}`. Canonicalize the result and require it to remain within `handoffs/`. If a filename exists, add the first available numeric suffix; never overwrite.

Obtain the packet creation instant from a reliable host or runtime clock and convert it to the configured timezone. Derive `created` and the filename's `YYYY-MM-DD-HHMM` from that same converted instant; never invent a time of day. Obtain every `retired` value from a reliable current instant converted to the configured timezone as well. If no reliable current instant is available at packet creation, stop before creating the packet and report the limitation. Never weaken the timestamp grammar or fabricate a value to continue.

Frontmatter:

```yaml
---
type: hub-memory-handoff
schema_version: "1.0"
created: <timezone-aware timestamp>
objective: <continuation objective>
supersedes: <optional relative packet link>
retired: <optional timezone-aware timestamp>
---
```

Required headings:

```markdown
## Objective
## Exact State
## Completed
## Unresolved Reasoning
## Artifacts
## Next Actions
## Validation
```

Every required section has a nonempty body. The minimum packet body contract is:

```markdown
## Objective

- Objective: <continuation objective>
- Success condition: <observable condition that finishes the handoff objective>

## Exact State

- Trusted state: <state supported by observed evidence>
- Uncertainty: <material uncertainty or None>
- Stopping point: <exact point at which work stopped>
- Workspace anchor: <optional owner-relative path>

## Completed

<meaningful completed state relevant to continuation, with durable IDs when available, or _None._>

## Unresolved Reasoning

- Open questions: <questions or None>
- Unverified assumptions: <assumptions or None>
- Rejected paths: <paths worth avoiding and why, or None>
- Conversation-only continuity: <consequential detail not stored elsewhere, or None>

## Artifacts

- Authoritative resources: <local and external resources or None>
- Repository state: <bounded relevant state or None>
- Environment constraints: <constraints or None>
- Hazards: <known hazards or None>

## Next Actions

1. <exact first action>
- Acceptance check: <observable check for the first action>
2. <optional necessary ordered tail>

## Validation

- Checks run: <tests and checks already run or None>
- Material failures: <failures or None>
- Cold-resume self-check: passed — <why the saved files are sufficient without this conversation>
```

The labels and capitalization shown above are exact. Each required label appears once with a nonempty value; `None` is an explicit value. The first meaningful line in `Next Actions` is the numbered first action. The cold-resume self-check is a checklist-based inspection of the saved files: it verifies that a fresh session can identify the objective, success condition, trusted state, uncertainty, stopping point, authoritative artifacts, relevant completed state and IDs, unresolved or rejected reasoning, prior validation and failures, the exact first action, and its acceptance check. Packet creation stops before create-new unless this self-check passes. This instruction-level self-check is not a claim that a separate fresh-session behavioral test ran.

Inside `Exact State`, a packet may include at most one optional portable workspace-anchor line:

```markdown
- Workspace anchor: <owner-relative path>
```

The label and capitalization are exact. The value is a nonempty forward-slash path resolved from the owner root. It must be relative, must not be a URL or a platform drive path, and must not contain a `..` segment. The anchor may name a file or directory and is not a Git object, branch, commit, or requirement that Git exist.

The live-memory validator checks the required packet fields and only this anchor line's structural form; it does not inspect the external target or judge the semantic quality of packet content. When the packet is active, `resume` may perform the single direct stat or existence check defined in [resume.md](resume.md). Handoff packets without this optional line remain valid.

The `CONTEXT.md` pointer alone determines activeness. `retired` is provenance, not authority.

`supersedes` is present only for explicit non-absorption supersession. It is a one-way provenance path to an existing direct packet in `handoffs/`; it must resolve and the chain must be acyclic. A fresh packet, including one whose predecessor was absorbed into living memory, omits `supersedes`. An active packet never carries `retired`. Unpointed, unretired packets are inactive and may be retained as failed-activation retry candidates.

## Optional annual archives

Directory owner: approved `maintain` apply mode.

Filename: `archive/YYYY.md`.

Frontmatter:

```yaml
---
type: hub-memory-archive
schema_version: "1.0"
year: YYYY
updated: YYYY-MM-DD
---
```

Required headings:

```markdown
## Direction
## Outcomes
## Decisions
## Guidance
## Candidates
## Taste
```

Archived entries retain their original heading and ID. Reactivation creates a new active entry linking the archived ID; archived content is not silently moved back.

## Existing-record replacement

This instruction-level contract is normative for every update to an existing memory record, handoff pointer, handoff provenance field, or archive. New records, packets, and archives use create-new/no-overwrite behavior instead.

1. Resolve the configured hub and memory roots, including ancestor symlinks, junctions, and other reparse points, and revalidate containment immediately before writing.
2. Require the existing target to be a regular Markdown memory file inside both resolved roots. Refuse a target file that is itself a symlink or reparse point.
3. Read the target as raw bytes and record its SHA-256. This expected hash is optimistic concurrency protection, not race-free compare-and-swap.
4. Prepare the complete proposed file as UTF-8 bytes without a BOM or newline translation.
5. Re-read and hash the raw target bytes immediately before every replacement attempt or retry. A mismatch is stale state and stops without replacement.
6. Create a unique reserved temporary sibling in the target directory, write the proposed bytes exactly, preserve the applicable target file mode, flush, and `fsync` before replacement.
7. Use a known platform atomic replacement primitive on that same filesystem. Clean the temporary sibling on every handled failure.
8. On transient Windows sharing or permission failures, use only a very small bounded retry with backoff and an elapsed-time ceiling. Recheck the expected hash before each retry. Exhaustion returns a distinct locked result; never wait unboundedly or for minutes.
9. Re-read the replaced target and verify that its raw bytes equal the proposed bytes.

When Python 3.10 or newer is available, prefer the standard-library `scripts/replace_record.py` helper. Its interface requires `--owner-root`, `--memory-root`, `--target`, `--expected-sha256`, and `--proposed-content`, with optional `--dry-run`. It emits one bounded JSON result and meaningful exit codes. It updates existing records only.

A helper refusal or nonzero result may not be bypassed manually. If Python is unavailable, follow the same contract directly only when a known same-directory atomic replacement primitive is available. Otherwise stop without writing. Dry run creates no files, performs no writes, and leaves target bytes and modification metadata unchanged.

## Structural invariants

- One config resolves one namespace.
- All six required records exist.
- Required headings and compatible frontmatter are present.
- Stable IDs are unique across active and archived memory.
- Counters exceed every allocated ID of their type.
- Roll-up and supersession links agree in both directions.
- At most one active handoff pointer exists, and it resolves.
- Optional resources are absent until needed.
- Reports, tasks, and workstream routing are never side effects.
- Reserved replacement remnants are inactive and never silently ignored or removed.

## Semantic rules

- Working context contains no completed history unless it affects continuation.
- Every bounded goal has observable completion criteria.
- Every open context item has a next action and resolution condition.
- Every outcome describes a result rather than a procedure transcript.
- Every active decision states scope and consequence.
- Every guidance entry has explicit approval and evidence.
- Every candidate has real evidence and cannot govern execution.

## Future portability boundary

Version 1 supports exactly one hub-owned namespace. It does not implement nearest-owner precedence, upward discovery, project routing, cross-namespace roll-up, or multiple namespaces. Stable IDs are authoritative within that one namespace; qualified IDs and cross-namespace references are future work. The owner-root and replacement-helper seam must remain reusable by a future project-memory capability without introducing project-memory behavior now.
