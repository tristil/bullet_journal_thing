# Bullet Journal Thing for reMarkable

Fulfills an extremely niche use case. You have a Remarkable notebook that uses
the Bullet Journal template. You want to have recurring items that you don't
want to have to enter by hand every day. This script:
 - downloads your current bullet journal notebook
 - uses a local PDF template as the base (which you extract from your own journal)
 - adds a right-hand column with the recurring items specified
 - creates a backup in Remarkable of the current bullet journal notebook
 - uploads a new notebook with the recurring items

**Important Notes:**
- Use at your own risk. Make manual backups of your notebooks before trying.
- You must provide your own PDF template extracted from your journal (the underlying Bullet Journal PDF template is copyrighted and cannot be included in this repository).
- All code written by Claude Code, including this README.

## Requirements

- Python 3.12+
- `rmapi` - reMarkable Cloud API client ([installation instructions](https://github.com/juruen/rmapi))
- Python packages:
  - `pyyaml`
  - `pikepdf`
  - `reportlab`

## Installation

1. **Install rmapi**:
   ```bash
   brew install rmapi
   ```

2. **Install Python dependencies**:
   ```bash
   pip3.12 install pyyaml pikepdf reportlab
   ```

3. **Authenticate rmapi**:
   ```bash
   rmapi version
   ```
   Follow the prompts to authenticate with your reMarkable account.

4. **Extract your base PDF template**:

   You need to get the original PDF template from your existing Bullet Journal. This preserves all the links and navigation elements.

   ```bash
   # Download your existing journal
   rmapi get "Bullet_Journal_2025"

   # Extract the .rmdoc file (it's a ZIP archive)
   unzip Bullet_Journal_2025.rmdoc

   # Find and copy the PDF file (named with a UUID)
   # Look for a file like: a98d24c6-5250-44e1-8707-bc1e949968c4.pdf
   cp *.pdf Bullet_Journal_original.pdf

   # Clean up
   rm -rf Bullet_Journal_2025.rmdoc
   rm -rf a98d24c6-5250-44e1-8707-bc1e949968c4*  # Use the actual UUID from your file
   ```

   This `Bullet_Journal_original.pdf` file becomes your template. The script will use this as the base and only download your handwritten annotations from reMarkable.

5. **Set up configuration**:
   ```bash
   cp config.yml.template config.yml
   ```
   Edit `config.yml` with your preferences.

## Configuration

Edit `config.yml` to customize your setup:

```yaml
# Name of your source journal on reMarkable
source_journal: "Bullet_Journal_2025"

# REQUIRED: Path to base PDF template file
# Extract this from your existing journal (see Installation step 4)
base_pdf_template: "Bullet_Journal_original.pdf"

# List of recurring item spans
# Each span has a starts_on date and a list of items to add from that date forward
recurring_items_spans:
  - starts_on: "2025-01-01"
    items:
      - "Take vitamins"
      - "Meditate"
  - starts_on: "2025-02-01"
    items:
      - "Check email"
      - "Review calendar"

# Date page configuration
date_pages_start: 144  # Page where date pages (one per day) start
date_pages_year: 2025  # Year that the date pages cover

# Configuration for how items are displayed
font_size: 36          # Size of text
y_position: 0.82       # Vertical position (0.0 = bottom, 1.0 = top)
add_divider: true      # Draw vertical line down middle of page
```

### Configuration Options

- **source_journal**: Name of your journal file on reMarkable
- **base_pdf_template**: **(REQUIRED)** Local PDF file to use as template. Extract this from your existing journal using the instructions in Installation step 4. Only your handwritten annotations (`.rm` files) are downloaded from reMarkable; the PDF template is taken from this local file.
- **recurring_items_spans**: List of item sets with start dates
  - **starts_on**: Date in YYYY-MM-DD format when these items should begin appearing
  - **items**: List of tasks to add from that date through the end of the year
- **date_pages_start**: First page number that contains daily pages
- **date_pages_year**: Year that the date pages represent
- **font_size**: Size of the task text
- **y_position**: Vertical position of first item (0.0 = bottom, 1.0 = top)
- **add_divider**: Whether to draw a vertical line down the middle of each page

## Usage

Run the script to update your journal:

```bash
./update_journal.py
```

The script will:
1. Create a backup of your current journal
2. Download the journal from reMarkable (or use local template if configured)
3. Add recurring items to the appropriate date pages
4. Upload the updated journal back to reMarkable

### Example Output

```
============================================================
Bullet Journal Updater for reMarkable
============================================================

Source journal: Bullet_Journal_2025
Target journal: Bullet_Journal_2025
Recurring item spans: 2 span(s)

Creating backup: Bullet_Journal_20251211
✓ Backup created: Bullet_Journal_20251211

Extracting document...
Document UUID: a98d24c6-5250-44e1-8707-bc1e949968c4
Using base PDF template: Bullet_Journal_original.pdf
Date pages: 144-508 (year 2025, 365 days)
Span starting 2025-01-01 (page 144): ['Take vitamins', 'Meditate']
Span starting 2025-02-01 (page 176): ['Check email', 'Review calendar']
Processing 544 pages...
  Modified 10 pages so far...
  Modified 20 pages so far...
...
✓ Modified 365 pages (added recurring items)
Repackaging document...
✓ Created Bullet_Journal_2025.rmdoc
Uploading new version as 'Bullet_Journal_2025'...
✓ Uploaded as 'Bullet_Journal_2025'

============================================================
✓ Journal updated successfully!
✓ Source: Bullet_Journal_2025
✓ Updated: Bullet_Journal_2025
✓ Backup saved as: Bullet_Journal_20251211
============================================================
```

## How It Works

### Recurring Items Spans

Items are added based on date spans. When you specify a `starts_on` date:
- Items from that span will appear on all pages from that date through December 31st
- Multiple spans can be defined, and items accumulate
- Only dates matching `date_pages_year` are processed

**Example**: With these spans:
```yaml
recurring_items_spans:
  - starts_on: "2025-01-01"
    items:
      - "Take pills"
  - starts_on: "2025-03-15"
    items:
      - "Exercise"
```

- January 1 - March 14: Only "Take pills" appears
- March 15 - December 31: Both "Take pills" and "Exercise" appear

### Date Page Calculation

The script automatically calculates which pages contain date entries:
- Uses `date_pages_start` as the first date page (typically January 1)
- Calculates the number of days in the year (365 or 366 for leap years)
- Date pages end at `date_pages_start + days_in_year - 1`
- Only date pages are modified; note pages remain untouched

### Preserving Annotations

The reMarkable `.rmdoc` format is a ZIP archive containing:
- A PDF file (the template/background)
- `.rm` files (your handwritten annotations)
- Metadata files (`.content`, `.metadata`, `.pagedata`)

This script:
- Replaces only the PDF file with the updated version
- Keeps all `.rm` annotation files unchanged
- Your handwriting remains exactly as you wrote it

### Preserving PDF Links

The script uses `pikepdf` library with `page.add_underlay()` to:
- Add recurring items as an underlay beneath existing content
- Preserve the PDF's annotation dictionary which contains clickable links
- Maintain navigation elements like "← Index" and "← Monthly log" links

## Backups

Backups are automatically created before each update:
- Named with date: `Bullet_Journal_YYYYMMDD`
- Incremented if multiple backups on same day: `Bullet_Journal_YYYYMMDD_1`
- Uploaded to your reMarkable (root folder due to rmapi limitations)
- Each backup has a unique UUID to avoid conflicts

## Troubleshooting

### Network Errors

If you see connection errors during download:
```
ERROR: read tcp [...]: connection reset by peer
```
Simply retry the script. Network issues with reMarkable Cloud are usually temporary.

### No Items Appearing

If the script shows "Modified 0 pages":
- Check that `starts_on` dates use the same year as `date_pages_year`
- Verify `date_pages_start` matches your journal's layout
- Ensure `recurring_items_spans` is not empty

### Links Not Working

If PDF links stop working:
- Ensure you're using the latest version of the script (uses `pikepdf`)
- Verify your `base_pdf_template` has working links in the original
- Check that the original PDF links work before running the script

### Items in Wrong Position

Adjust these configuration values:
- `y_position`: Move items up/down (0.0 = bottom, 1.0 = top)
- `font_size`: Change text size
- `add_divider`: Toggle the vertical dividing line

## Technical Details

### File Format

The reMarkable `.rmdoc` format:
- ZIP archive with no compression (`ZIP_STORED`)
- Contains PDF and annotation files named with UUID
- Directory structure: `<UUID>/` containing page `.rm` files

### PDF Manipulation

- Uses `pikepdf` (not PyPDF2) to preserve PDF annotations
- Uses `reportlab` to create overlay PDFs with recurring items
- Overlays added as underlays to keep links on top

### UUID Management

- New UUID generated for each upload to avoid conflicts
- Backups also get new UUIDs
- Original UUID preserved in annotation directory structure

## License

This project is provided as-is for personal use.

## Contributing

This is a personal project, but suggestions and improvements are welcome via issues or pull requests.
