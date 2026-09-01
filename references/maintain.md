# Maintain memory

Use this operation for drift checking, conservative repair, candidate review, semantic compaction, supersession, and archival.

## Modes

- **Check mode:** read-only. Report structural and semantic findings without changing files.
- **Apply mode:** make approved or unambiguously structural changes within the authority below.

Candidate learning review is a focused form of `maintain`; it is not a separate operation.

## Write authority

Apply mode may update active memory, create optional `TASTE.md`, update handoff provenance, and create or update approved annual archives. It never edits config and never hard-deletes durable memory.

## Review procedure

1. Read [config.md](config.md) and [schema.md](schema.md), then perform the shared config, containment, schema, and approved-guidance preflight.
2. Read all active memory. Scan ID headings and internal links from every annual archive; load full archived bodies only when required to resolve a finding. Scan for reserved replacement remnants and treat each as an interrupted write, never as a record or competing namespace.
3. Compare context, direction, outcomes, decisions, guidance, candidates, handoffs, and archives. For external evidence, inspect only the closed continuation-anchor set from [resume.md](resume.md) or another exact artifact path the user explicitly placed in scope. Do not glob, list, traverse, or scan the surrounding repository.
4. Separate findings into:
   - unambiguous structural defects;
   - semantic proposals requiring approval;
   - ambiguous conditions requiring user direction.
5. In check mode, report the plan and stop without writing.
6. In apply mode, show the proposed meaning-changing changes and obtain explicit approval before performing them.
7. Immediately before every write, re-read the target and repeat containment validation.
8. Use the existing-record replacement contract in [schema.md](schema.md) for each mutation, preferring `scripts/replace_record.py` when supported. A nonzero helper result stops the operation and may not be bypassed. Create a new archive only with create-new/no-overwrite behavior.
9. Re-read changed files and validate all structural invariants.
10. Report changes and unresolved findings. Do not save the report as a memory layer.

## Automatic structural repair

Apply mode may repair without semantic approval only when identity and intent are unique:

- retarget a stale internal link when its stable ID has one unique location;
- add a missing retirement timestamp when the superseded packet is unambiguous;
- reconstruct a missing or invalid counter after scanning active and archived IDs;
- normalize frontmatter or restore a missing empty heading only when content identity and placement are unambiguous.

Stop for review on wrong types, major schema mismatches, duplicate headings, nonempty content without its required heading, duplicate IDs that are not an identical interrupted move, or any ambiguous pointer or link.

Reserved replacement remnants are never silently ignored or deleted. If a remnant might contain uncommitted state, compare it with the target and require explicit approval before recovery or removal. Apply mode may remove a confirmed remnant after approval; this is cleanup of an interrupted write, not deletion of durable memory.

## Stale continuation claims

Classify an obvious missing, inaccessible, or contradictory continuation anchor as a stale-continuation finding. Report the saved claim, the directly observed state, and whether the evidence was inaccessible rather than contradictory. Inaccessibility of optional evidence is uncertainty, not proof that the saved claim is false.

Check mode reports the finding and stops without writing. Apply mode requires explicit approval before changing the meaning of `CONTEXT.md`, a handoff, direction, or an outcome. Do not infer that work is incomplete, complete, moved, or deleted from absence alone.

A repair is unambiguously structural only when the stable identity and intended representation already determine one correction, such as retargeting a stale internal link to the unique location of its existing stable ID. Changing a continuation statement, substituting another external artifact, or removing an unresolved next action is semantic and always requires approval.

## Approval-required semantic changes

Require explicit approval for:

- uncertain goal completion;
- dropping an ambiguous open thread;
- merging or rolling up outcomes;
- superseding decisions, guidance, or taste;
- promoting or rejecting a candidate;
- semantic compaction;
- archival;
- retiring information whose future value is uncertain;
- correcting or removing a stale continuation claim.

Age alone never authorizes removal.

## Candidate review

1. Require evidence from an actual correction, comparison, or explicit instruction.
2. Keep scope narrow and record uncertainty or exceptions.
3. Recurrence across distinct tasks triggers review but does not prove a rule.
4. On approval, create the `GUIDE` or `TASTE` entry first with evidence linking the candidate.
5. Validate the destination, then mark the candidate `promoted`, recording disposition date and destination ID.
6. On rejection, preserve a compact terminal disposition and reason.
7. If interrupted after destination creation, find the unique destination whose evidence links the candidate and finish that disposition on retry; never allocate a duplicate.

Create `TASTE.md` only for an approved concrete example that genuinely improves subjective work.

## Compaction and archive

- Replace sequential progress narration with the current frontier.
- Create an outcome for completion rather than retaining operational detail.
- Roll related outcomes into a milestone only when meaning and provenance remain recoverable through reciprocal links.
- Keep artifact detail in the artifact.
- Preserve superseded records until approved archival.

For an approved archive move:

1. Create or read `archive/YYYY.md` and validate its schema.
2. Copy the entry with its original heading and ID into the correct section and validate it.
3. Rewrite every inbound internal link to the archive target.
4. Remove the active copy only after the archived copy and links validate.
5. Revalidate global ID uniqueness and counters.

If interrupted with identical active and archived copies, treat it as a recoverable move only when the approval, contents, and destination agree uniquely. Finish the existing move; do not allocate a new ID. Otherwise stop.
