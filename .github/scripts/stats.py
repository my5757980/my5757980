"""Draw the profile's two stats cards (assets/stats.svg, assets/top-langs.svg) from the GitHub REST API.

The README used github-readme-stats.vercel.app, a shared public instance that answers 503 when it is
over its limits, so the cards were broken images. These are plain files in this repo instead, redrawn
by .github/workflows/stats.yml. Public repositories only; forks are not counted.

Usage: python3 .github/scripts/stats.py <username> <output dir>   (GITHUB_TOKEN is used when set)
"""
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from html import escape

USER, OUT = sys.argv[1], sys.argv[2]
API = "https://api.github.com"

BG, TITLE, TEXT, ACCENT, MUTED = "#1a1b27", "#70a5fd", "#38bdae", "#bf91f3", "#a9b1d6"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
# GitHub's linguist colours for the languages likely to appear; anything else is grey
COLORS = {
    "TypeScript": "#3178c6", "Python": "#3572A5", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#663399", "Solidity": "#AA6746", "PLpgSQL": "#336790", "Shell": "#89e051",
    "PowerShell": "#012456", "Dockerfile": "#384d54", "MDX": "#fcb32c", "PHP": "#4F5D95",
    "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584", "C#": "#178600", "Jupyter Notebook": "#DA5B0B",
    "SCSS": "#c6538c", "Batchfile": "#C1F12E", "Mako": "#7e858d", "Makefile": "#427819",
}


# SpecKit Plus puts the same five PowerShell scripts in every repo's .specify/scripts. They are tooling,
# not code I wrote, and would otherwise show up as one of my "most used" languages.
HIDDEN = {"PowerShell"}


def get(path: str) -> dict | list:
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                     "User-Agent": f"{USER}-profile-stats"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    for attempt in range(4):  # a dropped connection or a 5xx is retried; a 4xx is a real answer
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 3:
                raise
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def count(query: str) -> int:
    return get(f"/search/issues?q={query}&per_page=1")["total_count"]


repos = [r for r in get(f"/users/{USER}/repos?per_page=100&type=owner") if not r["fork"] and r["name"] != USER]
stars = sum(r["stargazers_count"] for r in repos)
languages: dict[str, int] = {}
for r in repos:
    for lang, size in get(f"/repos/{USER}/{r['name']}/languages").items():
        if lang not in HIDDEN:
            languages[lang] = languages.get(lang, 0) + size
commits = get(f"/search/commits?q=author:{USER}&per_page=1")["total_count"]
prs = count(f"author:{USER}+type:pr")
issues = count(f"author:{USER}+type:issue")

rows = [("★", "Total stars", stars), ("●", "Total commits", commits), ("⇄", "Pull requests", prs),
        ("!", "Issues", issues), ("▣", "Public repositories", len(repos))]
lines = []
for i, (icon, label, value) in enumerate(rows):
    y = 80 + i * 25
    lines.append(f'<text x="25" y="{y}" fill="{ACCENT}" font-size="14" font-family="{FONT}">{icon}</text>'
                 f'<text x="50" y="{y}" fill="{TEXT}" font-size="14" font-weight="600" font-family="{FONT}">{label}:</text>'
                 f'<text x="230" y="{y}" fill="{TEXT}" font-size="14" font-weight="700" font-family="{FONT}">{value:,}</text>')
stats_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="215" viewBox="0 0 400 215" role="img" aria-labelledby="t">
<title id="t">{escape(USER)}'s GitHub stats: {stars} stars, {commits} commits, {prs} pull requests, {issues} issues, {len(repos)} public repositories</title>
<rect width="400" height="215" rx="6" fill="{BG}"/>
<text x="25" y="38" fill="{TITLE}" font-size="18" font-weight="600" font-family="{FONT}">GitHub Stats</text>
{''.join(lines)}
<text x="25" y="200" fill="{MUTED}" font-size="10" font-family="{FONT}">Public repositories, forks excluded</text>
</svg>
"""

total = sum(languages.values()) or 1
top = sorted(languages.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
bar, x = [], 25.0
for lang, size in top:
    w = 250 * size / total
    bar.append(f'<rect x="{x:.2f}" y="50" width="{w:.2f}" height="8" fill="{COLORS.get(lang, "#858585")}"/>')
    x += w
legend = []
for i, (lang, size) in enumerate(top):
    lx, ly = 25 + (i % 2) * 130, 85 + (i // 2) * 25
    legend.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{COLORS.get(lang, "#858585")}"/>'
                  f'<text x="{lx + 16}" y="{ly}" fill="{TEXT}" font-size="12" font-family="{FONT}">{escape(lang)} {100 * size / total:.1f}%</text>')
height = 85 + ((len(top) + 1) // 2) * 25 + 20
langs_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="{height}" viewBox="0 0 300 {height}" role="img" aria-labelledby="t">
<title id="t">Most used languages by code size: {escape(', '.join(f'{l} {100 * s / total:.1f}%' for l, s in top))}</title>
<rect width="300" height="{height}" rx="6" fill="{BG}"/>
<text x="25" y="35" fill="{TITLE}" font-size="18" font-weight="600" font-family="{FONT}">Most Used Languages</text>
<mask id="m"><rect x="25" y="50" width="250" height="8" rx="4" fill="#fff"/></mask>
<g mask="url(#m)">{''.join(bar)}</g>
{''.join(legend)}
<text x="25" y="{height - 12}" fill="{MUTED}" font-size="10" font-family="{FONT}">Public repos by code size · SpecKit scripts left out</text>
</svg>
"""

os.makedirs(OUT, exist_ok=True)
for name, svg in (("stats.svg", stats_svg), ("top-langs.svg", langs_svg)):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
print(f"{len(repos)} repos, {stars} stars, {commits} commits, {prs} PRs, {issues} issues; top: "
      + ", ".join(f"{l} {100 * s / total:.1f}%" for l, s in top))
