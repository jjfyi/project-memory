# Configuration

This file is the single authority for `hub-memory` configuration.

## Ownership and root nomination

The **owner root** is the directory that owns one contained memory namespace. In version 1 the owner root is the hub root. The term exists so path-safety tooling does not foreclose a future project-memory capability; version 1 implements no project owner, nearest-owner precedence, or multiple namespaces.

Root nomination and config discovery are separate:

1. An explicit invocation may nominate the hub root or a config path for that invocation.
2. For optional automatic startup, the active repository or workspace context may nominate one candidate hub root only when that nomination is unambiguous. A root explicitly supplied in the current invocation takes precedence.
3. A nomination is accepted only when the expected hub-memory config below validates.
4. Never persist or cache a selected owner root in a file, marker, environment change, or memory record.

## Discovery

After one candidate hub root is nominated, resolve configuration in this order:

1. Use a config path explicitly provided for the current invocation when it is named `hub-memory.toml` beneath that hub's `.agents/config/` directory.
2. Otherwise use exactly `.agents/config/hub-memory.toml` beneath the nominated hub root.
3. Do not use a user-global or skill-local fallback in version 1.
4. Do not search Git metadata, arbitrary ancestors, drives, home directories, sibling or unrelated repositories, or other workspace folders.

The validated hub root is the parent of the `.agents/` directory containing the active config. Git is never used for discovery.

For an explicit ordinary operation, missing or invalid config stops the memory operation and offers `init`. For automatic startup, missing, invalid, or ambiguous memory stops only the memory operation: report once in that session, perform no writes, continue the substantive task, and offer initialization afterward. Suppress repeated failed automatic probes only in the current conversation; create no marker or artifact.

## Supported versions and field catalog

Config schema versions are exact strings, not decimals. Version 1 defines these fields in one closed catalog:

| Key | Type | Versions | Required | Meaning |
|---|---|---|---|---|
| `schema_version` | string | 1.0, 1.1 | yes | Declares the exact config contract version |
| `skill` | string | 1.0, 1.1 | yes | Must equal `"hub-memory"` |
| `namespace` | string | 1.1 only | yes in 1.1 | Must equal `"hub"`; absent and invalid under 1.0 |
| `timezone` | string | 1.0, 1.1 | yes | IANA timezone used for all dates and handoff timestamps |
| `paths.memory` | string | 1.0, 1.1 | yes | Memory directory relative to the hub root; fresh initialization defaults to `.ai-hub/memory` |

Config 1.0 permits exactly `schema_version`, `skill`, `timezone`, and the `paths` table containing only `memory`. Config 1.1 permits exactly the same closed set plus required `namespace`. Any other key or table is invalid for the declared version and stops all memory operations; do not preserve unknown config keys or guess their semantics.

## Supported states and version skew

| Config | Records and optional resources | Behavior |
|---|---|---|
| 1.0 with no `namespace` key | Complete compatible record schema 1.0 | Read/write as implicit `hub` |
| 1.1 with `namespace = "hub"` | Complete compatible record schema 1.0 | Read/write as explicit `hub` |
| 1.1 with missing or other `namespace` | Any | Invalid; stop before writes |
| Unsupported config major | Any | Invalid; stop |
| Newer unsupported config minor or an unknown key for a supported version | Any | Stop all memory operations; do not guess semantics |
| Unsupported or mixed record schema | Any | Stop before writes |

Config and record schema versions are independent. Hub-memory package 0.4.0 supports only the two complete states above. Config 1.1 requires package 0.4.0 or newer; package 0.3.0 cannot read it. Config 1.0 remains fully read/write under 0.4.0 and is not rewritten merely because the package was upgraded.

Automatic startup retains its degradation rule for every invalid or unsupported state: report once in the session, write nothing, continue the substantive task, and offer an appropriate next step.

## Initialization default and shared container

Fresh empty initialization uses config schema 1.1, requires `namespace = "hub"`, and defaults `paths.memory` to `.ai-hub/memory`. This is only the initialization default. An existing valid config may continue to use `.memory` or any other contained relative path; do not migrate it automatically.

`.ai-hub/` is a shared container for durable, human-readable data owned by future `hub-*` capabilities. `hub-memory` owns only `.ai-hub/memory/`. Do not inspect, validate, reject, create, modify, or govern sibling directories merely because they exist beneath `.ai-hub/`.

Version 1 still resolves one hub-owned namespace. A future project owner may independently use its own `.ai-hub/memory/`, but project-owner discovery, nearest-owner precedence, multiple namespaces, and cross-namespace roll-up are not implemented.

## Copy-ready example

```toml
schema_version = "1.1"
skill = "hub-memory"
namespace = "hub"
timezone = "America/Los_Angeles"

[paths]
memory = ".ai-hub/memory"
```

Replace the timezone with the hub owner's confirmed IANA timezone.

## Resolution and containment

1. Canonicalize the hub root and configured memory path.
2. Resolve `..`, symlinks, and platform equivalents such as Windows junctions.
3. Require the resolved memory path to remain beneath the hub root.
4. Repeat containment validation on every operation and immediately before every write.
5. Refuse an absolute or relative memory path that escapes the hub root.

The same rules apply if the config or memory directory changes after initialization.

## Optional manual upgrade

A user may explicitly request an upgrade of a valid config 1.0 to 1.1. Show and validate the complete proposed config before applying it. The only semantic edits are:

1. change `schema_version = "1.0"` to `schema_version = "1.1"`;
2. add `namespace = "hub"`.

Do not change `skill`, `timezone`, `paths.memory`, memory records, or optional resources. Never perform this upgrade automatically.

## Sensitive data

The config contains no secrets. Do not add credentials, tokens, cookies, private paths, or auth state. Keep runtime state and caches under `.agents/config/state/` and secrets under `.agents/config/secrets/`; do not place them in `.ai-hub/`.
