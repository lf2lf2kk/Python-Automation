import os
import subprocess
from pathlib import Path

# === Metadata ===
TITLE = "Learning"
AUTHOR = "Jeremy"
DATE = "2025"
LOGO = ""
MARGIN = "1in"
FONTSIZE = "12pt"
FONT = "Calibri"

# === Root folder (set this to where your markdown files are) ===
ROOT_DIR = Path(".")

# === Loop through all markdown files (recursively) ===
for md_path in ROOT_DIR.rglob("*.md"):
    # Get parts of the path for naming
    relative_parts = md_path.relative_to(ROOT_DIR).parts

    # Generate PDF file name with folder prefix
    if len(relative_parts) == 2:
        # e.g. exercises\lesson1.md → exercises_lesson1.pdf
        prefix = relative_parts[0]
        pdf_name = f"{prefix}_{md_path.stem}.pdf"
        subtitle = md_path.stem.replace("_", " ").title()

    elif len(relative_parts) > 2:
        # e.g. topic\subtopicA\intro.md → topic_subtopicA_intro.pdf
        prefix = "_".join(relative_parts[:-1])
        pdf_name = f"{prefix}_{md_path.stem}.pdf"
        subtitle = md_path.stem.replace("_", " ").title()

    else:
        # e.g. file directly in root
        pdf_name = f"{md_path.stem}.pdf"
        subtitle = md_path.stem.replace("_", " ").title()

    # Display progress
    print(f"📄 Converting {md_path} → {pdf_name}")

    # === Pandoc command ===
    command = [
        "pandoc", str(md_path),
        "-o", pdf_name,
        "--pdf-engine=xelatex",
        "--toc",
        f'--variable=title:{TITLE}',
        f'--variable=author:{AUTHOR}',
        f'--variable=date:{DATE}',
        f'--variable=subtitle:{subtitle}',
        f'--variable=logo:{LOGO}',
        f'--variable=geometry:margin={MARGIN}',
        f'--variable=fontsize:{FONTSIZE}',
        f'--variable=mainfont:{FONT}',
    ]

    subprocess.run(command, check=True)

print("\n✅ All Markdown files (including subfolders) have been converted to PDF.")
