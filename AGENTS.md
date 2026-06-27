# cqb-blog

Personal blog at `cqb.github.io` built with a Python/pandoc static site generator (adapted from [vbuterin/blogmaker](https://github.com/vbuterin/blogmaker)) served via GitHub Pages.

## Adding a post

1. Write markdown in Obsidian (or any editor) with YAML frontmatter.
2. Drop the `.md` file into `posts/slug.md` — date is read from the `date` field in frontmatter.
3. Run `python3 publish.py` to regenerate `index.html`, category pages, and `feed.xml`, then commit everything and push to `main`.

Do **not** edit generated files (`index.html`, `feed.xml`, category `.html` files, or post `.html` files) by hand — they are overwritten on every build.

## Post format

```yaml
---
title: My Post Title
date: YYYY-MM-DD
categories: [category1, category2]
---
```

- `title`, `date`, `categories` are required.
- Categories are lowercased and become category pages automatically.
- `icon` is optional (defaults to site icon from `config.yml`).
- Body is standard markdown.

## Key files

| Path | Source or generated? | Purpose |
|---|---|---|
| `posts/` | Source | Markdown posts (your input) |
| `publish.py` | Source | Build script — reads frontmatter, runs pandoc, outputs HTML |
| `config.yml` | Source | Site title, domain, icon |
| `css/main.css` | Source | Blog styling, dark mode, sidenote styles |
| `publish.py` (FOOTNOTE_JS) | Source | Inline JS for sidenote positioning & narrow-screen tooltip |
| `index.html` | Generated | Post listing / homepage |
| `feed.xml` | Generated | RSS feed |
| `*.html` (at root) | Generated | Per-category post listings (e.g. `general.html`) |

## Dev commands

```sh
# Build all posts locally (requires pandoc)
python3 publish.py

# Serve the generated site locally (static HTTP server)
python3 -m http.server 8000
# Open http://localhost:8000 in a browser
```

## Architecture notes

- **No build tool beyond pandoc.** No npm, no bundler. Pure Python + pandoc.
- **GitHub Pages** is configured to serve from the root of the main branch.
- **Generated files are committed to the repo** — this is intentional so GitHub Pages can serve them directly without an extra build step. Run `python3 publish.py` before every commit to regenerate them.
- Dark/light mode toggle is pure CSS/JS (no framework).
- Categories are derived from the `categories` field in each post's frontmatter.
- **Sidenote margin-footnotes**: `reorganize_footnotes()` in `publish.py` runs post-pandoc: extracts footnote content from the end-section via regex, wraps each footnote ref with `.sidenote-wrapper`/`.sidenote-content`, and replaces the end-section with a compact version. `FOOTNOTE_JS` positions sidenotes on load/resize and handles narrow-screen click-to-expand tooltips. On wide screens (≥1024px), sidenote width adapts via JS (`avail = innerWidth - content.rightEdge - 30px - 20px`, clamped 150–270px).

## Constraints

- Every post must have a `date` field in YAML frontmatter.
- `pandoc` must be installed to build locally or in CI.
- **URLs**: posts at `/slug.html`, categories at `/category.html` (e.g. `/hello-world.html`, `/general.html`).
- If a post slug collides with a category name, the category page gets `-group` appended (e.g. `general-group.html`).
- Generated `.html` files sit alongside source files in the repo root — don't manually modify them.
