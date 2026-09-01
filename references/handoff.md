# Create or use a handoff

A handoff is a deliberate high-fidelity continuation packet. Create one only on explicit request or when the user deliberately stops complex work and asks for detailed continuation state.

Every handoff request, including a combined save plus handoff, uses reconciliation-embedded save. Apply the evidence, classification, evaluation, adoption, stable-ID, and retry rules in [save.md](save.md), but do not run its standalone procedure. Reconciliation may create only records ordinary save could create. It never changes the `Active Handoff` section or retires the pointed packet. Report every durable record created during reconciliation as part of the one handoff operation.

If the user explicitly requests a packet-only handoff, do not reconcile progressive records. The only existing-record mutation allowed is the required `CONTEXT.md` pointer replacement, and the completion report must disclose that living memory was not reconciled. If a packet is already active, packet-only creation cannot silently replace it; require explicit authority to supersede that packet and carry forward every live item.

## Write authority

`handoff` may perform reconciliation-embedded save, create `handoffs/`, create a packet, update non-pointer continuation sections and then the `CONTEXT.md` pointer, and add one retirement timestamp to the uniquely replaced packet. Packet-only authority excludes progressive-record reconciliation and non-pointer context changes.

## Procedure

1. Read [config.md](config.md), [schema.md](schema.md), and [save.md](save.md), then perform the shared config, containment, schema, and approved-guidance preflight. Read current context, direction, every record reconciliation may touch, and the pointed packet. Validate the existing pointer.
2. Choose one old-packet disposition before writing:
   - absorb every live item into progressive memory during reconciliation; the successor is fresh, carries no `supersedes`, and the old packet is retired once only after activation; or
   - with explicit user approval, do not absorb and instead supersede the active packet; carry every live item forward and set a one-way `supersedes` path to that packet; or
   - when no packet is active, create a fresh successor with no `supersedes`.
   A packet-only request with an active packet requires the explicit non-absorption supersession choice.
3. For an ordinary handoff, ground and classify session changes using the bounded save evidence set, then write and validate durable records first. Reconcile a partial prior attempt by reusing uniquely matching IDs rather than creating duplicates. For packet-only, ground packet claims in the same bounded evidence but do not classify or write progressive records. Stop before changing context if a durable write or validation fails.
4. Unless packet-only was requested, update only the non-pointer continuation sections of `CONTEXT.md` using the existing-record replacement contract. Preserve the old `Active Handoff` section byte-for-byte within the proposed context and validate the continuation sections after replacement.
5. Obtain a reliable current instant from the host or runtime clock and convert it to the configured timezone. If no reliable current instant is available, stop before packet creation and report the limitation; never invent a time of day. Construct the complete proposed packet bytes from the current grounded state. Include the packet content required by [schema.md](schema.md), derive `created` from that converted instant, and perform the checklist-based cold-resume self-check as though the current conversation were unavailable. Prevalidate the exact bytes, frontmatter, headings, content fields, links, paths, and supersedes chain before creating anything.
6. Select the create-new path `YYYY-MM-DD-HHMM-<slug>.md`, deriving `YYYY-MM-DD-HHMM` from the same converted instant as `created` and using a lowercase slug matching `[a-z0-9-]{1,60}`. Reject separators, traversal, drive prefixes, reserved names, or overlong slugs. Canonicalize the path inside `handoffs/`. On a first attempt, an existing filename receives the first available numeric suffix and is never overwritten. On retry after pointer failure, do not choose a suffix automatically; follow the retry rules below.
7. Create the packet with create-new/no-overwrite behavior while the old pointer remains active. Re-read the created raw bytes and revalidate the complete inactive packet. Packet creation or post-create validation failure leaves the prior pointer unchanged.
8. Hash the post-reconciliation `CONTEXT.md` raw bytes. Immediately re-read and rehash it, then atomically replace only the `Active Handoff` section using that expected hash and the replacement contract in [schema.md](schema.md). Any content change, helper refusal, or failed replacement stops activation; the old pointer remains authoritative and the new packet remains inactive.
9. Re-read and validate the activated pointer and packet. The pointer alone activates the new packet and deactivates the old one.
10. If one old packet was uniquely replaced, obtain a reliable current instant from the host or runtime clock, convert it to the configured timezone, and add its retirement timestamp exactly once using the replacement contract. Never invent the retirement time. When reconciliation absorbed that packet, the successor is fresh with no `supersedes`, and this one post-activation retirement is never repeated. If no active packet was replaced, do not perform a retirement write. A missing clock or provenance failure after valid activation does not reverse the pointer; report the retirement as requiring repair.
11. Report the new packet, every durable record created, all other changed files, the old-packet disposition, validation performed, and any inactive candidates or provenance repair required. Do not claim that a fresh-session behavioral cold resume was tested; that requires a separate fresh-session exercise.

## Resume behavior

Load a packet only through the `CONTEXT.md` pointer. Unpointed packets are inactive even when their retirement timestamp is missing.

## Failure and retry behavior

Reconciliation or packet-creation failure preserves the prior active pointer. Pointer failure leaves the newly created packet inactive and reports its exact path. A concurrent context change never activates that packet.

On retry after pointer failure, first reconcile any completed record writes by identity without allocating duplicates. Reconstruct and prevalidate the intended packet bytes. Reuse a uniquely identified inactive packet only when its raw bytes exactly match those intended bytes and its paths, headings, links, retirement state, and supersedes chain still validate. Revalidate that the current non-pointer context is the intended reconciled state and that the prior pointer is still authoritative, then attempt pointer activation only; do not create or rewrite the packet.

If intended bytes differ, no unique byte-matching inactive packet exists, or more than one candidate could be the successor, stop and report every inactive candidate. Require explicit approval before creating a suffixed packet. Never guess between candidates or silently overwrite one. A missing retirement timestamp may be repaired only when the replaced packet is uniquely identifiable.

Packet creation always uses create-new/no-overwrite behavior; `scripts/replace_record.py` never creates packets.
