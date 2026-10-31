"""Generator kartu GitHub Analytics (desain sendiri, tema server hijau-hitam-putih).

Dijalankan oleh GitHub Actions (.github/workflows/stats.yml). Hanya pakai library bawaan Python.
Output: stats-general.svg, stats-langs.svg, stats-streak.svg, stats-activity.svg
"""
import html, json, math, os, sys, urllib.request
from datetime import date, datetime, timedelta

OUT = os.environ.get("OUT_DIR", ".")
USER = os.environ.get("GH_USER", "MradityaaD")
TOKEN = os.environ.get("GH_TOKEN", "")

MONO = "'JetBrains Mono','Fira Code',Consolas,'SF Mono','Courier New',monospace"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
GREEN, WHITE, GRAY, LINE, PANEL, TILE = "#39ff6e", "#f5f5f5", "#9a9a9a", "#3c3c3c", "#0a0a0a", "#101010"
HEAT = ["#161616", "#0f5a2a", "#138a3f", "#22c55a", "#39ff6e"]


def esc(s):
    return html.escape(str(s), quote=False)


def nf(n):
    return f"{int(n):,}"


# ------------------------------------------------------------------ data
QUERY = """
query($login:String!){ user(login:$login){
  createdAt
  repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){
    totalCount
    nodes{ name stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } }
  }
  contributionsCollection{
    totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
  }
}}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload or not payload.get("data", {}).get("user"):
        raise SystemExit("GitHub API error: " + json.dumps(payload.get("errors", payload))[:400])
    u = payload["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r_ in repos:
        for e in r_["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r_["stargazerCount"] for r_ in repos),
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "since": u["createdAt"][:4],
        "langs": sorted(langs.items(), key=lambda x: -x[1]),
        "weeks": cc["contributionCalendar"]["weeks"],
        "days": days,
        "total": cc["contributionCalendar"]["totalContributions"],
    }


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    cur = 0
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    return cur, longest


# ------------------------------------------------------------------ svg helpers
def wrap(w, h, body, title, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><defs><filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3.5" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
            f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>{defs}</defs>{body}</svg>\n')


def frame(w, h, title, sub):
    per = 2 * (w - 20 + h - 20)
    b = f'<rect x="10" y="10" width="{w-20}" height="{h-20}" rx="16" fill="{PANEL}" stroke="{LINE}"/>'
    b += (f'<rect x="10" y="10" width="{w-20}" height="{h-20}" rx="16" fill="none" stroke="url(#edge)" stroke-width="2.5" stroke-dasharray="200 {per-200}">'
          f'<animate attributeName="stroke-dashoffset" from="0" to="-{per}" dur="9s" repeatCount="indefinite"/></rect>')
    b += f'<text x="34" y="48" font-family="{SANS}" font-size="20" font-weight="700" fill="{GREEN}">{esc(title)}</text>'
    b += f'<text x="{w-34}" y="47" text-anchor="end" font-family="{MONO}" font-size="12.5" fill="{GRAY}">{esc(sub)}</text>'
    b += f'<rect x="34" y="62" width="{w-68}" height="1.5" fill="{LINE}"/><rect x="34" y="61" width="90" height="3.5" rx="2" fill="{GREEN}" filter="url(#glow)">'
    b += f'<animate attributeName="x" values="34;{w-124};34" dur="6s" repeatCount="indefinite"/></rect>'
    return b


# ------------------------------------------------------------------ cards
def card_general(d):
    W, H = 1200, 220
    b = frame(W, H, "General stats", f"member since {d['since']} | public data")
    tiles = [("Public repos", d["repos"], "owned by you, no forks"), ("Commits", d["commits"], "past 12 months"),
             ("Stars earned", d["stars"], "across all repos"), ("PRs & issues", d["prs"] + d["issues"], "past 12 months")]
    for i, (lab, val, sub) in enumerate(tiles):
        x = 34 + i * 285
        b += f'<rect x="{x}" y="84" width="265" height="106" rx="12" fill="{TILE}" stroke="#2a2a2a"/>'
        b += f'<circle cx="{x+246}" cy="104" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;.2;1" dur="{2+i*.4:.1f}s" repeatCount="indefinite"/></circle>'
        b += f'<text x="{x+20}" y="140" font-family="{SANS}" font-size="44" font-weight="800" fill="{GREEN}" filter="url(#glow)">{nf(val)}</text>'
        b += f'<text x="{x+20}" y="165" font-family="{SANS}" font-size="15" font-weight="600" fill="{WHITE}">{esc(lab)}</text>'
        b += f'<text x="{x+20}" y="183" font-family="{MONO}" font-size="11.5" fill="{GRAY}">{esc(sub)}</text>'
    return wrap(W, H, b, "General GitHub stats")


def card_langs(d):
    langs = d["langs"][:6]
    tot = sum(v for _, v in d["langs"]) or 1
    W = 1200
    H = 100 + len(langs) * 40 + 24
    b = frame(W, H, "Top languages", "by code size across all public repos")
    for i, (name, v) in enumerate(langs):
        y = 94 + i * 40
        pct = v / tot * 100
        wbar = max(6, 700 * pct / (langs[0][1] / tot * 100))
        b += f'<text x="34" y="{y+16}" font-family="{SANS}" font-size="16" font-weight="600" fill="{WHITE}">{esc(name)}</text>'
        b += f'<rect x="220" y="{y}" width="700" height="22" rx="11" fill="#161616"/>'
        b += (f'<rect x="220" y="{y}" width="{wbar:.0f}" height="22" rx="11" fill="{GREEN}" fill-opacity="{1-i*0.11:.2f}" filter="url(#glow)">'
              f'<animate attributeName="width" from="0" to="{wbar:.0f}" dur="{1+i*.2:.1f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>')
        b += f'<text x="940" y="{y+17}" font-family="{MONO}" font-size="15" font-weight="700" fill="{GREEN}">{pct:.1f}%</text>'
    return wrap(W, H, b, "Top languages")


def ring(cx, cy, r, frac, color=GREEN, dur=1.6):
    C = 2 * math.pi * r
    dd = max(0.01, C * frac)
    s = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1c1c1c" stroke-width="12"/>'
    s += (f'<g transform="rotate(-90 {cx} {cy})"><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="12" stroke-linecap="round" '
          f'stroke-dasharray="{dd:.1f} {C:.1f}" filter="url(#glow)"><animate attributeName="stroke-dasharray" from="0 {C:.1f}" to="{dd:.1f} {C:.1f}" dur="{dur}s" fill="freeze"/></circle></g>')
    s += f'<circle cx="{cx}" cy="{cy}" r="{r+14}" fill="none" stroke="{GRAY}" stroke-opacity=".35" stroke-dasharray="2 8"><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="24s" repeatCount="indefinite"/></circle>'
    return s


def card_streak(d):
    W, H = 1200, 270
    cur, lon = streaks(d["days"])
    first, last = d["days"][0]["date"], d["days"][-1]["date"]
    b = frame(W, H, "Streak tracker", f"{first} to {last}")
    items = [("Current streak", cur, "consecutive days", cur / lon if lon else 0), ("Longest streak", lon, "days (past 12 months)", 1.0),
             ("Total contributions", d["total"], "past 12 months", 1.0)]
    for i, (lab, val, sub, frac) in enumerate(items):
        cx = 140 + i * 390
        b += ring(cx, 150, 60, frac, GREEN, 1.4 + i * .3)
        b += f'<text x="{cx}" y="{150+14}" text-anchor="middle" font-family="{SANS}" font-size="40" font-weight="800" fill="{GREEN}">{nf(val)}</text>'
        b += f'<text x="{cx+86}" y="{128}" font-family="{SANS}" font-size="16" font-weight="700" fill="{WHITE}">{esc(lab)}</text>'
        b += f'<text x="{cx+86}" y="{150}" font-family="{MONO}" font-size="12" fill="{GRAY}">{esc(sub)}</text>'
    return wrap(W, H, b, "GitHub streak")


def card_activity(d):
    weeks = d["weeks"]
    mx = max([x["contributionCount"] for x in d["days"]] + [1])
    pitch, cell = 19, 15
    W = max(1200, 34 + 44 + len(weeks) * pitch + 34)
    H = 300
    b = frame(W, H, "Contribution graph", f"{nf(d['total'])} contributions in the past 12 months")
    x0, y0 = max(78, (W - len(weeks) * pitch) // 2 + 24), 108
    last_lab = -9
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_m = None
    for wi, w in enumerate(weeks):
        dt = datetime.strptime(w["contributionDays"][0]["date"], "%Y-%m-%d")
        if dt.month != last_m and (wi == 0 or dt.day <= 7) and wi - last_lab >= 3:
            last_lab = wi
            b += f'<text x="{x0+wi*pitch}" y="{y0-12}" font-family="{MONO}" font-size="11.5" fill="{GRAY}">{months[dt.month-1]}</text>'
        last_m = dt.month
        b += f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{wi*0.035:.2f}s" dur="0.35s" fill="freeze"/>'
        for di, day in enumerate(w["contributionDays"]):
            c = day["contributionCount"]
            lv = 0 if c == 0 else min(4, max(1, math.ceil(4 * c / mx)))
            b += f'<rect x="{x0+wi*pitch}" y="{y0+di*pitch}" width="{cell}" height="{cell}" rx="3.5" fill="{HEAT[lv]}"><title>{day["date"]}: {c} contributions</title></rect>'
        b += "</g>"
    for lab, di in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        b += f'<text x="{x0-44}" y="{y0+di*pitch+12}" font-family="{MONO}" font-size="11" fill="{GRAY}">{lab}</text>'
    # sweep
    gw = len(weeks) * pitch
    b += f'<rect x="{x0-30}" y="{y0-4}" width="30" height="{7*pitch+4}" fill="{GREEN}" fill-opacity=".12"><animate attributeName="x" values="{x0-30};{x0+gw};{x0+gw}" keyTimes="0;.7;1" dur="7s" begin="2s" repeatCount="indefinite"/></rect>'
    ly = y0 + 7 * pitch + 28
    b += f'<text x="{x0}" y="{ly}" font-family="{MONO}" font-size="12" fill="{GRAY}">Less</text>'
    for i, c in enumerate(HEAT):
        b += f'<rect x="{x0+56+i*22}" y="{ly-12}" width="15" height="15" rx="3.5" fill="{c}"/>'
    b += f'<text x="{x0+56+5*22+6}" y="{ly}" font-family="{MONO}" font-size="12" fill="{GRAY}">More</text>'
    return wrap(W, H, b, "GitHub contribution graph")


def placeholder(w, h, title):
    b = frame(w, h, title, "waiting for first update")
    b += f'<text x="{w/2}" y="{h/2+16}" text-anchor="middle" font-family="{MONO}" font-size="16" fill="{WHITE}">$ sync --github-api<tspan fill="{GREEN}"> ...</tspan></text>'
    b += f'<text x="{w/2}" y="{h/2+42}" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{GRAY}">data fills in automatically after the Update stats workflow runs</text>'
    b += f'<rect x="34" y="{h-44}" width="{w-68}" height="3" fill="#161616"/><rect x="34" y="{h-44}" width="120" height="3" fill="{GREEN}" filter="url(#glow)"><animate attributeName="x" values="34;{w-154};34" dur="3s" repeatCount="indefinite"/></rect>'
    return wrap(w, h, b, title + " (menunggu data)")


def demo():
    random_days, weeks, d0 = [], [], date.today() - timedelta(days=370)
    while d0.weekday() != 6:
        d0 += timedelta(days=1)
    import random
    random.seed(3)
    n = 0
    while d0 <= date.today():
        wk = []
        for _ in range(7):
            if d0 > date.today():
                break
            c = random.choice([0, 0, 0, 1, 2, 3, 5, 8]) if random.random() > .25 else 0
            wk.append({"date": d0.isoformat(), "contributionCount": c}); d0 += timedelta(days=1)
        weeks.append({"contributionDays": wk})
    days = [x for w in weeks for x in w["contributionDays"]]
    return {"repos": 9, "stars": 3, "commits": 142, "prs": 2, "issues": 1, "since": "2026", "weeks": weeks, "days": days,
            "total": sum(x["contributionCount"] for x in days),
            "langs": [("HTML", 420000), ("CSS", 210000), ("JavaScript", 150000), ("PHP", 90000), ("Python", 30000), ("Hack", 5000)]}


def write(name, s):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(s)
    print("wrote", name)


if __name__ == "__main__":
    if "--placeholder" in sys.argv:
        write("stats-general.svg", placeholder(1200, 220, "General stats"))
        write("stats-langs.svg", placeholder(1200, 300, "Top languages"))
        write("stats-streak.svg", placeholder(1200, 270, "Streak tracker"))
        write("stats-activity.svg", placeholder(1200, 300, "Contribution graph"))
    else:
        data = demo() if "--demo" in sys.argv else fetch()
        write("stats-general.svg", card_general(data))
        write("stats-langs.svg", card_langs(data))
        write("stats-streak.svg", card_streak(data))
        write("stats-activity.svg", card_activity(data))
