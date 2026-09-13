"""Build the standalone pitch artwork; no application or provider requests."""

import base64
import shutil
from html import escape
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
# Deliberately explicit presentation copy, never read credentials during rendering.
# Matched to the operator's configured openai/gpt-5.6-sol on 13 September 2026.
MODEL_LABEL = "GPT-5.6"
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


def stage(x, number, label, y=427):
    text(x, y, number, 19, PURPLE, 700)
    text(x + 39, y, label, 17, MUTED, 700, 'letter-spacing="2"')


def chip(x, y, width, label, fill="#ede5f2", color=PURPLE):
    rect(x, y, width, 39, fill, radius=19.5)
    text(x + width / 2, y + 26, label, 18, color, 600, 'text-anchor="middle"')


def image_data(path):
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def logo(name, x, y, width, height, url):
    add(f'<a xlink:href="{url}" target="_blank">')
    add(
        f'<image x="{x}" y="{y}" width="{width}" height="{height}" '
        f'xlink:href="{image_data(HERE / "assets" / name)}"/>'
    )
    add("</a>")


add("""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="1920" height="1080" viewBox="0 0 1920 1080" role="img"
    aria-labelledby="title description">
<title id="title">The intelligence behind femaktiv</title>
<desc id="description">Two separate inputs enter femaktiv coordination: private personal
context and a curated library of public sources. They use separate panels and arrows;
personal notes do not become evidence-library records. Intake and answer drafting pass
through Anymize, which handles identifier
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
  <marker id="coral-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M2 1 7 5 2 9" fill="none" stroke="#c4876e" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
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
text(84, 303, "Two distinct inputs. One thoughtful answer.", 25, MUTED)
add(
    f'<image x="1633" y="52" width="190" height="190" '
    f'xlink:href="{image_data(ROOT / "static/img/femaktiv-logo-rounded.png")}"/>'
)
chip(1601, 263, 224, "LIVE PROTOTYPE", "#f5eae8", "#866276")

stage(80, "01", "TWO DISTINCT INPUTS", 348)
stage(660, "02", "femaktiv")
stage(1100, "03", "PRIVACY + AI")
stage(1520, "04", "HER NEXT STEP")

# Two independent inputs: different ownership, visual treatment and entry arrows.
rect(80, 375, 500, 254, "#f1eaf5", "#dfd2e6", extra='filter="url(#shadow)"')
rect(80, 680, 500, 284, "url(#evidence)", "#e8ccc0", extra='filter="url(#shadow)"')
rect(660, 455, 360, 412, "url(#core)", extra='filter="url(#shadow)"')
rect(1100, 455, 340, 412, "url(#privacy)", "#dfd2e6")
rect(1520, 455, 320, 412, WHITE, "#ddcbdc", extra='filter="url(#shadow)"')

text(112, 414, "HER INFORMATION", 16, PURPLE, 700, 'letter-spacing="2"')
chip(450, 395, 99, "PRIVATE", "#e4d8ed", PURPLE)
text(112, 463, "Personal context", 35, PLUM, extra='class="serif"')
for name, label, y in [
    ("chat", "Her question", 511),
    ("note", "Notes she selects", 552),
    ("history", "Her active conversation", 593),
]:
    icon(name, 113, y - 22, PURPLE, 25)
    text(154, y, label, 23, MUTED)

text(112, 720, "PUBLIC KNOWLEDGE", 16, "#9d6b57", 700, 'letter-spacing="2"')
icon("book", 516, 703, "#a2737c", 29)
text(112, 763, "Curated sources", 35, PLUM, extra='class="serif"')
text(112, 799, "Selected nutrition + care guidance", 22, MUTED)
source_chips = [
    (112, 822, 95, "DGE"),
    (219, 822, 180, "NIH / NHLBI"),
    (411, 822, 137, "EFSA"),
    (112, 883, 287, "gesund.bund.de"),
    (411, 883, 137, "ZQP"),
]
for x, y, width, label in source_chips:
    rect(x, y, width, 46, "#fffdfbb5", "#ffffff", radius=13)
    text(x + width / 2, y + 30, label, 22, "#74566e", 600, 'text-anchor="middle"')

path(
    "M592 502H608Q622 502 622 516V555Q622 569 636 569H648",
    "#a78db3",
    2.5,
    'marker-end="url(#arrow)"',
)
path(
    "M592 822H608Q622 822 622 808V769Q622 755 636 755H648",
    "#c4876e",
    2.5,
    'marker-end="url(#coral-arrow)"',
)

# Backend coordination: neither personal notes nor the source library owns the other.
rect(692, 489, 50, 50, "#ffffff16", radius=15)
icon("spark", 704, 501, "#ecd2d9", 26)
text(692, 589, "Made relevant", 37, WHITE, extra='class="serif"')
text(692, 629, "to her.", 37, WHITE, extra='class="serif"')
text(692, 679, "Select relevant evidence.", 23, "#e4d5e9")
text(692, 714, "Preserve her constraints.", 23, "#e4d5e9")
text(692, 749, "Guide each model request.", 23, "#e4d5e9")
path("M692 776H988", "#ffffff25", 1)
text(692, 821, "BUILT WITH", 13, "#e4d5e9", 600, 'letter-spacing="1.7"')
rect(822, 791, 166, 48, WHITE, radius=10)
logo("django.svg", 844, 800, 122, 31, "https://www.djangoproject.com/")

# Identify the real integration and the model configured for this presentation.
logo("anymize.svg", 1132, 494, 206, 40, "https://anymize.ai/en")
text(1132, 590, "Identifier masking", 26, PLUM, 600)
text(1132, 630, "Handled by Anymize", 22, MUTED)
text(1132, 662, "before the AI model", 22, MUTED)
path("M1270 684V710", "#a78db3", 2, 'marker-end="url(#arrow)"')
rect(1132, 729, 276, 108, WHITE, "#ffffffa0", radius=18)
logo("openai.svg", 1152, 746, 41, 41, "https://openai.com/brand/")
text(1210, 776, MODEL_LABEL, 25, PLUM, 600)
text(1152, 814, "OpenAI model · via Anymize", 19, MUTED)

for start, end in [(1032, 1088), (1452, 1508)]:
    path(f"M{start} 661H{end}", "#a78db3", 2.3, 'marker-end="url(#arrow)"')

# Source checks occur in femaktiv after the draft returns.
rect(1552, 489, 50, 50, "#ede5f2", radius=15)
icon("check", 1564, 501, PURPLE, 26)
text(1552, 589, "Clear next steps.", 34, PLUM, extra='class="serif"')
text(1552, 635, "Practical guidance", 23, MUTED)
text(1552, 669, "with source references.", 23, MUTED)
rect(1552, 703, 256, 65, "#f5eae8", radius=13)
icon("link", 1568, 723, "#9d758a", 24)
text(1606, 729, "References checked", 19, PLUM)
text(1606, 753, "by femaktiv", 19, MUTED)
chip(1552, 792, 118, "ENGLISH")
chip(1682, 792, 117, "DEUTSCH")

text(
    660,
    924,
    "Her context brings relevance. Curated sources bring perspective.",
    30,
    PURPLE,
    extra='class="serif" font-style="italic"',
)
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
