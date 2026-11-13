#!/usr/bin/env python3
"""Record total release downloads daily and render SVG charts (daily / monthly / yearly).

History starts at the first release that has downloads. Days before the first
real snapshot are ESTIMATED (each release's downloads spread evenly from its
publish date to the first snapshot) because GitHub keeps no download history.
"""
import json, math, os, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

repo = os.environ["GITHUB_REPOSITORY"]
token = os.environ.get("GITHUB_TOKEN", "")
out = os.path.join(".github", "downloads")
today = datetime.now(timezone.utc).date()


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
info = [(date.fromisoformat((r["published_at"] or r["created_at"])[:10]),
         sum(a["download_count"] for a in r["assets"])) for r in releases]
total = sum(n for _, n in info)
with_dl = [(p, n) for p, n in info if n > 0]
if not with_dl:
    sys.exit("No downloads yet.")
start = min(p for p, _ in with_dl)

os.makedirs(out, exist_ok=True)
hp = os.path.join(out, "history.json")
hist = json.load(open(hp)) if os.path.exists(hp) else []
if not hist:  # one-time estimated backfill
    d = start
    while d < today:
        v = 0.0
        for p, n in with_dl:
            if d >= p and today > p:
                v += n * min(1.0, (d - p).days / (today - p).days)
        hist.append({"d": d.isoformat(), "n": round(v), "e": 1})
        d += timedelta(days=1)
hist = [h for h in hist if h["d"] != today.isoformat()] + [{"d": today.isoformat(), "n": total}]
hist.sort(key=lambda h: h["d"])
json.dump(hist, open(hp, "w"), separators=(",", ":"))
pts = [(date.fromisoformat(h["d"]), h["n"], bool(h.get("e"))) for h in hist]
est_until = max((d for d, _, e in pts if e), default=None)

W, H, L, R, T, B = 760, 280, 56, 20, 62, 40
FONT = "-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
STYLE = f"""<style>
.t{{font:12px {FONT};fill:#57606a}}.h{{font:600 15px {FONT};fill:#1f2328}}
.g{{stroke:#d0d7de;stroke-width:1}}.ln{{stroke:#0969da;stroke-width:2.5;stroke-linejoin:round;fill:none}}
.es{{stroke:#0969da;stroke-width:2.5;stroke-dasharray:5 4;opacity:.55;fill:none}}
.a{{fill:#0969da;opacity:.12}}.b{{fill:#0969da}}.bg{{fill:#fff;stroke:#d0d7de}}
@media (prefers-color-scheme:dark){{.t{{fill:#9198a1}}.h{{fill:#f0f6fc}}.g{{stroke:#3d444d}}.ln,.es{{stroke:#4493f8}}.a,.b{{fill:#4493f8}}.bg{{fill:#0d1117;stroke:#3d444d}}}}
</style>"""


def nice(v):
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    return next(m * e for m in (1, 2, 2.5, 5, 10) if v <= m * e)


def frame(title, sub, ymax, body):
    g = ""
    for i in range(5):
        v = ymax * i / 4
        y = T + (1 - i / 4) * (H - T - B)
        g += f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="g"/><text x="{L-8}" y="{y+4:.1f}" class="t" text-anchor="end">{v:,.0f}</text>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{title}">{STYLE}'
            f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="8" class="bg"/>'
            f'<text x="{L}" y="26" class="h">{title}</text><text x="{L}" y="45" class="t">{sub}</text>{g}{body}</svg>')


def Y(v, ymax):
    return T + (1 - v / ymax) * (H - T - B)


def line_chart():
    d0, d1 = pts[0][0], pts[-1][0]
    span = max((d1 - d0).days, 1)
    ymax = nice(max(n for _, n, _ in pts))
    X = lambda d: L + (d - d0).days / span * (W - L - R)
    est = [(X(d), Y(n, ymax)) for d, n, e in pts if e]
    real = [(X(d), Y(n, ymax)) for d, n, e in pts if not e]
    if est:
        real = [est[-1]] + real
    s = lambda p: " ".join(f"{x:.1f},{y:.1f}" for x, y in p)
    body = ""
    if len(pts) > 1:
        body += f'<polygon points="{X(d0):.1f},{H-B} {s([(X(d), Y(n, ymax)) for d, n, _ in pts])} {X(d1):.1f},{H-B}" class="a"/>'
    if len(est) > 1:
        body += f'<polyline points="{s(est)}" class="es"/>'
    if len(real) > 1:
        body += f'<polyline points="{s(real)}" class="ln"/>'
    body += f'<circle cx="{X(d1):.1f}" cy="{Y(pts[-1][1], ymax):.1f}" r="3.5" class="b"/>'
    for i in range(6):
        d = d0 + timedelta(days=round(span * i / 5))
        anchor = "start" if i == 0 else "end" if i == 5 else "middle"
        body += f'<text x="{X(d):.1f}" y="{H-14}" class="t" text-anchor="{anchor}">{d.isoformat()}</text>'
    sub = f"Cumulative, daily · since first release with downloads ({start})"
    if est_until:
        sub += f" · dashed = estimated until {est_until}"
    return frame(f"Download progress · {total:,} total", sub, ymax, body)


def cum_at(d):
    v = 0
    for pd_, n, _ in pts:
        if pd_ <= d:
            v = n
        else:
            break
    return v


def periods(kind):
    res, d = [], start
    while d <= today:
        if kind == "month":
            nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            label = d.strftime("%Y-%m")
        else:
            nxt = date(d.year + 1, 1, 1)
            label = str(d.year)
        end = min(nxt - timedelta(days=1), today)
        res.append((label, cum_at(end) - (cum_at(d - timedelta(days=1)) if d > start else 0)))
        d = nxt
    return res


def bar_chart(kind):
    data = periods(kind)
    ymax = nice(max(v for _, v in data))
    n = len(data)
    slot = (W - L - R) / n
    bw = min(slot * 0.7, 60)
    every = max(1, math.ceil(n / 12))
    body = ""
    for i, (lab, v) in enumerate(data):
        x = L + slot * i + (slot - bw) / 2
        y = Y(v, ymax)
        body += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{H-B-y:.1f}" rx="2" class="b"/>'
        if n <= 14 and v:
            body += f'<text x="{x+bw/2:.1f}" y="{y-5:.1f}" class="t" text-anchor="middle">{v:,}</text>'
        if i % every == 0:
            body += f'<text x="{x+bw/2:.1f}" y="{H-14}" class="t" text-anchor="middle">{lab}</text>'
    name = "Monthly" if kind == "month" else "Yearly"
    sub = f"New downloads per {kind} · since first release with downloads ({start})"
    if est_until:
        sub += f" · estimated until {est_until}"
    return frame(f"{name} downloads · {total:,} total", sub, ymax, body)


for fn, svg in (("chart.svg", line_chart()), ("chart-monthly.svg", bar_chart("month")), ("chart-yearly.svg", bar_chart("year"))):
    open(os.path.join(out, fn), "w", encoding="utf-8").write(svg)
print(repo, total, "downloads,", len(pts), "points")
