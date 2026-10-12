# project-memory ![Agent skill: filesystem memory](https://img.shields.io/badge/agent_skill-filesystem_memory-173D6D?labelColor=252422&style=flat-square)

<a href="https://jjfyi.substack.com/"><img src="jjfyi-readme-mark.svg" alt="JJFYI" align="right" width="92"></a>

**A JJFYI project** JJFYI is where I follow my curiosity, then share what I learn.
[Visit JJFYI on Substack](https://jjfyi.substack.com/)

<br clear="right">

---

`project-memory` helps an AI agent remember enough about an independent project to continue useful work in a later chat. It keeps current context concise and preserves meaningful outcomes, decisions, and approved guidance in Markdown files you can inspect and edit.

The skill is instruction-first. It requires no database, background service, embeddings, Git history, or retained chat transcript. Optional Python helpers validate the package and memory records and safely replace existing records.

## What it remembers

Each project has its own name, namespace, purpose, and scope in root `PROJECT.md`. Its memory and configuration live together under `.project-memory/`:

| File | Purpose |
|---|---|
| `project-memory.toml` | Project-local configuration |
| `CONTEXT.md` | Current stopping point, open threads, and next actions |
| `DIRECTION.md` | Goals, focuses, and current progress |
| `OUTCOMES.md` | Meaningful completed results |
| `DECISIONS.md` | Durable choices and constraints |
| `GUIDANCE.md` | Explicitly approved reusable guidance |
| `CANDIDATES.md` | Lessons and correction evidence awaiting review |

Detailed artifacts stay in their own files; memory links to them. Handoff packets and archives appear only when needed.

This is continuation memory, not a chat transcript or activity log. Current context and progress are updated in place. Outcomes and decisions have dated entries, but they do not capture every action. Daily reporting, Obsidian integration, transcript recovery, task management, and coordination across projects are outside this release's scope.

## Installation

The repository root is the installable skill root. Copy the complete package, including its references, scripts, templates, and license. Exclude `.git/`, Python caches, and any private project data.

### Codex and local ChatGPT workspaces

For a project-local installation, place the package at:

```text
<project>/.agents/skills/project-memory/
```

Install through your host's supported skill mechanism for a shared user-level installation. Skill location does not determine memory ownership: each explicitly selected project uses its own root `PROJECT.md` and `.project-memory/`.

### Claude Code

Use a project-local or personal skill directory:

```text
<project>/.claude/skills/project-memory/
~/.claude/skills/project-memory/
```

This skill needs persistent access to the selected project folder and a supported way to replace existing files atomically. Uploading it to a host without that filesystem access does not establish support.

See the current [OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skill documentation](https://code.claude.com/docs/en/skills) for discovery and installation behavior.

## Start and use

In the project folder, ask:

```text
Initialize project-memory here.
```

The agent asks for missing name, purpose, and scope, proposes a stable namespace and setup, and gets confirmation before creating `PROJECT.md` and `.project-memory/`. It should not guess your project identity from the folder name.

During ordinary work:

| Request | Result |
|---|---|
| “Resume” or “reground” | Read project identity and relevant saved context |
| “Save our progress” | Preserve meaningful results and update continuation state |
| “Create a handoff” | Prepare detailed context for a future session |
| “Check memory” | Review consistency without changing meaning |
| “Review learning candidates” | Review proposed reusable guidance for approval |

Resume loads identity into conversation context once. Ordinary follow-up questions do not reload memory. A later explicit memory operation rereads identity before relying on it or writing. Saving a particular document or artifact does not implicitly save project memory.

Automatic startup is optional. A project may explicitly add this instruction to its host's instruction file:

```text
At the start of each new agent session, before substantive work, use project-memory to resume.
```

The skill does not add that instruction automatically. Resume is read-only; missing or ambiguous memory is reported without silently initializing it.

## Requirements and verification

The helpers use the Python standard library. Package validation and record replacement require Python 3.10+; live-memory validation requires Python 3.11+ for native TOML parsing. Replace `python` below with your environment's Python executable if needed.

From the skill package folder:

```text
python scripts/validate_package.py --root .
python -B -m unittest discover -s tests
```

To validate a separate project's memory without writing:

```text
python scripts/validate_memory.py --owner-root <project-root> --format json
```

Configuration schema 1.2 references project identity in `PROJECT.md`. Legacy schemas 1.0 and 1.1 retain their fixed `hub` semantics without automatic migration. Record schemas remain 1.0. See [configuration](references/config.md) and the [manual](man.project-memory.md) for detailed contracts, exit codes, and recovery behavior.

Without Python, existing records may be updated only through the validated same-directory atomic replacement contract in [references/schema.md](references/schema.md). If the host cannot perform that operation safely, the skill stops without writing.

## Status

Version 0.5.1 is a public preview. Package structure and automated helper tests are checked on Windows; Linux and macOS execution and independent fresh-session behavioral acceptance remain pending. Successful script tests do not establish that every agent follows the instructions correctly.

Keep generated project memory separate from the public skill package. It may contain private project information; choose deliberately whether to version or synchronize it.

## License

The skill source, scripts, templates, and documentation are licensed under the [MIT License](LICENSE).

The JJFYI name and brand assets are excluded from the MIT License. All rights are reserved for those materials.
