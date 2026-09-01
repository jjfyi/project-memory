# Save progress

Use this operation when the user asks to save, update, checkpoint, or wrap up ordinary work.

The request must be session-level: save the session, work, or progress. A request to save a particular file, draft, document, image, artifact, or named path is not this operation.

## Save modes

Standalone `save` handles a save request that does not include handoff. It uses the full procedure below. It may absorb an active packet, clear its pointer, and retire it only when the active-packet disposition gate below passes.

Reconciliation-embedded save is used by every handoff request, including a combined save plus handoff request. It uses the same evidence grounding, classification, evaluation/adoption guard, stable-ID allocation, and durable-record authority as standalone save. It may create only records that ordinary save could create. It never changes the `Active Handoff` section and never retires the pointed packet during reconciliation. [handoff.md](handoff.md) is the sole authority for its ordering, activation, retry, and old-packet retirement.

## Write authority

`save` may update:

- `CONTEXT.md`;
- `DIRECTION.md`;
- `OUTCOMES.md`;
- `DECISIONS.md`;
- `CANDIDATES.md`;
- for standalone save only, the retirement timestamp of the currently referenced handoff after its state is absorbed.

It never writes `GUIDANCE.md`, `TASTE.md`, or archives.

## Bounded evidence grounding

Ground proposed changes in the smallest relevant closed evidence set:

1. the current conversation and active plan;
2. current memory records;
3. artifacts meaningfully touched, created, or discussed;
4. bounded repository state already named by the work when it materially affects continuation; and
5. validations and material failures already observed.

Do not recursively enumerate the repository, inspect unrelated files, reproduce raw logs, or require Git. Repository evidence is limited to named artifacts and small current-state checks such as branch or commit identity, concise status, or a diff summary when those facts affect continuation. If Git is unavailable, omit that optional evidence and label any resulting uncertainty; do not substitute a repository scan.

Claims of completion, artifact existence, validation, or current workspace state must come from evidence actually observed. Identify external resources as external; do not fetch them unless the user asks or the operation otherwise requires their contents.

Resolve owner-relative local artifact links from the owner root. Immediately before writing any memory file whose next action, completion claim, or handoff depends materially on an owner-relative or absolute local artifact, check that exact path using a direct stat or existence check. Do not glob, list a directory, walk an artifact graph, or traverse the repository. If the artifact is missing or inaccessible, demote the affected claim to explicit uncertainty. This does not block unrelated valid memory writes, but a result must not be marked complete when its required artifact cannot be verified.

The required names-and-ID-headings inventory is confined to the configured memory root and its fixed optional directories. It is structural namespace validation, not permission to traverse external evidence or the surrounding repository.

## Standalone save procedure

1. Read [config.md](config.md) and [schema.md](schema.md), then perform the shared config, containment, schema, and approved-guidance preflight.
2. Read the current versions of every file that may change. Read candidates only to record or propose evidence; never apply unapproved candidate content to the work being saved.
3. Compare the loaded state with the completed work and identify meaningful state changes.
4. Classify each useful item once:
   - unfinished continuation state → `CONTEXT.md`;
   - goal, focus, completion criterion, or progress frontier → `DIRECTION.md`;
   - meaningful completed state change → `OUTCOMES.md`;
   - durable choice, requirement, constraint, or scope boundary → `DECISIONS.md`;
   - plausible reusable correction evidence → `CANDIDATES.md`;
   - detailed content → its owning artifact, linked when useful;
   - attempts, searches, iterations, and consumed approvals → discard after their result is represented.
5. Apply the evaluation and adoption guard:
   - installation, initialization, or evaluation alone does not create an adoption decision;
   - an active evaluation updates a `FOCUS` current state;
   - create an `OUTCOME` only when the evaluation result is independently durable and meaningful;
   - create a `DECISION` only when the user explicitly chooses the approach or the conversation clearly establishes it as governing future work;
   - later adoption creates a new decision citing prior evidence and never rewrites a historical outcome.
6. Update ordinary progress in place. Create a progress outcome only when it remains meaningful independently of its goal.
7. Mark a goal completed only when the user states completion or every written criterion is verifiably met. Otherwise keep it active and report the uncertainty for maintenance review.
8. Allocate new stable IDs from the file counters. Increment counters in the same atomic file update. Never reuse an ID or lower a counter.
9. Apply the candidate evidence gate:
   - one real correction, comparison, or feedback instance creates a fresh candidate as `watching`;
   - a fresh or existing candidate becomes `proposed` only when the bounded evidence set contains at least two distinct supporting instances or the user explicitly requests review of that candidate as reusable guidance;
   - an ordinary or polite request to save, update, checkpoint, or continue work is not a request to review or approve reusable guidance;
   - `save` may surface a qualifying proposal, but it never promotes or rejects a candidate, and no candidate governs execution.
10. Condense context. Preserve every live open thread regardless of age. For each removed open thread or blocker, report its durable destination ID or that it was explicitly resolved; otherwise keep it.
11. Immediately before each write, re-read the target and stop if it changed unexpectedly since loading.
12. Write and validate durable records first. For each existing record, follow the replacement contract in [schema.md](schema.md), preferring `scripts/replace_record.py` when supported. A nonzero helper result stops the operation and may not be bypassed. Record, packet, and archive creation remains create-new/no-overwrite.
13. Apply the standalone active-packet disposition gate before changing the pointer. Absorb the packet only when bounded operation evidence establishes that it has been resumed or consumed and every live item is either explicitly resolved or durably represented in the proposed post-save progressive records or context. Unrelated completed work alone never establishes absorption. If any live packet item is unrelated, unresolved, or ambiguous, preserve the pointer and packet unchanged; the unrelated save may still proceed, and its completion report must state that the handoff remains active.
14. Write `CONTEXT.md` as the final continuation-state mutation using the same replacement contract.
15. Only after the disposition gate passes and the pointer is successfully cleared, add the absorbed packet's retirement timestamp using the same replacement contract. Failure of this provenance update does not reactivate the packet; report it for repair.
16. Validate counters, unique IDs across active and archived records, required headings, frontmatter, links, reciprocal roll-up/supersession fields, and the handoff pointer.

Do not run this standalone procedure before a handoff. Route a combined save plus handoff through the reconciliation-embedded mode in [handoff.md](handoff.md), so the existing pointer remains authoritative until successor activation.

## Interrupted writes and retry

If any durable write or post-write validation fails:

- stop immediately;
- do not write `CONTEXT.md`;
- report which files were written and which were not;
- preserve valid completed writes and any resulting ID gaps.

On retry, reconcile completed writes first. Reuse their stable IDs and evidence links and complete missing reciprocal fields; do not allocate replacement entries. Stop if matching is ambiguous.

## Maintenance advisory

Recommend `maintain` without running semantic cleanup when:

- active outcomes exceed 100 entries;
- active guidance exceeds 50 entries;
- context exceeds 250 lines;
- completed direction entries exceed 25; or
- structural validation finds drift.

These thresholds do not authorize compaction or archival.
