# BMAD Setup Design

**Date:** 2026-02-26
**Status:** Approved

## Goal

Set up the bmad-method framework in this project to structure future development work and as a learning exercise for the BMAD workflow.

## Approach

Run `npx bmad-method install` interactively in the project root with:
- **Tool:** Claude Code
- **Module:** BMad Method (bmm)

## What Gets Created

```
remarkable/
├── .claude/
│   └── commands/        # BMAD slash commands for Claude Code
├── _bmad/
│   ├── core/            # Required BMAD core files
│   └── bmm/
│       └── config.yaml  # Module config
└── _bmad-output/        # Generated PRDs, stories, arch docs
```

## Git Hygiene

- Commit `_bmad/` and `.claude/commands/` — these are configuration, not generated output
- Add `_bmad-output/` to `.gitignore` — generated artifacts, not source

## Post-Setup

After installation, `/bmad-help` in Claude Code shows all available commands. Key workflows:
- `/bmad-create-prd` — write a product requirements doc
- `/bmad-create-story` — create a user story for a feature
- Agent roles (Architect, Dev, PO) for structured work on future changes
