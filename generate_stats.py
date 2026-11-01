#!/usr/bin/env python3
"""
Generator kartu GitHub Analytics (SVG animasi) untuk README profil.

Mode live  : butuh GH_TOKEN (di GitHub Actions sudah otomatis dari secrets.GITHUB_TOKEN).
Mode snapshot: dipakai kalau tidak ada token / tidak ada internet.

Output: stats.svg, languages.svg, streak.svg, activity.svg  (ke folder OUT_DIR)
Hanya memakai library bawaan Python.
"""
import json, math, os, random, sys, urllib.request
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "MradityaaD")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_DIR", ".")

BG, PANEL, G, W, MUTED = "#020502", "#050b07", "#00ff66", "#f2f7f3", "#8fb09a"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,'Courier New',monospace"
SANS = "'Segoe UI','Helvetica Neue',Arial,sans-serif"
LANG_COLORS = {
    "HTML": "#ff6a3d", "CSS": "#a07bff", "JavaScript": "#f7df1e", "PHP": "#8892bf",
    "Python": "#4f8cc9", "TypeScript": "#3b9be0", "Java": "#f0a030", "C++": "#e84a8a",
    "Hack": "#9fb4ff", "Shell": "#89e051", "SCSS": "#e06aa6", "Ruby": "#ff4d4d",
}
FALLBACK_COLORS = ["#00ff66", "#f2f7f3", "#1fdc6b", "#8fb09a", "#5fffa0"]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(w, h, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">\n'
        f"<defs>{defs}<style>.mono{{font-family:{MONO}}} .sans{{font-family:{SANS}}}</style>"
        f'<pattern id="gp" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{G}" stroke-opacity=".06"/></pattern>'
        f'<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f"</defs>\n"
        f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/><rect width="{w}" height="{h}" rx="12" fill="url(#gp)"/>\n{body}\n</svg>\n'
    )


def corners(x, y, w, h, s=16):
    d = ""
    for cx, cy, dx, dy in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]:
        d += f"M{cx+dx*s},{cy} L{cx},{cy} L{cx},{cy+dy*s} "
    return f'<path d="{d}" fill="none" stroke="{G}" stroke-width="2.2"/>'


def panel(x, y, w, h, label):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{PANEL}" stroke="{G}" stroke-opacity=".35"/>'
    s += f'<circle cx="{x+18}" cy="{y+18}" r="4.5" fill="{G}"/><circle cx="{x+34}" cy="{y+18}" r="4.5" fill="{W}"/><circle cx="{x+50}" cy="{y+18}" r="4.5" fill="#1b2a20"/>'
    s += f'<text x="{x+68}" y="{y+22}" font-size="11.5" class="mono" fill="{MUTED}">{esc(label)}</text>'
    s += f'<line x1="{x}" y1="{y+34}" x2="{x+w}" y2="{y+34}" stroke="{G}" stroke-opacity=".2"/>'
    return s


def fmt(d):
    return f"{d:%b} {d.day}"


def thousands(n):
    return f"{n:,}".replace(",", ".")


# ---------------------------------------------------------------- data
def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-gen"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    if "errors" in res:
        raise RuntimeError(res["errors"])
    return res["data"]


QUERY = """
query($login:String!){ user(login:$login){
  createdAt
  followers{ totalCount }
  contributionsCollection{ contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } } }
  repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
    totalCount
    nodes{ stargazerCount languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
  }
}}"""


def live_data():
    u = gql(QUERY, {"login": USER})["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = {}
    for wk in cal["weeks"]:
        for d in wk["contributionDays"]:
            days[date.fromisoformat(d["date"])] = d["contributionCount"]
    langs = {}
    stars = 0
    for r in u["repositories"]["nodes"]:
        stars += r["stargazerCount"]
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return dict(
        total=cal["totalContributions"], days=days, repos=u["repositories"]["totalCount"],
        stars=stars, langs=langs, today=date.today(), note="data live dari GitHub API", snapshot=False,
    )


def snapshot_data():
    today = date(2026, 10, 31)
    days = {today - timedelta(days=i): 1 for i in range(4)}  # Oct 28 - Oct 31 (dari screenshot)
    return dict(
        total=125, days=days, repos=4, stars=0,
        langs={"HTML": 3, "CSS": 3, "JavaScript": 2, "PHP": 1},
        today=today, note="snapshot awal, otomatis live setelah workflow berjalan", snapshot=True,
        first_label="Jun 2",
    )


def streaks(days, today):
    cur, d = 0, today
    if days.get(d, 0) == 0:
        d -= timedelta(days=1)
    end = d
    while days.get(d, 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    cur_range = (d + timedelta(days=1), end) if cur else None
    best, run, best_r, start = 0, 0, None, None
    for d in sorted(days):
        if days[d] > 0:
            if run == 0:
                start = d
            run += 1
            if run > best:
                best, best_r = run, (start, d)
        else:
            run = 0
    return cur, cur_range, best, best_r


# ---------------------------------------------------------------- stats.svg
def ring_deco(cx, cy, r, dur, rev=False):
    c = 2 * math.pi * r
    a, b = ("360", "0") if rev else ("0", "360")
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{G}" stroke-opacity=".18" stroke-width="3"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{G}" stroke-width="3" stroke-linecap="round" stroke-dasharray="{c*0.28:.1f} {c:.1f}">'
        f'<animateTransform attributeName="transform" type="rotate" from="{a} {cx} {cy}" to="{b} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/></circle>'
    )


GLYPH = {
    "repo": f'<path d="M-9 -11 H7 A3 3 0 0 1 10 -8 V10 H-6 A3 3 0 0 1 -9 7 Z M-9 7 A3 3 0 0 1 -6 4 H10" fill="none" stroke="{W}" stroke-width="2.4" stroke-linejoin="round"/>',
    "commit": f'<circle r="5.5" fill="none" stroke="{W}" stroke-width="2.4"/><path d="M-16 0 H-5.5 M5.5 0 H16" stroke="{W}" stroke-width="2.4" stroke-linecap="round"/>',
    "code": f'<path d="M-6 -8 L-14 0 L-6 8 M6 -8 L14 0 L6 8 M3 -11 L-3 11" fill="none" stroke="{W}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "star": f'<path d="M0 -12 L3.6 -3.8 L12 -3.2 L5.6 2.6 L7.6 11 L0 6.6 L-7.6 11 L-5.6 2.6 L-12 -3.2 L-3.6 -3.8 Z" fill="none" stroke="{W}" stroke-width="2.4" stroke-linejoin="round"/>',
}


def render_stats(d):
    Wd, H = 1000, 250
    b = panel(10, 10, 980, 230, f"github_stats.sh  ·  {USER}")
    langs = len(d["langs"])
    items = [
        ("PUBLIC REPOS", d["repos"], "repo", "repositori publik"),
        ("CONTRIBUTIONS", d["total"], "commit", "kontribusi setahun terakhir"),
        ("LANGUAGES", langs, "code", "bahasa pemrograman"),
        ("STARS EARNED", d["stars"], "star", "bintang yang didapat"),
    ]
    cw = 980 / 4
    for i, (lab, val, gl, sub) in enumerate(items):
        cx = 10 + cw * i + cw / 2
        if i:
            b += f'<line x1="{10+cw*i}" y1="64" x2="{10+cw*i}" y2="220" stroke="{G}" stroke-opacity=".18" stroke-dasharray="3 6"/>'
        b += ring_deco(cx, 112, 34, 6 + i, rev=i % 2 == 1)
        b += f'<g transform="translate({cx},112)">{GLYPH[gl]}</g>'
        b += (
            f'<text x="{cx}" y="190" text-anchor="middle" font-size="38" font-weight="800" class="sans" fill="{W}" filter="url(#gl)" opacity="0">'
            f'{thousands(val)}<animate attributeName="opacity" from="0" to="1" dur=".6s" begin="{.2+i*.2:.1f}s" fill="freeze"/></text>'
        )
        b += f'<text x="{cx}" y="212" text-anchor="middle" font-size="12" font-weight="700" class="mono" fill="{G}" letter-spacing="1.5">{lab}</text>'
        b += f'<text x="{cx}" y="228" text-anchor="middle" font-size="11" class="sans" fill="{MUTED}">{sub}</text>'
    b += corners(10, 10, 980, 230, 18)
    return wrap(Wd, H, b)


# ---------------------------------------------------------------- languages.svg
def render_langs(d):
    Wd, H = 1000, 330
    tot = sum(d["langs"].values()) or 1
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:6]
    items = [(n, v, v / tot * 100) for n, v in items]
    b = panel(10, 10, 980, 310, "top_languages.py")
    x0, bw = 50, 470
    for i, (n, v, p) in enumerate(items):
        y = 78 + i * 38
        col = LANG_COLORS.get(n, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        b += f'<circle cx="{x0}" cy="{y-5}" r="6" fill="{col}"/>'
        b += f'<text x="{x0+16}" y="{y}" font-size="14" font-weight="700" class="sans" fill="{W}">{esc(n)}</text>'
        b += f'<text x="{x0+bw+86}" y="{y}" text-anchor="start" font-size="13" font-weight="700" class="mono" fill="{col}">{p:.1f}%</text>'
        b += f'<rect x="{x0+120}" y="{y-12}" width="{bw-50}" height="12" rx="6" fill="#0c1a11"/>'
        fw = max(8, (bw - 50) * p / (items[0][2] or 1))
        b += (
            f'<rect x="{x0+120}" y="{y-12}" width="0" height="12" rx="6" fill="{col}" filter="url(#gl)">'
            f'<animate attributeName="width" from="0" to="{fw:.1f}" dur="1.1s" begin="{.15*i:.2f}s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>'
        )
    # donut
    cx, cy, r = 800, 178, 78
    c = 2 * math.pi * r
    b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0c1a11" stroke-width="26"/>'
    off = 0
    seg = ""
    for i, (n, v, p) in enumerate(items):
        col = LANG_COLORS.get(n, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        ln = c * p / 100
        seg += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="26" stroke-dasharray="{max(ln-3,1):.1f} {c:.1f}" stroke-dashoffset="{-off:.1f}" opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" dur=".5s" begin="{.2*i:.1f}s" fill="freeze"/></circle>'
        )
        off += ln
    b += f'<g transform="rotate(-90 {cx} {cy})">{seg}<animateTransform attributeName="transform" type="rotate" from="-90 {cx} {cy}" to="270 {cx} {cy}" dur="40s" repeatCount="indefinite"/></g>'
    b += f'<circle cx="{cx}" cy="{cy}" r="52" fill="{PANEL}" stroke="{G}" stroke-opacity=".3"/>'
    b += f'<text x="{cx}" y="{cy-2}" text-anchor="middle" font-size="30" font-weight="800" class="sans" fill="{W}">{len(d["langs"])}</text>'
    b += f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-size="11" font-weight="700" class="mono" fill="{G}" letter-spacing="1.5">LANGS</text>'
    unit = "berdasarkan jumlah project yang memakainya" if d["snapshot"] else "berdasarkan ukuran kode di repositori publik"
    b += f'<text x="50" y="302" font-size="11" class="mono" fill="{MUTED}">// {esc(unit)}</text>'
    b += corners(10, 10, 980, 310, 18)
    return wrap(Wd, H, b)


# ---------------------------------------------------------------- streak.svg
def render_streak(d):
    Wd, H = 1000, 300
    cur, cur_r, best, best_r = streaks(d["days"], d["today"])
    cur_lab = f"{fmt(cur_r[0])} – {fmt(cur_r[1])}" if cur_r else "belum ada streak"
    best_lab = f"{fmt(best_r[0])} – {fmt(best_r[1])}" if best_r else "-"
    first = d.get("first_label")
    if not first:
        ds = [x for x in sorted(d["days"]) if d["days"][x] > 0]
        first = fmt(ds[0]) if ds else "-"
    b = panel(10, 10, 980, 280, "streak_tracker.log")
    cols = [(180, "TOTAL CONTRIBUTIONS", thousands(d["total"]), f"{first} – Present"),
            (820, "LONGEST STREAK", str(best), best_lab)]
    for cx, lab, num, sub in cols:
        b += f'<text x="{cx}" y="140" text-anchor="middle" font-size="54" font-weight="800" class="sans" fill="{W}" filter="url(#gl)">{num}</text>'
        b += f'<text x="{cx}" y="180" text-anchor="middle" font-size="14" font-weight="700" class="mono" fill="{G}" letter-spacing="1.5">{lab}</text>'
        b += f'<text x="{cx}" y="206" text-anchor="middle" font-size="13" class="sans" fill="{W}">{esc(sub)}</text>'
    # center ring
    cx, cy, r = 500, 150, 70
    c = 2 * math.pi * r
    b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#0c1a11" stroke-width="10"/>'
    b += (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{G}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{c:.1f}" stroke-dashoffset="{c:.1f}" transform="rotate(-90 {cx} {cy})" filter="url(#gl)">'
        f'<animate attributeName="stroke-dashoffset" from="{c:.1f}" to="0" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 .7 .3 1"/></circle>'
    )
    b += (
        f'<g transform="translate({cx},{cy-r})"><path d="M0 -20 C10 -10 12 -2 6 6 C4 2 2 0 0 0 C-2 2 -6 4 -6 10 C-14 2 -8 -10 0 -20 Z" fill="{G}" stroke="{BG}" stroke-width="3" paint-order="stroke">'
        f'<animateTransform attributeName="transform" type="scale" values="1 1;1.12 1.18;1 1" dur="1.2s" repeatCount="indefinite" additive="sum"/></path></g>'
    )
    b += f'<text x="{cx}" y="{cy+16}" text-anchor="middle" font-size="52" font-weight="800" class="sans" fill="{W}">{cur}</text>'
    b += f'<text x="{cx}" y="{cy+r+34}" text-anchor="middle" font-size="14" font-weight="700" class="mono" fill="{G}" letter-spacing="1.5">CURRENT STREAK</text>'
    b += f'<text x="{cx}" y="{cy+r+56}" text-anchor="middle" font-size="13" class="sans" fill="{W}">{esc(cur_lab)}</text>'
    b += f'<line x1="340" y1="60" x2="340" y2="262" stroke="{G}" stroke-opacity=".2" stroke-dasharray="3 6"/><line x1="660" y1="60" x2="660" y2="262" stroke="{G}" stroke-opacity=".2" stroke-dasharray="3 6"/>'
    b += corners(10, 10, 980, 280, 18)
    return wrap(Wd, H, b)


# ---------------------------------------------------------------- activity.svg
def render_activity(d):
    Wd, H = 1000, 270
    today = d["today"]
    start = today - timedelta(days=(today.weekday() + 1) % 7) - timedelta(weeks=52)
    ox, oy, pitch, cs = 66, 82, 17, 13
    pal = ["#0d1a12", "#0f5a2e", "#12a050", "#00d95f", "#7dffb0"]

    def lvl(n):
        return 0 if n == 0 else 1 if n < 3 else 2 if n < 6 else 3 if n < 10 else 4

    b = panel(10, 10, 980, 250, "contribution_graph.sh")
    b += f'<text x="{Wd-30}" y="32" text-anchor="end" font-size="12" font-weight="700" class="mono" fill="{G}">{thousands(d["total"])} contributions · 12 bulan terakhir</text>'
    rnd = random.Random(5)
    last_m = None
    last_w = -9
    cells = ""
    for w in range(53):
        wd = start + timedelta(weeks=w)
        if wd.month != last_m and w - last_w >= 3:
            last_w = w
            b += f'<text x="{ox+w*pitch}" y="{oy-12}" font-size="11" class="mono" fill="{MUTED}">{wd:%b}</text>'
        last_m = wd.month
        for dd in range(7):
            day = wd + timedelta(days=dd)
            if day > today:
                continue
            n = d["days"].get(day, 0)
            l = lvl(n)
            x, y = ox + w * pitch, oy + dd * pitch
            if l:
                cells += (
                    f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="3" fill="{pal[l]}" filter="url(#gl)">'
                    f'<animate attributeName="opacity" values="1;.55;1" dur="{rnd.uniform(2.5,5):.1f}s" begin="-{rnd.uniform(0,4):.1f}s" repeatCount="indefinite"/></rect>'
                )
            else:
                cells += f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="3" fill="{pal[0]}" stroke="{G}" stroke-opacity=".08"/>'
    for i, nm in [(1, "Sen"), (3, "Rab"), (5, "Jum")]:
        b += f'<text x="{ox-10}" y="{oy+i*pitch+11}" text-anchor="end" font-size="10.5" class="mono" fill="{MUTED}">{nm}</text>'
    b += cells
    # scan sweep
    b += (
        f'<rect x="{ox}" y="{oy-4}" width="40" height="{7*pitch+6}" fill="{G}" opacity=".10">'
        f'<animate attributeName="x" values="{ox-40};{ox+53*pitch};{ox-40}" dur="9s" repeatCount="indefinite"/></rect>'
    )
    ly = oy + 7 * pitch + 22
    b += f'<text x="{ox}" y="{ly+11}" font-size="11" class="mono" fill="{MUTED}">{esc(d["note"])}</text>'
    lx = Wd - 30 - (5 * 20 + 70)
    b += f'<text x="{lx-8}" y="{ly+11}" text-anchor="end" font-size="11" class="mono" fill="{MUTED}">sedikit</text>'
    for i, c in enumerate(pal):
        b += f'<rect x="{lx+i*20}" y="{ly}" width="{cs}" height="{cs}" rx="3" fill="{c}"/>'
    b += f'<text x="{lx+5*20+4}" y="{ly+11}" font-size="11" class="mono" fill="{MUTED}">banyak</text>'
    b += corners(10, 10, 980, 250, 18)
    return wrap(Wd, H, b)


def main():
    data = None
    if TOKEN:
        try:
            data = live_data()
            print("mode: live")
        except Exception as e:  # noqa
            print("gagal ambil data live:", e, file=sys.stderr)
            if os.environ.get("GITHUB_ACTIONS"):
                sys.exit(1)
    if data is None:
        data = snapshot_data()
        print("mode: snapshot")
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("stats.svg", render_stats), ("languages.svg", render_langs),
                     ("streak.svg", render_streak), ("activity.svg", render_activity)]:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(fn(data))
    print("selesai")


if __name__ == "__main__":
    main()
