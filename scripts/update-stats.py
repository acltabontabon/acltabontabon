"""Render ACT's GitHub card using public profile data; standard library only."""

import collections
import datetime
import html
import json
import os
from pathlib import Path
import re
import urllib.request
from zoneinfo import ZoneInfo

USER = "acltabontabon"
ROOT = Path(__file__).resolve().parents[1]


def fetch(url):
    headers = {"User-Agent": "ACT-profile", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def collect():
    profile = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    repos = []
    page = 1
    while True:
        batch = json.loads(fetch(
            f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
        ))
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    contribution_html = fetch(f"https://github.com/users/{USER}/contributions")
    text = html.unescape(re.sub(r"<[^>]+>", " ", contribution_html))
    total = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", text)
    if not total:
        raise RuntimeError("Contribution total missing; keeping the previous card.")
    languages = collections.Counter(
        repo["language"] for repo in repos if repo["language"] and not repo["fork"]
    )
    return {
        "date": datetime.datetime.now(ZoneInfo("Asia/Manila")).date().isoformat(),
        "contributions": int(total.group(1).replace(",", "")),
        "repositories": profile["public_repos"],
        "stars": sum(repo["stargazers_count"] for repo in repos if not repo["fork"]),
        "languages": dict(languages.most_common()),
    }


def render(data):
    esc = html.escape
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="280" viewBox="0 0 1280 280" role="img" aria-labelledby="title desc">',
        '<title id="title">ACT / In the workshop</title>',
        f'<desc id="desc">{data["contributions"]:,} contributions in the last year, '
        f'{data["repositories"]} public repositories, {data["stars"]} stars on owned '
        f'original repositories. Public GitHub snapshot: {esc(data["date"])}.</desc>',
        '<rect width="1280" height="280" rx="14" fill="#171816"/>',
        '<g font-family="Arial, Helvetica, sans-serif">',
        '<text x="40" y="38" fill="#c2ac82" font-family="Menlo, Consolas, monospace" font-size="14" letter-spacing="2">IN THE WORKSHOP / GITHUB</text>',
        f'<text x="1240" y="38" text-anchor="end" fill="#b1b1a7" font-size="13">PUBLIC SNAPSHOT · {esc(data["date"])} · UPDATED DAILY</text>',
    ]
    for x, key, label in [
        (40, "contributions", "contributions / past year"),
        (472, "repositories", "public repositories"),
        (902, "stars", "stars / original repositories"),
    ]:
        out.append(f'<text x="{x}" y="116" fill="#ece9e1" font-size="57" letter-spacing="-2">{data[key]:,}</text>')
        out.append(f'<text x="{x}" y="148" fill="#b1b1a7" font-size="18">{label}</text>')
    out.extend([
        '<path d="M420 69v86M850 69v86M40 177h1200" stroke="#363730"/>',
        '<text x="40" y="206" fill="#b1b1a7" font-family="Menlo, Consolas, monospace" font-size="12" letter-spacing="1">PRIMARY LANGUAGES / ORIGINAL REPOSITORIES</text>',
    ])
    languages = list(data["languages"].items())
    parts = languages[:4]
    if len(languages) > 4:
        parts.append(("Other", sum(count for _, count in languages[4:])))
    palette = ["#c2ac82", "#ece9e1", "#989c8a", "#777c70", "#454940"]
    total = sum(count for _, count in parts)
    x = 40
    for (name, count), color in zip(parts, palette):
        width = 1200 * count / total
        out.append(f'<rect x="{x:.2f}" y="222" width="{width:.2f}" height="6" fill="{color}"/>')
        x += width
    x = 40
    for (name, count), color in zip(parts, palette):
        out.append(f'<circle cx="{x + 4}" cy="253" r="4" fill="{color}"/>')
        out.append(f'<text x="{x + 16}" y="257" fill="#b1b1a7" font-size="14">{esc(name)} · {count}</text>')
        x += 240
    out.append("</g></svg>\n")
    return "\n".join(out)


if __name__ == "__main__":
    data = collect()
    svg = render(data)
    (ROOT / "assets" / "github-stats.svg").write_text(svg)
    (ROOT / "assets" / "github-stats.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Rendered public GitHub stats for {USER} ({data['date']}).")
