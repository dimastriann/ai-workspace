---
name: feature-slice
description: Implement a change as a small vertical slice with atomic commits and tests. Use when adding a feature, fixing a bug, or refactoring.
license: MIT
compatibility: claude-code,codex,opencode
metadata:
  version: "1.0"
---

# Feature slicing

1. Read `AGENTS.md`, then the relevant models, services, routers, hooks, and tests.
2. Slice vertically: `schema → service → router → tests → UI`.
3. Keep one logical change per commit. Use Conventional Commits and include tests with
   the change that makes them pass.
4. Run the `repo-gates` skill before each commit.
5. Refuse `wip` commits, mixed reformatting and behavior changes, skipped tests, and new
   mandatory infrastructure.

## Typical slices

- API feature: migration → service → router → tests → BFF route → query hook → page.
- Bug fix: write the failing regression test first, then the smallest fix.
- Refactor: no behavior change; keep formatting in a separate commit.

## Commit checklist

- [ ] One concern per commit, subject imperative and under ~72 characters.
- [ ] Lint, format, typecheck, tests, and build pass for the touched area.
- [ ] No secrets, debug logging, or commented-out code.
- [ ] Optional services remain optional.
