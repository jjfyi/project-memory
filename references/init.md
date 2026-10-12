# Initialize memory

Use this operation only when the user asks to initialize or set up `project-memory`.

## Preconditions

- Require an explicit target project root.
- Read [config.md](config.md) and [schema.md](schema.md).
- Initialization is the only operation allowed without existing config.
- Migration is outside version 1.
- Automatic startup never initializes memory.

## Identity and activation

Interview before proposing setup. When name, purpose, or scope is missing, ask for it and wait. Never infer personal-hub identity from a folder name or describe memory functions as the project's purpose. Read the identity reference before composing the first initialization response.

Read [identity.md](identity.md) and perform its initialization interview before any write. Show PROJECT.md together with memory and config targets. Create or repair identity with the approved procedure first, preserve it on retry, validate memory next, and write activating config last. Existing valid config 1.0/1.1 remains unchanged unless an upgrade is explicitly requested.

## Procedure

1. Resolve the proposed config path as `<project-root>/.project-memory/project-memory.toml` and the memory path as `.project-memory`. Do not discover or write config under .agents. Detect an older competing location and offer explicit migration instead of creating a parallel namespace.
2. Canonicalize both targets, resolve path indirection, and require the memory root to remain beneath the project root.
3. For the default path, preflight both required directory paths. A missing `.project-memory/` directory may be created. If either required path is a conflicting file, symlink, junction, reparse point, or other non-directory object, stop safely.
4. Inspect the hub for an existing config, the configured memory directory, required record names, optional `project-memory` resources, reserved replacement remnants, agent instructions, and plausible competing memory systems. Apply the strict namespace preflight only to the configured memory target. Other project directories are outside the memory namespace; do not inspect or govern them merely because they exist.
5. Before any write, preflight every existing namespace item:
   - require known required or optional names, plus project-memory.toml when present; validate that config separately as TOML;
   - require each present Markdown file's filename/type mapping;
   - require supported schema versions, required headings, valid counters, and no conflicting content;
   - stop and name any invalid file for manual repair or removal;
   - refuse foreign files or competing systems;
   - report each reserved replacement remnant as an interrupted write, and stop when it might contain uncommitted state until its content is compared with the target and the user explicitly approves recovery or removal.
6. Preserve every existing valid record. For fresh or config-less partial initialization, use config schema 1.2 with `paths.identity = "PROJECT.md"` only after the identity interview and full existing-record preflight pass. Existing valid config retains its version; legacy identity must remain compatible with its hub namespace until an explicit upgrade is approved.
7. Ask the user to confirm the IANA timezone if it was not explicitly provided.
8. Show the exact config and memory paths and every directory and file that would be created. Require confirmation before writing.
9. Create only the missing required directory path and required records from the six bundled templates using create-new/no-overwrite behavior. Replace dates and counters with valid initial values; do not add example records. This creates only `.project-memory/` and its required files.
10. Validate the complete six-file namespace.
11. Write an activating config last only when config is absent. Use the exact schema 1.2 fields from [config.md](config.md), including the identity reference, for fresh and config-less partial initialization. Preserve an existing valid config unchanged.
12. Re-read config and all required files, validate containment and structure, and report how to invoke `resume` and `save`.
13. Automatic startup is optional. Offer its instruction only when the user wants automatic resume; its absence is not a defect. Do not create or edit `AGENTS.md` without a separate explicit request and approval.

Do not create `TASTE.md`, `handoffs/`, or `archive/` during initialization.

This skill creates no runtime state, caches, or secrets.

Installation, initialization, or evaluation alone creates no goal, outcome, decision, guidance, candidate, or adoption record.

## Failure behavior

If creation or validation fails, stop and report exactly what was created and what remains missing. Do not write config after an incomplete namespace. A later `init` may create only missing required files after all present files pass preflight.

Never overwrite or delete a competing or malformed file.
