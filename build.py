#!/usr/bin/env python3
"""
Static site generator for a PDF-serving blog.

Walks the content/ directory, finds all PDFs, and generates an index.html
for every directory in the tree. Also copies the global stylesheet into
the output root.

Usage:
    python build.py              # builds into docs/ (for GitHub Pages)
    python build.py --out _site  # builds into _site/
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────

SITE_TITLE = "Cuyler's Notebook"
SITE_SUBTITLE = "Mathematics · Philosophy · History · Literature"
CONTENT_DIR = "content"
STYLE_FILE = "style.css"
FAVICON_FILE = "favicon.ico"


# ── Helpers ──────────────────────────────────────────────────────────────────

def pretty_name(filename: str) -> str:
    """Turn a filename or dirname into a display name.
    
    'set-theory' -> 'Set Theory'
    'ch1-intro.pdf' -> 'Ch1 Intro'
    'notes_on_axler.pdf' -> 'Notes on Axler'
    """
    stem = Path(filename).stem
    return stem.replace("-", " ").replace("_", " ").title()


def relative_depth(path: Path, root: Path) -> int:
    """How many levels deep is `path` relative to `root`?"""
    return len(path.relative_to(root).parts)


def breadcrumbs(rel_path: Path, site_title: str) -> str:
    """Generate HTML breadcrumb navigation for a given relative path."""
    parts = rel_path.parts
    if not parts:
        return ""

    crumbs = [f'<a href="/">Home</a>']
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            crumbs.append(f"<span>{pretty_name(part)}</span>")
        else:
            href = "/" + "/".join(parts[: i + 1]) + "/"
            crumbs.append(f'<a href="{href}">{pretty_name(part)}</a>')

    return '<nav class="breadcrumbs">' + " / ".join(crumbs) + "</nav>"


def file_size_str(path: Path) -> str:
    """Human-readable file size."""
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def file_date(path: Path) -> str:
    """Last-modified date as a readable string."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


# ── Page generation ──────────────────────────────────────────────────────────

def generate_index(
    dir_path: Path,
    content_root: Path,
    out_root: Path,
    is_site_root: bool = False,
) -> None:
    """Generate an index.html for a single directory."""
    rel = dir_path.relative_to(content_root)
    depth = relative_depth(dir_path, content_root)
    css_path = "../" * depth + "style.css" if depth > 0 else "style.css"

    # Collect subdirectories (skip hidden dirs)
    subdirs = sorted(
        [d for d in dir_path.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.name,
    )

    # Collect PDFs
    pdfs = sorted(dir_path.glob("*.pdf"), key=lambda f: f.name)

    # Page title
    if is_site_root:
        page_title = SITE_TITLE
    else:
        page_title = f"{pretty_name(dir_path.name)} — {SITE_TITLE}"

    # Build HTML
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{page_title}</title>",
        f'  <link rel="stylesheet" href="{css_path}">',
    ]
    # Favicon
    favicon_path = "../" * depth + FAVICON_FILE if depth > 0 else FAVICON_FILE
    lines.append(f'  <link rel="icon" href="{favicon_path}" type="image/x-icon">')
    lines += [
        "</head>",
        "<body>",
        '  <div class="container">',
    ]

    if is_site_root:
        lines += [
            '    <header class="site-header">',
            f'      <h1><a href="/">{SITE_TITLE}</a></h1>',
            f'      <p class="subtitle">{SITE_SUBTITLE}</p>',
            "    </header>",
        ]
    else:
        lines += [
            '    <header class="page-header">',
            f"      {breadcrumbs(rel, SITE_TITLE)}",
            f"      <h1>{pretty_name(dir_path.name)}</h1>",
            "    </header>",
        ]

    lines.append('    <main>')

    # Description file (optional): if a _description.txt exists, include it
    desc_file = dir_path / "_description.txt"
    if desc_file.exists():
        desc_text = desc_file.read_text().strip()
        lines.append(f'      <p class="section-desc">{desc_text}</p>')

    # Subdirectories
    if subdirs:
        lines.append('      <section class="listing">')
        lines.append('        <h2>Sections</h2>')
        lines.append('        <ul class="dir-list">')
        for sd in subdirs:
            sd_rel = sd.name + "/"
            n_pdfs = len(list(sd.rglob("*.pdf")))
            count_label = f"{n_pdfs} item{'s' if n_pdfs != 1 else ''}"
            lines.append(
                f'          <li>'
                f'<a href="{sd_rel}">{pretty_name(sd.name)}</a>'
                f'<span class="meta">{count_label}</span>'
                f'</li>'
            )
        lines.append("        </ul>")
        lines.append("      </section>")

    # PDFs
    if pdfs:
        lines.append('      <section class="listing">')
        if subdirs:
            lines.append('        <h2>Documents</h2>')
        lines.append('        <ul class="pdf-list">')
        for pdf in pdfs:
            size = file_size_str(pdf)
            date = file_date(pdf)
            lines.append(
                f'          <li>'
                f'<a href="{pdf.name}">{pretty_name(pdf.name)}</a>'
                f'<span class="meta">{date} · {size}</span>'
                f'</li>'
            )
        lines.append("        </ul>")
        lines.append("      </section>")

    if not subdirs and not pdfs:
        lines.append('      <p class="empty">Nothing here yet.</p>')

    lines += [
        "    </main>",
        '    <footer>',
        f'      <p>{SITE_TITLE} · {datetime.now().year}</p>',
        "    </footer>",
        "  </div>",
        "</body>",
        "</html>",
    ]

    # Write output
    out_dir = out_root / rel if str(rel) != "." else out_root
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text("\n".join(lines))


# ── Main build ───────────────────────────────────────────────────────────────

def build(out_dir: str = "docs") -> None:
    content_root = Path(CONTENT_DIR)
    out_root = Path(out_dir)

    if not content_root.exists():
        print(f"Creating {CONTENT_DIR}/ directory...")
        content_root.mkdir()

    # Clean output
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    # Copy stylesheet
    if Path(STYLE_FILE).exists():
        shutil.copy(STYLE_FILE, out_root / STYLE_FILE)

    # Copy favicon if it exists
    if Path(FAVICON_FILE).exists():
        shutil.copy(FAVICON_FILE, out_root / FAVICON_FILE)

    # Walk content tree
    all_dirs = [content_root] + sorted(
        [d for d in content_root.rglob("*") if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: str(d),
    )

    for d in all_dirs:
        generate_index(d, content_root, out_root, is_site_root=(d == content_root))

        # Copy PDFs to output
        rel = d.relative_to(content_root)
        target = out_root / rel if str(rel) != "." else out_root
        target.mkdir(parents=True, exist_ok=True)
        for pdf in d.glob("*.pdf"):
            shutil.copy(pdf, target / pdf.name)

    # Count what was built
    n_pages = len(all_dirs)
    n_pdfs = len(list(content_root.rglob("*.pdf")))
    print(f"Built {n_pages} index page(s) and copied {n_pdfs} PDF(s) into {out_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build static PDF blog")
    parser.add_argument("--out", default="docs", help="Output directory (default: docs)")
    args = parser.parse_args()
    build(args.out)
