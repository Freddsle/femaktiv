"""Build the standalone pitch artwork; no application or provider requests."""

import base64
import shutil
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAPER = "#fcf9f6"
PLUM = "#39273e"
PURPLE = "#785098"
MUTED = "#736675"
WHITE = "#fffdfb"
parts = []


def add(markup):
    parts.append(markup)


def text(x, y, value, size=24, color=PLUM, weight=400, extra=""):
    add(
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" {extra}>{escape(value)}</text>'
    )


def rect(x, y, width, height, fill=WHITE, stroke="none", radius=24, extra=""):
    add(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}" {extra}/>'
    )


def path(d, color=PURPLE, width=2, extra=""):
    add(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
        f'stroke-linecap="round" stroke-linejoin="round" {extra}/>'
    )


def icon(name, x, y, color=PURPLE, size=28):
    paths = {
        "chat": "M5 5h18a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H12l-7 5v-7a4 4 0 0 1-3-4V9a4 4 0 0 1 3-4 M9 12h12 M9 17h8",
        "note": "M8 3h13l6 6v20H8z M20 3v8h7 M12 16h11 M12 21h9",
        "history": "M5 11a12 12 0 1 1-1 10 M5 3v9h9 M17 10v8l5 3",
        "shield": "M16 2 28 7v10c0 7-12 13-12 13S4 24 4 17V7z M10 16l4 4 8-8",
        "spark": "M16 2l4 10 10 4-10 4-4 10-4-10L2 16l10-4z",
        "check": "M6 16l7 7L27 8",
        "book": "M16 7C11 3 6 3 2 5v23c5-2 9-2 14 1 5-3 9-3 14-1V5c-4-2-9-2-14 2v22",
        "link": "M12 21l-2 2a6 6 0 0 1-8-8l6-6a6 6 0 0 1 8 0 M20 11l2-2a6 6 0 0 1 8 8l-6 6a6 6 0 0 1-8 0 M10 22l12-12",
        "user": "M22 9a6 6 0 1 1-12 0 6 6 0 0 1 12 0 M4 29v-4c0-6 24-6 24 0v4",
    }
    add(f'<g transform="translate({x} {y}) scale({size / 32})">')
    path(paths[name], color, 1.8)
    add("</g>")


def stage(x, number, label):
    text(x, 358, number, 19, PURPLE, 700)
    text(x + 39, 358, label, 17, MUTED, 700, 'letter-spacing="2"')


def chip(x, y, width, label, fill="#ede5f2", color=PURPLE):
    rect(x, y, width, 39, fill, radius=19.5)
    text(x + width / 2, y + 26, label, 18, color, 600, 'text-anchor="middle"')


def image_data(path):
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


add("""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="1920" height="1080" viewBox="0 0 1920 1080" role="img"
    aria-labelledby="title description">
<title id="title">The intelligence behind femaktiv</title>
<desc id="description">Personal context enters femaktiv coordination. Selected evidence informs
the instructions. Intake and answer drafting pass through Anymize, which handles identifier
masking before the AI model. femaktiv checks source references and returns practical guidance
in English or German. The selected library includes DGE, NIH and NHLBI, EFSA, gesund.bund.de and ZQP.</desc>
<defs>
  <linearGradient id="core" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#39273e"/><stop offset="1" stop-color="#654674"/>
  </linearGradient>
  <linearGradient id="privacy" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#ede5f2"/><stop offset="1" stop-color="#f5eae8"/>
  </linearGradient>
  <linearGradient id="evidence" x1="0" y1="0" x2="1" y2="0">
    <stop stop-color="#f5eae8"/><stop offset="1" stop-color="#f8eee7"/>
  </linearGradient>
  <radialGradient id="glow"><stop stop-color="#ecd2d9" stop-opacity=".55"/>
    <stop offset="1" stop-color="#fcf9f6" stop-opacity="0"/></radialGradient>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1 7 5 2 9" fill="none" stroke="#a78db3" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="12" stdDeviation="20" flood-color="#39273e" flood-opacity=".055"/>
  </filter>
</defs>
<style>
text{font-family:Arial,"Liberation Sans",sans-serif}
.serif{font-family:Georgia,"Liberation Serif",serif;letter-spacing:-1.5px}
</style>
""")
rect(0, 0, 1920, 1080, PAPER, radius=0)
add('<ellipse cx="1680" cy="170" rx="560" ry="370" fill="url(#glow)"/>')
path("M1580-150C1800 130 1510 270 1860 340", "#ecd2d9", 1.2)
path("M1630-150C1850 130 1560 270 1910 340", "#ecd2d9", 1.2)

text(80, 82, "THE INTELLIGENCE BEHIND femaktiv", 18, PURPLE, 700, 'letter-spacing="3"')
text(80, 173, "Personal context.", 77, PLUM, extra='class="serif"')
text(80, 253, "Credible sources.", 77, PLUM, extra='class="serif"')
text(632, 253, "Practical support.", 77, PURPLE, extra='class="serif" font-style="italic"')
text(84, 303, "A thoughtful journey from her question to her next step.", 25, MUTED)
add(
    f'<image x="1633" y="52" width="190" height="190" '
    f'xlink:href="{image_data(ROOT / "static/img/femaktiv-logo-rounded.png")}"/>'
)
chip(1601, 263, 224, "LIVE PROTOTYPE", "#f5eae8", "#866276")

stage(80, "01", "PERSONAL CONTEXT")
stage(455, "02", "femaktiv COORDINATION")
stage(980, "03", "PRIVACY + AI")
stage(1475, "04", "PRACTICAL GUIDANCE")

# Four distinct visual weights keep the product, rather than infrastructure, central.
rect(80, 389, 300, 377, WHITE, "#e7dfe4", extra='filter="url(#shadow)"')
rect(455, 389, 450, 377, "url(#core)", extra='filter="url(#shadow)"')
rect(980, 389, 420, 377, "url(#privacy)", "#dfd2e6")
rect(1475, 389, 365, 377, WHITE, "#ddcbdc", extra='filter="url(#shadow)"')

for start, end in [(393, 442), (918, 967), (1413, 1462)]:
    path(f"M{start} 575H{end}", "#a78db3", 2.3, 'marker-end="url(#arrow)"')

# Context card.
rect(112, 423, 54, 54, "#f5eae8", radius=17)
icon("user", 125, 435, "#ae7f8c", 29)
text(112, 526, "Her world,", 36, PLUM, extra='class="serif"')
text(112, 564, "in context.", 36, PLUM, extra='class="serif"')
for name, label, y in [
    ("chat", "Her question", 612),
    ("note", "Selected notes", 658),
    ("history", "Active conversation", 704),
]:
    icon(name, 113, y - 21, PURPLE, 25)
    text(153, y, label, 22, MUTED)

# Orchestration card.
rect(487, 422, 56, 56, "#ffffff16", radius=17)
icon("spark", 500, 435, "#ecd2d9", 29)
text(561, 457, "The connecting layer", 24, "#f4e6ef", 600)
text(488, 526, "Context meets evidence.", 36, WHITE, extra='class="serif"')
text(488, 575, "Understand what matters.", 24, "#e4d5e9")
text(488, 612, "Select relevant source passages.", 24, "#e4d5e9")
text(488, 649, "Guide every model request.", 24, "#e4d5e9")
path("M488 682H872", "#ffffff25", 1)
icon("shield", 488, 706, "#d6b9de", 22)
text(522, 725, "Private workspace · persistent context", 19, "#e4d5e9")

# Anymize keeps its actual public logo; model identity stays configurable.
add(
    f'<image x="1013" y="428" width="217" height="42" '
    f'xlink:href="{image_data(HERE / "assets/anymize.svg")}"/>'
)
icon("shield", 1322, 430, PURPLE, 36)
text(1013, 519, "Identifier masking", 30, PLUM, 600)
text(1013, 554, "Handled by Anymize", 23, MUTED)
text(1013, 585, "before the AI model", 23, MUTED)
path("M1190 604V628", "#a78db3", 2, 'marker-end="url(#arrow)"')
rect(1012, 642, 356, 89, "#fffdfba8", "#ffffffa0", radius=18)
icon("spark", 1034, 669, PURPLE, 30)
text(1083, 679, "AI assistance", 25, PLUM, 600)
text(1083, 710, "Understand + draft", 21, MUTED)

# Result card depicts reference checks, not medical fact verification.
rect(1507, 423, 54, 54, "#ede5f2", radius=17)
icon("check", 1520, 435, PURPLE, 28)
text(1507, 526, "Clear next steps.", 36, PLUM, extra='class="serif"')
text(1507, 569, "Practical, personal guidance", 22, MUTED)
text(1507, 601, "with references to explore.", 22, MUTED)
rect(1507, 630, 300, 48, "#f5eae8", radius=13)
icon("link", 1520, 643, "#9d758a", 22)
text(1556, 661, "femaktiv checks references", 19, PLUM)
chip(1507, 704, 118, "ENGLISH")
chip(1637, 704, 117, "DEUTSCH")

# Evidence is an input to orchestration, not an independent live search service.
path("M680 832V782", "#a78db3", 2.2, 'marker-end="url(#arrow)"')
text(702, 811, "relevant passages + source links", 20, MUTED)
rect(455, 841, 1385, 147, "url(#evidence)", "#ecdeda", radius=24)
icon("book", 487, 866, "#a2737c", 28)
text(531, 890, "A curated foundation of credible sources", 27, PLUM, 600)
text(1810, 889, "Nutrition + family care", 21, MUTED, extra='text-anchor="end"')

source_chips = [
    (488, 163, "DGE"),
    (667, 222, "NIH / NHLBI"),
    (905, 157, "EFSA"),
    (1078, 323, "gesund.bund.de"),
    (1417, 153, "ZQP"),
]
for x, width, label in source_chips:
    rect(x, 913, width, 47, "#fffdfb99", "#ffffff", radius=13)
    text(x + width / 2, 944, label, 23, "#74566e", 600, 'text-anchor="middle"')
text(1594, 932, "Selected guidance.", 18, MUTED)
text(1594, 957, "Links with guidance.", 18, MUTED)

# Two short benefits balance the source panel without another technical layer.
text(83, 874, "Designed around her.", 28, PURPLE, extra='class="serif" font-style="italic"')
text(84, 913, "Personal context", 22, MUTED)
text(84, 944, "stays under her control.", 22, MUTED)
path("M80 1015H1840", "#e7dfe4", 1)
text(80, 1046, "LIVE PROTOTYPE ARCHITECTURE", 15, MUTED, 600, 'letter-spacing="1.8"')
text(
    1840,
    1046,
    "Intake + answer drafting both use Anymize · Selected evidence library",
    17,
    MUTED,
    extra='text-anchor="end"',
)
add("</svg>")

svg = "\n".join(parts)
(HERE / "backend-overview.svg").write_text(svg, encoding="utf-8")
html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>femaktiv — backend overview</title>
<style>
@page{{size:1920px 1080px;margin:0}}
html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:{PAPER}}}
svg{{display:block;width:1920px;height:1080px}}
</style>{svg}</html>"""
(HERE / "backend-overview.html").write_text(html, encoding="utf-8")

with sync_playwright() as p:
    executable = shutil.which("google-chrome") or shutil.which("chromium")
    browser = p.chromium.launch(executable_path=executable or p.chromium.executable_path)
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    page.goto((HERE / "backend-overview.html").as_uri())
    page.evaluate("document.fonts.ready")
    page.locator("svg").screenshot(path=str(HERE / "backend-overview.png"))
    page.pdf(
        path=str(HERE / "backend-overview.pdf"),
        width="1920px",
        height="1080px",
        print_background=True,
        prefer_css_page_size=True,
    )
    outside = page.locator("svg text").evaluate_all("""elements => elements.flatMap(el => {
        const b = el.getBBox();
        return b.x < 0 || b.y < 0 || b.x + b.width > 1920 || b.y + b.height > 1080
            ? [el.textContent] : [];
    })""")
    if outside:
        raise RuntimeError(f"Text outside canvas: {outside}")
    browser.close()

print("Created SVG, self-contained HTML, 3840 × 2160 PNG and one-page 16:9 PDF.")
