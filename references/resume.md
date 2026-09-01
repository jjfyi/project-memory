# Resume memory

Use this operation when the user asks to resume, reground, continue, or recall where work stands.

## Explicit and automatic invocation

An explicit ordinary request with no valid config stops and offers `init`.

For optional automatic startup, run at most once per fresh conversation before substantive work. Accept only a root supplied in the current invocation or nominated unambiguously by the active repository/workspace context, and only when its expected config validates under [config.md](config.md).

If the root is ambiguous or memory is missing or invalid:

- stop only the memory operation;
- report the condition once in that conversation;
- perform no writes and create no suppression marker;
- continue the substantive task; and
- offer initialization afterward.

Remember a failed automatic probe only in the current conversation so later turns do not repeat it. Automatic resume never initializes memory or edits `AGENTS.md`.

## Procedure

1. Read [config.md](config.md) and [schema.md](schema.md), then perform the shared config, containment, and schema preflight.
2. Read `CONTEXT.md` and `DIRECTION.md`.
3. Load all active approved guidance and evaluate each entry's scope, trigger, and exceptions against the current work.
4. Read decision headings and `Applies to` fields; load a decision body only when its scope matches.
5. Load taste only when the active state references it or its scope matches the work.
6. If `CONTEXT.md` contains one handoff pointer, validate and read that packet. The pointer alone determines activeness.
7. Do not load `CANDIDATES.md`, the complete outcome history, retired handoffs, or annual archives by default.
8. If an explicitly referenced stable ID has a stale file target, resolve it uniquely across active files and annual archives. Report ambiguity rather than guessing.
9. Perform the closed continuation-anchor check below.
10. Present a concise continuation brief:
   - current focus and immediate objective;
   - goal or focus progress frontier;
   - live open threads and blockers;
   - next meaningful action;
   - applicable approved guidance or decisions only when they materially affect continuation;
   - active handoff availability;
   - trusted saved state, observed anchor state, and any uncertainty or contradiction.

## Closed continuation-anchor check

After loading the active state, check only:

- the immediate local artifact named for the next action;
- one owner-relative `Workspace anchor` path explicitly recorded in the active handoff; and
- a local artifact whose existence is asserted as the current stopping point.

This list is complete. Use direct stat or existence checks only. Do not glob, list directories, traverse, walk artifact graphs, scan the repository, or validate historical outcomes. Git is not required and its absence does not prevent resume.

Treat the saved memory claim as trusted only when the observed state does not contradict it. When a check reveals an obvious contradiction, report the saved claim and the observed state separately, do not present the stale claim as trusted, and recommend `maintain` check mode. Do not repair memory or silently reinterpret the discrepancy.

Failure to access an optional evidence source is uncertainty, not proof of drift. Label it as unobserved and keep unaffected saved state distinct from that uncertainty. Automatic resume still continues the substantive task after reporting a material issue once.

## Read-only boundary

`resume` writes nothing, including when it detects continuation drift. If it finds structural drift or a stale continuation claim, report it once in that conversation and recommend `maintain` check mode. Continue the substantive task when the invocation was automatic. Do not repair, compact, create tasks, infer adoption, or update memory implicitly.
