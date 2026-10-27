#!/usr/bin/env python3
"""Rescrie secțiunea de statistici de download din README pe baza GitHub Releases API."""
import json
import os
import re
import sys
from urllib.request import Request, urlopen

START = "<!-- DOWNLOAD-STATS:START -->"
END = "<!-- DOWNLOAD-STATS:END -->"
LATEST_COUNT = 5
TYPES = (
    ("DEB", (".deb",)),
    ("RPM", (".rpm",)),
    ("Arch", (".pkg.tar.zst", ".pkg.tar.xz")),
)


def fetch_releases(repo, token):
    releases = []
    page = 1
    while True:
        request = Request(
            f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "TuxPulse-stats",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urlopen(request, timeout=20) as response:
            batch = json.loads(response.read().decode("utf-8"))
        if not batch:
            return releases
        releases.extend(batch)
        page += 1


def package_type(asset_name):
    name = asset_name.lower()
    for label, suffixes in TYPES:
        if name.endswith(suffixes):
            return label
    return None


def count_by_type(release):
    counts = {label: 0 for label, _ in TYPES}
    for asset in release.get("assets", []):
        label = package_type(asset.get("name", ""))
        if label:
            counts[label] += int(asset.get("download_count", 0))
    return counts


def fmt(value):
    return f"{value:,}"


def build_section(repo, releases):
    releases = [r for r in releases if not r.get("draft")]
    releases.sort(key=lambda r: r.get("published_at") or "", reverse=True)
    totals = {label: 0 for label, _ in TYPES}
    rows = []
    for index, release in enumerate(releases):
        counts = count_by_type(release)
        for label in totals:
            totals[label] += counts[label]
        if index < LATEST_COUNT:
            tag = release.get("tag_name", "")
            kind = " _(pre-release)_" if release.get("prerelease") else ""
            date = (release.get("published_at") or "")[:10]
            cells = " | ".join(fmt(counts[label]) for label, _ in TYPES)
            rows.append(
                f"| [{tag}](https://github.com/{repo}/releases/tag/{tag}){kind} | {date} | {cells} | **{fmt(sum(counts.values()))}** |"
            )

    header = " | ".join(label for label, _ in TYPES)
    align = " | ".join("---:" for _ in TYPES)
    total_cells = " | ".join(f"**{fmt(totals[label])}**" for label, _ in TYPES)
    lines = [
        START,
        f"#### Latest {LATEST_COUNT} releases",
        "",
        f"| Release | Date | {header} | Total |",
        f"| --- | --- | {align} | ---: |",
        *rows,
        "",
        f"#### All releases ({len(releases)})",
        "",
        f"| {header} | Total |",
        f"| {align} | ---: |",
        f"| {total_cells} | **{fmt(sum(totals.values()))}** |",
        "",
        "_Updated automatically every day by the `Update download stats` workflow._",
        END,
    ]
    return "\n".join(lines)


def main():
    readme_path = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    repo = os.environ.get("GITHUB_REPOSITORY", "eoliann/TuxPulse")
    token = os.environ.get("GITHUB_TOKEN", "")

    with open(readme_path, encoding="utf-8") as handle:
        content = handle.read()

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(content):
        raise SystemExit(f"Markers {START} / {END} not found in {readme_path}")

    section = build_section(repo, fetch_releases(repo, token))
    content = pattern.sub(lambda _: section, content)

    with open(readme_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


if __name__ == "__main__":
    main()
