# Configuration

This file is the single authority for project-memory configuration.

## Ownership and discovery

The owner root is the explicitly selected independent project folder. The active repository or workspace context may nominate one root when unambiguous. Do not search Git metadata, arbitrary ancestors, drives, home directories, sibling projects, or unrelated folders. Resolve only `.project-memory/project-memory.toml` below that root, or an explicit config at that exact location. No user-global or skill-local config fallback exists. Shared user-level installation does not change project-local ownership.

Missing or invalid config stops an explicit memory operation and offers init. Optional automatic startup reports once, writes nothing, and continues the substantive task. Suppress repeated failed automatic probes only in the current conversation.

## Config schema 1.2

Fresh initialization uses schema 1.2. The exact top-level keys are schema_version, skill, timezone, and paths. Paths contains exactly memory and identity. `paths.identity` must equal `PROJECT.md`; name, namespace, purpose, and scope are canonical there and are never duplicated in config. Read and validate identity using [identity.md](identity.md).

```toml
schema_version = "1.2"
skill = "project-memory"
timezone = "America/Los_Angeles"

[paths]
memory = ".project-memory"
identity = "PROJECT.md"
```

Timezone is a confirmed IANA timezone. Fresh initialization defaults memory to `.project-memory`; the configured memory path must remain `.project-memory`. `project-memory` owns only `.project-memory/` and its root identity contract. Do not inspect, validate, reject, create, modify, or govern sibling directories merely because they exist. The skill creates no runtime state, caches, or secrets.

## Compatibility

Config 1.0 permits exactly schema_version, skill, timezone, and paths.memory; it remains read/write as implicit hub. Config 1.1 permits exactly the same fields plus namespace = "hub"; it remains read/write as explicit hub. Neither requires PROJECT.md, but when present it must be valid and have namespace hub. Config 1.2 requires valid root identity and forbids a config namespace key. Record, handoff, archive, and template schemas remain 1.0 with no namespace field. Package 0.5.0 introduces config 1.2. Older package releases cannot read it.

Unknown keys, unsupported versions, missing identity, and mixed record schemas stop operations before writes. Never perform this upgrade automatically; an explicit upgrade interviews and confirms identity, validates it and the memory, then atomically replaces config with schema 1.2 while preserving timezone and memory path. Do not migrate old hub-memory filenames or record types automatically.

## Containment and concurrent change

Canonicalize the project root and paths, resolve indirection, and refuse escapes. PROJECT.md must be the regular non-reparse file directly below the root. Repeat containment checks immediately before writes. Reread config and identity before mutation; stop on unexpected change. Do not cache roots or identity in operational files.

## Folder ownership

All memory records and the activating config live directly in root `.project-memory/`. The config is `.project-memory/project-memory.toml`; `paths.memory` must equal `.project-memory`. The config is an allowed namespace file and is validated as TOML, not as a memory record. PROJECT.md remains at the project root for independent identity consumers. There is no config fallback to .agents and no .ai-hub folder. Existing installations at older locations require an explicit migration; do not create a second namespace silently.
