---
title: 'Day-of-Week Label on Daily Pages'
slug: 'day-of-week-label'
created: '2026-02-26'
status: 'implementation-complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.12', 'pikepdf', 'reportlab']
files_to_modify: ['update_journal.py']
code_patterns: ['reportlab canvas overlay', 'date page calculation', 'pikepdf add_underlay', 'timedelta date math']
test_patterns: ['manual visual verification only - no automated tests in project']
---

# Tech-Spec: Day-of-Week Label on Daily Pages

**Created:** 2026-02-26

## Overview

### Problem Statement

Daily pages in the Bullet Journal show the date number from the PDF template but no weekday name. Users cannot tell at a glance what day of the week a page belongs to without manually counting.

### Solution

For every date page, calculate the 3-letter day abbreviation (Mon, Tue, Wed, Thu, Fri, Sat, Sun) from the existing page-to-date math already in the script, and render it to the left of the date number using the reportlab canvas overlay system already used for recurring items. The label uses a separate hardcoded font size (to match the date heading size, not the smaller recurring items size) and renders on ALL date pages (not just those with recurring items).

### Scope

**In Scope:**
- Render 3-letter day abbreviation on every date page (pages `date_pages_start` through `date_pages_end`)
- Position: top-left area of the page, to the left of the date number (hardcoded coordinates)
- Font: Helvetica, hardcoded size to match the date heading (separate from `font_size` config which controls recurring items)
- Applies even to date pages with no recurring items

**Out of Scope:**
- Configuring day label position or font size via `config.yml`
- Showing month name or full date in the label
- Non-date pages (index, monthly logs, etc.)

## Context for Development

### Codebase Patterns

- Overlays are built with `reportlab.pdfgen.canvas.Canvas`, saved to a `BytesIO` buffer, opened with `pikepdf`, then added to the page via `page.add_underlay(overlay_page)`.
- `add_underlay()` is used (not `add_overlay()`) to keep clickable links on top of the drawn content.
- The function `add_recurring_items_to_pdf()` at line 204 owns all PDF rendering.
- Draw pattern inside canvas: `c.setFont("Helvetica", font_size)` → `c.setFillColorRGB(0, 0, 0)` → `c.drawString(x, y, text)`.
- Date-to-page mapping formula (line 260): `page_date = datetime(date_pages_year, 1, 1) + timedelta(days=(page_num - date_pages_start))`
- `timedelta` is imported at module level (line 11: `from datetime import datetime, timedelta`) and is already used inside `add_recurring_items_to_pdf` at line 260 via module scope. **No import changes needed.**
- The local import at line 209 (`from datetime import datetime`) only imports `datetime` — `timedelta` comes from module level.
- The render loop currently (line 278): `for page_num, items in sorted(page_items_map.items()):` — iterates only pages with recurring items.
- **There is NO `if items:` guard** — `c.save()` and `page.add_underlay()` are called unconditionally for every loop iteration. No guard needs to be removed.
- `page_items_map` is a `dict[int, list[str]]` — no date objects stored, just items.
- **Side effect of loop change — confirmed by user**: the divider (`add_divider`) currently only draws on pages with items. After expanding to all date pages it will draw on all date pages (including those with no recurring items). This is intentional and user-confirmed.
- Bounds guard at line 279: `if page_num > total_pages: break` — must be kept.

### Files to Reference

| File | Purpose |
| ---- | ------- |
| [update_journal.py](update_journal.py) | Only file to modify. Render loop at lines 277–324. |
| [config.yml](config.yml) | Runtime config — `font_size`, `date_pages_start`, `date_pages_year` |

### Technical Decisions

- **Position is hardcoded.** User confirmed no config param needed. Initial coordinates: `x = width * 0.04`, `y = height * 0.93`. Must be verified visually after first run — may need tuning.
- **Font size is a separate hardcoded constant.** The day label must match the date heading size in the template, which is larger than the recurring items `font_size` (36pt). Since the template PDF can't be inspected directly, use a named constant `DAY_LABEL_FONT_SIZE = 72` as the initial guess and tune by trial and error. This constant is defined at **function level inside `add_recurring_items_to_pdf()`**, right after the config unpacking block (before `# Open PDF with pikepdf` at line ~270) — not inside the loop, so it is only evaluated once.
- **Date recalculation in render loop.** Recalculate `page_date` inside the rendering loop using the same `timedelta` formula already at line 260. No structural changes needed to `page_items_map`.
- **Expand iteration from `page_items_map` to all date pages.** Change loop header; fetch items with `.get()`.
- **`--dry-run` flag skips all reMarkable interaction.** In dry-run mode: skip `journal_exists()`, `backup_journal()`, and `upload_journal()`. Always behave like first-run (generate fresh UUID, create metadata). Save the output `.rmdoc` to the current working directory as `dry_run_output.rmdoc` and print its path. This avoids touching reMarkable while tuning PDF rendering.
- **`argparse` for CLI parsing.** Add `import argparse` at module level. Parse `--dry-run` at the top of `main()`. `argparse` is stdlib — no new dependency.

## Implementation Plan

### Tasks

- [x] Task 1: Change the render loop header to iterate all date pages
  - File: `update_journal.py`
  - Action: Replace line 278 `for page_num, items in sorted(page_items_map.items()):` with the following — the guard must be the **first** line inside the loop body, before any dict lookup:
    ```python
    for page_num in range(date_pages_start, date_pages_end + 1):
        if page_num > total_pages:
            break
        items = page_items_map.get(page_num, [])
        # ... rest of loop body unchanged ...
    ```
  - Notes: The guard stays first — it was originally line 279 and its position relative to the new `items =` line is explicit above.

- [x] Task 2: Calculate `page_date` and `day_abbr` inside the render loop
  - File: `update_journal.py`
  - Action: After `items = page_items_map.get(page_num, [])`, add:
    ```python
    days_from_start = page_num - date_pages_start
    page_date = datetime(date_pages_year, 1, 1) + timedelta(days=days_from_start)
    day_abbr = page_date.strftime('%a')  # 'Mon', 'Tue', 'Wed', etc.
    ```
  - Notes: `timedelta` is available from module-level import — no import change needed.

- [x] Task 3: Define `DAY_LABEL_FONT_SIZE` at function level and draw the day label on the canvas
  - File: `update_journal.py`
  - Action: First, add the constant **after the config unpacking block, before `# Open PDF with pikepdf`** (around line 270) — this is inside `add_recurring_items_to_pdf()` but outside the render loop:
    ```python
    DAY_LABEL_FONT_SIZE = 72  # Tune to match date heading size in template
    ```
    Then, the existing canvas drawing block (lines 303–309) currently reads:
    ```python
    c.setFont("Helvetica", font_size)   # line 303 — REMOVE this line from here
    c.setFillColorRGB(0, 0, 0)          # line 304 — keep
    for item in items:                   # line 306 — keep
        ...
    ```
    Replace that block with the following (the `setFont` for `font_size` moves to after the label draw):
    ```python
    c.setFillColorRGB(0, 0, 0)
    # Draw day-of-week label at heading scale
    c.setFont("Helvetica", DAY_LABEL_FONT_SIZE)
    c.drawString(width * 0.04, height * 0.93, day_abbr)
    # Restore font for recurring items
    c.setFont("Helvetica", font_size)
    for item in items:
        ...
    ```
    The `c.setFont("Helvetica", font_size)` line is **moved** (not duplicated) — delete it from line 303 and add it after the label draw. `c.setFillColorRGB(0, 0, 0)` stays in place.
  - Notes: `DAY_LABEL_FONT_SIZE = 72` is an initial guess — tune by running the script, opening the output PDF, and comparing the label size to the printed date heading. Both the font size and x/y coordinates may need adjustment.

- [x] Task 4: Update log messages for consistency
  - File: `update_journal.py`
  - Action: Two changes:
    1. Change the progress print at lines 323–324 from `print(f"  Modified {modified_count} pages so far...")` to `print(f"  Processed {modified_count} pages so far...")`
    2. Change the final print at line 330 from `print(f"✓ Modified {modified_count} pages (added recurring items)")` to `print(f"✓ Processed {modified_count} date pages (added day labels and recurring items)")`
  - Notes: Both prints use "Modified" which is now incorrect since all date pages are processed. `modified_count` now counts all date pages, not just those with items.

- [x] Task 5: Add `--dry-run` CLI flag
  - File: `update_journal.py`
  - Action: Add `import argparse` to the module-level imports (line ~7, alongside existing imports). At the top of `main()`, before any other logic, add:
    ```python
    parser = argparse.ArgumentParser(description='Bullet Journal Updater')
    parser.add_argument('--dry-run', action='store_true',
                        help='Process PDF only, skip backup and upload, save .rmdoc locally')
    args = parser.parse_args()
    dry_run = args.dry_run
    ```
  - Notes: `argparse` is Python stdlib — no install needed.

- [x] Task 6: In `main()`, branch on `dry_run` to skip reMarkable interaction
  - File: `update_journal.py`
  - Action: Wrap the `source_exists` block so that in dry-run mode we always use the first-run path (generate UUID, create metadata, skip backup/download). Then wrap the upload block:
    ```python
    if dry_run:
        # Skip journal_exists check, backup, and upload
        # Always use first-run path: generate UUID and metadata
        extract_dir = Path(temp_dir) / 'extracted'
        extract_dir.mkdir()
        doc_uuid = str(uuid.uuid4())
        create_metadata_files(extract_dir, doc_uuid)
        backup_name = None
    else:
        source_exists = journal_exists(source_name)
        if source_exists:
            # ... existing backup + extract logic ...
        else:
            # ... existing first-run logic ...
    ```
    And replace the `upload_journal(...)` call with:
    ```python
    if dry_run:
        dry_run_path = Path.cwd() / 'dry_run_output.rmdoc'
        shutil.copy(output_rmdoc, dry_run_path)
        print(f"✓ Dry run complete. Output saved to: {dry_run_path}")
        print("  No backup created, no upload performed.")
    else:
        upload_journal(output_rmdoc, target_name)
    ```
  - Notes: `shutil` is already imported (line 15). The `shutil.copy` call **must remain inside the `with tempfile.TemporaryDirectory() as temp_dir:` block** — `output_rmdoc` is a path inside the temp directory and will be deleted when that `with` block exits. Placing the copy outside the block will cause a file-not-found error. The final summary block at the end of `main()` should also be guarded — skip the backup/upload lines when `dry_run` is True. In dry-run mode, the script always uses the base PDF template; it does not download or process any existing annotations from reMarkable.

### Acceptance Criteria

- [ ] AC1: Given `date_pages_start: 144` and `date_pages_year: 2026` (365 days), when `update_journal.py` runs, then every page from 144 to 508 has a day abbreviation rendered in the top-left area of the page.

- [ ] AC2: Given page 201 corresponds to **Friday Feb 27, 2026** (verified: `datetime(2026, 1, 1) + timedelta(days=201-144)` = `datetime(2026, 1, 1) + timedelta(57)` = Feb 27, 2026; Jan 1 2026 is a Thursday, +57 days = Thursday + 1 mod 7 = Friday), when the overlay is rendered for that page, then `day_abbr` = `"Fri"`.

- [ ] AC3: Given a date page has no entry in `page_items_map` (no recurring items configured for that day), when the render loop processes it, then an overlay containing just the day label is still applied — no bullet items, but the day abbreviation is present.

- [ ] AC4: Given pages 1–143 are non-date pages (index, monthly logs, etc.), when `update_journal.py` runs, then `page_num` never enters the range `1–143` in the render loop and those pages are untouched.

- [ ] AC5: Given the day label is rendered, then it uses `DAY_LABEL_FONT_SIZE` (a separate hardcoded constant, not `font_size`) — visually the label should appear at a similar scale to the printed date heading in the template.

- [ ] AC6: Given a normal run (no `--dry-run`), when the script completes successfully, then a backup named `Bullet_Journal_YYYYMMDD` (or with increment) is visible in the reMarkable root folder — confirming the backup mechanism is unaffected by the render loop changes.

- [ ] AC7: Given `--dry-run` is passed, when the script runs, then: (a) no rmapi commands are executed, (b) a file `dry_run_output.rmdoc` is written to the current working directory, (c) the script prints its path, (d) no backup is created on reMarkable.

## Additional Context

### Dependencies

- `reportlab` — already a project dependency, no new installs needed
- `pikepdf` — already a project dependency
- `argparse` — Python stdlib, no install needed
- `shutil` — Python stdlib, already imported at line 15

### Testing Strategy

Manual visual verification only (no automated test infrastructure exists for this project):

**PDF tuning cycle (use `--dry-run`):**
1. Run `./update_journal.py --dry-run`
2. Open `dry_run_output.rmdoc` — extract as ZIP, open the PDF inside
3. Navigate to any date page and confirm a 3-letter day abbreviation appears to the left of the date number
4. Check a page with no recurring items — day label should still appear
5. Check a non-date page (e.g., page 1) — no day label should appear
6. If the label size is wrong, adjust `DAY_LABEL_FONT_SIZE` in Task 3 and re-run
7. If the label position is off, adjust `width * 0.04` and/or `height * 0.93` in Task 3 and re-run

**Full run verification (once PDF looks correct):**
8. Run `./update_journal.py` (no flag) and confirm: backup appears in reMarkable root, journal is updated on device

### Notes

- The exact position and size of the date heading in the template PDF is unknown without rendering it. Both `DAY_LABEL_FONT_SIZE` (initial: 72) and coordinates (`width * 0.04`, `height * 0.93`) are initial estimates — expect one or two rounds of visual tuning using `--dry-run`.
- If the date heading sits low on the page, `height * 0.93` will be too high. Check by eye and adjust.
- After drawing the day label at `DAY_LABEL_FONT_SIZE`, the canvas font is explicitly reset to `font_size` before drawing recurring items — so item rendering is unaffected by the font size change.
- **`strftime('%a')` is locale-sensitive.** On macOS with an English locale it returns Mon/Tue/Wed/Thu/Fri/Sat/Sun as expected. If the script is ever run in a non-English environment and produces wrong day names, fix by adding `import locale; locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')` before the `strftime` call. Not required now (personal script on known English macOS).
- **`timedelta` scope**: the local import at line 209 (`from datetime import datetime`) intentionally does not import `timedelta` — that comes from the module-level import at line 11. Do not add `timedelta` to the local import; both the existing usage at line 260 and the new usage in Task 2 rely on module scope, which is correct.
- **Edge case — template PDF shorter than `date_pages_end`**: if the base PDF template has fewer than `date_pages_end` pages (508 for 2026), the `if page_num > total_pages: break` guard exits the loop early with no error. Some date pages will be unlabeled. This is acceptable — the PDF template should always have 365+ date pages, but if it does not, the script will not crash.
