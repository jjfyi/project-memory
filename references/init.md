# Initialize memory

Use this operation only when the user asks to initialize or set up `hub-memory`.

## Preconditions

- Require an explicit target hub root.
- Read [config.md](config.md) and [schema.md](schema.md).
- Initialization is the only operation allowed without existing config.
- Migration is outside version 1.
- Automatic startup never initializes memory.

## Procedure

1. Resolve the proposed config path as `<hub-root>/.agents/config/hub-memory.toml` and the proposed memory path from the requested value or the `.ai-hub/memory` initialization default. An existing valid config may keep `.memory` or another contained relative path; do not migrate it automatically.
2. Canonicalize both targets, resolve path indirection, and require the memory root to remain beneath the hub root.
3. For the default path, preflight both required directory paths. A missing `.ai-hub/` parent and `memory/` target may be created. If either required path is a conflicting file, symlink, junction, reparse point, or other non-directory object, stop safely.
4. Inspect the hub for an existing config, the configured memory directory, required record names, optional `hub-memory` resources, reserved replacement remnants, agent instructions, and plausible competing memory systems. Apply the strict namespace preflight only to the configured memory target. Existing sibling capability directories beneath `.ai-hub/` are permitted and are not foreign memory artifacts; do not inspect, validate, reject, create, modify, or govern them merely because they exist.
5. Before any write, preflight every existing namespace item:
   - require known required or optional names;
   - require each present Markdown file's filename/type mapping;
   - require supported schema versions, required headings, valid counters, and no conflicting content;
   - stop and name any invalid file for manual repair or removal;
   - refuse foreign files or competing systems;
   - report each reserved replacement remnant as an interrupted write, and stop when it might contain uncommitted state until its content is compared with the target and the user explicitly approves recovery or removal.
6. Classify the initialization without rewriting existing data:
   - a missing or empty memory target with no config is fresh empty initialization and uses config schema 1.1 with `namespace = "hub"`;
   - a config-less target containing one or more valid required record-schema-1.0 files is partial legacy recovery and completes as config schema 1.0 with implicit `hub`;
   - an existing valid config 1.0 or 1.1 retains its version and namespace semantics while missing records are recovered;
   - never combine partial legacy records with a new config 1.1 or upgrade config automatically.
   Never alter a present valid record.
7. Ask the user to confirm the IANA timezone if it was not explicitly provided.
8. Show the exact config and memory paths and every directory and file that would be created. Require confirmation before writing.
9. Create only the missing required directory path and required records from the six bundled templates using create-new/no-overwrite behavior. Replace dates and counters with valid initial values; do not add example records. For the default, this may create `.ai-hub/` and `.ai-hub/memory/`, but never sibling capability directories.
10. Validate the complete six-file namespace.
11. Write an activating config last only when config is absent. Use the exact schema 1.1 fields from [config.md](config.md) for fresh empty initialization, or the exact schema 1.0 field set for partial config-less record-schema-1.0 recovery. Preserve an existing valid config unchanged.
12. Re-read config and all required files, validate containment and structure, and report how to invoke `resume` and `save`.
13. Check `AGENTS.md` for the exact recommended automatic-resume line from the public README. Report its absence. Do not create or edit `AGENTS.md` without a separate explicit request and approval.

Do not create `TASTE.md`, `handoffs/`, or `archive/` during initialization.

Keep runtime state, caches, and secrets under `.agents/config/state/` and `.agents/config/secrets/`; initialization never places them in `.ai-hub/`.

Installation, initialization, or evaluation alone creates no goal, outcome, decision, guidance, candidate, or adoption record.

## Failure behavior

If creation or validation fails, stop and report exactly what was created and what remains missing. Do not write config after an incomplete namespace. A later `init` may create only missing required files after all present files pass preflight.

Never overwrite or delete a competing or malformed file.
