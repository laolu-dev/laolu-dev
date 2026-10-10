"""Generate the profile README art: assets/header.svg, assets/footer.svg and
assets/projects/*.png.

Text is converted to outlines (GitHub renders SVGs as images, so web fonts
can't load) and app icons are embedded as base64 PNGs, so every output is
self-contained. Colours follow the dark theme of olaoluwatoki.me.

    python3 -m venv .venv && .venv/bin/pip install -r art/requirements.txt
    .venv/bin/python art/build.py

Logos live in art/logos/. Fonts (Raleway, Open Sans; OFL) are downloaded
from google/fonts into art/fonts/ on first run.
"""
import base64, io, os, re, subprocess, sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
os.makedirs(f"{OUT}/assets/projects", exist_ok=True)

# dark palette from olaoluwatoki.me
INK, PANEL, SURFACE, MUTED, MUTED_FG, FG, GREEN = "#0A0A0A", "#121212", "#171717", "#262626", "#A1A1A1", "#FAFAFA", "#22C55E"

FONT_URLS = {
    "Raleway": "https://raw.githubusercontent.com/google/fonts/main/ofl/raleway/Raleway%5Bwght%5D.ttf",
    "OpenSans": "https://raw.githubusercontent.com/google/fonts/main/ofl/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf",
}

def font_path(name):
    path = f"{HERE}/fonts/{name}.ttf"
    if not os.path.exists(path):
        os.makedirs(f"{HERE}/fonts", exist_ok=True)
        # curl rather than urllib: some macOS Pythons ship without CA certs
        subprocess.run(["curl", "-fsSL", "-o", path, FONT_URLS[name]], check=True)
    return path

_fonts = {}
def font(name, wght):
    key = (name, wght)
    if key not in _fonts:
        f = TTFont(font_path(name))
        axes = {"wght": wght}
        if name == "OpenSans":
            axes["wdth"] = 100
        _fonts[key] = instantiateVariableFont(f, axes)
    return _fonts[key]

def text(name, wght, s, size, x, y, fill, spacing=0.0, anchor="start", attrs=""):
    """Return (<path>, width) for s rendered as outlines with baseline at y."""
    f = font(name, wght)
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    scale = size / f["head"].unitsPerEm
    width = sum(hmtx[cmap[ord(c)]][0] * scale + spacing for c in s) - spacing
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    pen = SVGPathPen(gs)
    cx = x
    for c in s:
        g = cmap[ord(c)]
        gs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, cx, y)))
        cx += hmtx[g][0] * scale + spacing
    d = re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.1f}".rstrip("0").rstrip("."), pen.getCommands())
    return f'<path d="{d}" fill="{fill}" {attrs}/>', width

def text_width(name, wght, s, size, spacing=0.0):
    return text(name, wght, s, size, 0, 0, "#000", spacing)[1]

# ---------- icons ----------
SRC = f"{HERE}/logos"

def load_icon(name, trim_white=False):
    im = Image.open(f"{SRC}/{name}.png").convert("RGBA")
    if trim_white:  # crop generous white padding, keep a small margin
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        x0, y0, x1, y1 = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
        pad = int(max(x1 - x0, y1 - y0) * 0.12)
        im = im.crop((max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, im.width), min(y1 + pad, im.height)))
    bbox = im.getchannel("A").getbbox()
    if bbox and bbox != (0, 0, *im.size):  # trim transparent margins
        im = im.crop(bbox)
    side = max(im.size)
    tile = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    tile.alpha_composite(im, ((side - im.width) // 2, (side - im.height) // 2))
    return tile

ICONS = {
    "fortel": load_icon("fortel", trim_white=True),
    "paypadi": load_icon("paypadi"),
    "agsol": load_icon("agsol"),
    "ellipsis": load_icon("ellipsis"),
    "dialink": load_icon("dialink"),
    "sigil": load_icon("sigil"),
}

def data_uri(im, px):
    buf = io.BytesIO()
    im.convert("RGB").resize((px, px), Image.LANCZOS).save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

# ---------- banner ----------
W, H = 1200, 440
DIAG_TOP, DIAG_BOTTOM = 700, 600  # mirrors LeftEdgeClipper's 100px offset
parts = []

# left: intro block, auto-fit so the name never crosses the diagonal
name_size = 76
while text_width("Raleway", 700, "Olaoluwa Toki", name_size) > 500:
    name_size -= 1
TOP = 178
hi, _ = text("Raleway", 700, "Hi, I am", 34, 64, TOP, MUTED_FG, attrs='class="in d1"')
nm, nm_w = text("Raleway", 700, "Olaoluwa Toki", name_size, 64, TOP + 30 + name_size, FG, attrs='class="in d2"')
role_y = TOP + 30 + name_size + 52
role, _ = text("Raleway", 900, "MOBILE ENGINEER", 24, 64, role_y, "#737373", spacing=5, attrs='class="in d3"')
tag_y = role_y + 48
tag, _ = text("OpenSans", 500, "Flutter & Dart · Lagos, Nigeria", 17, 64, tag_y, MUTED_FG, attrs='class="in d4"')

# phone geometry
PX, PY, PW, PH = 830, 34, 214, 372
SX, SY, SW, SH = PX + 10, PY + 10, PW - 20, PH - 20

icon_order = [("fortel", "Fortel"), ("paypadi", "PayPadi"), ("agsol", "AgSol"),
              ("ellipsis", "Ellipsis"), ("dialink", "Dialink"), ("sigil", "Sigil")]
ISZ = 50
icons_svg = []
for i, (key, label) in enumerate(icon_order):
    col, row = i % 3, i // 3
    cx = SX + SW * (2 * col + 1) / 6
    iy = SY + 118 + row * 92
    lbl, _ = text("OpenSans", 600, label, 10.5, cx, iy + ISZ + 16, "#D4D4D4", anchor="middle")
    icons_svg.append(
        f'<g class="pop" style="animation-delay:{0.15 * i:.2f}s">'
        f'<image href="{data_uri(ICONS[key], 112)}" x="{cx - ISZ / 2:.1f}" y="{iy}" width="{ISZ}" height="{ISZ}" clip-path="url(#ic{i})"/>'
        f'{lbl}</g>'
    )
    parts.append(f'<clipPath id="ic{i}"><rect x="{cx - ISZ / 2:.1f}" y="{iy}" width="{ISZ}" height="{ISZ}" rx="12"/></clipPath>')

clock, _ = text("OpenSans", 700, "9:41", 11, SX + 22, SY + 22, "#FFF")
date_big, _ = text("Raleway", 300, "Friday", 13, SX + SW / 2, SY + 66, MUTED_FG, anchor="middle")
greet, _ = text("Raleway", 700, "My apps", 26, SX + SW / 2, SY + 94, "#FFF", anchor="middle")

NX, NY, NW, NH = SX + 9, SY + 34, SW - 18, 58
n_title, _ = text("OpenSans", 700, "Olaoluwa Toki", 11, NX + 46, NY + 23, FG)
n_now, _ = text("OpenSans", 500, "now", 9.5, NX + NW - 10, NY + 23, "#737373", anchor="end")
n_body, _ = text("OpenSans", 500, "Open to new mobile roles", 9.6, NX + 46, NY + 40, MUTED_FG)

header = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Olaoluwa Toki, Mobile Engineer">
<style>
.in{{opacity:0;animation:rise .9s cubic-bezier(.2,.7,.2,1) forwards}}
.d1{{animation-delay:.1s}}.d2{{animation-delay:.3s}}.d3{{animation-delay:.55s}}.d4{{animation-delay:.75s}}
@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
.rule{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:draw 1s .9s cubic-bezier(.2,.7,.2,1) forwards}}
@keyframes draw{{to{{transform:scaleX(1)}}}}
.pop{{transform-box:fill-box;transform-origin:center;animation:pop 10s infinite both}}
@keyframes pop{{0%,3%{{opacity:0;transform:scale(.5)}}7%{{opacity:1;transform:scale(1.08)}}9%,90%{{opacity:1;transform:scale(1)}}95%,100%{{opacity:0;transform:scale(.5)}}}}
.notif{{animation:notif 10s infinite both}}
@keyframes notif{{0%,28%{{transform:translateY(-110px)}}33%,78%{{transform:translateY(0)}}84%,100%{{transform:translateY(-110px)}}}}
.glow{{animation:breathe 6s ease-in-out infinite alternate}}
@keyframes breathe{{from{{opacity:.55}}to{{opacity:.95}}}}
.dot{{animation:blink 1.6s ease-in-out infinite alternate}}
@keyframes blink{{from{{opacity:.35}}to{{opacity:1}}}}
</style>
<defs>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#FFF" stop-opacity=".10"/><stop offset=".6" stop-color="#FFF" stop-opacity=".03"/><stop offset="1" stop-color="#FFF" stop-opacity="0"/></radialGradient>
<radialGradient id="blob" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#FFF" stop-opacity=".06"/><stop offset="1" stop-color="#FFF" stop-opacity="0"/></radialGradient>
<linearGradient id="screen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1F1F1F"/><stop offset=".55" stop-color="{PANEL}"/><stop offset="1" stop-color="{INK}"/></linearGradient>
<pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.1" fill="#FFF" opacity=".05"/></pattern>
<clipPath id="scr"><rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="27"/></clipPath>
{''.join(parts)}
</defs>
<rect width="{W}" height="{H}" fill="{INK}"/>
<ellipse cx="160" cy="70" rx="220" ry="160" fill="url(#blob)"/>
<ellipse cx="420" cy="420" rx="260" ry="150" fill="url(#blob)"/>
<rect width="{DIAG_TOP}" height="{H}" fill="url(#grid)"/>
<polygon points="{DIAG_TOP},0 {W},0 {W},{H} {DIAG_BOTTOM},{H}" fill="{PANEL}"/>
<line x1="{DIAG_TOP}" y1="0" x2="{DIAG_BOTTOM}" y2="{H}" stroke="#FFF" stroke-opacity=".06" stroke-width="1.5"/>
<ellipse class="glow" cx="{PX + PW / 2}" cy="{PY + PH / 2}" rx="230" ry="210" fill="url(#glow)"/>
{hi}{nm}
<rect class="rule" x="64" y="{TOP + 30 + name_size + 16}" width="96" height="6" rx="3" fill="{GREEN}"/>
{role}{tag}
<rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="36" fill="{SURFACE}" stroke="#2E2E2E" stroke-width="1.5"/>
<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="27" fill="url(#screen)"/>
<g clip-path="url(#scr)">
{clock}
<rect x="{SX + SW - 40}" y="{SY + 13}" width="20" height="10" rx="3" fill="none" stroke="#FFF" stroke-width="1.2"/><rect x="{SX + SW - 38}" y="{SY + 15}" width="13" height="6" rx="1.5" fill="#FFF"/>
{date_big}{greet}
{''.join(icons_svg)}
<rect x="{SX + SW / 2 - 40}" y="{SY + SH - 14}" width="80" height="4" rx="2" fill="#FFF" opacity=".7"/>
<g class="notif">
<rect x="{NX}" y="{NY}" width="{NW}" height="{NH}" rx="15" fill="{MUTED}" opacity=".96" stroke="#333" stroke-width="1"/>
<rect x="{NX + 9}" y="{NY + 11}" width="28" height="28" rx="8" fill="{INK}"/>
<circle class="dot" cx="{NX + 23}" cy="{NY + 25}" r="6" fill="{GREEN}"/>
{n_title}{n_now}{n_body}
</g>
</g>
<rect x="{PX + PW / 2 - 34}" y="{PY + 18}" width="68" height="18" rx="9" fill="{INK}"/>
</svg>'''
open(f"{OUT}/assets/header.svg", "w").write(header)

# ---------- footer ----------
FW, FH = 1200, 110
f1, _ = text("Raleway", 700, "Thanks for stopping by.", 26, 64, 64, FG)
f2, _ = text("OpenSans", 600, "olaoluwatoki.me", 16, FW - 64, 62, MUTED_FG, anchor="end")
footer = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FW} {FH}" width="{FW}" height="{FH}" role="img" aria-label="Thanks for stopping by">
<polygon points="100,0 {FW},0 {FW},{FH} 0,{FH}" fill="{PANEL}"/>
<rect x="64" y="80" width="64" height="5" rx="2.5" fill="{GREEN}"/>
{f1}{f2}
</svg>'''
open(f"{OUT}/assets/footer.svg", "w").write(footer)

FULL_BLEED = ("agsol", "dialink")  # logos that fill their square edge to edge

# ---------- project images (portfolio card: white image area, icon centred) ----------
for key in ["fortel", "paypadi", "agsol", "ellipsis", "dialink"]:
    ic = ICONS[key].convert("RGB").resize((280, 280), Image.LANCZOS)
    bg = "white" if key in FULL_BLEED else ic.getpixel((2, 2))  # blend into the logo's own background
    cw = 1600 if key == "dialink" else 800  # Dialink's card spans both columns
    card = Image.new("RGB", (cw, 400), bg)
    if key in FULL_BLEED:  # full-bleed tiles get rounded corners like an app icon
        mask = Image.new("L", (280, 280), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 279, 279), 64, fill=255)
        card.paste(ic, ((cw - 280) // 2, 60), mask)
    else:
        card.paste(ic, ((cw - 280) // 2, 60))
    card.save(f"{OUT}/assets/projects/{key}.png", optimize=True)

print("name size", name_size, "name width", round(nm_w))
for p in ["assets/header.svg", "assets/footer.svg"] + [f"assets/projects/{k}.png" for k in ["fortel", "paypadi", "agsol", "ellipsis", "dialink"]]:
    print(p, os.path.getsize(f"{OUT}/{p}") // 1024, "KB")
