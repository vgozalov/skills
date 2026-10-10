#!/usr/bin/env python3
"""Generate the README art: the banner, the two diagrams and the five skill emblems.

Everything is drawn here as plain SVG. Text is converted to outlines with fontTools, so the art
looks the same on every machine and nothing is fetched when the page is viewed.

Usage:  python3 assets/generate.py [OUT_DIR]        (default: the folder this file lives in)
Needs:  fonttools (pip install fonttools). The three typefaces (SIL OFL 1.1) are downloaded once
        into assets/.fonts/, pinned to a google/fonts commit and checked against a SHA-256.
"""
import hashlib
import os
import random
import sys
import urllib.parse
import urllib.request
from math import cos, radians, sin

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
FONT_DIR = os.path.join(HERE, ".fonts")
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------------------------
# Type: Instrument Serif (headlines), Instrument Sans (running text), IBM Plex Mono (labels).
# --------------------------------------------------------------------------------------------
FONTS_COMMIT = "bd8f81ddb5c74d5c8897b36ad88b440266245103"
FONT_FILES = {
    "serif": ("ofl/instrumentserif/InstrumentSerif-Regular.ttf", "InstrumentSerif-Regular.ttf",
              "498efd461f6ddfcb7a111bf9a565709d2085d48201d501ead960d93e84ffbb88"),
    "sans": ("ofl/instrumentsans/InstrumentSans[wdth,wght].ttf", "InstrumentSans.ttf",
             "b24f1812584816958afcf22e22d08e44318c5e51651e25d2438efdde389b33b1"),
    "mono": ("ofl/ibmplexmono/IBMPlexMono-Regular.ttf", "IBMPlexMono-Regular.ttf",
             "6a3412f058c7d8dfd9170c41e85ade48e5156ecb89356110ca57a0a27734af46"),
}


def fetch_font(repo_path, name, sha256):
    path = os.path.join(FONT_DIR, name)
    if os.path.exists(path) and hashlib.sha256(open(path, "rb").read()).hexdigest() == sha256:
        return path
    os.makedirs(FONT_DIR, exist_ok=True)
    url = ("https://raw.githubusercontent.com/google/fonts/%s/%s"
           % (FONTS_COMMIT, urllib.parse.quote(repo_path, safe="/,")))
    data = urllib.request.urlopen(url, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != sha256:
        sys.exit("generate.py: %s does not match its pinned SHA-256" % name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def num(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


class Face:
    """A typeface that turns a string into one SVG path of outlines."""

    def __init__(self, path):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]

    def width(self, s, size, tracking=0.0):
        k = size / self.upm
        return sum(self.hmtx[self.cmap[ord(c)]][0] * k + tracking for c in s) - tracking

    def outline(self, s, size, x, y, tracking=0.0, anchor="start"):
        k = size / self.upm
        w = self.width(s, size, tracking)
        x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
        out = []
        for c in s:
            name = self.cmap[ord(c)]
            pen = SVGPathPen(self.glyphs, ntos=num)
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x, y)))
            out.append(pen.getCommands())
            x += self.hmtx[name][0] * k + tracking
        return "".join(out)


FACES = {key: Face(fetch_font(*spec)) for key, spec in FONT_FILES.items()}


def text(face, s, size, x, y, fill, tracking=0.0, anchor="start", opacity=None):
    d = FACES[face].outline(s, size, x, y, tracking, anchor)
    extra = "" if opacity is None else ' opacity="%s"' % opacity
    return '<path d="%s" fill="%s"%s/>' % (d, fill, extra)


def twidth(face, s, size, tracking=0.0):
    return FACES[face].width(s, size, tracking)


# --------------------------------------------------------------------------------------------
# Palette: a dark opera house lit by lamps. Gold is the one accent, copper marks the tags.
# --------------------------------------------------------------------------------------------
C = dict(
    night="#140D08", night2="#1D130B", wood="#2B1B10",
    gold="#E4B04A", goldlt="#F3D58F", brass="#B88A34", brassdk="#6B4A1C", bronze="#3B2811",
    cream="#EFE4CF", muted="#B3A285", copper="#D4703C", lamp="#FFC45E", paper="#D8C79E",
)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


FINISH_DEFS = """
    <pattern id="hatchB" width="3.8" height="3.8" patternUnits="userSpaceOnUse" patternTransform="rotate(-34)">
      <line x1="0" y1="0" x2="0" y2="3.8" stroke="#000" stroke-width="0.8" opacity="0.55"/>
    </pattern>
    <linearGradient id="shadeRampDeep" x1="0.1" y1="0.05" x2="0.95" y2="1">
      <stop offset="0.6" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
    </linearGradient>
    <mask id="shadeDeep" maskContentUnits="objectBoundingBox"><rect x="-0.1" y="-0.1" width="1.2" height="1.2" fill="url(#shadeRampDeep)"/></mask>
    <clipPath id="clipHead"><path d="__HEAD__"/></clipPath>
    <clipPath id="clipTorso"><path d="__TORSO__"/></clipPath>
    <clipPath id="clipCHead"><path d="__CHEAD__"/></clipPath>
    <clipPath id="clipCoat"><path d="__COAT__"/></clipPath>
    <pattern id="wallLines" width="4.6" height="8" patternUnits="userSpaceOnUse">
      <line x1="0.5" y1="0" x2="0.5" y2="8" stroke="#000" stroke-width="0.9" opacity="0.5"/>
    </pattern>
    <radialGradient id="wallRamp" gradientUnits="userSpaceOnUse" cx="860" cy="250" r="640">
      <stop offset="0.3" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
    </radialGradient>
    <mask id="wallMask"><rect x="0" y="0" width="__W__" height="__H__" fill="url(#wallRamp)"/></mask>
    <radialGradient id="wallRampC" gradientUnits="userSpaceOnUse" cx="__CX__" cy="__CY__" r="__R__">
      <stop offset="0.35" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
    </radialGradient>
    <mask id="wallMaskC"><rect x="0" y="0" width="__W__" height="__H__" fill="url(#wallRampC)"/></mask>
    <radialGradient id="vigNat" cx="0.62" cy="0.44" r="0.74">
      <stop offset="0.48" stop-color="#050302" stop-opacity="0"/>
      <stop offset="0.76" stop-color="#050302" stop-opacity="0.32"/>
      <stop offset="1" stop-color="#050302" stop-opacity="0.88"/>
    </radialGradient>
    <filter id="ink" filterUnits="userSpaceOnUse" x="0" y="0" width="__W__" height="__H__" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.026" numOctaves="2" seed="8" result="lo"/>
      <feDisplacementMap in="SourceGraphic" in2="lo" scale="2.6" xChannelSelector="R" yChannelSelector="G" result="w1"/>
      <feTurbulence type="fractalNoise" baseFrequency="0.42" numOctaves="2" seed="2" result="hi"/>
      <feDisplacementMap in="w1" in2="hi" scale="0.9" xChannelSelector="G" yChannelSelector="B"/>
    </filter>
    <filter id="inkSoft" filterUnits="userSpaceOnUse" x="0" y="0" width="__W__" height="__H__" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="13" result="lo"/>
      <feDisplacementMap in="SourceGraphic" in2="lo" scale="2.4" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="warpV" filterUnits="userSpaceOnUse" x="-120" y="-120" width="__WV__" height="__HV__" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.0035 0.006" numOctaves="3" seed="17" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="150" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="film" filterUnits="userSpaceOnUse" x="0" y="0" width="__W__" height="__H__" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.62" numOctaves="3" seed="21" result="f"/>
      <feColorMatrix in="f" type="matrix" values="1.5 0 0 0 -0.25  1.5 0 0 0 -0.25  1.5 0 0 0 -0.25  0 0 0 0 1" result="fg"/>
      <feTurbulence type="fractalNoise" baseFrequency="0.010 0.016" numOctaves="3" seed="5" result="b"/>
      <feColorMatrix in="b" type="matrix" values="3.2 0 0 0 -1.1  3.2 0 0 0 -1.1  3.2 0 0 0 -1.1  0 0 0 0 1" result="bg"/>
      <feComposite in="fg" in2="bg" operator="arithmetic" k1="1" k2="0.5" k3="0" k4="0"/>
    </filter>
    <filter id="stain" filterUnits="userSpaceOnUse" x="0" y="0" width="__W__" height="__H__" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.0032 0.0055" numOctaves="4" seed="9"/>
      <feColorMatrix type="matrix" values="2.6 0 0 0 -0.78  2.3 0 0 0 -0.68  1.7 0 0 0 -0.4  0 0 0 0 1"/>
    </filter>
  """


def defs(w=1200, h=460):
    return (_defs_body() + "</defs>").replace("__W__", str(w)).replace("__H__", str(h)) \
        .replace("__WV__", str(w + 240)).replace("__HV__", str(h + 240)) \
        .replace("__CX__", str(w // 2)).replace("__CY__", str(h // 2)).replace("__R__", str(int(w * 0.62))) \
        .replace("__HEAD__", HEAD).replace("__TORSO__", TORSO).replace("__CHEAD__", CHEAD).replace("__COAT__", COAT)


def _defs_body():
    return """<defs>
    <pattern id="hatch" width="3.2" height="3.2" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">
      <line x1="0" y1="0" x2="0" y2="3.2" stroke="#000" stroke-width="0.9" opacity="0.5"/>
    </pattern>
    <linearGradient id="shadeRamp" x1="0.1" y1="0.05" x2="0.95" y2="1">
      <stop offset="0.35" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
    </linearGradient>
    <mask id="shade" maskContentUnits="objectBoundingBox"><rect x="-0.1" y="-0.1" width="1.2" height="1.2" fill="url(#shadeRamp)"/></mask>
    <linearGradient id="brassH" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#4E3514"/><stop offset="0.38" stop-color="#C9993C"/>
      <stop offset="0.66" stop-color="#F3D58F"/><stop offset="1" stop-color="#7A5520"/>
    </linearGradient>
    <radialGradient id="dome" cx="0.36" cy="0.28" r="0.85">
      <stop offset="0" stop-color="#F8E0A2"/><stop offset="0.42" stop-color="#C9993C"/>
      <stop offset="1" stop-color="#4A3212"/>
    </radialGradient>
    <linearGradient id="cloth" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0F0905"/><stop offset="0.55" stop-color="#2A1A0E"/>
      <stop offset="1" stop-color="#150D07"/>
    </linearGradient>
    <linearGradient id="woodgrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#82431A"/><stop offset="1" stop-color="#32180A"/>
    </linearGradient>
    <linearGradient id="podium" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3A2514"/><stop offset="1" stop-color="#150D07"/>
    </linearGradient>
    <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E9DAB0"/><stop offset="1" stop-color="#9E8A5E"/>
    </linearGradient>
    <radialGradient id="lamp" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFC45E" stop-opacity="0.78"/>
      <stop offset="0.35" stop-color="#FFAA3C" stop-opacity="0.30"/>
      <stop offset="1" stop-color="#FF9A2A" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="hole" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#000" stop-opacity="1"/><stop offset="0.55" stop-color="#000" stop-opacity="0.7"/>
      <stop offset="1" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="eye" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFEDB0" stop-opacity="0.95"/>
      <stop offset="1" stop-color="#FFD064" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="cone" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFD27A" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#FFB547" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="room" cx="0.72" cy="0.38" r="0.7">
      <stop offset="0" stop-color="#7A4A18" stop-opacity="0.50"/>
      <stop offset="1" stop-color="#7A4A18" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx="0.5" cy="0.5" r="0.75">
      <stop offset="0.6" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.6"/>
    </radialGradient>
    <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#241609"/><stop offset="1" stop-color="#090503"/>
    </linearGradient>
    <linearGradient id="folds" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="64" y2="0" spreadMethod="repeat">
      <stop offset="0" stop-color="#1A0907"/><stop offset="0.5" stop-color="#5A2118"/>
      <stop offset="1" stop-color="#1A0907"/>
    </linearGradient>
    <linearGradient id="fadeLeft" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0B0705" stop-opacity="0.96"/>
      <stop offset="0.5" stop-color="#0B0705" stop-opacity="0.7"/>
      <stop offset="1" stop-color="#0B0705" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="fadeBottom" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0B0705" stop-opacity="0"/>
      <stop offset="1" stop-color="#0B0705" stop-opacity="0.85"/>
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M1 1.5 L8.5 5 L1 8.5 Z" fill="#E4B04A"/>
    </marker>
  """ + FINISH_DEFS


STYLE = """<style>
    .swing { transform-origin: -50px -138px; }
    .breathe { opacity: 1; }
    @media (prefers-reduced-motion: no-preference) {
      .swing { animation: swing 2.8s ease-in-out infinite; }
      .breathe { animation: breathe 4.6s ease-in-out infinite; }
      .breathe.b { animation-delay: -1.3s; }
      .breathe.c { animation-delay: -2.6s; }
      .breathe.d { animation-delay: -3.5s; }
    }
    @keyframes swing { 0%, 100% { transform: rotate(-5deg); } 50% { transform: rotate(4deg); } }
    @keyframes breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.78; } }
  </style>"""


def svg_doc(w, h, title, desc, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
            'aria-labelledby="title desc">\n  <title id="title">%s</title>\n  <desc id="desc">%s</desc>\n  %s\n  %s\n%s\n</svg>\n'
            % (w, h, w, h, esc(title), esc(desc), STYLE, defs(w, h), body))


def card_bg(w, h):
    return ('<rect x="1" y="1" width="%d" height="%d" rx="22" fill="%s"/>' % (w - 2, h - 2, C["night"]) +
            '<rect x="1" y="1" width="%d" height="%d" rx="22" fill="url(#room)"/>' % (w - 2, h - 2))


def clip_defs(w, h):
    return '<clipPath id="card"><rect x="1" y="1" width="%d" height="%d" rx="22"/></clipPath>' % (w - 2, h - 2)


def vignette(w, h):
    """Off-centre and irregular, like the edge of a printed plate, not a perfect radial gradient."""
    return ('<g filter="url(#warpV)"><rect x="-120" y="-120" width="%d" height="%d" fill="url(#vigNat)"/></g>'
            % (w + 240, h + 240))


def dust(w, h, seed=11):
    """A few specks, fibres and hairline scratches, gathered towards the edges like a handled plate."""
    rng = random.Random(seed)
    out = []
    for _ in range(40):
        x, y = rng.random() * w, rng.random() * h
        if rng.random() < 0.55:
            x = (rng.random() * 0.14 if rng.random() < 0.5 else 1 - rng.random() * 0.14) * w
        r = 0.35 + rng.random() ** 3 * 0.9
        out.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" transform="rotate(%d %s %s)" fill="#F1E3C4" opacity="%s"/>'
                   % (num(x), num(y), num(r * (1 + rng.random())), num(r), rng.randint(0, 179), num(x), num(y),
                      num(0.1 + rng.random() * 0.28)))
    for _ in range(12):
        x, y = rng.random() * w, rng.random() * h
        dx, dy = rng.uniform(-9, 9), rng.uniform(-6, 6)
        out.append('<path d="M %s %s q %s %s %s %s" fill="none" stroke="#F1E3C4" stroke-width="0.6" stroke-linecap="round" opacity="%s"/>'
                   % (num(x), num(y), num(dx * 0.6), num(dy * 1.4), num(dx), num(dy), num(0.1 + rng.random() * 0.22)))
    for _ in range(3):
        x, y0 = rng.random() * w, rng.random() * h * 0.4
        length = h * rng.uniform(0.3, 0.7)
        out.append('<path d="M %s %s q %s %s %s %s" fill="none" stroke="#F1E3C4" stroke-width="0.5" opacity="0.1"/>'
                   % (num(x), num(y0), num(rng.uniform(-3, 3)), num(length / 2), num(rng.uniform(-4, 4)), num(length)))
    return "".join(out)


def finish(w, h):
    """Age stains, then film grain. Both blend with the picture, so they follow its tones."""
    return ('<rect x="0" y="0" width="%d" height="%d" fill="#000" filter="url(#stain)" style="mix-blend-mode:soft-light" opacity="0.22"/>'
            '<rect x="0" y="0" width="%d" height="%d" fill="#000" filter="url(#film)" style="mix-blend-mode:overlay" opacity="0.3"/>'
            % (w, h, w, h))


def border(w, h):
    return ('<rect x="1" y="1" width="%d" height="%d" rx="22" fill="none" stroke="%s" stroke-opacity="0.28" stroke-width="2"/>'
            % (w - 2, h - 2, C["gold"]))


def plate(w, h, content, labels):
    """Wrap a drawing as one printed plate: engraved wall, ink wobble, vignette, dust, stains, grain."""
    return "".join([
        clip_defs(w, h), '<g clip-path="url(#card)">', card_bg(w, h),
        '<rect x="0" y="0" width="%d" height="%d" fill="url(#wallLines)" mask="url(#wallMaskC)"/>' % (w, h),
        '<g filter="url(#ink)">', "\n  ".join(content), '</g>',
        '<g filter="url(#inkSoft)">', "\n  ".join(labels), '</g>',
        vignette(w, h), dust(w, h), finish(w, h), '</g>', border(w, h)])


# --------------------------------------------------------------------------------------------
# The orchestra: clockwork robots, each with its own music stand and lamp.
# Local coordinates: origin at the robot's hips, y grows downward, so the head is at about -90.
# --------------------------------------------------------------------------------------------
def arm(points):
    d = "M" + " L".join("%s %s" % (num(x), num(y)) for x, y in points)
    joints = "".join('<circle cx="%s" cy="%s" r="4" fill="#8A6224" stroke="#150C05" stroke-width="1.2"/>'
                     % (num(x), num(y)) for x, y in points[:-1])
    hx, hy = points[-1]
    return ('<path d="%s" fill="none" stroke="#150C05" stroke-width="9.6" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="#B8892F" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
            '<path d="%s" fill="none" stroke="#F0CB7A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>'
            '%s<circle cx="%s" cy="%s" r="4.6" fill="#D9AB52" stroke="#150C05" stroke-width="1.3"/>'
            % (d, d, d, joints, num(hx), num(hy)))


COAT = "M -23 -62 L -27 -118 Q -27 -130 -14 -130 L 14 -130 Q 27 -130 27 -118 L 23 -62 Z"
CHEAD = "M -26 -136 L -26 -158 A 26 26 0 0 1 26 -158 L 26 -136 Q 0 -131 -26 -136 Z"
TORSO = "M -24 0 L -27 -50 Q -27 -58 -19 -58 L 19 -58 Q 27 -58 27 -50 L 24 0 Z"
HEAD = "M -23 -66 L -23 -86 A 23 23 0 0 1 23 -86 L 23 -66 Q 0 -61 -23 -66 Z"


def winding_key(x, y):
    return ('<path d="M %s %s H %s" stroke="#8A6224" stroke-width="3" stroke-linecap="round"/>'
            '<ellipse cx="%s" cy="%s" rx="5.2" ry="3.7" fill="#C9993C" stroke="#150C05" stroke-width="1.3"/>'
            '<ellipse cx="%s" cy="%s" rx="5.2" ry="3.7" fill="#C9993C" stroke="#150C05" stroke-width="1.3"/>'
            % (num(x), num(y), num(x - 10), num(x - 14), num(y - 6.5), num(x - 14), num(y + 6.5)))


def shade(tag, geom, contours=""):
    """Engraving for one form: single hatching in the half-shadow, crossing hatching in the deep shadow."""
    return ('<%s %s fill="url(#hatch)" mask="url(#shade)"/><%s %s fill="url(#hatchB)" mask="url(#shadeDeep)"/>%s'
            % (tag, geom, tag, geom, contours))


def contours(clip, curves):
    """Form-following lines, clipped to the shape and shown only where the shadow falls."""
    return ('<g clip-path="url(#%s)" mask="url(#shade)" fill="none" stroke="#000" stroke-width="0.8" '
            'stroke-linecap="round" opacity="0.6">%s</g>' % (clip, "".join('<path d="%s"/>' % c for c in curves)))


TORSO_LINES = contours("clipTorso", ["M %d -58 Q %d -30 %d 0" % (x, x + 3, x - 1) for x in (4, 8, 12, 16, 20, 24)])
HEAD_LINES = contours("clipHead", ["M -23 %d Q 0 %d 23 %d" % (y, y - 9, y) for y in (-91, -97, -102, -106)])
COAT_LINES = contours("clipCoat", ["M %d -130 Q %d -96 %d -62" % (x, x + 3, x - 2) for x in (2, 7, 12, 17, 22)])
CHEAD_LINES = contours("clipCHead", ["M -26 %d Q 0 %d 26 %d" % (y, y - 10, y) for y in (-150, -157, -164, -170, -175)])


def robot_body(look):
    eyes = ""
    for ex in (-8.5, 8.5):
        eyes += ('<circle cx="%s" cy="-84" r="11" fill="url(#eye)"/>'
                 '<circle cx="%s" cy="-84" r="5.8" fill="#FFF1CC"/>'
                 '<circle cx="%s" cy="-83.4" r="2.5" fill="#1A0F06"/>' % (num(ex), num(ex), num(ex + look)))
    return (
        '<path d="%s" fill="url(#brassH)" stroke="#150C05" stroke-width="1.8"/>'
        '%s'
        '<path d="M -25 -18 H 25" stroke="#3B2811" stroke-width="1.3" opacity="0.8"/>'
        '<circle cx="0" cy="-36" r="8" fill="#1B1109" stroke="#F3D58F" stroke-width="1.4"/>'
        '<path d="M 0 -36 L 4 -41" stroke="#F3D58F" stroke-width="1.2" stroke-linecap="round"/>'
        '<g fill="#F3D58F"><circle cx="-18" cy="-50" r="1.6"/><circle cx="18" cy="-50" r="1.6"/>'
        '<circle cx="-21" cy="-8" r="1.6"/><circle cx="21" cy="-8" r="1.6"/></g>'
        '<rect x="-5.5" y="-67" width="11" height="9" fill="#4F3714" stroke="#2E1F0C" stroke-width="0.9"/>'
        '<path d="%s" fill="url(#dome)" stroke="#150C05" stroke-width="1.8"/>'
        '%s'
        '<path d="M -23 -70 Q 0 -65 23 -70" fill="none" stroke="#3B2811" stroke-width="1.1"/>'
        '<rect x="-18" y="-94" width="36" height="20" rx="10" fill="#140C07"/>%s'
        '<circle cx="-24" cy="-82" r="3.2" fill="#B88A34" stroke="#2E1F0C" stroke-width="0.8"/>'
        '<circle cx="24" cy="-82" r="3.2" fill="#B88A34" stroke="#2E1F0C" stroke-width="0.8"/>'
        '<ellipse cx="-10" cy="-104" rx="7" ry="2.8" fill="#FFF3D0" opacity="0.28" transform="rotate(-24 -10 -104)"/>'
        % (TORSO, shade("path", 'd="%s"' % TORSO, TORSO_LINES), HEAD, shade("path", 'd="%s"' % HEAD, HEAD_LINES), eyes))


def stand():
    """Music stand with a brass lamp. Returns (svg, lamp centre in local coordinates)."""
    staff = ""
    for row in (0, 1):
        for line in range(5):
            y = -22 + row * 15 + line * 1.9
            staff += '<path d="M -26 %s H 26"/>' % num(y)
    notes = ""
    for nx, ny in ((-18, -17), (-9, -15), (2, -18), (13, -16), (-14, -3), (-3, -1), (8, -4), (19, -2)):
        notes += '<circle cx="%s" cy="%s" r="1.5"/><path d="M %s %s V %s" stroke="#4B3A1E" stroke-width="0.7"/>' % (
            nx, ny, num(nx + 1.4), ny, ny - 8)
    return (
        '<path d="M 0 4 V 34 M 0 32 L -15 46 M 0 32 L 15 46" stroke="#5C3F17" stroke-width="3" stroke-linecap="round" fill="none"/>'
        '<path d="M -31 -27 L 31 -30 L 29 2 L -29 5 Z" fill="url(#paper)" stroke="#2A1A09" stroke-width="1.7"/>'
        '<g stroke="#6B5A3A" stroke-width="0.55" opacity="0.8">%s</g><g fill="#4B3A1E" opacity="0.85">%s</g>'
        '<path d="M -31 5 L 29 2" stroke="#6B4A1C" stroke-width="2.4"/>'
        '<path d="M -8 -43 L 22 -26 L -26 -26 Z" fill="url(#cone)"/>'
        '<path d="M 18 -29 Q 19 -47 9 -50" fill="none" stroke="#B88A34" stroke-width="2.2" stroke-linecap="round"/>'
        '<path d="M 4 -56 L 14 -56 L 20 -45 L -2 -45 Z" fill="#E4B04A" stroke="#4A3212" stroke-width="1"/>'
        '<ellipse cx="9" cy="-44" rx="4" ry="2.4" fill="#FFF2C4"/>'
        % (staff, notes)), (9, -40)


def instrument(kind):
    """Returns (behind the body, in front of the body, arms)."""
    wood = 'fill="url(#woodgrad)" stroke="#120A04" stroke-width="1.7"'
    if kind == "violin":
        front = ('<g transform="rotate(-32 -12 -60)"><ellipse cx="-12" cy="-60" rx="14" ry="8.2" %s/>'
                 '%s</g>'
                 '<path d="M -4 -64 L 31 -80" stroke="#2B1405" stroke-width="3.2" stroke-linecap="round"/>'
                 '<circle cx="33" cy="-81" r="2.6" fill="#7A3E16"/>'
                 '<path d="M -30 -44 L 42 -66" stroke="#EADBB6" stroke-width="1.3" stroke-linecap="round"/>'
                 % (wood, shade("ellipse", 'cx="-12" cy="-60" rx="14" ry="8.2"')))
        arms = arm([(-26, -50), (-36, -34), (-14, -40)]) + arm([(26, -50), (42, -44), (28, -72)])
        return "", front, arms
    if kind == "cello":
        body_path = ("M -26 -34 C -26 -48 -12 -52 -6 -52 C 0 -52 14 -48 14 -34 C 14 -26 8 -24 8 -18 C 8 -8 16 -4 16 4 "
                     "C 16 14 4 18 -6 18 C -16 18 -28 14 -28 4 C -28 -4 -20 -8 -20 -18 C -20 -24 -26 -26 -26 -34 Z")
        front = ('<path d="M -22 -44 L -36 -104" stroke="#2B1405" stroke-width="4.5" stroke-linecap="round"/>'
                 '<circle cx="-37" cy="-108" r="3.8" fill="#7A3E16" stroke="#2B1405" stroke-width="1"/>'
                 '<g transform="translate(-14 0)"><path d="%s" %s/>%s</g>'
                 '<path d="M -44 -16 L 22 -26" stroke="#EADBB6" stroke-width="1.3" stroke-linecap="round"/>' % (body_path, wood, shade("path", 'd="%s"' % body_path)))
        arms = arm([(-26, -50), (-42, -66), (-35, -86)]) + arm([(26, -50), (40, -34), (22, -21)])
        return "", front, arms
    if kind == "bass":
        bass = ("M -58 -36 C -58 -52 -44 -58 -36 -58 C -28 -58 -16 -52 -16 -36 C -16 -26 -22 -24 -22 -16 C -22 -4 -12 0 -12 12 "
                "C -12 26 -26 30 -36 30 C -46 30 -60 26 -60 12 C -60 0 -50 -4 -50 -16 C -50 -24 -58 -26 -58 -36 Z")
        back = ('<path d="M -36 -52 V -134" stroke="#120A04" stroke-width="5.6" stroke-linecap="round"/>'
                '<circle cx="-36" cy="-139" r="4.4" fill="#7A3E16" stroke="#120A04" stroke-width="1.4"/>'
                '<path d="%s" %s/>%s' % (bass, wood, shade("path", 'd="%s"' % bass)))
        arms = arm([(-26, -50), (-40, -74), (-34, -100)]) + arm([(26, -50), (4, -44), (-22, -24)])
        return back, "", arms
    if kind == "trumpet":
        front = ('<path d="M 12 -80 L 52 -84" stroke="#F3D58F" stroke-width="4.2" stroke-linecap="round"/>'
                 '<path d="M 24 -80 V -70 M 31 -81 V -70 M 38 -82 V -70" stroke="#B88A34" stroke-width="2.4" stroke-linecap="round"/>'
                 '<path d="M 50 -85 L 70 -98 L 72 -72 Z" fill="#E4B04A" stroke="#4A3212" stroke-width="1.1" stroke-linejoin="round"/>'
                 + shade("path", 'd="M 50 -85 L 70 -98 L 72 -72 Z"'))
        arms = arm([(26, -50), (42, -58), (32, -76)]) + arm([(-26, -50), (-6, -58), (18, -74)])
        return "", front, arms
    if kind == "clarinet":
        front = ('<path d="M 6 -78 L 18 -26" stroke="#1A1008" stroke-width="4.6" stroke-linecap="round"/>'
                 '<g fill="#E4B04A"><circle cx="9" cy="-66" r="1.4"/><circle cx="11.5" cy="-55" r="1.4"/>'
                 '<circle cx="14" cy="-44" r="1.4"/></g>'
                 '<path d="M 14 -30 L 24 -18 L 10 -18 Z" fill="#1A1008" stroke="#E4B04A" stroke-width="0.8"/>')
        arms = arm([(26, -50), (30, -52), (11.5, -55)]) + arm([(-26, -50), (-8, -48), (14, -42)])
        return "", front, arms
    raise ValueError(kind)


def robot(cx, base, s, kind, look=1.0):
    """One seated robot. Returns its markup and the (x, y, r) of its lamp glow in banner coordinates."""
    back, front, arms = instrument(kind)
    st, lamp_xy = stand()
    svg = ('<g transform="translate(%s %s) scale(%s)">%s%s%s%s%s%s</g>'
           % (num(cx), num(base), num(s), back, winding_key(-27, -34), robot_body(look), front, arms, st))
    return svg, (cx + lamp_xy[0] * s, base + lamp_xy[1] * s, 36 * s)


def conductor(cx, base, s):
    """A taller brass robot in a tailcoat, half-lidded eyes, baton raised towards the orchestra."""
    hx, hy = 0, -158
    eyes = ""
    for ex in (-9.5, 9.5):
        eyes += ('<circle cx="%s" cy="%s" r="12" fill="url(#eye)" opacity="0.8"/>'
                 '<circle cx="%s" cy="%s" r="6.6" fill="#FFF1CC"/>'
                 '<path d="M %s %s A 6.6 6.6 0 0 1 %s %s Z" fill="#140C07"/>'
                 '<circle cx="%s" cy="%s" r="2.5" fill="#1A0F06"/>'
                 % (num(ex), hy, num(ex), hy, num(ex - 6.6), hy, num(ex + 6.6), hy, num(ex - 1.5), hy + 2.4))
    coat, head = COAT, CHEAD
    body = (
        '<path d="M -22 -62 L -34 -26 L -12 -56 Z M 22 -62 L 34 -26 L 12 -56 Z" fill="#120B06" stroke="#6B4A1C" stroke-width="1"/>'
        '<path d="M -9 -62 V 0 M 9 -62 V 0" stroke="#1C120A" stroke-width="12" stroke-linecap="round"/>'
        '<path d="M -9 -62 V -2 M 9 -62 V -2" stroke="#3A2616" stroke-width="2" stroke-linecap="round" opacity="0.7"/>'
        '<ellipse cx="-10" cy="0" rx="10" ry="3.6" fill="#0E0805" stroke="#B88A34" stroke-width="0.9"/>'
        '<ellipse cx="10" cy="0" rx="10" ry="3.6" fill="#0E0805" stroke="#B88A34" stroke-width="0.9"/>'
        + winding_key(-26, -100) +
        '<path d="%s" fill="url(#cloth)" stroke="#6B4A1C" stroke-width="1.4"/>'
        '%s'
        '<path d="M -7 -129 L 7 -129 L 4 -84 L -4 -84 Z" fill="#EFE4CF" opacity="0.92"/>'
        '<g fill="#B88A34"><circle cx="0" cy="-116" r="1.5"/><circle cx="0" cy="-104" r="1.5"/><circle cx="0" cy="-92" r="1.5"/></g>'
        '<path d="M -14 -130 L -4 -100 L -8 -84 M 14 -130 L 4 -100 L 8 -84" fill="none" stroke="#B88A34" stroke-width="1" opacity="0.8"/>'
        '<path d="M -5 -128 L 0 -125 L -5 -122 Z M 5 -128 L 0 -125 L 5 -122 Z" fill="#E4B04A"/>'
        '<rect x="-6" y="-141" width="12" height="11" fill="#4F3714" stroke="#2E1F0C" stroke-width="0.9"/>'
        '<path d="%s" fill="url(#dome)" stroke="#150C05" stroke-width="1.9"/>'
        '%s'
        '<path d="M -26 -141 Q 0 -136 26 -141" fill="none" stroke="#3B2811" stroke-width="1.1"/>'
        '<rect x="-21" y="-171" width="42" height="22" rx="11" fill="#140C07"/>%s'
        '<path d="M -7 -144 H 7" stroke="#140C07" stroke-width="2" stroke-linecap="round"/>'
        '<ellipse cx="-11" cy="-180" rx="8" ry="3" fill="#FFF3D0" opacity="0.28" transform="rotate(-24 -11 -180)"/>'
        % (coat, shade("path", 'd="%s"' % coat, COAT_LINES), head, shade("path", 'd="%s"' % head, CHEAD_LINES), eyes))
    free_arm = arm([(24, -120), (42, -98), (22, -82)])
    swing = ('<g class="swing">' + arm([(-50, -138), (-64, -170)]) +
             '<path d="M -64 -170 L -108 -214" stroke="#EFE4CF" stroke-width="2.4" stroke-linecap="round"/>'
             '<circle cx="-108" cy="-214" r="1.8" fill="#FFF3D0"/></g>')
    upper = arm([(-22, -122), (-50, -138)])
    place = 'transform="translate(%s %s) scale(%s)"' % (num(cx), num(base), num(s))
    return '<g %s>%s%s%s</g>' % (place, body, free_arm, upper), '<g %s>%s</g>' % (place, swing)


def podium(cx, top, w=150, h=62):
    x0 = cx - w / 2
    inner = ""
    for i in range(3):
        px = x0 + 10 + i * (w - 20) / 3
        inner += '<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="none" stroke="#B88A34" stroke-opacity="0.45" stroke-width="1"/>' % (
            num(px), top + 14, num((w - 20) / 3 - 6), h - 24)
    return ('<rect x="%s" y="%s" width="%s" height="%s" fill="url(#podium)" stroke="#6B4A1C" stroke-width="1.2"/>'
            '<rect x="%s" y="%s" width="%s" height="7" fill="#4A3014" stroke="#B88A34" stroke-opacity="0.6" stroke-width="1"/>%s'
            % (num(x0), top, w, h, num(x0 - 6), top, w + 12, inner))


BALCONY_X = (662, 760, 858)


def balcony():
    out = []
    for x in BALCONY_X:
        out.append('<path d="M %d 118 V 58 A 28 28 0 0 1 %d 58 V 118" fill="#0A0604" fill-opacity="0.5" stroke="#8A6224" '
                   'stroke-opacity="0.5" stroke-width="2"/>' % (x - 28, x + 28))
        out.append('<circle cx="%d" cy="66" r="4" fill="#FFE6A8"/>' % x)
    out.append('<path d="M 620 122 H 900" stroke="#8A6224" stroke-opacity="0.5" stroke-width="2"/>')
    out.append('<path d="M 620 130 H 900" stroke="#8A6224" stroke-opacity="0.22" stroke-width="1"/>')
    return "".join(out)


def balcony_glows():
    return "".join('<circle cx="%d" cy="66" r="46" fill="url(#lamp)" class="breathe %s"/>' % (x, "bcd"[i])
                   for i, x in enumerate(BALCONY_X))


def floor(w, y0, h):
    planks = ""
    for i in range(-6, 19):
        planks += '<path d="M %s %s L %s %s"/>' % (num(600 + (i * 120 - 600) * 0.35), y0, num(i * 120 - 60), h)
    return ('<path d="M 1 %d H %d V %d H 1 Z" fill="url(#floor)"/>' % (y0, w - 1, h - 22) +
            '<g stroke="#000" stroke-opacity="0.5" stroke-width="1.2">%s</g>' % planks +
            '<path d="M 1 %d H %d" stroke="#B88A34" stroke-opacity="0.25" stroke-width="1.5"/>' % (y0, w - 1))


# --------------------------------------------------------------------------------------------
# Emblems: one gold line drawing per skill, used on the banner strip and as table markers.
# --------------------------------------------------------------------------------------------
def emblem(name):
    g, s = C["gold"], 'fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"' % C["gold"]
    if name == "parallel-agent-development":  # a baton leading three parallel tracks
        tracks = "".join('<path d="M 33 %d H 43" %s/>' % (y, s) for y in (11, 22, 33))
        return ('<path d="M 8 41 L 27 22" %s/><circle cx="8" cy="41" r="3.4" fill="%s"/><circle cx="28" cy="21" r="2.2" fill="%s"/>%s'
                % (s, g, g, tracks))
    if name == "parallel-plans":  # a score with two beamed notes
        staff = "".join('<path d="M 14 %d H 34" stroke="%s" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/>' % (y, g)
                        for y in (13, 17, 21, 25, 29))
        return ('<rect x="9" y="7" width="30" height="34" rx="3.5" %s/>%s'
                '<circle cx="19" cy="34" r="2.7" fill="%s"/><circle cx="30" cy="32" r="2.7" fill="%s"/>'
                '<path d="M 21.4 34 V 22 L 32.4 20 V 32" %s/>' % (s, staff, g, g, s))
    if name == "parallel-briefs":  # a music stand with its lamp
        return ('<path d="M 10 14 L 38 14 L 36 29 L 12 29 Z" %s/><path d="M 24 29 V 40 M 24 38 L 15 45 M 24 38 L 33 45" %s/>'
                '<path d="M 34 14 Q 39 7 31 4" %s/><path d="M 27 1.5 H 35 L 37 6.5 H 25 Z" fill="%s"/>'
                '<path d="M 17 20 H 31 M 17 24 H 27" stroke="%s" stroke-width="1.2" stroke-linecap="round" opacity="0.7"/>'
                % (s, s, s, g, g))
    if name == "wrap-up":  # stage curtains drawn closed
        return ('<path d="M 6 7 H 42" %s/><circle cx="6" cy="7" r="2.2" fill="%s"/><circle cx="42" cy="7" r="2.2" fill="%s"/>'
                '<path d="M 9 10 H 24 V 41 Q 20.5 44.5 16.5 41 Q 12.5 44.5 9 41 Z" %s/>'
                '<path d="M 24 10 H 39 V 41 Q 35.5 44.5 31.5 41 Q 27.5 44.5 24 41 Z" %s/>'
                '<path d="M 14 11 Q 12.5 26 14 38 M 19 11 Q 20.5 26 19 38 M 29 11 Q 27.5 26 29 38 M 34 11 Q 35.5 26 34 38" '
                'fill="none" stroke="%s" stroke-width="1.2" stroke-linecap="round" opacity="0.65"/>'
                % (s, g, g, s, s, g))
    if name == "create-sprint":  # a metronome
        return ('<path d="M 15 42 L 20 8 H 28 L 33 42 Z" %s/><path d="M 11 42 H 37" %s/>'
                '<path d="M 24 36 L 31 14" %s/><rect x="27.4" y="18" width="6" height="5" rx="1" fill="%s" transform="rotate(12 30 20)"/>'
                % (s, s, s, g))
    raise ValueError(name)


SKILLS = ["parallel-plans", "parallel-agent-development", "parallel-briefs", "wrap-up", "create-sprint"]


MARKER_DEFS = ('<defs><radialGradient id="lamp" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#FFC45E" stop-opacity="0.78"/>'
               '<stop offset="0.35" stop-color="#FFAA3C" stop-opacity="0.30"/><stop offset="1" stop-color="#FF9A2A" stop-opacity="0"/>'
               '</radialGradient></defs>')


def marker(name):
    body = ('<rect x="1" y="1" width="54" height="54" rx="13" fill="#17100B" stroke="%s" stroke-opacity="0.45" stroke-width="1.5"/>'
            '<circle cx="28" cy="28" r="24" fill="url(#lamp)" opacity="0.35"/><g transform="translate(4 4)">%s</g>'
            % (C["gold"], emblem(name)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 56 56" width="56" height="56" role="img" aria-label="%s">'
            '<title>%s</title>%s%s</svg>\n' % (name, name, MARKER_DEFS, body))


# --------------------------------------------------------------------------------------------
# Banner
# --------------------------------------------------------------------------------------------
def banner():
    W, H = 1200, 460
    scene = []

    # the house: engraved wall, a curtain on the left, a gilded balcony on the right, a wooden stage
    scene.append('<rect x="330" y="0" width="870" height="380" fill="url(#wallLines)" mask="url(#wallMask)"/>')
    scene.append('<g transform="translate(330 0)"><rect x="0" y="0" width="190" height="380" fill="url(#folds)" opacity="0.8"/>'
                 '<rect x="0" y="0" width="190" height="380" fill="url(#wallLines)" opacity="0.55"/></g>')
    scene.append('<path d="M 330 0 H 520 Q 470 44 430 40 Q 380 36 330 0 Z" fill="#2A0E0A" opacity="0.9"/>')
    scene.append(balcony())
    scene.append(floor(W, 372, H))
    scene.append('<ellipse cx="1100" cy="250" rx="230" ry="250" fill="url(#lamp)" opacity="0.30"/>')

    glows = []
    back = []
    for cx, kind, look in ((580, "bass", 1.5), (722, "clarinet", 1.5), (864, "violin", 1.5)):
        svg, glow = robot(cx, 322, 1.2, kind, look=look)
        back.append(svg)
        glows.append(glow)
    scene.append('<g opacity="0.8">%s</g>' % "".join(back))

    for cx, kind, look in ((505, "violin", 1.6), (647, "cello", 1.6), (789, "violin", 1.6), (931, "trumpet", 1.6)):
        svg, glow = robot(cx, 372, 1.5, kind, look=look)
        scene.append(svg)
        glows.append(glow)

    scene.append(podium(1100, 322, w=170))
    body, swing = conductor(1100, 322, 1.35)
    scene.append(body)

    parts = [clip_defs(W, H), '<g clip-path="url(#card)">', card_bg(W, H), '<g filter="url(#ink)">', "".join(scene), "</g>"]

    # light falls in pools: a shadow over the whole stage, cut open around every lamp and the podium
    holes = "".join('<circle cx="%s" cy="%s" r="%s" fill="url(#hole)"/>' % (num(x), num(y), num(r * 2.1)) for x, y, r in glows)
    holes += "".join('<circle cx="%d" cy="66" r="78" fill="url(#hole)"/>' % x for x in BALCONY_X)
    holes += '<ellipse cx="1100" cy="240" rx="250" ry="270" fill="url(#hole)"/>'
    parts.append('<mask id="lightmap" maskUnits="userSpaceOnUse" x="0" y="0" width="%d" height="%d">'
                 '<rect x="0" y="0" width="%d" height="%d" fill="#fff"/>%s</mask>' % (W, H, W, H, holes))
    parts.append('<rect x="0" y="0" width="%d" height="%d" fill="#0A0503" opacity="0.52" mask="url(#lightmap)"/>' % (W, H))

    # light and the moving baton stay outside the filtered scene, so the animation stays cheap
    parts.append(swing)
    parts.append(balcony_glows())
    for i, (x, y, r) in enumerate(glows):
        parts.append('<circle cx="%s" cy="%s" r="%s" fill="url(#lamp)" opacity="0.8" class="breathe %s"/>'
                     % (num(x), num(y), num(r * 1.6), "abcd"[i % 4]))

    parts.append(vignette(W, H))
    parts.append('<rect x="1" y="1" width="600" height="%d" fill="url(#fadeLeft)"/>' % (H - 2))
    parts.append('<rect x="1" y="330" width="%d" height="129" fill="url(#fadeBottom)"/>' % (W - 2))
    parts.append(dust(W, H))

    # the words
    gold, cream, muted, copper = C["gold"], C["cream"], C["muted"], C["copper"]
    x = 56
    for label in ("claude", "codex"):
        w = twidth("mono", label, 14) + 26
        parts.append('<rect x="%s" y="86" width="%s" height="28" rx="8" fill="none" stroke="%s" stroke-width="1.4"/>'
                     % (num(x), num(w), copper))
        parts.append(text("mono", label, 14, x + 13, 105, copper))
        x += w + 10
    parts.append('<path d="M %s 84 V 116" stroke="%s" stroke-opacity="0.55" stroke-width="1.5"/>' % (num(x + 4), gold))
    parts.append(text("mono", "agent skills", 15, x + 20, 105, muted))

    parts.append(text("serif", "Every agent", 80, 54, 208, cream, tracking=-1.6))
    parts.append(text("serif", "owns its part.", 80, 54, 284, cream, tracking=-1.6))
    parts.append(text("sans", "Skills for running coding agents in parallel", 19, 56, 326, muted))
    parts.append(text("sans", "without collisions.", 19, 56, 352, muted))

    # a strip with one chip per skill, like the slide index it borrows from
    cx, cy, ch = 56, 388, 44
    for name in SKILLS:
        w = 26 + 28 + twidth("mono", name, 13) + 22
        parts.append('<rect x="%s" y="%d" width="%s" height="%d" rx="9" fill="#120B07" fill-opacity="0.82" stroke="%s" '
                     'stroke-opacity="0.34" stroke-width="1.2"/>' % (num(cx), cy, num(w), ch, gold))
        parts.append('<g transform="translate(%s %d) scale(0.58)">%s</g>' % (num(cx + 12), cy + 8, emblem(name)))
        parts.append(text("mono", name, 13, cx + 12 + 28 + 8, cy + 27, cream))
        cx += w + 12

    parts.append(finish(W, H))
    parts.append("</g>")
    parts.append(border(W, H))

    desc = ("Skills for Claude Code and Codex. A conductor robot and an orchestra of brass clockwork robots, "
            "each reading from its own music stand under its own lamp: every agent owns its part.")
    return svg_doc(W, H, "skills", desc, "\n  ".join(parts))


# --------------------------------------------------------------------------------------------
# Diagrams
# --------------------------------------------------------------------------------------------
def box(x, y, w, h, accent=False, fill="#1A110A"):
    stroke = C["gold"] if accent else "#6B4A1C"
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="12" fill="%s" fill-opacity="0.92" stroke="%s" '
            'stroke-width="%s"%s/>' % (num(x), num(y), num(w), num(h), fill, stroke, "2" if accent else "1.4",
                                       "" if accent else ' stroke-opacity="0.9"'))


def line(d, dashed=False, arrow=True, color=None, width=2):
    return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"%s%s/>'
            % (d, color or C["gold"], width, ' stroke-dasharray="6 6"' if dashed else "",
               ' marker-end="url(#arrow)"' if arrow else ""))


def parallel_waves():
    W, H = 1200, 480
    p, t = [], []
    gold, cream, muted = C["gold"], C["cream"], C["muted"]
    ys = (104, 188, 272, 356)  # task rows

    # plan and the shared kit
    p.append(box(48, 170, 172, 140))
    t.append(text("serif", "Plan", 38, 70, 222, cream))
    t.append(text("mono", "Owns per task", 13, 70, 256, muted))
    t.append(text("mono", "Frozen files", 13, 70, 278, muted))
    p.append(line("M 220 240 H 262"))
    p.append(box(262, 192, 130, 96))
    t.append(text("serif", "Wave 0", 28, 280, 238, cream))
    t.append(text("mono", "shared kit", 13, 280, 262, muted))

    # four tasks run side by side
    for i, y in enumerate(ys):
        p.append(line("M 392 240 C 436 240 438 %d 480 %d" % (y, y)))
        p.append(box(480, y - 28, 150, 56))
        p.append('<circle cx="500" cy="%d" r="14" fill="url(#lamp)"/><circle cx="500" cy="%d" r="4" fill="#FFE6A8"/>' % (y, y))
        t.append(text("serif", "Task %d" % (i + 2), 26, 522, y + 9, cream))
        p.append(line("M 630 %d H 692" % y, arrow=False))

    # the gate
    p.append('<rect x="692" y="54" width="24" height="%d" rx="12" fill="#E4B04A" fill-opacity="0.10" stroke="%s" stroke-width="2"/>' % (410 - 54 - 18, gold))
    p.append('<circle cx="704" cy="240" r="46" fill="url(#lamp)" opacity="0.8"/>')
    t.append(text("mono", "ownership-check", 15, 704, 36, cream, anchor="middle"))

    # clean commits go to the integration task, then main
    p.append(line("M 716 240 H 800"))
    t.append(text("mono", "clean", 13, 758, 226, muted, anchor="middle"))
    p.append(box(800, 196, 206, 88, accent=True))
    t.append(text("serif", "Integration task", 25, 820, 240, cream))
    t.append(text("mono", "frozen files, proposals", 12, 820, 264, muted))
    p.append(line("M 1006 240 H 1056"))
    p.append('<circle cx="1096" cy="240" r="40" fill="#1A110A" stroke="%s" stroke-width="2"/>' % gold)
    t.append(text("serif", "main", 28, 1096, 250, cream, anchor="middle"))

    # a violation sends that implementer back to its own lane
    p.append(line("M 704 394 V 440 H 692"))
    t.append(text("mono", "violation", 13, 720, 424, muted))
    p.append(box(440, 418, 252, 44))
    t.append(text("serif", "Resume that implementer", 22, 460, 447, cream))
    p.append(line("M 540 418 V 390", dashed=True))

    desc = ("A plan with owned and frozen files feeds a shared kit, wave 0. Four tasks then run in parallel, "
            "and every commit passes ownership-check. Clean commits go to an integration task and on to main. "
            "A violation resumes that implementer.")
    return svg_doc(W, H, "Parallel waves", desc, plate(W, H, p, t))


def install_flow():
    W, H = 1200, 400
    p, t = [], []
    gold, cream, muted = C["gold"], C["cream"], C["muted"]

    sources = (("anthropics/skills", "installed first", False),
               ("any other source", "in manifest order", False),
               ("this repo", "installed last, replaces same names", True))
    ys = (64, 168, 272)
    for (name, note, accent), y in zip(sources, ys):
        p.append(box(48, y, 300, 72, accent=accent))
        t.append(text("mono", name, 16, 68, y + 31, cream))
        t.append(text("sans", note, 14, 68, y + 54, muted))
        p.append(line("M 348 %d C 410 %d 392 %d 452 %d" % (y + 36, y + 36, 204, 204)))

    p.append(box(452, 160, 210, 88, accent=True))
    t.append(text("mono", "npx skills add", 17, 477, 198, gold))
    t.append(text("sans", "one run per source", 14, 477, 224, muted))

    outs = ((".agents/skills/<name>/", "the real copy, read by Codex", 50),
            (".claude/skills/<name>", "a symlink, read by Claude Code", 164),
            ("skills-lock.json", "source and tag for every skill", 278))
    for i, (name, note, y) in enumerate(outs):
        p.append(box(776, y, 376, 72))
        t.append(text("mono", name, 16, 796, y + 31, cream))
        t.append(text("sans", note, 14, 796, y + 54, muted))
    p.append(line("M 662 204 C 720 204 720 86 776 86"))
    p.append(line("M 662 204 C 720 204 720 314 776 314"))
    p.append(line("M 964 122 V 164", dashed=True))
    t.append(text("mono", "symlink", 12, 980, 148, muted))

    desc = ("Sources are installed one after another with npx skills add: other sources first, this repo last so it "
            "replaces skills with the same name. Each skill is written once to .agents/skills, which Codex reads, "
            "with a symlink in .claude/skills for Claude Code, and its source and tag go into skills-lock.json.")
    return svg_doc(W, H, "How installing works", desc, plate(W, H, p, t))


def write(name, content):
    with open(os.path.join(OUT, name), "w") as fh:
        fh.write(content)


write("banner.svg", banner())
write("parallel-waves.svg", parallel_waves())
write("install-flow.svg", install_flow())
for skill in SKILLS:
    write("marker-%s.svg" % skill, marker(skill))
print("ok")
