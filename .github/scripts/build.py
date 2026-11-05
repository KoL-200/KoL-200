#!/usr/bin/env python3
"""Builds the profile README and its animated SVG assets from live GitHub data.

Zero configuration: the username is the repo owner. Optional tweaks live in
.github/profile.config.json. Standard library only.
"""
import base64
import json
import os
import random
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svgkit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github" / "profile.config.json"
TEMPLATE = ROOT / ".github" / "README.template.md"
ASSETS = Path(os.environ.get("ASSETS_OUT", ROOT / "assets"))
OUT = Path(os.environ.get("README_OUT", ROOT / "README.md"))
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SAMPLE = os.environ.get("SAMPLE") == "1"
USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "octocat"

DEFAULT_CONFIG = {
    "theme": "auto",          # "auto" follows the viewer's GitHub theme; or "dark" / "light"
    "accent": "aurora",       # aurora | ocean | sunset | forest
    "name": "",               # override display name
    "taglines": [],           # override the typing lines (max 4)
    "pinned_repos": [],       # repo names to feature (default: top starred)
    "show_heatmap": True,
    "linkedin": "",           # full URL, shown in the links row
}

TOPIC_NAMES = {
    "nextjs": "Next.js", "next-js": "Next.js", "nodejs": "Node.js", "node": "Node.js", "react": "React",
    "reactjs": "React", "react-native": "React Native", "vue": "Vue", "vuejs": "Vue", "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL", "mongodb": "MongoDB", "mysql": "MySQL", "graphql": "GraphQL", "tailwindcss": "Tailwind",
    "tailwind": "Tailwind", "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS", "fastapi": "FastAPI",
    "django": "Django", "flask": "Flask", "express": "Express", "firebase": "Firebase", "supabase": "Supabase",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "redis": "Redis", "flutter": "Flutter", "laravel": "Laravel",
    "typescript": "TypeScript", "javascript": "JavaScript", "python": "Python", "machine-learning": "Machine Learning",
    "api": "API", "cli": "CLI", "ai": "AI", "ml": "ML", "devops": "DevOps", "open-source": "Open Source",
}
TOPIC_COLORS = ["#22d3ee", "#8b5cf6", "#f472b6", "#fb923c", "#34d399", "#facc15"]


# ------------------------------------------------------------------ data
def http_json(url, data=None, headers=None):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "profile-readme-builder"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api(path):
    return http_json(path if path.startswith("http") else f"https://api.github.com{path}")


def graphql(query, variables):
    if not TOKEN:
        return None
    body = json.dumps({"query": query, "variables": variables}).encode()
    return http_json("https://api.github.com/graphql", data=body, headers={"Content-Type": "application/json"})


def fetch_avatar(url):
    try:
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(f"{url}{sep}s=240", headers={"User-Agent": "profile-readme-builder"})
        with urllib.request.urlopen(req, timeout=30) as r:
            mime = r.headers.get_content_type() or "image/png"
            return f"data:{mime};base64,{base64.b64encode(r.read()).decode()}"
    except Exception:
        return None


def contributions():
    q = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
         "totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}")
    try:
        res = graphql(q, {"login": USER})
        cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception:
        return None
    weeks = []
    for w in cal["weeks"]:
        slots = [None] * 7
        for d in w["contributionDays"]:
            slots[d["weekday"]] = (d["date"], d["contributionCount"])
        weeks.append(slots)
    return weeks, cal["totalContributions"]


def streaks(weeks):
    counts = [d[1] for w in weeks for d in w if d]
    best = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, best


def sample_data():
    rnd = random.Random(5)
    end = date.today()
    start = end - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks, d = [], start
    while d <= end:
        slot = [None] * 7
        for i in range(7):
            if d <= end:
                busy = rnd.random() < 0.62
                slot[i] = (d.isoformat(), rnd.choice([1, 2, 3, 5, 8, 12]) if busy else 0)
            d += timedelta(days=1)
        weeks.append(slot)
    repos = [
        dict(name="awesome-project", description="A fast, friendly tool that does one thing really well.", language="TypeScript", stargazers_count=128, forks_count=14, html_url="#", topics=["react", "nodejs", "docker"]),
        dict(name="data-playground", description="Notebooks and experiments exploring datasets, models and visualizations.", language="Python", stargazers_count=76, forks_count=9, html_url="#", topics=["machine-learning", "api"]),
        dict(name="dotfiles", description="My terminal, editor and system setup.", language="Shell", stargazers_count=41, forks_count=3, html_url="#", topics=["linux"]),
        dict(name="tiny-api", description="Minimal REST API starter with auth and tests.", language="Go", stargazers_count=22, forks_count=2, html_url="#", topics=["api", "docker"]),
    ]
    return dict(
        name="Your Name", login="yourname", bio="Your profile builds itself", location="Anywhere", company="", blog="",
        twitter="", email="", avatar=None, followers=128, following=64, public_repos=24, repos=repos, stars=267,
        langs=[("TypeScript", 52000), ("Python", 41000), ("Go", 18000), ("Shell", 9000), ("CSS", 6000), ("HTML", 4000)],
        topics=Counter({"react": 3, "nodejs": 2, "docker": 2, "api": 2, "machine-learning": 1, "linux": 1}),
        weeks=weeks, total=sum(d[1] for w in weeks for d in w if d), recent=repos[:3],
    )


def collect():
    if SAMPLE:
        return sample_data()
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while page <= 3:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&type=owner&sort=pushed")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    repos = [r for r in repos if not r["fork"] and r["name"].lower() != USER.lower()]

    langs = Counter()
    for r in repos[:40]:
        try:
            for k, v in api(r["languages_url"]).items():
                langs[k] += v
        except urllib.error.URLError:
            pass
    topics = Counter(t for r in repos for t in r.get("topics", []))
    cal = contributions()
    weeks, total = cal if cal else (None, None)
    return dict(
        name=user.get("name") or USER, login=USER, bio=(user.get("bio") or "").strip(), location=user.get("location") or "",
        company=(user.get("company") or "").lstrip("@"), blog=(user.get("blog") or "").strip(),
        twitter=user.get("twitter_username") or "", email=user.get("email") or "",
        avatar=fetch_avatar(user["avatar_url"]) if user.get("avatar_url") else None,
        followers=user["followers"], following=user["following"], public_repos=user["public_repos"], repos=repos,
        stars=sum(r["stargazers_count"] for r in repos), langs=langs.most_common(), topics=topics,
        weeks=weeks, total=total, recent=repos[:5],
    )


# ------------------------------------------------------------------ rendering helpers
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            print("profile.config.json is not valid JSON - using defaults")
    if cfg["accent"] not in svgkit.ACCENTS:
        cfg["accent"] = "aurora"
    if cfg["theme"] not in ("auto", "dark", "light"):
        cfg["theme"] = "auto"
    return cfg


def pic(name, alt, mode, width="100%", href=None):
    if mode == "auto":
        inner = (
            f'<picture><source media="(prefers-color-scheme: dark)" srcset="./assets/{name}-dark.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="./assets/{name}-light.svg">'
            f'<img src="./assets/{name}-dark.svg" alt="{escape(alt)}" width="{width}"></picture>'
        )
    else:
        inner = f'<img src="./assets/{name}-{mode}.svg" alt="{escape(alt)}" width="{width}">'
    return f'<a href="{escape(href)}">{inner}</a>' if href else inner


def pretty_topic(t):
    if t in TOPIC_NAMES:
        return TOPIC_NAMES[t]
    return t.upper() if len(t) <= 3 else t.replace("-", " ").title()


def initials(name):
    parts = [p for p in name.replace("-", " ").split() if p]
    return ("".join(p[0] for p in parts[:2]) or name[:2]).upper()


def section(title, body):
    return f'<h2 align="center">{escape(title)}</h2>\n\n{body}\n' if body else ""


def build(D, cfg):
    acc, mode = cfg["accent"], cfg["theme"]
    name = cfg["name"] or D["name"]
    langs = [(k, v) for k, v in D["langs"] if v > 0][:8]
    main_lang = langs[0][0] if langs else None

    taglines = [t for t in cfg["taglines"] if t][:4]
    if not taglines:
        taglines = [D["bio"][:50]] if D["bio"] else []
        if main_lang:
            taglines.append(f"{main_lang} developer")
        taglines.append(f"{D['public_repos']} public repos and counting")
        if D["stars"]:
            taglines.append(f"{D['stars']:,} stars earned")
        taglines = taglines[:4]

    blog = D["blog"]
    if blog and not blog.startswith("http"):
        blog = "https://" + blog
    domain = blog.replace("https://", "").replace("http://", "").rstrip("/") if blog else ""
    meta = [D["location"], D["company"], domain]

    # featured repos
    pool = [r for r in D["repos"] if not r.get("archived")]
    pinned = [r for n in cfg["pinned_repos"] for r in pool if r["name"].lower() == n.lower()]
    featured = pinned or sorted(pool, key=lambda r: (r["stargazers_count"], r.get("pushed_at", "")), reverse=True)
    featured = featured[:6]

    # chips
    row1 = [(k, svgkit.lang_color(k)) for k, _ in langs]
    row2 = [(pretty_topic(t), TOPIC_COLORS[i % len(TOPIC_COLORS)]) for i, (t, _) in enumerate(D["topics"].most_common(12))]

    weeks = D["weeks"]
    if weeks:
        cur, best = streaks(weeks)
        total = D["total"]
    else:
        cur = best = total = 0
    show_heat = bool(weeks) and cfg["show_heatmap"]

    stats = dict(repos=D["public_repos"], stars=D["stars"], followers=D["followers"], following=D["following"], contrib=total if weeks else None)

    ASSETS.mkdir(parents=True, exist_ok=True)
    for old in ASSETS.glob("card-*.svg"):
        old.unlink()
    for theme in ("dark", "light"):
        files = {
            f"hero-{theme}.svg": svgkit.hero(theme, acc, name, taglines, meta, D["avatar"], initials(name)),
            f"stats-{theme}.svg": svgkit.stats(theme, acc, stats, langs),
            f"stack-{theme}.svg": svgkit.stack(theme, acc, [row1, row2]) if row1 else None,
            f"footer-{theme}.svg": svgkit.footer(theme, acc),
        }
        if show_heat:
            files[f"heatmap-{theme}.svg"] = svgkit.heatmap(theme, acc, weeks, total, cur, best)
        for i, repo in enumerate(featured):
            files[f"card-{i}-{theme}.svg"] = svgkit.card(theme, acc, repo, i)
        for fname, svg in files.items():
            if svg:
                (ASSETS / fname).write_text(svg, encoding="utf-8")

    # ---- README blocks
    p = lambda inner: f'<p align="center">{inner}</p>'
    links = [f'<a href="https://github.com/{D["login"]}">GitHub</a>']
    if blog:
        links.append(f'<a href="{escape(blog)}">Website</a>')
    if D["twitter"]:
        links.append(f'<a href="https://x.com/{escape(D["twitter"])}">X</a>')
    if cfg["linkedin"]:
        links.append(f'<a href="{escape(cfg["linkedin"])}">LinkedIn</a>')
    if D["email"]:
        links.append(f'<a href="mailto:{escape(D["email"])}">Email</a>')

    about = []
    if D["recent"]:
        r0 = D["recent"][0]
        about.append(f"- 🔭 Currently working on **[{r0['name']}]({r0['html_url']})**")
    if main_lang:
        about.append(f"- 💻 Mostly writing **{main_lang}**" + (f" and **{langs[1][0]}**" if len(langs) > 1 else ""))
    if D["bio"]:
        about.append(f"- 💬 {D['bio']}")
    if D["location"]:
        about.append(f"- 📍 Based in **{D['location']}**")
    if D["company"]:
        about.append(f"- 🏢 Working at **{D['company']}**")
    about.append(f"- ⚡ **{D['public_repos']}** public repos · **{D['stars']:,}** stars · **{D['followers']:,}** followers")

    cards = " ".join(pic(f"card-{i}", r["name"], mode, "48.5%", r["html_url"]) for i, r in enumerate(featured))
    recent = "\n".join(f"- [{r['name']}]({r['html_url']}) — {r.get('pushed_at', '')[:10]}" for r in D["recent"][:5] if r.get("pushed_at"))

    values = {
        "{{HERO}}": p(pic("hero", f"{name} — profile banner", mode)),
        "{{LINKS}}": p("  ·  ".join(links)),
        "{{ABOUT}}": section("About", "\n".join(about)),
        "{{STATS}}": p(pic("stats", "GitHub stats", mode)),
        "{{STACK}}": section("Tech Stack", p(pic("stack", "Languages and tools", mode))) if row1 else "",
        "{{HEATMAP}}": p(pic("heatmap", "Contribution activity", mode)) if show_heat else "",
        "{{PROJECTS}}": section("Featured Projects", p(cards)) if featured else "",
        "{{RECENT}}": section("Recently Active", recent) if recent else "",
        "{{FOOTER}}": p(pic("footer", "Thanks for stopping by", mode)),
        "{{UPDATED}}": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "{{USER}}": D["login"],
    }
    text = TEMPLATE.read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace(k, v)
    if not SAMPLE:
        OUT.write_text(text, encoding="utf-8")
    print(f"Built profile for {D['login']} (theme={mode}, accent={acc})")


if __name__ == "__main__":
    build(collect(), load_config())
