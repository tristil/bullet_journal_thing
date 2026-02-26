# BMAD Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Install the bmad-method framework with Claude Code integration so future development work can use BMAD's structured agent/story workflow.

**Architecture:** Run the official bmad-method CLI installer in the project root, selecting Claude Code as the tool and BMad Method (bmm) as the module. This creates `.claude/commands/` with BMAD slash commands and `_bmad/` with module config. The `_bmad-output/` directory (generated artifacts) is already in `.gitignore`.

**Tech Stack:** Node.js/npx, bmad-method npm package, Claude Code

---

### Task 1: Run the BMAD installer

> Note: This is a CLI installation — no application code or tests involved.

**Files:**
- Create: `.claude/commands/` (created by installer)
- Create: `_bmad/` (created by installer)

**Step 1: Run the installer**

```bash
npx bmad-method install
```

When prompted:
- **Installation location:** current directory (`.`)
- **AI tool:** Claude Code
- **Module:** BMad Method (bmm)

Accept all defaults. If asked about `_bmad-output/`, let the installer create it.

**Step 2: Verify files were created**

```bash
ls .claude/commands/
ls _bmad/
```

Expected: `.claude/commands/` contains `.md` command files; `_bmad/` contains `core/` and `bmm/` subdirectories.

**Step 3: Confirm _bmad-output/ is gitignored**

```bash
git status
```

Expected: `_bmad-output/` does NOT appear in untracked files (it's already in `.gitignore`).

**Step 4: Stage and commit the installed files**

```bash
git add .claude/ _bmad/
git commit -m "feat: install bmad-method with Claude Code integration"
```

---

### Task 2: Verify the setup works

**Step 1: Check BMAD help is available in Claude Code**

Open a new Claude Code session in this project and run:

```
/bmad-help
```

Expected: BMAD responds with a list of available commands and workflows.

**Step 2: Done**

BMAD is set up. Future features should start with `/bmad-create-prd` or `/bmad-create-story`.
