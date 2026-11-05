"""Self-contained animated SVG generators for the profile README.

Everything is drawn here (no third-party image services), in a dark and a
light variant, so the page never depends on anything but this repo.
"""
import math
import random
import textwrap
from datetime import date
from html import escape

SANS = "ui-sans-serif, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

THEMES = {
    "dark": dict(bg1="#060a13", bg2="#0e1830", panel="#0f1729", border="#22304d",
                 text="#e8eefc", muted="#8fa1c4", empty="#18223a", blob=0.55, grid=0.05),
    "light": dict(bg1="#f6f9ff", bg2="#e4ecff", panel="#ffffff", border="#d3ddf2",
                  text="#0f1a33", muted="#566786", empty="#e4eaf6", blob=0.42, grid=0.07),
}

ACCENTS = {
    "aurora": {"dark": ("#22d3ee", "#8b5cf6", "#f472b6"), "light": ("#0891b2", "#7c3aed", "#db2777")},
    "ocean": {"dark": ("#38bdf8", "#6366f1", "#2dd4bf"), "light": ("#0284c7", "#4f46e5", "#0d9488")},
    "sunset": {"dark": ("#fb923c", "#f43f5e", "#a855f7"), "light": ("#ea580c", "#e11d48", "#9333ea")},
    "forest": {"dark": ("#34d399", "#22c55e", "#a3e635"), "light": ("#059669", "#16a34a", "#65a30d")},
}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
    "CSS": "#563d7c", "SCSS": "#c6538c", "Java": "#b07219", "C": "#555555", "C++": "#f34b7d",
    "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584", "PHP": "#4F5D95", "Ruby": "#701516",
    "Kotlin": "#A97BFF", "Swift": "#F05138", "Dart": "#00B4AB", "Shell": "#89e051",
    "Dockerfile": "#384d54", "Vue": "#41b883", "Svelte": "#ff3e00", "Lua": "#000080",
    "R": "#198CE7", "Jupyter Notebook": "#DA5B0B", "Solidity": "#AA6746", "HCL": "#844FBA",
    "PowerShell": "#012456", "Elixir": "#6e4a7e", "Scala": "#c22d40", "Haskell": "#5e5086",
    "Perl": "#0298c3", "MATLAB": "#e16737", "Objective-C": "#438eff", "Astro": "#ff5a03",
    "Makefile": "#427819", "Batchfile": "#C1F12E", "Nix": "#7e7eff", "Zig": "#ec915c",
}


def esc(s):
    return escape(str(s), quote=True)


def lang_color(name):
    if name in LANG_COLORS:
        return LANG_COLORS[name]
    h = sum(ord(c) * (i + 3) for i, c in enumerate(name)) % 360
    return f"hsl({h},65%,55%)"


def _svg(w, h, defs, body, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
        f"{'<style>' + style + '</style>' if style else ''}<defs>{defs}</defs>{body}</svg>"
    )


def _grad(gid, cols, x2=1, y2=0, extra=""):
    n = len(cols) - 1
    stops = "".join(f'<stop offset="{i / n:.2f}" stop-color="{c}"/>' for i, c in enumerate(cols))
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}" {extra}>{stops}</linearGradient>'


def _tl(points, total):
    """Keyframe helper: [(seconds, value)] -> (values, keyTimes) strings."""
    pts = sorted(points, key=lambda p: p[0])
    if pts[0][0] > 0:
        pts.insert(0, (0.0, pts[0][1]))
    if pts[-1][0] < total:
        pts.append((total, pts[-1][1]))
    keys, last = [], -1.0
    for t, _ in pts:
        k = max(t / total, last + 1e-4)
        keys.append(k)
        last = k
    keys[0], keys[-1] = 0.0, 1.0
    for i in range(len(keys) - 2, 0, -1):
        if keys[i] >= keys[i + 1]:
            keys[i] = keys[i + 1] - 1e-4
    return ";".join(f"{v:.1f}" for _, v in pts), ";".join(f"{k:.5f}" for k in keys)


def _enter(begin, dy=14, dur=0.9):
    """Fade + slide-up entrance; put inside a <g opacity="0">."""
    return (
        f'<animate attributeName="opacity" from="0" to="1" begin="{begin}s" dur="{dur}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="0 {dy}" to="0 0" '
        f'begin="{begin}s" dur="{dur}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/>'
    )


def _wave(w, base, amp, k, phase, step=16):
    pts = []
    x = 0
    while x <= w + step:
        pts.append(f"L{x} {base + amp * math.sin(k * x + phase):.1f}")
        x += step
    return f"M0 {base} " + " ".join(pts) + f" L{w + step} 400 L0 400 Z"


def _waves(w, layers, grad_id):
    """layers: [(base, amp, k, seconds, opacity)] - flowing wave paths."""
    out = ""
    for base, amp, k, secs, op in layers:
        frames = [_wave(w, base, amp, k, 2 * math.pi * j / 6) for j in range(7)]
        out += (
            f'<path d="{frames[0]}" fill="url(#{grad_id})" opacity="{op}">'
            f'<animate attributeName="d" values="{";".join(frames)}" dur="{secs}s" repeatCount="indefinite"/></path>'
        )
    return out


def _counter(x, y, value, fs, fill, begin, anchor="start", steps=16, family=SANS, weight=800):
    out = ""
    for i in range(steps):
        v = value if i == steps - 1 else round(value * ((i + 1) / steps) ** 2.2)
        b = f"{begin + i * 0.09:.2f}s"
        if i == steps - 1:
            setter = f'<set attributeName="opacity" to="1" begin="{b}" fill="freeze"/>'
        else:
            setter = f'<set attributeName="opacity" to="1" begin="{b}" dur="0.09s"/>'
        out += (
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{fs}" '
            f'font-weight="{weight}" fill="{fill}" opacity="0">{v:,}{setter}</text>'
        )
    return out


def _typewriter(lines, tx, top, fs, color, cursor_color):
    charw = fs * 0.6
    per = 4.6
    total = per * len(lines)
    defs, body = "", ""
    cur_pts = []
    for i, line in enumerate(lines):
        w = len(line) * charw
        s = i * per
        te, he, de = s + 1.7, s + 4.0, s + 4.5
        wv, kt = _tl([(0, 0), (s, 0), (te, w), (he, w), (de, 0), (total, 0)], total)
        defs += (
            f'<clipPath id="tw{i}"><rect x="{tx}" y="{top}" height="{fs * 2}" width="0">'
            f'<animate attributeName="width" values="{wv}" keyTimes="{kt}" dur="{total}s" repeatCount="indefinite"/>'
            f"</rect></clipPath>"
        )
        body += (
            f'<g clip-path="url(#tw{i})"><text x="{tx}" y="{top + fs * 1.4:.0f}" font-family="{MONO}" '
            f'font-size="{fs}" fill="{color}" textLength="{w:.1f}" lengthAdjust="spacing">{esc(line)}</text></g>'
        )
        cur_pts += [(s, tx), (te, tx + w + 2), (he, tx + w + 2), (de, tx)]
    xv, xk = _tl(cur_pts + [(total, tx)], total)
    body += (
        f'<rect y="{top + 3}" width="2.5" height="{fs * 1.5:.0f}" rx="1" fill="{cursor_color}">'
        f'<animate attributeName="x" values="{xv}" keyTimes="{xk}" dur="{total}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.5;.5001;.99;1" dur="1s" repeatCount="indefinite"/></rect>'
    )
    return defs, body


# =============================================================== HERO
def hero(t, accent, name, taglines, meta, avatar, initials):
    th = THEMES[t]
    a1, a2, a3 = ACCENTS[accent][t]
    W, H = 880, 300
    rnd = random.Random(11)

    fs_name = int(max(30, min(56, 600 / (0.58 * max(len(name), 1)))))
    lines = [l[:50] for l in taglines if l][:4] or ["Building things on the internet"]

    tw_defs, tw_body = _typewriter(lines, 284, 188, 18, th["text"], a1)

    defs = (
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>'
        f'<clipPath id="av"><circle r="62"/></clipPath>'
        + _grad("bgG", [th["bg1"], th["bg2"]], 0, 1)
        + _grad("ng", [a1, a2, a3], 1, 0, 'spreadMethod="reflect"').replace(
            "</linearGradient>",
            '<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="2 0" '
            'dur="7s" repeatCount="indefinite"/></linearGradient>')
        + _grad("waveG", [a1, a2, a3])
        + _grad("ringG", [a1, a3], 1, 1)
        + f'<radialGradient id="glow"><stop offset="0" stop-color="{a2}" stop-opacity=".6"/>'
          f'<stop offset="1" stop-color="{a2}" stop-opacity="0"/></radialGradient>'
        + '<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="38"/></filter>'
        + f'<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">'
          f'<path d="M32 0H0V32" fill="none" stroke="{th["text"]}" stroke-opacity="{th["grid"]}"/></pattern>'
        + tw_defs
    )

    def blob(cx, cy, rx, ry, col, dx, dy, dur):
        return (
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{col}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;{dx} {dy};0 0" '
            f'dur="{dur}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".4 0 .6 1;.4 0 .6 1"/></ellipse>'
        )

    pc = "#ffffff" if t == "dark" else a2
    particles = ""
    for _ in range(38):
        x, y, r = rnd.uniform(10, 870), rnd.uniform(10, 250), rnd.uniform(0.7, 2.3)
        d1, d2 = rnd.uniform(2.5, 6), rnd.uniform(6, 11)
        particles += (
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{pc}" opacity=".1">'
            f'<animate attributeName="opacity" values=".08;.85;.08" dur="{d1:.1f}s" begin="-{rnd.uniform(0, 5):.1f}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;{rnd.uniform(-10, 10):.0f} -14;0 0" '
            f'dur="{d2:.1f}s" repeatCount="indefinite"/></circle>'
        )

    avatar_inner = (
        f'<image href="{avatar}" x="-62" y="-62" width="124" height="124" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>'
        if avatar else
        f'<circle r="62" fill="url(#ng)"/><text y="16" text-anchor="middle" font-family="{SANS}" font-size="46" '
        f'font-weight="800" fill="#ffffff">{esc(initials)}</text>'
    )
    avatar_g = (
        '<g transform="translate(142,150)"><g>'
        '<animateTransform attributeName="transform" type="scale" from=".5" to="1" dur="1s" fill="freeze" '
        'calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/>'
        '<circle r="90" fill="url(#glow)"><animate attributeName="r" values="80;96;80" dur="3.2s" repeatCount="indefinite"/></circle>'
        '<circle r="77" fill="none" stroke="url(#ringG)" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="130 50 40 60">'
        '<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="9s" repeatCount="indefinite"/></circle>'
        f'<circle r="86" fill="none" stroke="{a2}" stroke-opacity=".55" stroke-width="1.5" stroke-dasharray="2 9" stroke-linecap="round">'
        '<animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="18s" repeatCount="indefinite"/></circle>'
        f'<circle r="66" fill="{th["panel"]}"/>{avatar_inner}</g></g>'
    )

    waves = _waves(W, [(266, 9, 0.011, 9, 0.30), (276, 8, 0.016, 7, 0.28), (286, 6, 0.021, 11, 0.45)], "waveG")

    name_g = (
        f'<g opacity="0">{_enter(0.4)}'
        f'<text x="284" y="96" font-family="{SANS}" font-size="12" font-weight="600" letter-spacing="4" fill="{th["muted"]}">HELLO WORLD, I’M</text>'
        f'<text x="282" y="{96 + fs_name:.0f}" font-family="{SANS}" font-size="{fs_name}" font-weight="800" fill="url(#ng)">{esc(name)}</text>'
        f'<rect x="284" y="{110 + fs_name:.0f}" height="4" rx="2" fill="{a1}" width="0">'
        f'<animate attributeName="width" from="0" to="120" begin="1s" dur=".9s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect></g>'
    )
    type_g = (
        f'<g opacity="0">{_enter(0.9)}'
        f'<text x="262" y="{188 + 25}" font-family="{MONO}" font-size="18" font-weight="700" fill="{a1}">›</text>{tw_body}</g>'
    )
    meta_txt = "   •   ".join(m for m in meta if m)
    meta_g = (
        f'<g opacity="0">{_enter(1.3)}<text x="284" y="250" font-family="{SANS}" font-size="13" fill="{th["muted"]}">{esc(meta_txt)}</text></g>'
        if meta_txt else ""
    )
    live = (
        f'<g opacity="0">{_enter(1.6, 0)}<circle cx="722" cy="28" r="3.5" fill="{a3}">'
        '<animate attributeName="r" values="3;5.5;3" dur="1.6s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></circle>'
        f'<text x="856" y="32" text-anchor="end" font-family="{SANS}" font-size="11" letter-spacing="1" fill="{th["muted"]}">LIVE FROM GITHUB</text></g>'
    )

    body = (
        f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="url(#bgG)"/>'
        f'<g filter="url(#blur)" opacity="{th["blob"]}">'
        + blob(170, 90, 210, 110, a1, 90, 40, 14) + blob(640, 60, 240, 100, a2, -100, 50, 17)
        + blob(780, 250, 220, 110, a3, -70, -40, 19) + "</g>"
        f'<rect width="{W}" height="{H}" fill="url(#grid)"/>'
        + particles + waves + avatar_g + name_g + type_g + meta_g + live + "</g>"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="{th["border"]}"/>'
    )
    return _svg(W, H, defs, body)


# =============================================================== STATS
def _star(r1, r2, n=5):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{r * math.cos(a):.1f},{r * math.sin(a):.1f}")
    return " ".join(pts)


def _icon(kind, color):
    s = f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "repos":
        return f'<rect x="-8" y="-10" width="16" height="20" rx="3" {s}/><line x1="-4" y1="-4" x2="4" y2="-4" {s}/><line x1="-4" y1="1" x2="2" y2="1" {s}/>'
    if kind == "stars":
        return f'<polygon points="{_star(11, 4.6)}" {s}/>'
    if kind == "followers":
        return f'<circle cy="-4" r="4.6" {s}/><path d="M-9 10 Q0 -2 9 10" {s}/>'
    cells = "".join(
        f'<rect x="{-10 + c * 8}" y="{-10 + r * 8}" width="6" height="6" rx="1.5" fill="{color}" opacity="{.35 + .65 * ((r * 3 + c) % 3) / 2:.2f}"/>'
        for r in range(3) for c in range(3))
    return cells


def stats(t, accent, s, langs):
    th = THEMES[t]
    a1, a2, a3 = ACCENTS[accent][t]
    W, H = 880, 244
    tiles = [("REPOSITORIES", s["repos"], "repos", a1), ("STARS EARNED", s["stars"], "stars", a2),
             ("FOLLOWERS", s["followers"], "followers", a3),
             ("CONTRIBUTIONS" if s.get("contrib") is not None else "FOLLOWING",
              s["contrib"] if s.get("contrib") is not None else s.get("following", 0), "contrib", a1)]
    tw, gp = 205, 20
    defs = _grad("ng", [a1, a2, a3], 1, 0) + f'<clipPath id="barclip"><rect x="24" y="0" width="0" height="40" rx="7">' \
        '<animate attributeName="width" from="0" to="832" begin="0.9s" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .2 1"/></rect></clipPath>' \
        '<clipPath id="barshape"><rect x="24" y="52" width="832" height="14" rx="7"/></clipPath>'
    body = ""
    for i, (label, val, icon, col) in enumerate(tiles):
        x = i * (tw + gp)
        b = 0.15 * i
        body += (
            f'<g transform="translate({x:.0f},0)"><g opacity="0">{_enter(b)}'
            f'<rect x=".5" y=".5" width="{tw - 1}" height="108" rx="16" fill="{th["panel"]}" stroke="{th["border"]}"/>'
            f'<text x="22" y="34" font-family="{SANS}" font-size="11" font-weight="600" letter-spacing="1.5" fill="{th["muted"]}">{label}</text>'
            f'<g transform="translate({tw - 36},29)">{_icon(icon, col)}</g>'
            + _counter(22, 80, val, 38, col, 0.5 + b)
            + f'<rect x="22" y="94" height="3" rx="1.5" fill="{col}" width="0"><animate attributeName="width" from="0" to="40" begin="{0.9 + b}s" dur=".7s" fill="freeze"/></rect></g></g>'
        )
    total = sum(b for _, b in langs) or 1
    bar, legend, x = "", "", 24
    for i, (name, size) in enumerate(langs[:6]):
        w = 832 * size / total
        bar += f'<rect x="{x:.1f}" y="52" width="{w + 1:.1f}" height="14" fill="{lang_color(name)}"/>'
        x += w
    slot = 832 / max(1, min(6, len(langs)))
    for i, (name, size) in enumerate(langs[:6]):
        lx = 24 + i * slot
        nm = name if len(name) <= 12 else name[:11] + "…"
        legend += (
            f'<g opacity="0">{_enter(1.4 + i * 0.12, 8, .6)}<circle cx="{lx + 5:.0f}" cy="92" r="5" fill="{lang_color(name)}"/>'
            f'<text x="{lx + 16:.0f}" y="96" font-family="{SANS}" font-size="12" fill="{th["text"]}">{esc(nm)}'
            f'<tspan fill="{th["muted"]}"> {size / total * 100:.0f}%</tspan></text></g>'
        )
    lang_panel = (
        f'<g transform="translate(0,130)"><g opacity="0">{_enter(0.7)}'
        f'<rect x=".5" y=".5" width="{W - 1}" height="112" rx="16" fill="{th["panel"]}" stroke="{th["border"]}"/>'
        f'<text x="24" y="32" font-family="{SANS}" font-size="11" font-weight="600" letter-spacing="1.5" fill="{th["muted"]}">TOP LANGUAGES</text>'
        + (f'<g clip-path="url(#barshape)"><g clip-path="url(#barclip)" transform="translate(0,52)"><g transform="translate(0,-52)">{bar}</g></g></g>' if langs else "")
        + legend + "</g></g>"
    )
    return _svg(W, H, defs, body + lang_panel)


# =============================================================== HEATMAP
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def heatmap(t, accent, weeks, total, cur, best):
    """weeks: list of 7-slot lists holding (iso_date, count) or None."""
    th = THEMES[t]
    a1, a2, a3 = ACCENTS[accent][t]
    n = len(weeks)
    pitch, cell = 16, 13
    W, H = 880, 236
    ox, oy = max(8, (W - n * pitch) // 2), 88
    mx = max([d[1] for wk in weeks for d in wk if d] + [1])

    def level(c):
        if not c:
            return 0
        r = c / mx
        return 1 if r < .25 else 2 if r < .5 else 3 if r < .75 else 4

    style = (
        ".c{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.8,.2,1) both,wave 7s ease-in-out infinite}"
        "@keyframes pop{from{opacity:0;transform:scale(.2)}to{opacity:1;transform:scale(1)}}"
        "@keyframes wave{0%,32%,100%{opacity:1;transform:scale(1)}14%{opacity:.4;transform:scale(.72)}}"
        "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.2}}"
        f".l0{{fill:{th['empty']}}}.l1{{fill:{a1};fill-opacity:.4}}.l2{{fill:{a1}}}.l3{{fill:{a2}}}.l4{{fill:{a3}}}"
    )
    cells, last = "", None
    for wi, wk in enumerate(weeks):
        for di, d in enumerate(wk):
            if not d:
                continue
            d1 = wi * 0.028 + di * 0.012
            d2 = 2.4 + wi * 0.085 + di * 0.02
            cells += (f'<rect class="c l{level(d[1])}" x="{ox + wi * pitch}" y="{oy + di * pitch}" width="{cell}" height="{cell}" '
                      f'rx="3.5" style="animation-delay:{d1:.2f}s,{d2:.2f}s"/>')
            last = (wi, di)

    months, prev, last_x = "", None, -99
    for wi, wk in enumerate(weeks):
        first = next((d for d in wk if d), None)
        if not first:
            continue
        m = int(first[0][5:7])
        if m != prev:
            x = ox + wi * pitch
            if x - last_x >= 34 and not (wi == 0 and n > 3 and int(weeks[2][0][0][5:7] if weeks[2][0] else m) != m):
                months += f'<text x="{x}" y="{oy - 12}" font-family="{SANS}" font-size="11" fill="{th["muted"]}">{MONTHS[m - 1]}</text>'
                last_x = x
            prev = m

    ring = ""
    if last:
        ring = (f'<rect x="{ox + last[0] * pitch - 2}" y="{oy + last[1] * pitch - 2}" width="{cell + 4}" height="{cell + 4}" rx="5" '
                f'fill="none" stroke="{a1}" stroke-width="2" opacity="0" style="animation:pulse 1.6s ease-in-out infinite;animation-delay:2.4s"/>')

    sq0 = W - 24 - 30 - 6 - 5 * 17
    legend = (
        f'<text x="{sq0 - 6}" y="{H - 14}" text-anchor="end" font-family="{SANS}" font-size="11" fill="{th["muted"]}">Less</text>'
        + "".join(f'<rect x="{sq0 + i * 17}" y="{H - 25}" width="12" height="12" rx="3.5" class="l{i}"/>' for i in range(5))
        + f'<text x="{W - 24}" y="{H - 14}" text-anchor="end" font-family="{SANS}" font-size="11" fill="{th["muted"]}">More</text>'
    )
    body = (
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="{th["panel"]}" stroke="{th["border"]}"/>'
        f'<text x="24" y="40" font-family="{SANS}" font-size="15" font-weight="700" fill="{th["text"]}">Contribution activity</text>'
        f'<text x="{W - 24}" y="40" text-anchor="end" font-family="{SANS}" font-size="12" fill="{th["muted"]}">'
        f'<tspan fill="{a1}" font-weight="700">{total:,}</tspan> in the last year   •   current streak '
        f'<tspan fill="{a2}" font-weight="700">{cur}d</tspan>   •   best <tspan fill="{a3}" font-weight="700">{best}d</tspan></text>'
        + months + cells + ring + legend
    )
    return _svg(W, H, "", body, style)


# =============================================================== STACK MARQUEE
def stack(t, accent, rows):
    th = THEMES[t]
    rows = [r for r in rows if r]
    W = 880
    H = 20 + len(rows) * 48
    gap = 12
    defs = (
        '<linearGradient id="fade" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#000"/>'
        '<stop offset=".08" stop-color="#fff"/><stop offset=".92" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>'
    )
    body = '<g mask="url(#m)">'
    for ri, items in enumerate(rows):
        widths = [26 + len(lbl) * 7.8 + 18 for lbl, _ in items]
        seq, seqw = [], []
        while sum(w + gap for w in seqw) < W + 200 or not seq:
            for it, w in zip(items, widths):
                seq.append(it)
                seqw.append(w)
            if sum(w + gap for w in seqw) >= W + 200:
                break
        setw = sum(w + gap for w in seqw)
        y = 14 + ri * 48
        chips, x = "", 0
        for (lbl, col), w in zip(seq, seqw):
            chips += (
                f'<g transform="translate({x:.0f},{y})"><rect width="{w:.0f}" height="34" rx="17" fill="{th["panel"]}" stroke="{th["border"]}"/>'
                f'<circle cx="18" cy="17" r="5" fill="{col}"/><text x="31" y="22" font-family="{SANS}" font-size="13" font-weight="600" fill="{th["text"]}">{esc(lbl)}</text></g>'
            )
            x += w + gap
        a, b = (0, -setw) if ri % 2 == 0 else (-setw, 0)
        secs = setw / 38
        body += (
            f'<g><animateTransform attributeName="transform" type="translate" from="{a:.0f} 0" to="{b:.0f} 0" dur="{secs:.1f}s" repeatCount="indefinite"/>'
            f'<g>{chips}</g><g transform="translate({setw:.0f},0)">{chips}</g><g transform="translate({-setw:.0f},0)">{chips}</g></g>'
        )
    body += "</g>"
    return _svg(W, H, defs, body)


# =============================================================== PROJECT CARD
def card(t, accent, repo, idx):
    th = THEMES[t]
    a1, a2, a3 = ACCENTS[accent][t]
    W, H = 430, 132
    desc = (repo.get("description") or "No description yet.").strip()
    lines = textwrap.wrap(desc, 58)[:2] or [""]
    if len(textwrap.wrap(desc, 58)) > 2:
        lines[1] = lines[1][:55].rstrip() + "…"
    name = repo["name"] if len(repo["name"]) <= 30 else repo["name"][:29] + "…"
    lang = repo.get("language") or ""
    b = idx * 0.14
    defs = (
        _grad("bd", [a1, a2, a3, a1], 1, 1, 'gradientUnits="objectBoundingBox"').replace(
            "</linearGradient>",
            '<animateTransform attributeName="gradientTransform" type="rotate" from="0 .5 .5" to="360 .5 .5" dur="8s" repeatCount="indefinite"/></linearGradient>')
        + _grad("tg", [a1, a2], 1, 0)
        + f'<radialGradient id="orb"><stop offset="0" stop-color="{a2}" stop-opacity=".35"/><stop offset="1" stop-color="{a2}" stop-opacity="0"/></radialGradient>'
        + f'<clipPath id="cc"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
    )
    body = (
        f'<g opacity="0">{_enter(b, 12, .7)}<g clip-path="url(#cc)"><rect width="{W}" height="{H}" fill="{th["panel"]}"/>'
        '<circle cx="380" cy="30" r="90" fill="url(#orb)"><animateTransform attributeName="transform" type="translate" values="0 0;-60 40;0 0" dur="9s" repeatCount="indefinite"/></circle></g>'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="15" fill="none" stroke="url(#bd)" stroke-width="1.6" stroke-opacity=".85"/>'
        f'<text x="22" y="36" font-family="{SANS}" font-size="17" font-weight="800" fill="url(#tg)">{esc(name)}</text>'
        + "".join(f'<text x="22" y="{62 + i * 18}" font-family="{SANS}" font-size="12.5" fill="{th["muted"]}">{esc(l)}</text>' for i, l in enumerate(lines))
        + (f'<circle cx="28" cy="108" r="5" fill="{lang_color(lang)}"/><text x="40" y="112" font-family="{SANS}" font-size="12" fill="{th["text"]}">{esc(lang)}</text>' if lang else "")
        + f'<g transform="translate(168,107)"><polygon points="{_star(7, 3)}" fill="none" stroke="{a1}" stroke-width="1.6" stroke-linejoin="round"/></g>'
        f'<text x="182" y="112" font-family="{SANS}" font-size="12" fill="{th["text"]}">{repo.get("stargazers_count", 0):,}</text>'
        f'<g transform="translate(232,107)" fill="none" stroke="{a3}" stroke-width="1.6" stroke-linecap="round"><circle cx="-3" cy="-5" r="2.2"/><circle cx="3" cy="-5" r="2.2"/><circle cy="5" r="2.2"/><path d="M-3 -3 V0 Q-3 2 0 2.8 Q3 2 3 0 V-3 M0 2.8 V3"/></g>'
        f'<text x="244" y="112" font-family="{SANS}" font-size="12" fill="{th["text"]}">{repo.get("forks_count", 0):,}</text></g>'
    )
    return _svg(W, H, defs, body)


# =============================================================== FOOTER
def footer(t, accent, text="Thanks for stopping by"):
    th = THEMES[t]
    a1, a2, a3 = ACCENTS[accent][t]
    W, H = 880, 130
    defs = _grad("wg", [a1, a2, a3]) + _grad("tg", [a1, a2, a3], 1, 0, 'spreadMethod="reflect"').replace(
        "</linearGradient>",
        '<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="2 0" dur="7s" repeatCount="indefinite"/></linearGradient>'
    ) + f'<clipPath id="fc"><rect width="{W}" height="{H}" rx="22"/></clipPath>'
    waves = _waves(W, [(70, 10, 0.010, 10, .28), (82, 9, 0.015, 8, .3), (96, 7, 0.02, 12, .5)], "wg")
    body = (
        f'<g clip-path="url(#fc)">{waves}'
        f'<g opacity="0">{_enter(0.2, 10)}<text x="{W / 2}" y="56" text-anchor="middle" font-family="{SANS}" font-size="22" font-weight="800" fill="url(#tg)">{esc(text)}</text></g></g>'
    )
    return _svg(W, H, defs, body)
