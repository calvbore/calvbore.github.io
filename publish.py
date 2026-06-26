#!/usr/bin/env python3
"""
publish.py — static blog generator adapted from vbuterin/blogmaker.
Reads markdown posts with YAML frontmatter, runs pandoc, outputs HTML.
"""

import os
import re
import sys
import zlib
import base64
import datetime
import subprocess
import tempfile

try:
    import yaml
except ImportError:
    yaml = None

POSTS_DIR = 'posts'


def load_config():
    with open('config.yml') as f:
        return yaml.safe_load(f) or {}


def find_posts():
    if not os.path.isdir(POSTS_DIR):
        return []
    return sorted(
        os.path.join(POSTS_DIR, f) for f in os.listdir(POSTS_DIR)
        if f.endswith('.md')
    )


def parse_post(filepath):
    with open(filepath) as f:
        content = f.read()

    metadata = {}
    body = content

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            if yaml:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except Exception as e:
                    print(f"  Warning: YAML parse error in {filepath}: {e}")
            else:
                print("  Warning: PyYAML not installed, using empty metadata")
            body = parts[2].strip()

    metadata['filename'] = os.path.basename(filepath)[:-3] + '.html'

    if 'date' in metadata and not isinstance(metadata['date'], str):
        metadata['date'] = metadata['date'].strftime('%Y-%m-%d')

    if 'title' not in metadata:
        name = os.path.splitext(os.path.basename(filepath))[0]
        metadata['title'] = name.replace('-', ' ').replace('_', ' ').title()

    # Derive URL slug from title
    slug = metadata['title'].lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    words = slug.split()
    if len(words) > 3:
        words = words[:3]
    slug = '-'.join(words)
    metadata['filename'] = slug + '.html'
    if 'categories' not in metadata:
        metadata['categories'] = []
    if isinstance(metadata.get('categories'), str):
        metadata['categories'] = [c.strip().lower() for c in metadata['categories'].split(',')]
    elif isinstance(metadata.get('categories'), list):
        metadata['categories'] = [str(c).strip().lower() for c in metadata['categories']]

    return metadata, body


def get_post_output_path(metadata):
    return metadata['filename']


def get_printed_date(date_text):
    try:
        year, month, day = date_text.split('-')
        month_names = 'JanFebMarAprMayJunJulAugSepOctNovDec'
        month_abbr = month_names[(int(month) - 1) * 3:(int(month)) * 3]
        return f'{year} {month_abbr} {day}'
    except (ValueError, IndexError):
        return date_text


def get_linked_date(date_text):
    try:
        parts = date_text.split('-')
        year, month, day = parts[0], parts[1], parts[2]
        month_names = 'JanFebMarAprMayJunJulAugSepOctNovDec'
        month_abbr = month_names[(int(month) - 1) * 3:(int(month)) * 3]
        style = 'color:inherit;text-decoration:none'
        return (f'<a href="/{year}/" style="{style}">{year}</a> '
                f'<a href="/{year}/{month}/" style="{style}">{month_abbr}</a> '
                f'<a href="/{year}/{month}/{day}/" style="{style}">{int(day)}</a>')
    except (ValueError, IndexError):
        return date_text


# --- HTML templates ---

PRE_HEADER = '''<!DOCTYPE html>
<html>
<meta charset="UTF-8">
'''

HEADER_TEMPLATE = '''<link rel="stylesheet" type="text/css" href="/css/main.css">
<script>
MathJax = {
  svg: { fontCache: 'global' }
};
</script>
<script type="text/javascript" id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>
<div id="doc" class="container-fluid markdown-body comment-enabled" data-hard-breaks="true">
<div id="top-bar">
<a id="rss-link" href="/feed.xml" title="RSS feed">
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 11a9 9 0 0 1 9 9"/>
    <path d="M4 4a16 16 0 0 1 16 16"/>
    <circle cx="5" cy="19" r="1"/>
  </svg>
</a>
<div id="color-mode-switch">
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" width="20" height="20">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
  </svg>
  <input type="checkbox" id="switch"/>
  <label for="switch">Dark Mode Toggle</label>
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" width="20" height="20">
    <path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
  </svg>
</div>
</div>
'''

TOGGLE_COLOR_SCHEME_JS = '''<script>
var r=document.querySelector('html'),t=document.querySelector('#color-mode-switch input[type="checkbox"]');
function a(s){r.classList.remove('dark','light');r.classList.add(s);if(t)t.checked=s==='dark';localStorage.setItem('colorScheme',s);}
var s=localStorage.getItem('colorScheme');
if(s){a(s);}else{a(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}
if(t)t.onclick=function(){a(r.classList.contains('dark')?'light':'dark');};
</script>
'''

PLANTUML_JS = '''<script>
function copyPlantuml(b){var s=b.closest(".plantuml-container").getAttribute("data-plantuml-src");navigator.clipboard.writeText(s).then(function(){var i=b.innerHTML;b.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';setTimeout(function(){b.innerHTML=i},2000)})}
function copyPlantumlImage(b){var i=b.closest(".plantuml-container").querySelector("img");fetch(i.src).then(function(r){return r.blob()}).then(function(b){navigator.clipboard.write([new ClipboardItem({[b.type]:b})])}).then(function(){var i=b.innerHTML;b.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';setTimeout(function(){b.innerHTML=i},2000)})}
</script>
'''

CODE_COPY_JS = '''<script>
function copyCodeBlock(b){var c=b.closest(".code-block-wrapper").querySelector("code");navigator.clipboard.writeText(c.textContent).then(function(){var i=b.innerHTML;b.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';setTimeout(function(){b.innerHTML=i},2000)})}
</script>
'''

MATH_COPY_JS = '''<script>
function copyLatex(b){var s=b.closest(".math-wrapper").getAttribute("data-latex-src");navigator.clipboard.writeText(s).then(function(){var i=b.innerHTML;b.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';setTimeout(function(){b.innerHTML=i},2000)})}
</script>
'''

FOOTNOTE_JS = '''<script>
(function(){var m=document.querySelector('.markdown-body');if(!m)return;
function p(){var n=m.querySelectorAll('.sidenote-content');for(var i=0;i<n.length;i++){var e=n[i],w=e.closest('.sidenote-wrapper');if(window.innerWidth>=1024){e.style.position='absolute';e.style.top=w.querySelector('.footnote-ref').offsetTop+'px';e.style.left='';var r=m.getBoundingClientRect(),avail=window.innerWidth-(r.left+r.width+30)-20;e.style.width=Math.min(270,Math.max(150,avail))+'px'}else{e.style.position='';e.style.top='';e.style.left='';e.style.width=''}}}
p();window.addEventListener('resize',p);
m.addEventListener('click',function(e){var r=e.target.closest('.sidenote-wrapper .footnote-ref');var a=m.querySelectorAll('.sidenote-wrapper.active');if(!r){for(var i=0;i<a.length;i++)a[i].classList.remove('active');return}
e.preventDefault();if(window.innerWidth<1024){var w=r.closest('.sidenote-wrapper');var d=w.classList.contains('active');for(var i=0;i<a.length;i++)a[i].classList.remove('active');if(!d){w.classList.add('active');var n=w.querySelector('.sidenote-content'),t=r.getBoundingClientRect();n.style.left=Math.min(t.left,window.innerWidth-310)+'px';n.style.top=(t.bottom+4)+'px'}}})})();
</script>
'''

RSS_LINK = '<link rel="alternate" type="application/rss+xml" href="/feed.xml" title="{title}">\n'

TITLE_TEMPLATE = '''<br>
<h1 style="margin-bottom:7px"> {title} </h1>
<small style="float:left; color: #888"> {date} </small>
<small style="float:right; color: #888"><a href="/index.html">See all posts</a></small>
<br><br><br>
<title> {title} </title>
'''

TOC_TITLE_TEMPLATE = '''<title> {title} </title>
<br>
<center><h1 style="border-bottom:0px; font-family:Georgia,'Times New Roman',Times,serif"> {title} </h1></center>
'''

FOOTER = '</div>'

TOC_START = '<br>\n<ul class="post-list" style="padding-left:0">\n'

TOC_END = '</ul>\n'

TOC_ITEM_TEMPLATE = '''<li>
    <span class="post-meta">{date}</span>
    <h3 style="margin-top:12px;margin-bottom:0">
      <a class="post-link" href="{link}">{title}</a>
    </h3>
    <div style="font-size:0.85em; font-family:monospace; color:var(--text-secondary);margin-top:-4px">{word_count}</div>
</li>
'''

RSS_ITEM_TEMPLATE = '''<item>
<title>{title}</title>
<link>{link}</link>
<guid>{link}</guid>
<pubDate>{pub_date}</pubDate>
<description>{description}</description>
</item>
'''

RSS_MAIN_TEMPLATE = '''<?xml version="1.0" ?>
<rss version="2.0">
<channel>
  <title>{title}</title>
  <link>{link}</link>
  <description>{title}</description>
  <image>
      <url>{icon}</url>
      <title>{title}</title>
      <link>{link}</link>
  </image>
{items}
</channel>
</rss>'''


def make_categories_header(categories, category_slug_map):
    o = ['<center><hr>']
    for cat in categories:
        size = min(100, 900 // max(len(cat), 1))
        cat_file = category_slug_map.get(cat, f'{cat}.html')
        o.append(
            f'<span class="toc-category" style="font-size:{size}%">'
            f'<a href="/{cat_file}">{cat.capitalize()}</a>'
            f'</span>'
        )
    o.append('<hr></center>')
    return '\n'.join(o)


def make_toc_item(config, metadata):
    link = get_post_output_path(metadata)
    return TOC_ITEM_TEMPLATE.format(
        date=get_linked_date(metadata.get('date', '')),
        link=f"/{link}",
        title=metadata.get('title', 'Untitled'),
        word_count=format_word_count(metadata.get('word_count', 0)),
    )


def make_toc(toc_items, all_categories, category_slug_map, title):
    return (
        PRE_HEADER
        + RSS_LINK.format(title=title)
        + HEADER_TEMPLATE
        + TOGGLE_COLOR_SCHEME_JS
        + PLANTUML_JS
        + TOC_TITLE_TEMPLATE.format(title=title)
        + make_categories_header(all_categories, category_slug_map)
        + TOC_START
        + ''.join(toc_items)
        + TOC_END
    )


def generate_feed(config, metadatas):
    domain = config.get('domain', '').rstrip('/')

    def get_link(route):
        return f"{domain}/{route}"

    def rfc2822_date(date_text):
        try:
            y, m, d = (int(x) for x in date_text.split('-'))
            dt = datetime.date(y, m, d)
            return dt.strftime('%a, %d %b %Y 00:00:00 +0000')
        except (ValueError, IndexError):
            return ''

    items = []
    for m in metadatas:
        route = get_post_output_path(m)
        items.append(RSS_ITEM_TEMPLATE.format(
            title=m.get('title', ''),
            link=get_link(route),
            pub_date=rfc2822_date(m.get('date', '')),
            description='',
        ))

    return RSS_MAIN_TEMPLATE.strip().format(
        title=config.get('title', ''),
        link=get_link(''),
        icon=config.get('icon', ''),
        items='\n'.join(items),
    )


def build_post_html(metadata, body_html, config, category_slug_map):
    title = metadata.get('title', 'Untitled')
    date = metadata.get('date', '')
    cats = metadata.get('categories', [])

    cat_links = ' · '.join(
        f'<a href="/{category_slug_map.get(c, c + ".html")}" style="color:var(--text-secondary)">{c.capitalize()}</a>'
        for c in cats
    )
    cat_line = f'<div style="font-size:0.85em; color:var(--text-secondary); margin:6px 0"><hr style="border:none;border-top:1px solid var(--border);margin:4px 0">{cat_links}<hr style="border:none;border-top:1px solid var(--border);margin:4px 0"></div>\n' if cat_links else ''

    wc = format_word_count(metadata.get('word_count', 0))
    wc_line = f'<div style="font-size:0.85em; font-family:monospace; color:var(--text-secondary);margin-bottom:0">{wc}</div>\n' if wc else ''

    footer_date = get_linked_date(date)
    footer_cats = ' · '.join(
        f'<a href="/{category_slug_map.get(c, c + ".html")}" style="color:var(--text-secondary)">{c.capitalize()}</a>'
        for c in cats
    ) if cats else ''
    footer_line = (
        '<hr style="border:none;border-top:1px solid var(--border);margin:16px 0 8px 0">\n'
        f'<div style="font-size:0.85em; color:var(--text-secondary)">\n'
        f'  <span style="float:left">{footer_date}</span>\n'
        f'  <span style="float:right">{footer_cats}</span>\n'
        f'  <div style="clear:both"></div>\n'
        f'</div>\n'
    ) if date else ''

    return (
        PRE_HEADER
        + RSS_LINK.format(title=title)
        + HEADER_TEMPLATE
        + TOGGLE_COLOR_SCHEME_JS
        + PLANTUML_JS
        + CODE_COPY_JS
        + MATH_COPY_JS
        + TITLE_TEMPLATE.format(title=title, date=get_linked_date(date))
        + wc_line
        + cat_line
        + body_html
        + FOOTNOTE_JS
        + footer_line
        + FOOTER
    )


def defancify(text):
    return text.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"').replace('\u2026', '...')


def format_word_count(n):
    s = f'{n:,}'
    if n >= 10000:
        s = s.replace(',', ' ')
    else:
        s = s.replace(',', '')
    s = s.rjust(5).replace(' ', '\u00a0')
    return s + ' words'


PLANTUML_TRANS = str.maketrans(
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
    '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_',
)

def plantuml_encode(text):
    c = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-zlib.MAX_WBITS)
    data = c.compress(text.encode('utf-8')) + c.flush()
    return base64.b64encode(data).decode('ascii').translate(PLANTUML_TRANS).rstrip('=')


def render_plantuml(markdown):
    def replacer(match):
        diagram = match.group(1).strip()
        encoded = plantuml_encode(diagram)
        escaped = diagram.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        return (
            f'<div class="plantuml-container" data-plantuml-src="{escaped}">'
            f'<img src="https://www.plantuml.com/plantuml/svg/{encoded}" />'
            f'<div class="plantuml-buttons">'
            f'<button class="plantuml-copy-btn" onclick="copyPlantuml(this)" title="Copy PlantUML source">'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
            f'</svg></button>'
            f'<button class="plantuml-copy-btn" onclick="copyPlantumlImage(this)" title="Copy image">'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>'
            f'</svg></button>'
            f'</div></div>'
        )
    return re.sub(r'```plantuml\n(.*?)```', replacer, markdown, flags=re.DOTALL)


def wrap_code_blocks(html):
    def replacer(match):
        pre = match.group(0)
        return (
            '<div class="code-block-wrapper">'
            + pre
            + '<button class="code-copy-btn" onclick="copyCodeBlock(this)" title="Copy code">'
            + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            + '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
            + '</svg></button></div>'
        )
    return re.sub(r'<pre[^>]*>.*?</pre>', replacer, html, flags=re.DOTALL)


def wrap_math_blocks(html):
    def replacer(match):
        full = match.group(0)
        inner = match.group(2)
        kind = match.group(1)

        # Only wrap display math for now.
        # To enable inline later: remove this guard and add .math-inline-wrapper CSS.
        if kind != 'display':
            return full

        latex = inner[2:-2].strip()
        escaped = latex.replace('&', '&amp;').replace('"', '&quot;')
        return (
            '<span class="math-wrapper math-display-wrapper" data-latex-src="' + escaped + '">'
            + full
            + '<button class="math-copy-btn" onclick="copyLatex(this)" title="Copy LaTeX">'
            + '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            + '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
            + '</svg></button></span>'
        )
    return re.sub(
        r'<span class="math (inline|display)">(\\\(.*?\\\)|\\\[.*?\\\])</span>',
        replacer,
        html,
        flags=re.DOTALL,
    )


def reorganize_footnotes(html):
    if 'class="footnotes footnotes-end-of-document"' not in html:
        return html

    li_pattern = re.compile(r'<li id="fn(\d+)">(.*?)</li>', re.DOTALL)

    section_match = re.search(
        r'<section id="footnotes"[^>]*>.*?<ol>(.*?)</ol>.*?</section>',
        html, re.DOTALL,
    )
    if not section_match:
        return html

    fn_defs = {}
    for m in li_pattern.finditer(section_match.group(1)):
        fn_id = m.group(1)
        raw = m.group(2).strip()
        raw = re.sub(
            rf'<a[\s\S]*?href="#fnref{fn_id}"[\s\S]*?class="footnote-back"[\s\S]*?>[\s\S]*?</a>',
            '', raw,
        )
        raw = raw.replace('\u21a9', '').replace('\ufe0e', '').strip()
        # Strip outer <p>...</p> so content is phrasing-only (safe inside <span> in <p>)
        content = re.sub(r'^<p>(.*)</p>$', r'\1', raw, flags=re.DOTALL)
        content = content.strip()
        fn_defs[fn_id] = content
        fn_defs[fn_id + '_raw'] = raw  # keep raw for end-section

    if not fn_defs:
        return html

    def ref_replacer(m):
        fn_id = m.group(1)
        content = fn_defs.get(fn_id, '')
        return (
            f'<span class="sidenote-wrapper">'
            f'<a href="#fn{fn_id}" class="footnote-ref" id="fnref{fn_id}">'
            f'<sup>{fn_id}</sup></a>'
            f'<span class="sidenote-content" data-fn="{fn_id}">{content}</span>'
            f'</span>'
        )

    ref_pattern = re.compile(
        r'<a[^>]*?href="#fn(\d+)"[^>]*?class="footnote-ref"[^>]*?><sup>\d+</sup></a>'
    )
    html = ref_pattern.sub(ref_replacer, html)

    compact = '<section id="footnotes" class="footnotes">\n<hr>\n<ol>\n'
    for fn_id in sorted((k for k in fn_defs if not k.endswith('_raw')), key=int):
        raw = fn_defs.get(fn_id + '_raw', fn_defs[fn_id])
        # Insert back-link before </p> so it appears inline at end of footnote text
        raw_with_back = re.sub(
            r'</p>\s*$',
            f' <a href="#fnref{fn_id}" class="footnote-back" role="doc-backlink">'
            f'\u21a9\ufe0e</a></p>',
            raw,
        )
        compact += f'<li id="fn{fn_id}">{raw_with_back}</li>\n'
    compact += '</ol>\n</section>'

    html = re.sub(
        r'<section id="footnotes"[^>]*>.*?</section>',
        compact, html, flags=re.DOTALL,
    )

    return html


def main():
    config = load_config()
    posts = find_posts()

    if not posts:
        print("No posts found in posts/")
        with open('index.html', 'w') as f:
            f.write(make_toc([], [], {}, config.get('title', 'Blog')))
        return

    # Pass 1: read frontmatter only to build category map
    metadatas = []
    categories = set()

    for filepath in posts:
        print(f"Parsing: {filepath}")
        metadata, body = parse_post(filepath)

        if 'date' not in metadata:
            print(f"  Skipping (no date): {filepath}")
            continue

        metadata['_filepath'] = filepath
        metadata['_body'] = body
        text_no_code = re.sub(r'```.*?```', '', body, flags=re.DOTALL)
        metadata['word_count'] = len(text_no_code.split()) if text_no_code.strip() else 0
        metadatas.append(metadata)
        for c in metadata.get('categories', []):
            categories.add(c)

    if not metadatas:
        print("No valid posts found")
        with open('index.html', 'w') as f:
            f.write(make_toc([], [], {}, config.get('title', 'Blog')))
        return

    categories = sorted(categories)
    sorted_metadatas = sorted(metadatas, key=lambda x: x.get('date', ''), reverse=True)

    # Build category slug map (handle post/category name collisions)
    post_slugs = {}
    for m in sorted_metadatas:
        fn = m['filename']
        if fn in post_slugs:
            print(f"  Warning: duplicate slug '{fn}' for posts '{post_slugs[fn]}' and '{m['title']}'")
        post_slugs[fn] = m['title']

    post_slug_set = set(post_slugs.keys())
    category_slug_map = {}
    for cat in categories:
        cat_file = f'{cat}.html'
        if cat_file in post_slug_set:
            cat_file = f'{cat}-group.html'
            print(f"  Category '{cat}' collides with a post, renaming to '{cat_file}'")
        category_slug_map[cat] = cat_file

    # Pass 2: render plantuml, run pandoc, generate post HTML
    for metadata in sorted_metadatas:
        filepath = metadata['_filepath']
        print(f"Building: {filepath}")

        body = metadata['_body']
        body = render_plantuml(body)
        body = re.sub(r'(?<=\S)\n(?=[-*+]\s|\d+\.\s)', '\n\n', body)

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(body)
                tmp_path = f.name

            result = subprocess.run(
                ['pandoc', '-f', 'markdown', '-t', 'html', '--mathjax', tmp_path],
                capture_output=True, text=True, check=True,
            )
            body_html = wrap_code_blocks(result.stdout)
            body_html = wrap_math_blocks(body_html)
            body_html = reorganize_footnotes(body_html)
        except subprocess.CalledProcessError as e:
            print(f"  pandoc error: {e}")
            continue
        except FileNotFoundError:
            print("  Error: pandoc not found. Install it first: apt install pandoc")
            sys.exit(1)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        output_path = get_post_output_path(metadata)
        html = build_post_html(metadata, defancify(body_html), config, category_slug_map)
        with open(output_path, 'w') as f:
            f.write(html)

        print(f"  -> {output_path}")

    # Feed
    feed = generate_feed(config, sorted_metadatas)
    with open('feed.xml', 'w') as f:
        f.write(feed)
    print("Generated feed.xml")

    # Homepage
    homepage_items = [make_toc_item(config, m) for m in sorted_metadatas]
    site_title = config.get('title', 'Blog')
    with open('index.html', 'w') as f:
        f.write(make_toc(homepage_items, categories, category_slug_map, site_title))
    print("Generated index.html")

    # Category pages
    for cat in categories:
        cat_file = category_slug_map[cat]
        cat_items = [
            make_toc_item(config, m) for m in sorted_metadatas
            if cat in [c.lower() for c in m.get('categories', [])]
        ]
        with open(cat_file, 'w') as f:
            f.write(make_toc(cat_items, categories, category_slug_map, cat.capitalize()))
    print(f"Generated {len(categories)} category pages")

    # Date archive pages
    MONTH_NAMES = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    date_groups = {}
    for m in sorted_metadatas:
        d = m.get('date', '')
        if not d:
            continue
        parts = d.split('-')
        y = parts[0]
        date_groups.setdefault(y, []).append(m)
        if len(parts) >= 2:
            ym = f'{parts[0]}-{parts[1]}'
            date_groups.setdefault(ym, []).append(m)
        if len(parts) >= 3:
            date_groups.setdefault(d, []).append(m)

    for date_key, posts in date_groups.items():
        parts = date_key.split('-')
        dir_path = '/'.join(parts)
        os.makedirs(dir_path, exist_ok=True)
        if len(parts) == 3:
            month_num = int(parts[1])
            day_num = int(parts[2])
            title = f'{day_num} {MONTH_NAMES[month_num]} {parts[0]}'
        elif len(parts) == 2:
            month_num = int(parts[1])
            title = f'{MONTH_NAMES[month_num]} {parts[0]}'
        else:
            title = f'{parts[0]}'
        items = [make_toc_item(config, m) for m in posts]
        with open(os.path.join(dir_path, 'index.html'), 'w') as f:
            f.write(make_toc(items, categories, category_slug_map, title))
    print(f"Generated {len(date_groups)} date archive pages")

    print(f"\nDone. {len(sorted_metadatas)} posts, {len(categories)} categories.")


if __name__ == '__main__':
    main()
