# cqb-blog

Personal blog at [cqb.github.io](https://cqb.github.io) — a static site built with Python + pandoc, served via GitHub Pages.

## Quick start

```sh
# Install dependencies
sudo apt install pandoc
pip3 install pyyaml

# Build the site
python3 publish.py

# Serve locally
python3 -m http.server 8000
# → http://localhost:8000
```

## Adding a post

1. Write a markdown file with YAML frontmatter:

```yaml
---
title: My Post Title
date: YYYY-MM-DD
categories: [category1, category2]
---
```

2. Place it in `posts/<slug>.md`.
3. Run `python3 publish.py` to regenerate all HTML, then commit and push to `main`.

## Project structure

| Path | Description |
|---|---|
| `posts/` | Markdown source files |
| `publish.py` | Build script — parses frontmatter, runs pandoc, outputs HTML |
| `config.yml` | Site title, domain, icon |
| `css/main.css` | Styling, dark mode, sidenotes |
| `*.html` (root) | Generated output (index, posts, categories) |
| `feed.xml` | Generated RSS feed |

## Tech

- **Python 3** — frontmatter parsing, HTML generation
- **pandoc** — markdown → HTML conversion
- **GitHub Pages** — hosting from the `main` branch root

Generated files are committed to the repo so GitHub Pages can serve them directly without a build step. Do **not** edit generated `.html` files by hand — they are overwritten on every build.
