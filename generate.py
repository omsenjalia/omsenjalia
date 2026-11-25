#!/usr/bin/env python3
"""
Pixel Studio style GitHub profile README generator (no third-party packages).

Reads your public GitHub data, draws animated SVGs into ./assets and rewrites
README.md. Run by the GitHub Action in .github/workflows/update.yml.
"""
import base64
import datetime
import hashlib
import json
import os
import random
import re
import sys
import textwrap
import urllib.request
from html import escape

# ----------------------------------------------------------------------------
# Settings (the workflow file overrides these with environment variables)
# ----------------------------------------------------------------------------
LOGIN = os.environ.get("GH_LOGIN", "omsenjalia")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
LAT = float(os.environ.get("WEATHER_LAT", "23.0225"))
LON = float(os.environ.get("WEATHER_LON", "72.5714"))
TZ_MIN = int(os.environ.get("TZ_OFFSET_MINUTES", "330"))  # India = +5:30
ROOT = os.environ.get("OUT_DIR", os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
NUM_PINNED = 4
NUM_RANDOM = 4
FORCE_WEATHER = os.environ.get("WEATHER_FORCE", "")  # test: clear/rain/snow/storm/fog/cloudy
FORCE_NIGHT = os.environ.get("NIGHT_FORCE", "")      # test: "1"

SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
HEAVY = "'Arial Black','Segoe UI Black',Helvetica,Arial,sans-serif"
MONO = "'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"

BG = "#151b23"
BORDER = "#222c38"
GREEN = "#3fd35a"
WHITE = "#e6edf3"
MUTED = "#8394a7"
LEVELS = ["#1b222b", "#17492c", "#1f7a3b", "#2fb350", "#56e07a"]

LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "HTML": "#e34c26", "CSS": "#563d7c", "Dart": "#00B4AB", "Shell": "#89e051",
    "Java": "#b07219", "C": "#9aa4b1", "C++": "#f34b7d", "C#": "#178600",
    "Go": "#00ADD8", "Rust": "#dea584", "Kotlin": "#A97BFF", "PHP": "#4F5D95",
    "Ruby": "#CC342D", "Swift": "#F05138", "Lua": "#000080", "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384d54", "Nix": "#7e7eff",
}

# ----------------------------------------------------------------------------
# 5x7 pixel font
# ----------------------------------------------------------------------------
FONT_SRC = """
A .###.|#...#|#...#|#####|#...#|#...#|#...#
B ####.|#...#|#...#|####.|#...#|#...#|####.
C .###.|#...#|#....|#....|#....|#...#|.###.
D ###..|#..#.|#...#|#...#|#...#|#..#.|###..
E #####|#....|#....|####.|#....|#....|#####
F #####|#....|#....|####.|#....|#....|#....
G .###.|#...#|#....|#.###|#...#|#...#|.####
H #...#|#...#|#...#|#####|#...#|#...#|#...#
I #####|..#..|..#..|..#..|..#..|..#..|#####
J ..###|...#.|...#.|...#.|...#.|#..#.|.##..
K #...#|#..#.|#.#..|##...|#.#..|#..#.|#...#
L #....|#....|#....|#....|#....|#....|#####
M #...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#
N #...#|##..#|#.#.#|#..##|#...#|#...#|#...#
O .###.|#...#|#...#|#...#|#...#|#...#|.###.
P ####.|#...#|#...#|####.|#....|#....|#....
Q .###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#
R ####.|#...#|#...#|####.|#.#..|#..#.|#...#
S .####|#....|#....|.###.|....#|....#|####.
T #####|..#..|..#..|..#..|..#..|..#..|..#..
U #...#|#...#|#...#|#...#|#...#|#...#|.###.
V #...#|#...#|#...#|#...#|#...#|.#.#.|..#..
W #...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#
X #...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#
Y #...#|#...#|.#.#.|..#..|..#..|..#..|..#..
Z #####|....#|...#.|..#..|.#...|#....|#####
0 .###.|#...#|#..##|#.#.#|##..#|#...#|.###.
1 ..#..|.##..|..#..|..#..|..#..|..#..|.###.
2 .###.|#...#|....#|...#.|..#..|.#...|#####
3 ####.|....#|....#|.###.|....#|....#|####.
4 ...#.|..##.|.#.#.|#..#.|#####|...#.|...#.
5 #####|#....|####.|....#|....#|#...#|.###.
6 ..##.|.#...|#....|####.|#...#|#...#|.###.
7 #####|....#|...#.|..#..|.#...|.#...|.#...
8 .###.|#...#|#...#|.###.|#...#|#...#|.###.
9 .###.|#...#|#...#|.####|....#|...#.|.##..
> #....|.#...|..#..|...#.|..#..|.#...|#....
- .....|.....|.....|#####|.....|.....|.....
. .....|.....|.....|.....|.....|.##..|.##..
, .....|.....|.....|.....|..##.|..#..|.#...
: .....|.##..|.##..|.....|.##..|.##..|.....
/ ....#|....#|...#.|..#..|.#...|#....|#....
* ..#..|#.#.#|.###.|#####|.###.|#.#.#|..#..
+ .....|..#..|..#..|#####|..#..|..#..|.....
"""
FONT = {}
for _line in FONT_SRC.strip().splitlines():
    _k, _rows = _line.split(" ", 1)
    FONT[_k] = _rows.split("|")


def ptext(text, x, y, s, fill, anchor="start"):
    """Draw text with the pixel font as one <path>. s = pixel size."""
    text = str(text).upper()
    width = len(text) * 6 * s - s
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    parts = []
    cx = x
    for ch in text:
        g = FONT.get(ch)
        if g:
            for r, row in enumerate(g):
                c = 0
                while c < 5:
                    if row[c] == "#":
                        c2 = c
                        while c2 < 5 and row[c2] == "#":
                            c2 += 1
                        w = (c2 - c) * s
                        parts.append(f"M{cx + c * s:g} {y + r * s:g}h{w}v{s}h-{w}z")
                        c = c2
                    else:
                        c += 1
        cx += 6 * s
    return f'<path d="{" ".join(parts)}" fill="{fill}" shape-rendering="crispEdges"/>'


def pwidth(text, s):
    return len(str(text)) * 6 * s - s


# ----------------------------------------------------------------------------
# Networking
# ----------------------------------------------------------------------------
def http(url, data=None, headers=None, timeout=25, binary=False):
    h = {"User-Agent": "pixel-studio-profile-readme"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def gh_headers():
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def rest(path):
    return json.loads(http("https://api.github.com" + path, headers=gh_headers()))


def graphql(query, variables):
    h = gh_headers()
    h["Content-Type"] = "application/json"
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = json.loads(http("https://api.github.com/graphql", data=body, headers=h))
    if not out.get("data"):
        raise RuntimeError(str(out.get("errors")))
    return out["data"]


GQL = """
query($login:String!){
  user(login:$login){
    pinnedItems(first:6, types:REPOSITORY){
      nodes{ ... on Repository{ name description stargazerCount url
        primaryLanguage{ name color } } }
    }
    contributionsCollection{
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date contributionCount contributionLevel } }
      }
    }
  }
}
"""
LEVEL_MAP = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
             "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def calendar_from_html(login):
    """No-token fallback: read the public contribution graph."""
    html = http(f"https://github.com/users/{login}/contributions")
    tips = {}
    for m in re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>(.*?)</tool-tip>', html, re.S):
        t = re.sub(r"\s+", " ", m.group(2)).strip()
        n = re.match(r"(\d+) contribution", t)
        tips[m.group(1)] = int(n.group(1)) if n else 0
    days = []
    for m in re.finditer(r"<td\b([^>]*)>", html):
        a = m.group(1)
        d = re.search(r'data-date="([\d-]+)"', a)
        lv = re.search(r'data-level="(\d)"', a)
        i = re.search(r'\bid="([^"]+)"', a)
        if d and lv:
            days.append((d.group(1), tips.get(i.group(1), 0) if i else 0, int(lv.group(1))))
    days.sort()
    return days


def fetch_all():
    if os.environ.get("FIXTURE"):  # test mode: canned API data, live contribution graph
        data = json.load(open(os.environ["FIXTURE"]))
        data["days"] = [tuple(x) for x in data.get("days", [])] or calendar_from_html(LOGIN)
        data["weather"] = fetch_weather()
        return data
    data = {}
    user = rest(f"/users/{LOGIN}")
    data["user"] = user

    repos, page = [], 1
    while True:
        chunk = rest(f"/users/{LOGIN}/repos?per_page=100&type=owner&sort=pushed&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    data["repos"] = repos

    data["pinned"], data["days"] = [], []
    data["commits"] = data["prs"] = None
    if TOKEN:
        try:
            u = graphql(GQL, {"login": LOGIN})["user"]
            for n in u["pinnedItems"]["nodes"]:
                if n:
                    lang = n.get("primaryLanguage") or {}
                    data["pinned"].append({
                        "name": n["name"], "description": n.get("description"),
                        "stars": n["stargazerCount"], "url": n["url"],
                        "language": lang.get("name"), "color": lang.get("color")})
            cc = u["contributionsCollection"]
            data["commits"] = cc["totalCommitContributions"]
            data["prs"] = cc["totalPullRequestContributions"]
            for w in cc["contributionCalendar"]["weeks"]:
                for d in w["contributionDays"]:
                    data["days"].append((d["date"], d["contributionCount"],
                                         LEVEL_MAP.get(d["contributionLevel"], 0)))
        except Exception as e:  # fall through to public fallbacks
            print("GraphQL failed, using public fallbacks:", e, file=sys.stderr)
    if not data["days"]:
        data["days"] = calendar_from_html(LOGIN)
    if data["commits"] is None:
        try:
            data["commits"] = rest(f"/search/commits?q=author:{LOGIN}&per_page=1")["total_count"]
        except Exception:
            data["commits"] = 0
    if data["prs"] is None:
        try:
            data["prs"] = rest(f"/search/issues?q=author:{LOGIN}+type:pr&per_page=1")["total_count"]
        except Exception:
            data["prs"] = 0

    # latest commit messages for the monitor
    lines = []
    try:
        res = rest(f"/search/commits?q=author:{LOGIN}&sort=author-date&order=desc&per_page=12")
        for it in res.get("items", []):
            repo = it["repository"]["name"]
            msg = it["commit"]["message"].splitlines()[0]
            lines.append(f"{repo}: {msg}")
    except Exception as e:
        print("commit search failed:", e, file=sys.stderr)
    data["commit_lines"] = lines

    # weather
    data["weather"] = fetch_weather()
    return data


def fetch_weather():
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(minutes=TZ_MIN)
    night = not (6 <= now.hour < 18)
    cond, temp = "clear", None
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
               "&current=temperature_2m,weather_code,is_day")
        cur = json.loads(http(url, timeout=15))["current"]
        code, night, temp = cur["weather_code"], cur["is_day"] == 0, round(cur["temperature_2m"])
        if code == 0:
            cond = "clear"
        elif code in (1, 2):
            cond = "partly"
        elif code == 3:
            cond = "cloudy"
        elif code in (45, 48):
            cond = "fog"
        elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            cond = "rain"
        elif code in (71, 73, 75, 77, 85, 86):
            cond = "snow"
        elif code in (95, 96, 99):
            cond = "storm"
    except Exception as e:
        print("weather unavailable, using clear sky:", e, file=sys.stderr)
    if FORCE_WEATHER:
        cond = FORCE_WEATHER
    if FORCE_NIGHT:
        night = FORCE_NIGHT == "1"
    return {"cond": cond, "night": night, "temp": temp, "now": now}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def lang_color(name, fallback=None):
    if fallback:
        return fallback
    if name in LANG_COLORS:
        return LANG_COLORS[name]
    h = hashlib.md5((name or "x").encode()).hexdigest()
    return "#" + "".join(f"{int(h[i:i + 2], 16) // 2 + 100:02x}" for i in (0, 2, 4))


def darken(hexcol, f):
    hexcol = hexcol.lstrip("#")
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)))


def svg_open(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title>")


def write(name, content):
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(content)


def fmt(n):
    return f"{n:,}"


def streaks(days):
    counts = [c for _, c, _ in days]
    best = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    cur = 0
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today may simply not have a contribution yet
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, best


def anim(attr, values, dur, begin="0s", extra=""):
    return (f'<animate attributeName="{attr}" values="{values}" dur="{dur}s" '
            f'begin="{begin}" repeatCount="indefinite" {extra}/>')


def anim_t(kind, values, dur, begin="0s", extra=""):
    return (f'<animateTransform attributeName="transform" type="{kind}" values="{values}" '
            f'dur="{dur}s" begin="{begin}" repeatCount="indefinite" {extra}/>')


def sheen(uid, w, h, rx, dur=8, begin="0s"):
    """Glossy light band that sweeps across a card."""
    return (f'<clipPath id="{uid}"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>'
            f'<g clip-path="url(#{uid})"><rect x="-120" y="0" width="70" height="{h}" fill="#fff" opacity="0.07" '
            f'transform="skewX(-20)">{anim("x", f"-140;{w + 140}", dur, begin)}</rect></g>')


# ----------------------------------------------------------------------------
# Room (animated pixel scene)
# ----------------------------------------------------------------------------
SKY = {
    "clear": ("#7cc4ff", "#0f1a36"), "partly": ("#86c3f5", "#101c38"),
    "cloudy": ("#9db3c8", "#1a2338"), "rain": ("#7088a0", "#141d30"),
    "storm": ("#4d5a70", "#0f1626"), "snow": ("#bccbda", "#2a3550"),
    "fog": ("#b0bac4", "#202a3a"),
}


def cloud(x, y, col, dur, begin):
    shape = (f'<rect x="{x}" y="{y + 8}" width="44" height="8" fill="{col}"/>'
             f'<rect x="{x + 8}" y="{y + 2}" width="12" height="8" fill="{col}"/>'
             f'<rect x="{x + 22}" y="{y}" width="14" height="10" fill="{col}"/>')
    return f"<g>{shape}{anim_t('translate', '-70 0;230 0', dur, begin)}</g>"


def window_scene(w):
    cond, night = w["cond"], w["night"]
    sky = SKY.get(cond, SKY["clear"])[1 if night else 0]
    s = [f'<clipPath id="win"><rect x="40" y="56" width="192" height="152"/></clipPath>',
         f'<rect x="24" y="40" width="224" height="184" fill="#10161f"/>',
         f'<g clip-path="url(#win)"><rect x="40" y="56" width="192" height="152" fill="{sky}"/>']
    cl = "#e8eef5" if not night else "#3a4660"
    if night and cond in ("clear", "partly"):
        for i, (sx, sy) in enumerate([(52, 70), (96, 90), (60, 120), (110, 66), (150, 150),
                                      (204, 70), (214, 120), (70, 170), (120, 190), (190, 184)]):
            s.append(f'<rect x="{sx}" y="{sy}" width="4" height="4" fill="#fff">'
                     f'{anim("opacity", "1;0.2;1", 2 + (i % 3), f"-{i * 0.7:.1f}s")}</rect>')
        s.append('<circle cx="188" cy="90" r="15" fill="#f4efd0"/>'
                 f'<circle cx="197" cy="84" r="13" fill="{sky}"/>')
    elif cond in ("clear", "partly"):
        s.append('<circle cx="190" cy="90" r="34" fill="#ffe27a" opacity="0.18">'
                 f'{anim("opacity", "0.1;0.28;0.1", 4)}</circle>'
                 '<g fill="#ffd84a"><rect x="180" y="76" width="20" height="4"/>'
                 '<rect x="172" y="80" width="36" height="20"/><rect x="180" y="100" width="20" height="4"/>'
                 f'{anim("opacity", "1;0.82;1", 3)}</g>')
    if cond in ("partly", "clear"):
        s.append(cloud(40, 72, cl, 38, "-8s"))
        if cond == "partly":
            s.append(cloud(40, 150, cl, 50, "-30s"))
    if cond in ("cloudy", "rain", "storm", "snow"):
        dark = {"cloudy": "#c9d3de", "rain": "#8fa0b3", "storm": "#5d6a80", "snow": "#e4ebf2"}[cond]
        if night:
            dark = "#3a4660"
        for i, (cy, d) in enumerate([(62, 34), (96, 46), (140, 40)]):
            s.append(cloud(40, cy, dark, d, f"-{i * 11}s"))
    if cond in ("rain", "storm"):
        for i in range(18):
            x = 44 + (i * 37) % 184
            d = 0.8 + (i % 4) * 0.12
            s.append(f'<rect x="{x}" y="44" width="2" height="9" fill="#cfe2f7" opacity="0.8">'
                     f'{anim_t("translate", "0 0;-6 180", d, f"-{i * 0.19:.2f}s")}</rect>')
    if cond == "storm":
        s.append('<rect x="40" y="56" width="192" height="152" fill="#fff" opacity="0">'
                 '<animate attributeName="opacity" values="0;0;0;0.75;0;0.5;0;0;0" dur="6s" '
                 'repeatCount="indefinite"/></rect>')
    if cond == "snow":
        for i in range(16):
            x = 44 + (i * 41) % 184
            d = 4 + (i % 5)
            s.append(f'<rect x="{x}" y="44" width="4" height="4" fill="#fff">'
                     f'{anim_t("translate", "0 0;10 180", d, f"-{i * 0.6:.1f}s")}</rect>')
    if cond == "fog":
        for i, y in enumerate((72, 112, 152, 188)):
            s.append(f'<rect x="30" y="{y}" width="200" height="12" fill="#fff" opacity="0.3">'
                     f'{anim_t("translate", "-14 0;14 0;-14 0", 9 + i * 2)}</rect>')
    s.append("</g>")
    # frame bars + sill
    s.append('<rect x="132" y="56" width="8" height="152" fill="#10161f"/>'
             '<rect x="40" y="128" width="192" height="8" fill="#10161f"/>'
             '<rect x="24" y="216" width="224" height="12" fill="#6b4a30"/>'
             '<rect x="24" y="216" width="224" height="3" fill="#8a6342"/>')
    return "".join(s)


def build_room(initials, d, langs, lines):
    w = d["weather"]
    now = w["now"]
    hour_a = ((now.hour % 12) + now.minute / 60) * 30
    min_a = now.minute * 6 + now.second / 10
    sec_a = now.second * 6
    o = [svg_open(880, 448, f"{LOGIN} pixel room")]
    # wall + floor
    o.append('<rect width="880" height="448" fill="#1b2335"/>')
    for x in range(0, 880, 24):
        o.append(f'<rect x="{x}" y="0" width="2" height="352" fill="#141b2a" opacity="0.6"/>')
    o.append('<rect y="352" width="880" height="96" fill="#4a3226"/>'
             '<rect y="352" width="880" height="4" fill="#352217"/>')
    for i, y in enumerate((384, 416)):
        o.append(f'<rect y="{y}" width="880" height="2" fill="#3a271c"/>')
        for x in range((i * 60) % 120, 880, 120):
            o.append(f'<rect x="{x}" y="{y - 32}" width="2" height="32" fill="#3a271c"/>')
    # temperature label
    if w["temp"] is not None:
        o.append(ptext(f'{w["temp"]}C', 32, 14, 3, "#9fb3c8"))
    # frame "OM"
    o.append('<rect x="388" y="36" width="84" height="58" fill="#10161f"/>'
             '<rect x="392" y="40" width="76" height="50" fill="#f1e7d0"/>')
    o.append(ptext(initials, 430, 53, 4, "#1b2335", "middle"))
    # clock
    cx, cy = 768, 62
    o.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="#10161f"/><circle cx="{cx}" cy="{cy}" r="30" fill="#f1e7d0"/>')
    for k in range(12):
        o.append(f'<rect x="{cx - 1}" y="{cy - 27}" width="2" height="4" fill="#2a2118" '
                 f'transform="rotate({k * 30} {cx} {cy})"/>')
    o.append(f'<g stroke="#2a2118" stroke-linecap="square"><line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - 14}" stroke-width="4">'
             f'{anim_t("rotate", f"{hour_a} {cx} {cy};{hour_a + 360} {cx} {cy}", 43200)}</line>'
             f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - 22}" stroke-width="3">'
             f'{anim_t("rotate", f"{min_a} {cx} {cy};{min_a + 360} {cx} {cy}", 3600)}</line></g>'
             f'<line x1="{cx}" y1="{cy + 6}" x2="{cx}" y2="{cy - 25}" stroke="#d0453a" stroke-width="1.5">'
             f'{anim_t("rotate", f"{sec_a} {cx} {cy};{sec_a + 360} {cx} {cy}", 60)}</line>'
             f'<rect x="{cx - 3}" y="{cy - 3}" width="6" height="6" fill="#2a2118"/>')
    # shelf with books (one per language)
    o.append('<rect x="680" y="176" width="176" height="12" fill="#6b4a30"/>'
             '<rect x="680" y="176" width="176" height="3" fill="#8a6342"/>'
             '<rect x="680" y="248" width="176" height="12" fill="#6b4a30"/>'
             '<rect x="680" y="248" width="176" height="3" fill="#8a6342"/>')
    bx = 686
    for i, name in enumerate(langs[:6]):
        bw = (26, 14, 12, 14, 10, 12)[i]
        bh = (48, 36, 40, 36, 40, 32)[i]
        col = lang_color(name)
        o.append(f'<rect x="{bx}" y="{176 - bh}" width="{bw}" height="{bh}" fill="{col}">'
                 f'<title>{escape(name)}</title></rect>'
                 f'<rect x="{bx + 2}" y="{176 - bh + 6}" width="{max(bw - 4, 2)}" height="2" fill="#000" opacity="0.25"/>')
        bx += bw + 4
    # plant
    o.append('<g>' + anim_t("rotate", "-2 168 312;2 168 312;-2 168 312", 5) +
             '<rect x="164" y="250" width="8" height="64" fill="#2f9e4f"/>'
             '<rect x="140" y="268" width="24" height="8" fill="#2f9e4f"/>'
             '<rect x="172" y="262" width="28" height="8" fill="#38b85c"/>'
             '<rect x="146" y="288" width="18" height="8" fill="#38b85c"/>'
             '<rect x="172" y="282" width="22" height="8" fill="#2f9e4f"/></g>'
             '<rect x="140" y="312" width="56" height="48" fill="#a85a38"/>'
             '<rect x="136" y="312" width="64" height="8" fill="#c0714c"/>')
    # cat (sleeping)
    o.append('<rect x="680" y="344" width="28" height="8" fill="#c98240"/>'
             '<rect x="704" y="336" width="64" height="24" fill="#e8a15a">'
             + anim("height", "24;26;24", 3) + anim("y", "336;334;336", 3) + '</rect>'
             '<rect x="716" y="336" width="4" height="24" fill="#c98240"/>'
             '<rect x="732" y="336" width="4" height="24" fill="#c98240"/>'
             '<rect x="752" y="324" width="26" height="22" fill="#e8a15a"/>'
             '<rect x="752" y="318" width="6" height="8" fill="#e8a15a"/>'
             '<rect x="772" y="318" width="6" height="8" fill="#e8a15a"/>'
             '<rect x="760" y="334" width="10" height="2" fill="#6b3d1c"/>')
    # chair + desk
    o.append('<rect x="496" y="236" width="14" height="64" fill="#262d37"/>'
             '<rect x="440" y="296" width="72" height="12" fill="#2f3743"/>'
             '<rect x="468" y="308" width="8" height="38" fill="#262d37"/>'
             '<rect x="448" y="344" width="56" height="8" fill="#262d37"/>'
             '<rect x="264" y="264" width="368" height="24" fill="#6b4a30"/>'
             '<rect x="264" y="264" width="368" height="4" fill="#8a6342"/>'
             '<rect x="280" y="288" width="12" height="64" fill="#553822"/>'
             '<rect x="604" y="288" width="12" height="64" fill="#553822"/>')
    # night dimming (before window/monitor so those stay bright)
    if w["night"]:
        o.append('<rect width="880" height="448" fill="#050a1c" opacity="0.4"/>')
    o.append(window_scene(w))
    # lamp
    o.append('<polygon points="284,156 324,156 350,264 258,264" fill="#ffe08a" opacity="0.07">'
             + anim("opacity", "0.05;0.09;0.05", 5) + '</polygon>'
             '<rect x="292" y="156" width="8" height="106" fill="#2c3440"/>'
             '<rect x="280" y="136" width="48" height="20" fill="#f2c94c"/>'
             '<rect x="280" y="136" width="48" height="4" fill="#ffe28a"/>'
             '<rect x="282" y="258" width="32" height="6" fill="#2c3440"/>')
    # monitor
    o.append('<rect x="328" y="112" width="240" height="144" fill="#343c4a"/>'
             '<rect x="336" y="120" width="224" height="128" fill="#0f1a2e"/>'
             '<rect x="428" y="256" width="40" height="8" fill="#2c3440"/>'
             '<rect x="400" y="256" width="96" height="4" fill="#2c3440"/>')
    prompt = "$ git log --oneline"
    msgs = [m if len(m) <= 34 else m[:33] + "…" for m in lines[:10]] or ["(no public commits yet)"]
    base = [prompt] + msgs
    while len(base) < 9:
        base += msgs
    n = len(base)
    rows = []
    for rep in range(2):
        for i, t in enumerate(base):
            y = 134 + (rep * n + i) * 16
            col = WHITE if t == prompt else "#58d36b"
            rows.append(f'<text x="342" y="{y}" font-family="{MONO}" font-size="10.5" fill="{col}">{escape(t)}</text>')
    vals = ";".join(f"0 -{i * 16}" for i in range(n))
    o.append('<clipPath id="scr"><rect x="336" y="120" width="224" height="128"/></clipPath>'
             '<g clip-path="url(#scr)"><g>' + "".join(rows) +
             f'<animateTransform attributeName="transform" type="translate" values="{vals}" '
             f'calcMode="discrete" dur="{n * 2.2:.1f}s" repeatCount="indefinite"/></g></g>'
             '<rect x="336" y="120" width="224" height="128" fill="#58d36b" opacity="0.04">'
             + anim("opacity", "0.02;0.07;0.02", 3) + '</rect>')
    # mug + steam
    o.append('<rect x="588" y="236" width="24" height="28" fill="#e9e4da"/>'
             '<rect x="612" y="242" width="8" height="14" fill="none" stroke="#e9e4da" stroke-width="4"/>')
    for i, sx in enumerate((594, 602)):
        o.append(f'<rect x="{sx}" y="226" width="3" height="8" fill="#cfd8e3" opacity="0">'
                 f'{anim_t("translate", "0 0;0 -16", 2.4, f"-{i * 1.2}s")}'
                 f'{anim("opacity", "0;0.7;0", 2.4, f"-{i * 1.2}s")}</rect>')
    # Zzz
    for i, (zs, zx, zy) in enumerate(((3, 792, 276), (2, 812, 300))):
        o.append(f'<g opacity="0">{ptext("Z", zx, zy, zs, "#9aa8b8")}'
                 f'{anim_t("translate", "0 0;6 -22", 3.2, f"-{i * 1.6}s")}'
                 f'{anim("opacity", "0;0.9;0", 3.2, f"-{i * 1.6}s")}</g>')
    o.append("</svg>")
    return "".join(o)


# ----------------------------------------------------------------------------
# About card, stats strip, headers
# ----------------------------------------------------------------------------
_AV = {}


def fetch_avatar(user):
    """Return avatar PNG/JPG bytes (56px) or None."""
    if "v" in _AV:
        return _AV["v"]
    _AV["v"] = _fetch_avatar(user)
    return _AV["v"]


def _fetch_avatar(user):
    try:
        if os.environ.get("AVATAR_FILE"):  # test mode
            return open(os.environ["AVATAR_FILE"], "rb").read()
        u = user["avatar_url"] + ("&" if "?" in user["avatar_url"] else "?") + "s=56"
        return http(u, binary=True)
    except Exception as e:
        print("avatar unavailable, drawing identicon:", e, file=sys.stderr)
        return None


def avatar_dots(raw, cx, cy, size=112, grid=28):
    """Dot-matrix version of the avatar (needs Pillow; returns None if missing)."""
    try:
        import io
        from PIL import Image
    except Exception:
        return None
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((grid, grid), Image.LANCZOS)
    except Exception:
        return None
    px = im.load()
    lum = [[(0.2126 * px[x, y][0] + 0.7152 * px[x, y][1] + 0.0722 * px[x, y][2]) / 255
            for x in range(grid)] for y in range(grid)]
    corners = (lum[0][0] + lum[0][-1] + lum[-1][0] + lum[-1][-1]) / 4
    if corners > 0.5:  # bright background: flip so the subject is what lights up
        lum = [[1 - v for v in row] for row in lum]
    flat = sorted(v for row in lum for v in row)
    lo, hi = flat[int(len(flat) * 0.05)], flat[int(len(flat) * 0.97)]
    pitch, R = size / grid, size / 2
    out = []
    for y in range(grid):
        for x in range(grid):
            dx, dy = (x + 0.5) * pitch - R, (y + 0.5) * pitch - R
            if dx * dx + dy * dy > R * R:
                continue
            v = min(1.0, max(0.0, (lum[y][x] - lo) / max(hi - lo, 1e-6)))
            if v < 0.15:
                continue
            sz = 1.4 + v * (pitch - 1.6)
            op = 0.35 + 0.65 * v
            h = (x * 73856093 ^ y * 19349663) % 100
            tw = ""
            if h < 14:
                tw = anim("opacity", f"{op:.2f};{op * 0.25:.2f};{op:.2f}", 2 + h % 4, f"-{h * 0.3:.1f}s")
            out.append(f'<rect x="{cx - R + (x + 0.5) * pitch - sz / 2:.1f}" y="{cy - R + (y + 0.5) * pitch - sz / 2:.1f}" '
                       f'width="{sz:.1f}" height="{sz:.1f}" fill="#dbe7ff" opacity="{op:.2f}">{tw}</rect>')
    return "".join(out)


def name_cells(text, x, y, s, base="#e6edf3", hi="#6cb6ff", dur=4.0):
    """Big pixel-font name where a light sweeps through the letters."""
    text = text.upper()
    total = max(len(text) * 6 * s - s, 1)
    out, cx = [], x
    for ch in text:
        g = FONT.get(ch)
        if g:
            for r, row in enumerate(g):
                for c in range(5):
                    if row[c] == "#":
                        px = cx + c * s
                        begin = (px - x) / total * 1.6
                        out.append(f'<rect x="{px}" y="{y + r * s}" width="{s}" height="{s}" fill="{base}">'
                                   f'<animate attributeName="fill" values="{base};{hi};{base};{base}" '
                                   f'keyTimes="0;0.1;0.25;1" dur="{dur}s" begin="{begin:.2f}s" repeatCount="indefinite"/></rect>')
        cx += 6 * s
    return f'<g shape-rendering="crispEdges">{"".join(out)}</g>'


def identicon_rects(seed, col, x0, y0, cell, grid=9):
    h = hashlib.sha256(seed.encode()).digest()
    half = (grid + 1) // 2
    out, k = [], 0
    for r in range(grid):
        for c in range(half):
            on = (h[(r * half + c) % 32] >> ((r + c) % 8)) & 1
            if on:
                for cc in {c, grid - 1 - c}:
                    k += 1
                    delay = (k * 0.37) % 4
                    twinkle = ""
                    if k % 5 == 0:
                        twinkle = anim("opacity", "1;0.3;1", 2.5 + (k % 3), f"-{delay:.1f}s")
                    out.append(f'<rect x="{x0 + cc * cell}" y="{y0 + r * cell}" width="{cell}" height="{cell}" fill="{col}">{twinkle}</rect>')
    return "".join(out)


def build_about(user):
    name = user.get("name") or user["login"]
    bio = user.get("bio") or "Building things on GitHub."
    lines = textwrap.wrap(bio, 46)[:2]
    loc = user.get("location") or ""
    meta = " · ".join(x for x in [loc, f'{user["followers"]} followers',
                                   f'{user["public_repos"]} repositories',
                                   (f'joined {user["created_at"][:4]}' if user.get("created_at") else '')] if x)
    cx, cy = 774, 115
    o = [svg_open(880, 230, "About"),
         '<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">'
         '<path d="M24 0H0V24" fill="none" stroke="#8fb3ff" stroke-opacity="0.05"/></pattern>'
         f'<radialGradient id="glow"><stop offset="0" stop-color="#3b82f6" stop-opacity="0.35"/>'
         '<stop offset="1" stop-color="#3b82f6" stop-opacity="0"/></radialGradient>'
         f'<clipPath id="av"><circle cx="{cx}" cy="{cy}" r="56"/></clipPath></defs>',
         f'<rect width="880" height="230" rx="18" fill="{BG}"/>',
         '<rect width="880" height="230" rx="18" fill="url(#grid)"/>',
         ptext("> ABOUT", 36, 28, 3, GREEN),
         f'<rect x="{36 + pwidth("> ABOUT", 3) + 10}" y="28" width="12" height="21" fill="{GREEN}">'
         + anim("opacity", "1;1;0;0", 1.2) + "</rect>"]
    # name (pixel letters with a sweeping light)
    if all(ch in FONT or ch == " " for ch in name.upper()):
        n = len(name)
        ns = 8 if n <= 6 else 6 if n <= 10 else 4
        o.append(name_cells(name, 36, 64, ns))
        name_bottom = 64 + 7 * ns
    else:
        o.append(f'<text x="36" y="108" font-family="{HEAVY}" font-size="32" font-weight="900" fill="#fff">{escape(name)}</text>')
        name_bottom = 112
    y0 = max(name_bottom + 30, 136)
    for i, t in enumerate(lines):
        o.append(f'<text x="36" y="{y0 + i * 24}" font-family="{SANS}" font-size="16" fill="#c4ced9">{escape(t)}</text>')
    o.append(f'<text x="36" y="{y0 + 24 * (len(lines) - 1) + 32}" font-family="{MONO}" font-size="12" fill="{MUTED}">{escape(meta)}</text>')

    # avatar: glow, dot-matrix disc, scan line
    o.append(f'<circle cx="{cx}" cy="{cy}" r="100" fill="url(#glow)">' + anim("opacity", "0.7;1;0.7", 4) + "</circle>")
    raw = fetch_avatar(user)
    dots = avatar_dots(raw, cx, cy) if raw else None
    if dots:
        o.append(dots)
    else:
        o.append(f'<g clip-path="url(#av)"><rect x="{cx - 56}" y="{cy - 56}" width="112" height="112" fill="#05080f"/>'
                 + identicon_rects(user["login"], "#dbe7ff", cx - 54, cy - 54, 12) + "</g>")
    o.append(f'<g clip-path="url(#av)"><rect x="{cx - 56}" y="{cy - 56}" width="112" height="5" fill="#6cb6ff" opacity="0.28">'
             + anim("y", f"{cy - 62};{cy + 58}", 4.5) + "</rect></g>")
    # rings: static, rotating arcs, orbiting squares
    o.append(f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="#1d2a44" stroke-width="1"/>'
             f'<circle cx="{cx}" cy="{cy}" r="68" fill="none" stroke="#1d2a44" stroke-width="1"/>')
    r1, r2 = 84, 76
    c1, c2 = 2 * 3.14159 * r1, 2 * 3.14159 * r2
    o.append(f'<g>{anim_t("rotate", f"0 {cx} {cy};360 {cx} {cy}", 26)}'
             f'<circle cx="{cx}" cy="{cy}" r="{r1}" fill="none" stroke="#4a8cff" stroke-width="2" stroke-dasharray="95 {c1 - 95:.0f}"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r1}" fill="none" stroke="#4a8cff" stroke-width="2" stroke-opacity="0.5" '
             f'stroke-dasharray="40 {c1 - 40:.0f}" stroke-dashoffset="-{c1 / 2:.0f}"/></g>')
    o.append(f'<g>{anim_t("rotate", f"360 {cx} {cy};0 {cx} {cy}", 38)}'
             f'<circle cx="{cx}" cy="{cy}" r="{r2}" fill="none" stroke="#8a6cff" stroke-width="2" stroke-dasharray="70 {c2 - 70:.0f}"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{r2}" fill="none" stroke="#8a6cff" stroke-width="2" stroke-opacity="0.45" '
             f'stroke-dasharray="30 {c2 - 30:.0f}" stroke-dashoffset="-{c2 * 0.6:.0f}"/></g>')
    o.append(f'<g>{anim_t("rotate", f"0 {cx} {cy};360 {cx} {cy}", 14)}<rect x="{cx + 92 - 3}" y="{cy - 3}" width="6" height="6" fill="#6cb6ff"/></g>'
             f'<g>{anim_t("rotate", f"180 {cx} {cy};-180 {cx} {cy}", 22)}<rect x="{cx + 68 - 2}" y="{cy - 2}" width="4" height="4" fill="#b49cff"/></g>')
    o.append(sheen("sh-about", 880, 230, 18, 9, "-3s") + "</svg>")
    return "".join(o)


def build_stats(commits, prs, active, best):
    items = [(fmt(commits), "COMMITS"), (fmt(prs), "PULL REQS"), (fmt(active), "ACTIVE DAYS"), (f"{best}D", "BEST STREAK")]
    xs = (24, 242, 456, 668)
    o = [svg_open(880, 84, "Stats"),
         f'<clipPath id="sc"><rect width="880" height="84" rx="14"/></clipPath>',
         f'<rect width="880" height="84" rx="14" fill="{BG}"/>']
    for (val, label), x in zip(items, xs):
        o.append(ptext(val, x, 10, 6, WHITE))
        o.append(f'<text x="{x}" y="70" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{label}</text>')
    o.append('<g clip-path="url(#sc)"><rect x="-80" y="0" width="60" height="84" fill="#fff" opacity="0.04" '
             'transform="skewX(-20)">' + anim("x", "-100;960", 7) + "</rect></g></svg>")
    return "".join(o)


def build_header(title):
    w = pwidth(title, 4)
    return "".join([
        svg_open(880, 44, title), ptext(title, 0, 8, 4, GREEN),
        f'<line x1="{w + 16}" y1="22" x2="880" y2="22" stroke="{MUTED}" stroke-width="2" '
        'stroke-dasharray="6 6" opacity="0.7">' + anim("stroke-dashoffset", "0;-24", 1.6) + "</line></svg>"])


# ----------------------------------------------------------------------------
# Project card
# ----------------------------------------------------------------------------
def build_card(i, repo):
    name = repo["name"]
    desc = repo.get("description") or "A project in progress."
    lines = textwrap.wrap(desc, 34)[:4]
    if len(textwrap.wrap(desc, 34)) > 4:
        lines[-1] = lines[-1][:31] + "..."
    col = lang_color(repo.get("language"), repo.get("color")) if repo.get("language") else "#8394a7"
    uid = f"c{i}"
    o = [svg_open(430, 205, name),
         f'<clipPath id="{uid}"><rect width="430" height="205" rx="14"/></clipPath>',
         f'<rect x="0.5" y="0.5" width="429" height="204" rx="14" fill="{BG}" stroke="{BORDER}"/>',
         f'<rect x="14" y="34" width="100" height="100" rx="8" fill="{darken(col, 0.28)}"/>',
         identicon_rects(name, col, 19, 39, 10),
         f'<text x="132" y="50" font-family="{MONO}" font-size="16" font-weight="700" fill="#fff">{escape(name[:24])}</text>']
    for k, t in enumerate(lines):
        o.append(f'<text x="132" y="{76 + k * 19}" font-family="{SANS}" font-size="13" fill="#9aa8b8">{escape(t)}</text>')
    stars = str(repo.get("stars", 0))
    o.append(ptext("*", 14, 166, 3, GREEN) + ptext(stars, 14 + 24, 166, 3, GREEN))
    if repo.get("language"):
        lname = repo["language"]
        tw = len(lname) * 7
        o.append(f'<rect x="{414 - tw - 22}" y="166" width="14" height="14" rx="3" fill="{col}"/>'
                 f'<text x="414" y="177" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">{escape(lname)}</text>')
    o.append(f'<g clip-path="url(#{uid})"><rect x="-80" y="0" width="50" height="205" fill="#fff" opacity="0.04" '
             f'transform="skewX(-20)">{anim("x", "-100;520", 8 + i % 3, f"-{i * 1.7:.1f}s")}</rect></g></svg>')
    return "".join(o)


# ----------------------------------------------------------------------------
# Activity heatmap
# ----------------------------------------------------------------------------
def fmt_k(n):
    return f"{n / 1000:.1f}K" if n >= 1000 else str(n)


def tint(hexcol, mix):
    """Mix a colour toward white (mix 0..1)."""
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(int(v + (255 - v) * mix) for v in (r, g, b))


def build_activity(days, total, cur, best):
    weeks = {}
    for d, c, lv in days:
        dt = datetime.date.fromisoformat(d)
        start = dt - datetime.timedelta(days=(dt.weekday() + 1) % 7)
        weeks.setdefault(start, {})[(dt.weekday() + 1) % 7] = (c, lv)
    cols = [weeks[k] for k in sorted(weeks)][-53:]
    counts = [c for col in cols for (c, _) in col.values()]
    mx = max(counts) if counts and max(counts) > 0 else 1
    active = sum(1 for c in counts if c > 0)
    last30 = sum(c for _, c, _ in days[-30:])
    H = 650
    o = [svg_open(880, H, "Activity"),
         '<defs><radialGradient id="cg" cx="0.55" cy="0.35" r="0.6"><stop offset="0" stop-color="#3fd35a" stop-opacity="0.13"/>'
         '<stop offset="1" stop-color="#3fd35a" stop-opacity="0"/></radialGradient></defs>',
         f'<rect width="880" height="{H}" rx="18" fill="{BG}"/>',
         f'<rect width="880" height="{H}" rx="18" fill="url(#cg)"/>',
         ptext("> ACTIVITY", 36, 28, 3, GREEN),
         ptext(fmt_k(total), 36, 70, 6, WHITE),
         f'<text x="36" y="130" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">CONTRIBUTIONS IN</text>'
         f'<text x="36" y="146" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">THE LAST YEAR</text>',
         f'<text x="36" y="186" font-family="{MONO}" font-size="13" font-weight="700" fill="#7ee787">{active} ACTIVE DAYS</text>',
         f'<text x="36" y="208" font-family="{MONO}" font-size="13" font-weight="700" fill="#7ee787">BUSIEST DAY: {mx}</text>']

    # ---- isometric city ----
    a, b, ox, oy, f = 9.5, 4.75, 336, 104, 0.86
    cubes = sorted((wi + r, wi, r, c, lv) for wi, col in enumerate(cols) for r, (c, lv) in col.items())
    for _, wi, r, c, lv in cubes:
        cx, cy = ox + (wi - r) * a, oy + (wi + r) * b
        L0, R0 = (cx - a * f, cy), (cx + a * f, cy)
        B0 = (cx, cy + b * f)

        def pts(*p):
            return " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
        if c == 0:
            o.append(f'<polygon points="{pts((cx, cy - b * f - 1), (cx + a * f, cy - 1), (cx, cy + b * f - 1), (cx - a * f, cy - 1))}" fill="#1b222b"/>')
            continue
        h = 4 + (c / mx) ** 0.5 * 66
        top = tint(LEVELS[lv], 0.18) if lv > 1 else darken(LEVELS[lv], 1.5)
        left, right = darken(LEVELS[lv], 0.78), darken(LEVELS[lv], 0.52)
        T = (cx, cy - b * f - h)
        Rr = (cx + a * f, cy - h)
        Bb = (cx, cy + b * f - h)
        Ll = (cx - a * f, cy - h)
        begin = f"{wi * 0.1:.1f}s"
        o.append(
            f'<g>{anim_t("translate", "0 0;0 -4;0 0;0 0", 6, begin, "keyTimes=\"0;0.1;0.22;1\"")}'
            f'<polygon points="{pts(Ll, Bb, B0, L0)}" fill="{left}"/>'
            f'<polygon points="{pts(Bb, Rr, R0, B0)}" fill="{right}"/>'
            f'<polygon points="{pts(T, Rr, Bb, Ll)}" fill="{top}">'
            f'<animate attributeName="fill" values="{top};#c8ffd6;{top};{top}" keyTimes="0;0.1;0.22;1" dur="6s" begin="{begin}" repeatCount="indefinite"/></polygon></g>')

    # ---- flat heatmap (with legend) ----
    o.append(ptext("> CONTRIBUTION ACTIVITY", 36, 396, 3, GREEN))
    o.append(f'<text x="36" y="436" font-family="{MONO}" font-size="12" fill="{MUTED}">{fmt(total)} contributions in the last year</text>')
    lx = 731
    o.append(f'<text x="{lx - 8}" y="418" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">LESS</text>')
    for i, col in enumerate(LEVELS):
        o.append(f'<rect x="{lx + i * 16}" y="408" width="12" height="12" rx="3" fill="{col}" stroke="#2a3441" stroke-width="0.8"/>')
    o.append(f'<text x="{lx + 84}" y="418" font-family="{MONO}" font-size="11" fill="{MUTED}">MORE</text>')
    for ci, col in enumerate(cols):
        for r in range(7):
            if r not in col:
                continue
            c, lv = col[r]
            wave = anim("opacity", "1;0.5;1", 3.4, f"-{(ci * 0.09 + r * 0.03):.2f}s") if lv > 0 else ""
            o.append(f'<rect x="{36 + ci * 15}" y="{450 + r * 15}" width="12" height="12" rx="3" fill="{LEVELS[lv]}">{wave}</rect>')

    # ---- stats row ----
    stats = [("CURRENT STREAK", f"{cur} DAY{'S' if cur != 1 else ''}"), ("BEST STREAK", f"{best} DAYS"),
             ("LAST 30 DAYS", fmt(last30))]
    for k, (lab, val) in enumerate(stats):
        x = 36 + k * 280
        o.append(f'<text x="{x}" y="588" font-family="{MONO}" font-size="12" letter-spacing="1" fill="{MUTED}">{lab}</text>')
        o.append(ptext(val, x, 598, 4, WHITE))
    o.append(sheen("sh-act", 880, H, 18, 10, "-5s"))
    o.append("</svg>")
    return "".join(o)


# ----------------------------------------------------------------------------
# Commit metro (randomised language lines)
# ----------------------------------------------------------------------------
ABBR = {"TypeScript": "TS", "JavaScript": "JS", "Python": "PY", "HTML": "H5", "CSS": "C3", "Dart": "DA",
        "Shell": "SH", "Java": "JV", "C": "C", "C++": "C+", "C#": "C#", "Go": "GO", "Rust": "RS",
        "Kotlin": "KT", "Dockerfile": "DK", "PHP": "PH", "Ruby": "RB", "Swift": "SW", "Lua": "LU"}
LEFT_SLOTS = [(110, "up"), (170, "up"), (375, "down"), (440, "down")]
RIGHT_SLOTS = [(150, "up"), (228, "up"), (312, "down"), (388, "down")]
# which side of the line labels go on (keeps them clear of the diagonals near the hub)
LABEL_POLICY = {110: "alt", 170: "down", 375: "alt", 440: "down", 150: "alt", 228: "down", 312: "up", 388: "alt"}


def visible(col):
    h = col.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tint(col, 0.28) if 0.299 * r + 0.587 * g + 0.114 * b < 95 else col


def build_metro(user, own):
    login = user["login"]
    by = {}
    for r in own:
        if r["language"]:
            by.setdefault(r["language"], []).append(r["name"])
    langs = sorted(by, key=lambda k: (-len(by[k]), random.random()))[:8]
    random.shuffle(langs)
    n = len(langs)
    W, H, hx, hy = 880, 490, 440, 271
    n_left = (n + 1) // 2
    left = random.sample(LEFT_SLOTS, min(n_left, 4))
    right = random.sample(RIGHT_SLOTS, min(n - n_left, 4))
    o = [svg_open(W, H, "Commit metro"),
         '<defs><pattern id="mg" width="24" height="24" patternUnits="userSpaceOnUse">'
         '<path d="M24 0H0V24" fill="none" stroke="#8fb3ff" stroke-opacity="0.05"/></pattern>'
         f'<clipPath id="hub"><circle cx="{hx}" cy="{hy}" r="25"/></clipPath></defs>',
         f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/><rect width="{W}" height="{H}" rx="18" fill="url(#mg)"/>',
         ptext("> COMMIT METRO", 36, 28, 3, GREEN),
         f'<text x="36" y="76" font-family="{SANS}" font-size="22" font-weight="700" fill="#c4ced9">'
         'Every line is a language, every stop a project</text>']
    paths, flows, stops, labels, pills, trains = [], [], [], [], [], []
    plan = [(langs[i], slot, "L") for i, slot in enumerate(left)] + \
           [(langs[n_left + i], slot, "R") for i, slot in enumerate(right)]
    for lang, (y, kind), side in plan:
        col = visible(lang_color(lang))
        label = lang.upper()[:11]
        pw = 8 + 18 + 7 + len(label) * 7.1 + 12
        ey = hy - 17 if kind == "up" else hy + 17
        if side == "L":
            ex = hx - 17
            xs, xb = 24 + pw - 6, ex - abs(ey - y)
            d = f"M{xs:.0f} {y} H{xb:.0f} L{ex} {ey}"
            lo, hi = xs + 24, xb - 34
            px = 24
        else:
            ex = hx + 17
            xb, xe = ex + abs(ey - y), 856 - pw + 6
            d = f"M{ex} {ey} L{xb:.0f} {y} H{xe:.0f}"
            lo, hi = xb + 44, xe - 22
            px = 856 - pw
        paths.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>')
        flows.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity="0.28" stroke-width="3" stroke-linecap="round" '
                     f'stroke-dasharray="10 140">{anim("stroke-dashoffset", "0;-150", 3 + random.random() * 2, f"-{random.random() * 3:.1f}s")}</path>')
        names = random.sample(by[lang], min(len(by[lang]), 3))
        k = min(len(names), max(1, int((hi - lo) / 58) + 1)) if hi > lo else 1
        pol = LABEL_POLICY.get(y, "alt")
        above = pol == "up" or (pol == "alt" and random.random() < 0.5)
        for i in range(k):
            x = (lo + hi) / 2 if k == 1 else lo + (hi - lo) * i / (k - 1) + random.uniform(-6, 6)
            x = min(max(x, lo - 4), hi + 4)
            nm = names[i] if len(names[i]) <= 13 else names[i][:12] + "…"
            ping = f"-{random.random() * 3:.1f}s"
            stops.append(f'<circle cx="{x:.0f}" cy="{y}" r="9" fill="none" stroke="{col}" stroke-width="2" opacity="0.6">'
                         f'{anim("r", "9;24", 3.2, ping)}{anim("opacity", "0.6;0", 3.2, ping)}</circle>'
                         f'<circle cx="{x:.0f}" cy="{y}" r="9" fill="#0b0f14" stroke="{col}" stroke-width="3"/>')
            stagger = 12 if (pol != "alt" and i % 2) else 0
            ly = y - 18 - stagger if above else y + 28 + stagger
            labels.append(f'<text x="{x:.0f}" y="{ly}" text-anchor="middle" font-family="{SANS}" font-size="11" fill="#cdd9e5" opacity="0.85">{escape(nm)}</text>')
            if pol == "alt":
                above = not above
        pills.append(f'<rect x="{px:.0f}" y="{y - 13}" width="{pw:.0f}" height="26" rx="13" fill="{col}"/>'
                     f'<rect x="{px + 8:.0f}" y="{y - 9}" width="18" height="18" rx="4" fill="#fff"/>'
                     f'<text x="{px + 17:.0f}" y="{y + 3.5}" text-anchor="middle" font-family="{MONO}" font-size="9" font-weight="700" fill="{darken(col, 0.8)}">{ABBR.get(lang, lang[:2].upper())}</text>'
                     f'<text x="{px + 33:.0f}" y="{y + 4}" font-family="{MONO}" font-size="11" font-weight="700" letter-spacing="0.5" fill="#fff">{escape(label)}</text>')
        dur, off = 9 + random.random() * 7, random.random() * 9
        trains.append(f'<g opacity="0"><rect x="-15" y="-7" width="30" height="14" rx="7" fill="#eaf2ff" stroke="{col}" stroke-width="2.5"/>'
                      f'<animateMotion path="{d}" dur="{dur:.1f}s" begin="-{off:.1f}s" repeatCount="indefinite" rotate="auto"/>'
                      f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.94;1" dur="{dur:.1f}s" begin="-{off:.1f}s" repeatCount="indefinite"/></g>')
    o += paths + flows + stops + labels + pills + trains
    # hub
    raw = fetch_avatar(user)
    dots = avatar_dots(raw, hx, hy, 48, 24) if raw else None
    o.append(f'<circle cx="{hx}" cy="{hy}" r="46" fill="#0b0f14" fill-opacity="0.6"/>'
             f'<circle cx="{hx}" cy="{hy}" r="50" fill="none" stroke="{GREEN}" stroke-opacity="0.35" stroke-width="2"/>'
             f'<circle cx="{hx}" cy="{hy}" r="44" fill="none" stroke="{GREEN}" stroke-width="2" stroke-dasharray="5 11">'
             f'{anim_t("rotate", f"0 {hx} {hy};360 {hx} {hy}", 30)}</circle>'
             f'<circle cx="{hx}" cy="{hy}" r="26" fill="#05080f" stroke="#fff" stroke-width="2"/>')
    if dots:
        o.append(f'<g clip-path="url(#hub)">{dots}</g>')
    else:
        o.append(f'<g clip-path="url(#hub)">{identicon_rects(login, "#dbe7ff", hx - 24, hy - 24, 6, 8)}</g>')
    tag = "@" + login
    tw = len(tag) * 7.4 + 26
    o.append(f'<rect x="{hx - tw / 2:.0f}" y="{hy + 40}" width="{tw:.0f}" height="24" rx="12" fill="#0b0f14" stroke="#2a3441"/>'
             f'<text x="{hx}" y="{hy + 56}" text-anchor="middle" font-family="{MONO}" font-size="12" font-weight="700" fill="#fff">{escape(tag)}</text>')
    o.append(sheen("sh-metro", W, H, 18, 11, "-7s") + "</svg>")
    return "".join(o)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    d = fetch_all()
    user, repos = d["user"], d["repos"]
    own = [r for r in repos if not r["fork"] and not r["archived"] and r["name"].lower() != LOGIN.lower()]

    def to_card(r):
        return {"name": r["name"], "description": r["description"], "stars": r["stargazers_count"],
                "url": r["html_url"], "language": r["language"], "color": None}

    pinned = d["pinned"][:NUM_PINNED]
    have = {p["name"] for p in pinned}
    for r in own:  # top up with the most recently pushed repos
        if len(pinned) >= NUM_PINNED:
            break
        if r["name"] not in have:
            pinned.append(to_card(r))
            have.add(r["name"])
    pool = [to_card(r) for r in own if r["name"] not in have]
    random.shuffle(pool)
    picks = pool[:NUM_RANDOM]

    # language counts for the bookshelf
    counts = {}
    for r in own:
        if r["language"]:
            counts[r["language"]] = counts.get(r["language"], 0) + 1
    langs = [k for k, _ in sorted(counts.items(), key=lambda kv: -kv[1])]

    stars = sum(r["stargazers_count"] for r in repos if not r["fork"])
    days = d["days"]
    cur, best = streaks(days)
    total = sum(c for _, c, _ in days)

    name = user.get("name") or user["login"]
    parts = name.split()
    initials = (parts[0][0] + parts[1][0] if len(parts) > 1 else name[:2]).upper()

    write("room.svg", build_room(initials, d, langs, d["commit_lines"]))
    write("about.svg", build_about(user))
    write("stats.svg", build_stats(d["commits"], d["prs"], sum(1 for _, c, _ in days if c > 0), best))
    write("header-pinned.svg", build_header("> PINNED PROJECTS"))
    write("header-random.svg", build_header("> RANDOM PICKS"))
    if os.environ.get("SEED"):
        random.seed(os.environ["SEED"])
    write("activity.svg", build_activity(days, total, cur, best))
    write("metro.svg", build_metro(user, own))
    for i, r in enumerate(pinned):
        write(f"pinned-{i + 1}.svg", build_card(i, r))
    for i, r in enumerate(picks):
        write(f"random-{i + 1}.svg", build_card(10 + i, r))

    place = user.get("location") or "my city"
    def cards(prefix, items):
        return "\n".join(
            f'<a href="{escape(r["url"])}"><img src="assets/{prefix}-{i + 1}.svg" width="49%" alt="{escape(r["name"])}"></a>'
            for i, r in enumerate(items))

    readme = f"""<div align="center">

<img src="assets/room.svg" width="100%" alt="Animated pixel room">

<sub>The window shows the weather in {escape(place)} right now. The monitor scrolls my latest commits; the shelf holds a book for each language I write.</sub>

<a href="https://github.com/{LOGIN}"><img src="assets/about.svg" width="100%" alt="About"></a>

<img src="assets/stats.svg" width="100%" alt="Stats">

<img src="assets/header-pinned.svg" width="100%" alt="Pinned projects">

{cards("pinned", pinned)}

<img src="assets/header-random.svg" width="100%" alt="Random picks">

{cards("random", picks)}

<img src="assets/metro.svg" width="100%" alt="Commit metro">

<img src="assets/activity.svg" width="100%" alt="Activity">

<sub>Auto-generated from my GitHub data every 6 hours.</sub>

</div>
"""
    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"ok: {len(pinned)} pinned, {len(picks)} random, streak {cur}/{best}, commits {d['commits']}, prs {d['prs']}")


if __name__ == "__main__":
    main()
