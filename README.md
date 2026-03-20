# Cuyler's Notebook

A minimal static site that serves PDFs organized in a browsable hierarchy. Write in LaTeX, compile to PDF, drop it in the right folder, push. Done.

## Setup

1. **Clone and init:**
   ```bash
   git clone git@github.com:YOUR_USERNAME/notebook.git
   cd notebook
   ```

2. **Enable GitHub Pages:**
   - Go to your repo → Settings → Pages
   - Under "Build and deployment", set Source to **GitHub Actions**

3. **Push to deploy:**
   ```bash
   git add -A && git commit -m "initial" && git push
   ```
   The GitHub Action will build the site and deploy it automatically.

## Usage

### Adding a document

1. Compile your `.tex` file to PDF as usual.
2. Place the PDF in the appropriate folder under `content/`:
   ```
   cp ~/texmf/my-paper.pdf content/philosophy/
   ```
3. Push:
   ```bash
   git add -A && git commit -m "add my-paper" && git push
   ```

That's it. The CI rebuilds index pages automatically.

### Creating a new section

Just create a directory:
```bash
mkdir -p content/mathematics/category-theory
```

Optionally add a `_description.txt` file with a one-liner that appears on the section page:
```bash
echo "Notes on categories, functors, and natural transformations." \
  > content/mathematics/category-theory/_description.txt
```

### Directory structure

```
content/
  mathematics/
    _description.txt          # optional section blurb
    set-theory/
      ch1-propositional-logic.pdf
      ch2-predicate-logic.pdf
    linear-algebra/
      notes-on-axler.pdf
  philosophy/
    newcomb-casino.pdf
  history/
    ancient-near-east/
      shuruppak.pdf
```

The folder hierarchy becomes the URL hierarchy:
- `yoursite.com/` → root index
- `yoursite.com/mathematics/` → math section
- `yoursite.com/mathematics/set-theory/ch1-propositional-logic.pdf` → the PDF

### Local preview

```bash
python3 build.py
cd docs
python3 -m http.server 8000
# open http://localhost:8000
```

## Configuration

Edit the top of `build.py` to change:
- `SITE_TITLE` — your site name
- `SITE_SUBTITLE` — the tagline under the title
- `CONTENT_DIR` — where your PDFs live (default: `content/`)

Edit `style.css` to change fonts, colours, spacing, etc.

## How it works

`build.py` walks `content/`, and for each directory:
1. Generates an `index.html` listing subdirectories and PDFs
2. Copies all PDFs into the output folder

The GitHub Action runs this on every push and deploys to Pages. No dependencies beyond Python 3.
