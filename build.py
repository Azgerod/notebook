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


def breadcrumbs(rel_path: Path, site_title: str, collapsed: set[str] = None) -> str:
    """Generate HTML breadcrumb navigation for a given relative path."""
    parts = rel_path.parts
    if not parts:
        return ""

    if collapsed is None:
        collapsed = set()

    crumbs = [f'<a href="/">Home</a>']
    for i, part in enumerate(parts):
        partial = "/".join(parts[: i + 1])
        if i == len(parts) - 1:
            crumbs.append(f"<span>{pretty_name(part)}</span>")
        elif partial in collapsed:
            # Collapsed intermediate — show as plain text, not a link
            crumbs.append(f"<span>{pretty_name(part)}</span>")
        else:
            href = "/" + partial + "/"
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


# ── Collapse logic ───────────────────────────────────────────────────────────

def _visible_subdirs(d: Path) -> list[Path]:
    """Non-hidden subdirectories of d."""
    return sorted(
        [x for x in d.iterdir() if x.is_dir() and not x.name.startswith(".")],
        key=lambda x: x.name,
    )


def _visible_pdfs(d: Path) -> list[Path]:
    """PDF files directly in d."""
    return sorted(d.glob("*.pdf"), key=lambda f: f.name)


def resolve_collapse(d: Path, content_root: Path):
    """Follow single-child directory chains downward.

    Returns (target, display_name, is_pdf):
      - If the chain ends at a directory with multiple items:
            (dir_path, "Outer / Inner / ...", False)
      - If the chain ends at a single PDF:
            (pdf_path, "Outer / Inner / ... / Doc Name", True)
    """
    name_parts = [pretty_name(d.name)]

    current = d
    while True:
        subdirs = _visible_subdirs(current)
        pdfs = _visible_pdfs(current)

        if len(subdirs) == 0 and len(pdfs) == 1:
            # Single PDF, nothing else → collapse to direct PDF link
            pdf_display = pretty_name(pdfs[0].name)
            # Avoid redundant "Chapter1 / Chapter1" when names match
            if pdf_display != name_parts[-1]:
                name_parts.append(pdf_display)
            return pdfs[0], " / ".join(name_parts), True

        if len(subdirs) == 1 and len(pdfs) == 0:
            # Single subdir, no PDFs → keep collapsing
            current = subdirs[0]
            name_parts.append(pretty_name(current.name))
            continue

        # Multiple items or mixed content → stop here
        return current, " / ".join(name_parts), False


def find_collapsed_dirs(content_root: Path) -> set[str]:
    """Return set of relative dir paths that are collapsed (skipped) intermediates.

    A directory is collapsed if its parent's listing will skip over it because
    the chain resolves past it.
    """
    collapsed = set()

    def _walk(d: Path):
        for sd in _visible_subdirs(d):
            target, _, is_pdf = resolve_collapse(sd, content_root)
            if is_pdf or target != sd:
                # Everything between sd and target (exclusive of target if dir) is collapsed
                cur = sd
                while True:
                    rel = str(cur.relative_to(content_root))
                    collapsed.add(rel)
                    inner_subdirs = _visible_subdirs(cur)
                    inner_pdfs = _visible_pdfs(cur)
                    if is_pdf:
                        # Collapse all the way down
                        if len(inner_subdirs) == 1 and len(inner_pdfs) == 0:
                            cur = inner_subdirs[0]
                            continue
                        elif len(inner_subdirs) == 0 and len(inner_pdfs) == 1:
                            break
                        else:
                            break
                    else:
                        # Collapse up to (but not including) target
                        if cur == target:
                            collapsed.discard(rel)  # target itself is NOT collapsed
                            break
                        if len(inner_subdirs) == 1 and len(inner_pdfs) == 0:
                            cur = inner_subdirs[0]
                            continue
                        break
            # Recurse into the resolved target if it's a directory
            if not is_pdf:
                _walk(target)

    _walk(content_root)
    return collapsed


# ── Page generation ──────────────────────────────────────────────────────────

def generate_index(
    dir_path: Path,
    content_root: Path,
    out_root: Path,
    collapsed: set[str],
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
            f"      {breadcrumbs(rel, SITE_TITLE, collapsed)}",
            f"      <h1>{pretty_name(dir_path.name)}</h1>",
            "    </header>",
        ]

    lines.append('    <main>')

    # Description file (optional): if a _description.txt exists, include it
    desc_file = dir_path / "_description.txt"
    if desc_file.exists():
        desc_text = desc_file.read_text().strip()
        lines.append(f'      <p class="section-desc">{desc_text}</p>')

    # Resolve subdirectories (collapse single-child chains)
    resolved_dirs = []   # (href, display_name, pdf_count)
    collapsed_pdfs = []  # (href, display_name, pdf_path) — dirs that collapsed to a single PDF
    for sd in subdirs:
        target, display_name, is_pdf = resolve_collapse(sd, content_root)
        if is_pdf:
            # Build relative href from current dir to the PDF
            try:
                href = str(target.relative_to(dir_path))
            except ValueError:
                href = str(target.relative_to(content_root))
            collapsed_pdfs.append((href, display_name, target))
        else:
            # Build relative href from current dir to the resolved dir
            try:
                href = str(target.relative_to(dir_path)) + "/"
            except ValueError:
                href = str(target.relative_to(content_root)) + "/"
            n_pdfs = len(list(target.rglob("*.pdf")))
            count_label = f"{n_pdfs} item{'s' if n_pdfs != 1 else ''}"
            resolved_dirs.append((href, display_name, count_label))

    if resolved_dirs:
        lines.append('      <section class="listing">')
        lines.append('        <h2>Sections</h2>')
        lines.append('        <ul class="dir-list">')
        for href, display_name, count_label in resolved_dirs:
            lines.append(
                f'          <li>'
                f'<a href="{href}">{display_name}</a>'
                f'<span class="meta">{count_label}</span>'
                f'</li>'
            )
        lines.append("        </ul>")
        lines.append("      </section>")

    # Combine direct PDFs with collapsed-to-PDF entries
    all_pdfs = [(pdf.name, pretty_name(pdf.name), pdf) for pdf in pdfs]
    all_pdfs += [(href, display_name, pdf_path) for href, display_name, pdf_path in collapsed_pdfs]

    if all_pdfs:
        lines.append('      <section class="listing">')
        if resolved_dirs:
            lines.append('        <h2>Documents</h2>')
        lines.append('        <ul class="pdf-list">')
        for href, display_name, pdf_path in all_pdfs:
            size = file_size_str(pdf_path)
            date = file_date(pdf_path)
            lines.append(
                f'          <li>'
                f'<a href="{href}">{display_name}</a>'
                f'<span class="meta">{date} · {size}</span>'
                f'</li>'
            )
        lines.append("        </ul>")
        lines.append("      </section>")

    if not resolved_dirs and not all_pdfs:
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

    # Determine which directories are collapsed (skipped)
    collapsed = find_collapsed_dirs(content_root)

    # Walk content tree
    all_dirs = [content_root] + sorted(
        [d for d in content_root.rglob("*") if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: str(d),
    )

    built_pages = 0
    for d in all_dirs:
        rel = str(d.relative_to(content_root))

        # Skip collapsed intermediate directories
        if rel != "." and rel in collapsed:
            pass
        else:
            generate_index(d, content_root, out_root, collapsed, is_site_root=(d == content_root))
            built_pages += 1

        # Always copy PDFs to output (even from collapsed dirs, so links work)
        target = out_root / rel if rel != "." else out_root
        target.mkdir(parents=True, exist_ok=True)
        for pdf in d.glob("*.pdf"):
            shutil.copy(pdf, target / pdf.name)

    # Count what was built
    n_pdfs = len(list(content_root.rglob("*.pdf")))
    n_collapsed = len(collapsed)
    print(f"Built {built_pages} index page(s), collapsed {n_collapsed} intermediate(s), copied {n_pdfs} PDF(s) into {out_dir}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build static PDF blog")
    parser.add_argument("--out", default="docs", help="Output directory (default: docs)")
    args = parser.parse_args()
    build(args.out)
