#!/usr/bin/env python3
"""Convert Butterfly Effect .draft.md files to .html chapters."""

import re
import os
import html

# Arc metadata
ARCS = {
    1: "The Silence",
    2: "The Signal",
    3: "The Crossing",
    4: "The Stranger",
    5: "The Mirror",
    6: "The Return",
    7: "The Choice",
}

# Chapter metadata: (arc, number, title, pov, location, timeline)
CHAPTERS = []

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUSCRIPT = os.path.join(BASE, "manuscript")
BUILD = os.path.join(BASE, "build")
STYLE_REL = "../../style/novel.css"
INDEX_REL = "../../build/index.html"


def parse_draft(filepath):
    """Parse a .draft.md file and extract metadata + prose."""
    with open(filepath, "r") as f:
        content = f.read()

    # Extract title from first line: # Chapter N: Title
    title_match = re.match(r"^# Chapter (\d+):\s*(.+)$", content, re.MULTILINE)
    if not title_match:
        return None
    chapter_num = int(title_match.group(1))
    chapter_title = title_match.group(2).strip()

    # Extract metadata from HTML comment
    meta_match = re.search(
        r"<!--\s*Arc:\s*(\d+)\s*\|\s*POV:\s*(.+?)\s*\|\s*Location:\s*(.+?)\s*\|\s*Timeline:\s*(.+?)\s*-->",
        content,
    )
    if meta_match:
        arc_num = int(meta_match.group(1))
        pov = meta_match.group(2).strip()
        location = meta_match.group(3).strip()
        timeline = meta_match.group(4).strip()
    else:
        arc_num = 1
        pov = "Unknown"
        location = "Unknown"
        timeline = "Unknown"

    # Strip everything before first non-comment, non-header prose
    # Remove title line, metadata comments, beat comments, continuity notes
    lines = content.split("\n")
    prose_lines = []
    in_continuity = False
    for line in lines:
        # Skip title
        if re.match(r"^# Chapter \d+:", line):
            continue
        # Skip HTML comments (single-line)
        if re.match(r"^\s*<!--.*-->\s*$", line):
            continue
        # Skip multi-line HTML comment start
        if re.match(r"^\s*<!--", line) and "-->" not in line:
            in_continuity = True
            continue
        # Inside multi-line comment
        if in_continuity:
            if "-->" in line:
                in_continuity = False
            continue
        # Skip word count target lines
        if re.match(r"^\s*<!--\s*Word count", line, re.IGNORECASE):
            continue
        prose_lines.append(line)

    prose = "\n".join(prose_lines).strip()

    # Remove trailing --- and anything after (continuity notes)
    prose = re.sub(r"\n---\s*$", "", prose)

    return {
        "chapter_num": chapter_num,
        "chapter_title": chapter_title,
        "arc_num": arc_num,
        "pov": pov,
        "location": location,
        "timeline": timeline,
        "prose": prose,
    }


def prose_to_html(prose):
    """Convert markdown prose to HTML paragraphs."""
    # Split on scene breaks (--- or ***)
    # First, handle scene breaks
    prose = re.sub(r"\n\s*\*\s*\*\s*\*\s*\n", "\n<SCENE_BREAK>\n", prose)
    prose = re.sub(r"\n---\n", "\n<SCENE_BREAK>\n", prose)

    # Handle blockquotes (> lines) - often used for pidgin/translation
    lines = prose.split("\n")
    result_lines = []
    in_blockquote = False
    for line in lines:
        if line.startswith("> "):
            if not in_blockquote:
                result_lines.append("<BLOCKQUOTE_START>")
                in_blockquote = True
            result_lines.append(line[2:])
        else:
            if in_blockquote:
                result_lines.append("<BLOCKQUOTE_END>")
                in_blockquote = False
            result_lines.append(line)
    if in_blockquote:
        result_lines.append("<BLOCKQUOTE_END>")
    prose = "\n".join(result_lines)

    # Split into paragraphs (double newline)
    paragraphs = re.split(r"\n\s*\n", prose)

    html_parts = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if para == "<SCENE_BREAK>":
            html_parts.append('    <hr class="scene-break">')
            continue

        # Handle blockquotes
        if "<BLOCKQUOTE_START>" in para:
            para = para.replace("<BLOCKQUOTE_START>", "").strip()
            if "<BLOCKQUOTE_END>" in para:
                para = para.replace("<BLOCKQUOTE_END>", "").strip()
            bq_lines = para.split("\n")
            bq_html = "\n".join(
                f"      <p>{process_inline(l.strip())}</p>" for l in bq_lines if l.strip()
            )
            html_parts.append(f"    <blockquote>\n{bq_html}\n    </blockquote>")
            continue

        if "<BLOCKQUOTE_END>" in para:
            para = para.replace("<BLOCKQUOTE_END>", "").strip()

        if not para:
            continue

        # Convert markdown italics to <em>
        para = process_inline(para)
        html_parts.append(f"    <p>{para}</p>")

    return "\n".join(html_parts)


def process_inline(text):
    """Process inline markdown: *italic*, **bold**."""
    # Escape HTML entities first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic: *text*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    return text


def generate_chapter_html(data, prev_href, next_href):
    """Generate the full HTML for a chapter."""
    arc_title = ARCS.get(data["arc_num"], "Unknown")
    prose_html = prose_to_html(data["prose"])

    # Use Butterfly Effect as title
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Butterfly Effect — Chapter {data['chapter_num']}: {html.escape(data['chapter_title'])}</title>
  <link rel="stylesheet" href="{STYLE_REL}">
</head>
<body>
  <nav class="chapter-nav">
    <a href="{prev_href}">← Previous</a>
    <a href="{INDEX_REL}">Contents</a>
    <a href="{next_href}">Next →</a>
  </nav>
  <header>
    <p class="arc-label">Arc {data['arc_num']}: {html.escape(arc_title)}</p>
    <h1>Chapter {data['chapter_num']}<br><span class="chapter-title">{html.escape(data['chapter_title'])}</span></h1>
    <p class="chapter-meta">{html.escape(data['pov'])} · {html.escape(data['location'])} · {html.escape(data['timeline'])}</p>
  </header>
  <article class="chapter-body">
{prose_html}
  </article>
  <nav class="chapter-nav bottom">
    <a href="{prev_href}">← Previous</a>
    <a href="{INDEX_REL}">Contents</a>
    <a href="{next_href}">Next →</a>
  </nav>
</body>
</html>
"""


def generate_index(chapters):
    """Generate index.html table of contents."""
    arc_groups = {}
    for ch in chapters:
        arc = ch["arc_num"]
        if arc not in arc_groups:
            arc_groups[arc] = []
        arc_groups[arc].append(ch)

    groups_html = []
    for arc_num in sorted(arc_groups.keys()):
        arc_title = ARCS.get(arc_num, "Unknown")
        links = []
        for ch in arc_groups[arc_num]:
            num_str = f"{ch['chapter_num']:02d}"
            href = f"../manuscript/arc-{arc_num}/chapter-{num_str}.html"
            links.append(
                f'    <a href="{href}"><span class="chapter-number">{ch["chapter_num"]}.</span> {html.escape(ch["chapter_title"])}</a>'
            )
        groups_html.append(
            f"""  <div class="arc-group">
    <h2>Arc {arc_num}: {html.escape(arc_title)}</h2>
{chr(10).join(links)}
  </div>"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Butterfly Effect — Table of Contents</title>
  <link rel="stylesheet" href="../style/novel.css">
</head>
<body>
  <div class="index-header">
    <h1>Butterfly Effect</h1>
    <p class="subtitle">A Novel</p>
  </div>
{chr(10).join(groups_html)}
</body>
</html>
"""


def main():
    chapters = []

    # Collect all draft files
    for arc_num in range(1, 8):
        arc_dir = os.path.join(MANUSCRIPT, f"arc-{arc_num}")
        if not os.path.isdir(arc_dir):
            continue
        for fname in sorted(os.listdir(arc_dir)):
            if fname.endswith(".draft.md"):
                filepath = os.path.join(arc_dir, fname)
                data = parse_draft(filepath)
                if data:
                    chapters.append(data)

    chapters.sort(key=lambda x: x["chapter_num"])
    print(f"Found {len(chapters)} chapters")

    # Generate HTML for each chapter
    for i, ch in enumerate(chapters):
        arc_dir = os.path.join(MANUSCRIPT, f"arc-{ch['arc_num']}")
        num_str = f"{ch['chapter_num']:02d}"
        html_path = os.path.join(arc_dir, f"chapter-{num_str}.html")

        # Navigation links
        if i > 0:
            prev_ch = chapters[i - 1]
            prev_num = f"{prev_ch['chapter_num']:02d}"
            prev_href = f"../arc-{prev_ch['arc_num']}/chapter-{prev_num}.html"
        else:
            prev_href = INDEX_REL

        if i < len(chapters) - 1:
            next_ch = chapters[i + 1]
            next_num = f"{next_ch['chapter_num']:02d}"
            next_href = f"../arc-{next_ch['arc_num']}/chapter-{next_num}.html"
        else:
            next_href = INDEX_REL

        chapter_html = generate_chapter_html(ch, prev_href, next_href)
        with open(html_path, "w") as f:
            f.write(chapter_html)
        print(f"  ✓ Chapter {ch['chapter_num']}: {ch['chapter_title']} → {html_path}")

    # Generate index
    index_path = os.path.join(BUILD, "index.html")
    index_html = generate_index(chapters)
    with open(index_path, "w") as f:
        f.write(index_html)
    print(f"  ✓ Index → {index_path}")
    print(f"\nDone. {len(chapters)} chapters converted.")


if __name__ == "__main__":
    main()
