#!/usr/bin/env python3.12
"""
Bullet Journal Updater for reMarkable
Backs up and updates your journal with recurring items
"""

import yaml
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import zipfile
import uuid

def run_command(cmd, check=True):
    """Run a shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def load_config():
    """Load configuration from config.yml"""
    config_path = Path(__file__).parent / 'config.yml'
    if not config_path.exists():
        print(f"Error: config.yml not found at {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config

def ensure_backup_folder():
    """Ensure 'Bullet Journal Backups' folder exists on reMarkable"""
    # Check if folder exists
    output = run_command('rmapi ls')
    if 'Bullet Journal Backups' not in output:
        print("Creating 'Bullet Journal Backups' folder...")
        run_command('rmapi mkdir "Bullet Journal Backups"')
    return True

def get_backup_name():
    """Generate backup name with date stamp and increment if needed"""
    today = datetime.now().strftime('%Y%m%d')
    base_name = f"Bullet_Journal_{today}"

    # List all files in root (backups are saved to root)
    output = run_command('rmapi ls')

    # Check if base name exists
    if base_name not in output:
        return base_name

    # Find next available increment
    increment = 1
    while True:
        candidate = f"{base_name}_{increment}"
        if candidate not in output:
            return candidate
        increment += 1

def backup_journal(source_name, temp_dir):
    """Create a backup of the source journal"""
    ensure_backup_folder()
    backup_name = get_backup_name()

    print(f"Creating backup: {backup_name}")

    # Download the source journal
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    run_command(f'rmapi get "{source_name}"')
    os.chdir(original_dir)

    # Find the downloaded file
    rmdoc_files = list(Path(temp_dir).glob('*.rmdoc'))
    if not rmdoc_files:
        print("Error: Failed to download source journal for backup")
        sys.exit(1)

    backup_file = rmdoc_files[0]

    # Extract the rmdoc to change its UUID
    backup_extract = Path(temp_dir) / 'backup_extract'
    backup_extract.mkdir()

    with zipfile.ZipFile(backup_file, 'r') as zip_ref:
        zip_ref.extractall(backup_extract)

    # Find old UUID
    pdf_files = list(backup_extract.glob('*.pdf'))
    if not pdf_files:
        print("Error: No PDF in backup")
        sys.exit(1)

    old_uuid = pdf_files[0].stem

    # Generate new UUID for backup
    new_uuid = str(uuid.uuid4())

    # Rename all files
    for old_file in backup_extract.glob(f"{old_uuid}.*"):
        new_file = backup_extract / f"{new_uuid}{old_file.suffix}"
        old_file.rename(new_file)

    # Rename directory if exists
    old_dir = backup_extract / old_uuid
    if old_dir.exists():
        new_dir = backup_extract / new_uuid
        old_dir.rename(new_dir)

    # Repackage with new UUID
    backup_path = Path(temp_dir) / f"{backup_name}.rmdoc"
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk(backup_extract):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(backup_extract)
                zipf.write(file_path, arcname)

    # Upload backup (cd to temp_dir so path is local)
    os.chdir(temp_dir)
    run_command(f'rmapi put "{backup_name}.rmdoc"')
    os.chdir(original_dir)

    print(f"✓ Backup created: {backup_name}")
    print(f"  (Note: Backup saved to root folder due to rmapi limitations)")
    return backup_name

def download_journal(source_name, temp_dir):
    """Download the source journal to temp directory"""
    print(f"Downloading {source_name}...")

    # Download to temp directory
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    run_command(f'rmapi get "{source_name}"')

    os.chdir(original_dir)

    # Find the downloaded .rmdoc file
    rmdoc_files = list(Path(temp_dir).glob('*.rmdoc'))
    if not rmdoc_files:
        print("Error: No .rmdoc file downloaded")
        sys.exit(1)

    return rmdoc_files[0]

def extract_rmdoc(rmdoc_path, extract_dir):
    """Extract .rmdoc file to directory"""
    print("Extracting document...")

    with zipfile.ZipFile(rmdoc_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Find the UUID (base name of files)
    pdf_files = list(Path(extract_dir).glob('*.pdf'))
    if not pdf_files:
        print("Error: No PDF found in .rmdoc")
        sys.exit(1)

    doc_uuid = pdf_files[0].stem
    return doc_uuid

def add_recurring_items_to_pdf(pdf_path, output_path, recurring_items_spans, config):
    """Add recurring items to PDF using overlay with pikepdf to preserve links"""
    import pikepdf
    from reportlab.pdfgen import canvas
    from io import BytesIO
    from datetime import datetime

    # Get configuration
    font_size = config.get('font_size', 36)
    y_position = config.get('y_position', 0.82)
    add_divider = config.get('add_divider', True)

    # Calculate page range for date pages
    date_pages_start = config.get('date_pages_start', 144)
    date_pages_year = config.get('date_pages_year', datetime.now().year)

    # Calculate days in year (365 or 366 for leap year)
    is_leap_year = (date_pages_year % 4 == 0 and date_pages_year % 100 != 0) or (date_pages_year % 400 == 0)
    days_in_year = 366 if is_leap_year else 365

    # Date pages end after all days of the year
    date_pages_end = date_pages_start + days_in_year - 1

    print(f"Date pages: {date_pages_start}-{date_pages_end} (year {date_pages_year}, {days_in_year} days)")

    # Parse recurring item spans and convert dates to page numbers
    page_items_map = {}  # Map of page_num -> list of items for that page

    for span in recurring_items_spans:
        starts_on = datetime.strptime(span['starts_on'], '%Y-%m-%d')
        items = span['items']

        # Calculate which page this date corresponds to
        if starts_on.year == date_pages_year:
            day_of_year = starts_on.timetuple().tm_yday
            span_start_page = date_pages_start + day_of_year - 1

            print(f"Span starting {starts_on.strftime('%Y-%m-%d')} (page {span_start_page}): {items}")

            # Add these items to all pages from span_start_page to end
            for page_num in range(span_start_page, date_pages_end + 1):
                if page_num not in page_items_map:
                    page_items_map[page_num] = []
                page_items_map[page_num].extend(items)

    # Open PDF with pikepdf
    pdf = pikepdf.Pdf.open(pdf_path)
    total_pages = len(pdf.pages)
    print(f"Processing {total_pages} pages...")

    modified_count = 0

    # Process each page that has items
    for page_num, items in sorted(page_items_map.items()):
        if page_num > total_pages:
            break

        page = pdf.pages[page_num - 1]  # Convert to 0-indexed

        # Get page dimensions
        mediabox = page.MediaBox
        width = float(mediabox[2] - mediabox[0])
        height = float(mediabox[3] - mediabox[1])

        # Create overlay with recurring items
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))

        # Draw vertical divider if enabled
        if add_divider:
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(1)
            c.line(width / 2, 0, width / 2, height)

        # Draw recurring items on right side
        x_position = width * 0.55  # Right column
        current_y = height * y_position

        c.setFont("Helvetica", font_size)
        c.setFillColorRGB(0, 0, 0)

        for item in items:
            text = f"• {item}"
            c.drawString(x_position, current_y, text)
            current_y -= font_size * 1.5  # Space between items

        c.save()

        # Create overlay PDF
        packet.seek(0)
        overlay_pdf = pikepdf.Pdf.open(packet)
        overlay_page = overlay_pdf.pages[0]

        # Add overlay as underlay to preserve links on top
        # This preserves the annotation dictionary which contains the links
        page.add_underlay(overlay_page)

        modified_count += 1
        if modified_count % 10 == 0:
            print(f"  Modified {modified_count} pages so far...")

    # Save output
    pdf.save(output_path)
    pdf.close()

    print(f"✓ Modified {modified_count} pages (added recurring items)")

def repackage_rmdoc(extract_dir, doc_uuid, output_path):
    """Repackage the modified document as .rmdoc"""
    print("Repackaging document...")

    # Create zip file with no compression (store only)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(extract_dir)
                zipf.write(file_path, arcname)

    print(f"✓ Created {output_path}")

def upload_journal(rmdoc_path, target_name):
    """Upload the modified journal back to reMarkable"""
    print(f"Uploading new version as '{target_name}'...")

    # Check if target already exists and delete it
    result = run_command('rmapi ls', check=False)
    if target_name in result:
        print(f"  Removing existing '{target_name}'...")
        run_command(f'rmapi rm "{target_name}"')

    # Upload directly with target name
    run_command(f'rmapi put "{rmdoc_path}"')

    # Get the uploaded name (will be the filename without .rmdoc)
    uploaded_name = Path(rmdoc_path).stem

    # Rename if needed
    if uploaded_name != target_name:
        run_command(f'rmapi mv "{uploaded_name}" "{target_name}"')

    print(f"✓ Uploaded as '{target_name}'")
    return target_name

def main():
    print("=" * 60)
    print("Bullet Journal Updater for reMarkable")
    print("=" * 60)
    print()

    # Load config
    config = load_config()
    source_name = config.get('source_journal', 'Bullet Journal')
    recurring_items_spans = config.get('recurring_items_spans', [])

    # Target name includes current year
    current_year = datetime.now().year
    target_name = f"Bullet_Journal_{current_year}"

    print(f"Source journal: {source_name}")
    print(f"Target journal: {target_name}")
    print(f"Recurring item spans: {len(recurring_items_spans)} span(s)")
    print()

    # Create temp directory for work
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create backup (downloads to temp_dir)
        backup_name = backup_journal(source_name, temp_dir)
        print()

        # The backup function already downloaded the journal
        # Find it in temp_dir
        rmdoc_files = list(Path(temp_dir).glob('*.rmdoc'))
        if not rmdoc_files:
            print("Error: No .rmdoc file found after backup")
            sys.exit(1)
        rmdoc_path = rmdoc_files[0]

        # Extract
        extract_dir = Path(temp_dir) / 'extracted'
        extract_dir.mkdir()
        doc_uuid = extract_rmdoc(rmdoc_path, extract_dir)

        print(f"Document UUID: {doc_uuid}")

        # Check if using a base PDF template
        base_pdf_template = config.get('base_pdf_template')
        if base_pdf_template:
            print(f"Using base PDF template: {base_pdf_template}")
            template_path = Path(__file__).parent / base_pdf_template
            if not template_path.exists():
                print(f"Error: Base PDF template not found: {template_path}")
                sys.exit(1)

            # Use template instead of downloaded PDF
            original_pdf = template_path
            modified_pdf = extract_dir / f"{doc_uuid}_modified.pdf"
            add_recurring_items_to_pdf(original_pdf, modified_pdf, recurring_items_spans, config)

            # Replace extracted PDF with modified template
            final_pdf = extract_dir / f"{doc_uuid}.pdf"
            modified_pdf.replace(final_pdf)
        else:
            # Modify the PDF from reMarkable
            original_pdf = extract_dir / f"{doc_uuid}.pdf"
            modified_pdf = extract_dir / f"{doc_uuid}_modified.pdf"
            add_recurring_items_to_pdf(original_pdf, modified_pdf, recurring_items_spans, config)

            # Replace original PDF with modified
            modified_pdf.replace(original_pdf)

        # Generate new UUID for upload (to avoid conflicts)
        new_uuid = str(uuid.uuid4())

        # Rename all files to new UUID
        for old_file in extract_dir.glob(f"{doc_uuid}.*"):
            new_file = extract_dir / f"{new_uuid}{old_file.suffix}"
            old_file.rename(new_file)

        # Rename directory if it exists
        old_dir = extract_dir / doc_uuid
        if old_dir.exists():
            new_dir = extract_dir / new_uuid
            old_dir.rename(new_dir)

        # Repackage
        output_rmdoc = Path(temp_dir) / f"{target_name}.rmdoc"
        repackage_rmdoc(extract_dir, new_uuid, output_rmdoc)

        # Upload as target name
        upload_journal(output_rmdoc, target_name)

    print()
    print("=" * 60)
    print("✓ Journal updated successfully!")
    print(f"✓ Source: {source_name}")
    print(f"✓ Updated: {target_name}")
    print(f"✓ Backup saved as: Bullet Journal Backups/{backup_name}")
    print("=" * 60)

if __name__ == '__main__':
    main()
