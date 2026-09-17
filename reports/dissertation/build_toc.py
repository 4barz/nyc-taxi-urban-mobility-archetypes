"""Builds the dissertation with a real, static table of contents.

python-docx has no page-layout engine, so page numbers for a TOC can't be
computed directly. This script instead renders the document, measures where
each heading actually lands (via LibreOffice -> PDF, then locating each
heading's text), and feeds those page numbers back into build_dissertation.py
to produce a final TOC that needs no manual "Update Field" step.

Because inserting the real (longer) TOC shifts every later page down, this
runs the render-measure-rebuild cycle until the page numbers stop changing.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROC = ROOT / "data" / "processed"
VENV_PY = ROOT / "venv" / "bin" / "python3"
DOCX_PATH = HERE / "NYC_Taxi_Urban_Mobility_Dissertation.docx"
PDF_PATH = HERE / "NYC_Taxi_Urban_Mobility_Dissertation.pdf"
HEADING_RECORD_PATH = PROC / "heading_record.json"
TOC_ENTRIES_PATH = PROC / "toc_entries.json"
SOFFICE = "/snap/bin/libreoffice"
MAX_ITERATIONS = 4


def build_docx():
    subprocess.run([str(VENV_PY), str(HERE / "build_dissertation.py")], check=True, cwd=HERE)


def convert_to_pdf():
    PDF_PATH.unlink(missing_ok=True)
    subprocess.run(
        [SOFFICE, "--headless", "--convert-to", "pdf", str(DOCX_PATH)],
        check=True, cwd=HERE, timeout=120,
    )


def _is_toc_listing(page_text, match_idx, text):
    """True if this occurrence of `text` is a TOC entry (heading immediately
    followed by a dot-leader run), not the real heading in the document body."""
    tail = page_text[match_idx + len(text): match_idx + len(text) + 20]
    return bool(re.match(r"\s*\.{3,}", tail))


def measure_heading_pages():
    with open(HEADING_RECORD_PATH) as f:
        headings = json.load(f)  # [[level, text], ...] in document order

    reader = PdfReader(str(PDF_PATH))
    pages_text = [p.extract_text().replace("\n", " ") for p in reader.pages]

    entries = []
    page_ptr, char_ptr = 0, 0
    for level, text in headings:
        if text == "Table of Contents":
            entries.append([level, text, None])
            continue

        found_page = None
        p, start = page_ptr, char_ptr
        while p < len(pages_text):
            idx = pages_text[p].find(text, start)
            if idx == -1:
                p += 1
                start = 0
                continue
            if _is_toc_listing(pages_text[p], idx, text):
                start = idx + len(text)
                continue
            found_page = p
            page_ptr, char_ptr = p, idx + len(text)
            break

        if found_page is None:
            # Shouldn't happen; never regress the search pointer.
            found_page = (entries[-1][2] - 1) if entries and entries[-1][2] else 0
        entries.append([level, text, found_page + 1])
    return entries


def main():
    TOC_ENTRIES_PATH.unlink(missing_ok=True)

    previous = None
    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"--- TOC pass {iteration} ---")
        build_docx()
        convert_to_pdf()
        entries = measure_heading_pages()

        if previous is not None and entries == previous:
            print("Converged: page numbers stable between passes.")
            break

        with open(TOC_ENTRIES_PATH, "w") as f:
            json.dump(entries, f, indent=2)
        previous = entries
    else:
        print("Warning: did not fully converge after max iterations; using last result.", file=sys.stderr)

    # One final build+convert so the saved docx/pdf reflect the converged TOC.
    build_docx()
    convert_to_pdf()
    print(f"Final document: {DOCX_PATH}")
    print(f"Final PDF: {PDF_PATH}")


if __name__ == "__main__":
    main()
