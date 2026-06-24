# cqb-blog

Personal blog at `cqb.github.io` built with a Python/pandoc static site generator (adapted from [vbuterin/blogmaker](https://github.com/vbuterin/blogmaker)) served via GitHub Pages.

## Adding a post

1. Write markdown in Obsidian (or any editor) with YAML frontmatter.
2. Drop the `.md` file into `posts/slug.md` — date is read from the `date` field in frontmatter.
3. Push to `main`. The GitHub Action (`publish.yml`) runs `publish.py`, which regenerates `index.html`, category pages, and `feed.xml`.

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
| `css/main.css` | Source | Blog styling, dark mode |
| `.github/workflows/publish.yml` | Source | CI: installs pandoc, runs publish.py, commits generated files |
| `index.html` | Generated | Post listing / homepage |
| `feed.xml` | Generated | RSS feed |
| `*.html` (at root) | Generated | Per-category post listings (e.g. `general.html`) |

## Dev commands

```sh
# Build all posts locally (requires pandoc)
python3 publish.py
```

## Architecture notes

- **No build tool beyond pandoc.** No npm, no bundler. Pure Python + pandoc.
- **GitHub Action** (`publish.yml`) installs pandoc in CI, runs `publish.py`, then commits any generated files back to main so they're served by GitHub Pages.
- **GitHub Pages** is configured to serve from the root of the main branch.
- **Generated files are committed to the repo** — this is intentional so GitHub Pages can serve them directly without an extra build step.
- Dark/light mode toggle is pure CSS/JS (no framework).
- Categories are derived from the `categories` field in each post's frontmatter.

## Constraints

- Every post must have a `date` field in YAML frontmatter.
- `pandoc` must be installed to build locally or in CI.
- **URLs**: posts at `/slug.html`, categories at `/category.html` (e.g. `/hello-world.html`, `/general.html`).
- If a post slug collides with a category name, the category page gets `-group` appended (e.g. `general-group.html`).
- Generated `.html` files sit alongside source files in the repo root — don't manually modify them.
