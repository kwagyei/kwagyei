#!/usr/bin/env python3
"""Render a GitHub stats card as a self-hosted SVG, styled like a terminal window."""
import json, os, subprocess, html

USER = os.environ.get("STATS_USER", "kwagyei")
OUT = os.environ.get("STATS_OUT", "stats.svg")

QUERY = """
query($login:String!) {
  user(login:$login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false) {
      totalCount
      nodes {
        stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}"""

proc = subprocess.run(
    ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={USER}"],
    capture_output=True, text=True)
if proc.returncode != 0:
    raise SystemExit("gh api failed: " + proc.stderr.strip())
data = json.loads(proc.stdout)
if "errors" in data:
    raise SystemExit("GraphQL error: " + json.dumps(data["errors"]))
u = data["data"]["user"]

repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
commits = u["contributionsCollection"]["totalCommitContributions"]
contribs = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
followers = u["followers"]["totalCount"]

langs = {}
colors = {}
for r in repos:
    for e in r["languages"]["edges"]:
        name = e["node"]["name"]
        langs[name] = langs.get(name, 0) + e["size"]
        colors[name] = e["node"]["color"] or "#8b949e"
top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
total = sum(v for _, v in top) or 1

W, H = 880, 250
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'role="img" aria-label="GitHub stats for {USER}">',
    '<defs><clipPath id="s-clip"><rect width="880" height="250" rx="10"/></clipPath></defs>',
    '<g clip-path="url(#s-clip)">',
    '<rect width="880" height="250" fill="#0d1117"/>',
    '<rect x="0.5" y="0.5" width="879" height="249" rx="10" fill="none" stroke="#30363d"/>',
    '<rect width="880" height="34" fill="#161b22"/>',
    '<circle cx="22" cy="17" r="5" fill="#ff5f56"/><circle cx="42" cy="17" r="5" fill="#ffbd2e"/>'
    '<circle cx="62" cy="17" r="5" fill="#27c93f"/>',
    f'<text x="86" y="22" font-family="{MONO}" font-size="12" fill="#8b949e">stats — {USER}</text>',
    f'<text x="26" y="70" font-family="{MONO}" font-size="15" fill="#58a6ff">~ <tspan fill="#7ee787">$</tspan>'
    f' <tspan fill="#e6edf3">gh stats --user {USER}</tspan></text>',
]

rows = [("public repos", u["repositories"]["totalCount"]), ("followers", followers),
        ("here since", u["createdAt"][:4]), ("commits (12 mo)", commits), ("contributions", contribs)]
y = 104
for label, value in rows[:3]:
    parts.append(f'<text x="26" y="{y}" font-family="{MONO}" font-size="14" fill="#8b949e">{label}</text>')
    parts.append(f'<text x="230" y="{y}" font-family="{MONO}" font-size="14" font-weight="700" fill="#e6edf3" text-anchor="end">{value}</text>')
    y += 26
y = 104
for label, value in rows[3:]:
    parts.append(f'<text x="290" y="{y}" font-family="{MONO}" font-size="14" fill="#8b949e">{label}</text>')
    parts.append(f'<text x="500" y="{y}" font-family="{MONO}" font-size="14" font-weight="700" fill="#e6edf3" text-anchor="end">{value}</text>')
    y += 26

parts.append(f'<text x="26" y="196" font-family="{MONO}" font-size="13" fill="#8b949e">languages</text>')
x = 26.0
BAR_W = 828.0
for name, size in top:
    w = BAR_W * size / total
    parts.append(f'<rect x="{x:.1f}" y="206" width="{max(w-2,2):.1f}" height="9" rx="4.5" fill="{colors[name]}"/>')
    x += w
lx = 26
for name, size in top:
    pct = 100.0 * size / total
    parts.append(f'<circle cx="{lx+4}" cy="{236}" r="4" fill="{colors[name]}"/>')
    label = f"{html.escape(name)} {pct:.1f}%"
    parts.append(f'<text x="{lx+15}" y="{240}" font-family="{MONO}" font-size="12" fill="#8b949e">{label}</text>')
    lx += 15 + int(len(label) * 7.3) + 22
parts += ["</g>", "</svg>"]
open(OUT, "w").write("\n".join(parts))
print(f"wrote {OUT}: repos={u['repositories']['totalCount']} stars={stars} followers={followers} "
      f"commits={commits} contribs={contribs} langs={[n for n,_ in top]}")
