# hub-memory

`hub-memory` is a planned portable Agent Skill for progressive, filesystem-first memory in a knowledge-worker hub.

The skill will help an agent:

- maintain concise working context for reliable resumption;
- track goals, ongoing focuses, and progress frontiers;
- preserve meaningful outcomes, decisions, requirements, and approved guidance;
- learn cautiously from correction evidence without turning one-off feedback into permanent rules;
- create high-fidelity handoffs when explicitly needed;
- periodically reconcile, compact, and repair its own memory records.

## Status

Design stage. The architecture and phased build plan are being finalized before the skill package, schemas, fixtures, and behavioral tests are added.

## Version 1 boundary

Version 1 will manage one contained memory namespace in a new hub. It will not provide workstream or project orchestration, task management, periodic activity reports, or migration of an existing memory system.

Development and acceptance testing will use disposable fresh-hub fixtures. The skill will not be installed into the `ai.hub` repository where it originated.
