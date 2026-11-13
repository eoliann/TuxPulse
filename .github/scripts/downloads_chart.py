#!/usr/bin/env python3
"""Salveaza totalul de descarcari al release-urilor si genereaza graficul SVG."""
import json, os, sys, urllib.request
from datetime import datetime, timezone

repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ.get("GITHUB_TOKEN", "")
out_dir = os.path.join(".github", "downloads")
hist_path = os.path.join(out_dir, "history.json")
svg_path = os.path.join(out_dir, "chart.svg")


def api(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


releases, page = [], 1
while True:
    chunk = api(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}")
    if not chunk:
        break
    releases += chunk
    page += 1
releases = [r for r in releases if not r.get("draft")]
if not releases:
    sys.exit("Niciun release.")
total = sum(a["download_count"] for r in releases for a in r["assets"])
first = min(r["published_at"] or r["created_at"] for r in releases)[:10]

os.makedirs(out_dir, exist_ok=True)
hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
hist = [h for h in hist if h["d"] != today] + [{"d": today, "n": total}]
hist.sort(key=lambda h: h["d"])
json.dump(hist, open(hist_path, "w"), indent=1)

W, H, L, R, T, B = 760, 260, 56, 20, 58, 36
d0 = datetime.fromisoformat(hist[0]["d"])
span = max((datetime.fromisoformat(hist[-1]["d"]) - d0).days, 1)
top = max(max(h["n"] for h in hist), 1)
step = 10 ** (len(str(top)) - 1)
ymax = ((top + step - 1) // step) * step
if ymax == top:
    ymax += step


def X(d):
    return L + (datetime.fromisoformat(d) - d0).days / span * (W - L - R) if len(hist) > 1 else L + (W - L - R) / 2


def Y(n):
    return T + (1 - n / ymax) * (H - T - B)


grid = ""
for i in range(5):
    v = ymax * i / 4
    y = Y(v)
    grid += f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="g"/><text x="{L-8}" y="{y+4:.1f}" class="t" text-anchor="end">{int(v):,}</text>'
pts = " ".join(f"{X(h['d']):.1f},{Y(h['n']):.1f}" for h in hist)
dots = "".join(f'<circle cx="{X(h["d"]):.1f}" cy="{Y(h["n"]):.1f}" r="{3 if len(hist)<40 else 1.5}" class="l"/>' for h in hist)
area = f'<polygon points="{L if len(hist)>1 else X(hist[0]["d"]):.1f},{H-B} {pts} {X(hist[-1]["d"]):.1f},{H-B}" class="a"/>' if len(hist) > 1 else ""
line = f'<polyline points="{pts}" fill="none" class="ln"/>' if len(hist) > 1 else ""
xl = f'<text x="{L}" y="{H-12}" class="t">{hist[0]["d"]}</text><text x="{W-R}" y="{H-12}" class="t" text-anchor="end">{hist[-1]["d"]}</text>'
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Progres descarcari">
<style>
.t{{font:12px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;fill:#57606a}}
.h{{font:600 15px -apple-system,Segoe UI,Helvetica,Arial,sans-serif;fill:#1f2328}}
.g{{stroke:#d0d7de;stroke-width:1}} .ln{{stroke:#0969da;stroke-width:2.5;stroke-linejoin:round}}
.l{{fill:#0969da}} .a{{fill:#0969da;opacity:.12}} .bg{{fill:#fff;stroke:#d0d7de}}
@media (prefers-color-scheme:dark){{.t{{fill:#9198a1}}.h{{fill:#f0f6fc}}.g{{stroke:#3d444d}}.ln{{stroke:#4493f8}}.l{{fill:#4493f8}}.a{{fill:#4493f8}}.bg{{fill:#0d1117;stroke:#3d444d}}}}
</style>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="8" class="bg"/>
<text x="{L}" y="26" class="h">Progres descărcări · {total:,} total</text>
<text x="{L}" y="44" class="t">De la primul release ({first}) · {len(releases)} release-uri · actualizat zilnic</text>
{grid}{area}{line}{dots}{xl}
</svg>'''
open(svg_path, "w", encoding="utf-8").write(svg)
print(repo, total, "descarcari,", len(hist), "puncte")
