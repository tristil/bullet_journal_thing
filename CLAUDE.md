# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal automation tool for managing a Bullet Journal on a reMarkable tablet. The main script (`update_journal.py`) downloads a journal from reMarkable, adds recurring daily tasks to date pages, and uploads it back with backups.

**Key constraint**: The underlying Bullet Journal PDF template is copyrighted and cannot be included. Users must extract their own PDF template from an existing journal.

## Critical Rules

**NEVER delete files on reMarkable without explicit user permission.**

If you need to delete a file using `rmapi rm`:
1. **ASK the user for permission first** - explain why and what will be deleted
2. **Download a backup copy** of the file before deletion using `rmapi get`
3. Only proceed with deletion after user approval

Deletions via rmapi are permanent and cannot be undone. Always err on the side of caution.

## Running the Script

```bash
./update_journal.py
```

The script requires:
- `rmapi` installed and authenticated (`rmapi version`)
- Python 3.12+ with `pyyaml`, `pikepdf`, and `reportlab`
- A `config.yml` file in the repository root
- A base PDF template file (specified in config.yml)

## Configuration (config.yml)

The script is driven entirely by `config.yml`:

- **source_journal**: Name of the journal on reMarkable to back up
- **base_pdf_template**: Local PDF file extracted from an existing journal (REQUIRED)
- **recurring_items_spans**: List of date-based item sets
  - Each span has `starts_on` (YYYY-MM-DD) and `items` (list of tasks)
  - Optional `day_of_week` dict for day-specific items (e.g., `monday: ["Put out compost"]`)
  - Spans are cumulative: later spans replace earlier ones from their start date forward
- **date_pages_start**: Page number where daily pages begin (e.g., 144)
- **date_pages_year**: Year for date page calculations (e.g., 2026)
- **font_size**, **y_position**, **add_divider**: Display formatting options

## Architecture

### Core Workflow

1. **Check existence**: Verify if source journal exists on reMarkable
   - If exists: Download, extract, backup (with new UUID)
   - If not exists: Create fresh journal with metadata files (first-time setup)

2. **PDF processing**:
   - Use local `base_pdf_template` as the PDF base (never download PDF from reMarkable)
   - Calculate which pages correspond to which dates based on `date_pages_start` and `date_pages_year`
   - For each date page, determine which recurring items apply (based on date spans)
   - Add day-of-week items to appropriate days
   - Use `pikepdf` with `page.add_underlay()` to preserve PDF links and annotations

3. **Repackaging**:
   - Generate new UUID to avoid conflicts
   - Repackage as .rmdoc (ZIP with `ZIP_STORED` compression)
   - Upload to reMarkable, replacing any existing target journal

### .rmdoc File Format

A `.rmdoc` is a ZIP archive (uncompressed) containing:
- `{UUID}.pdf` - The template/background PDF
- `{UUID}.content` - JSON metadata (fileType, pageCount, lastOpenedPage, etc.)
- `{UUID}.pagedata` - Page metadata (usually empty array `[]` for PDFs)
- `{UUID}.metadata` - Additional metadata (created by reMarkable on upload)
- `{UUID}/` directory - Contains `.rm` files with handwritten annotations per page

**Key insight**: Handwritten annotations are in separate `.rm` files. This script only replaces the PDF; all handwriting is preserved.

### First-Time Journal Creation

When the source journal doesn't exist yet:
1. Script generates a new UUID
2. Creates `.content` and `.pagedata` metadata files (required for rmapi to upload)
3. Processes the base PDF template to add recurring items
4. Packages everything into a valid .rmdoc without needing an existing source

This handles the bootstrap case where you're creating a journal for the first time.

### UUID Management

- Every upload gets a fresh UUID to avoid conflicts with cached documents
- Backups also get new UUIDs (distinct from the journal they back up)
- Original UUID preserved in annotation directory structure when extracting existing journals

### Date Page Calculation

- Date pages start at `date_pages_start` (e.g., page 144)
- Script calculates days in year (365 or 366 for leap years)
- Each page maps to one day: page N = Jan 1 + (N - date_pages_start) days
- Only pages within the date range are modified; note pages remain untouched

### Recurring Items Logic

Items are span-based, not replacement-based:
- Each span starts on `starts_on` date and continues through Dec 31
- Later spans can add to or replace earlier spans
- Day-of-week items are added after regular daily items for matching weekdays

Example: If span 1 has `["Task A"]` starting Jan 1, and span 2 has `["Task B"]` starting Mar 1, then:
- Jan 1 - Feb 28: Page shows "Task A"
- Mar 1 - Dec 31: Page shows "Task B"

## Critical Implementation Details

### PDF Link Preservation

Use `pikepdf` (not PyPDF2) with `page.add_underlay()`:
- Adding as underlay keeps clickable links on top
- Preserves the PDF annotation dictionary
- Maintains navigation like "← Index" and "← Monthly log" links

### Backup System

Backups are named `Bullet_Journal_YYYYMMDD` with auto-increment if multiple per day:
- `get_backup_name()` checks existing files and finds next available name
- Backups saved to reMarkable root folder (rmapi limitation)
- Each backup has unique UUID to avoid document conflicts

### rmapi Integration

All reMarkable operations use `rmapi` CLI:
- `rmapi ls` - List files, check existence
- `rmapi get "{name}"` - Download to current directory
- `rmapi put "{path}"` - Upload file
- `rmapi rm "{name}"` - Delete file
- `rmapi mv "{old}" "{new}"` - Rename file

The script changes directories when needed (using `os.chdir`) to ensure rmapi operations work correctly.

## Notable Edge Cases

1. **First run**: Script detects missing source journal and creates metadata files from scratch
2. **Leap years**: Automatically calculates 366 days for leap years in date range
3. **Network retries**: rmapi can have transient connection issues; user should retry
4. **Metadata on upload**: rmapi adds `.metadata` file automatically; script only creates `.content` and `.pagedata`

## Git Repository Notes

- `config.yml` is checked in with the owner's personal configuration
- Base PDF templates should NOT be checked in (copyrighted material)
- `remarkable_files/` directory contains an unrelated project (remarks library) - ignore for this project
