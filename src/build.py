#!/usr/bin/env python3
"""Build radiowheel.cold.fyi - The Radio Wheel, a cited independent guide to Rockstar Games' music.

    python3 build.py            # writes the site to OUT
    STRICT=1 python3 build.py   # also fails on [[GAP:]] markers or unknown footnote keys

Inputs (R = the report folder):
  R/parts/NN-slug.md       one section each, starting "## Title"; footnotes as [^key]
  R/frag/*-sources.tsv     key <TAB> Publisher: Title <TAB> URL
  R/frag/tracks-*.json     every song on every station {game, station, artist, title, year, added, removed, note, source}
  R/frag/stations-*.json   station facts {game, station, genre, host, ...}
  R/frag/talk.json, hosts.json, lore.json, removals.json, circoloco-releases.json, gta6.json, online.json, people.json
  R/frag/*-glossary.json, *-timeline.json, *-faq.json, *-resources.json
  R/quiz.json, R/seo.json, R/gaps.json, R/corrections.json (optional)
Outputs: hub with a radio wheel per game, one page per section, one page per station, /stations/, /songs/,
/removed/, /all/, /glossary/, /sources/, /corrections/, 404, sitemap, robots, llms.txt and JSON/CSV copies of every dataset.
"""
import csv, glob, html, io, json, math, os, re, sys, datetime
import markdown
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_pixel  # noqa: E402
META_PIXEL = "2368576097306858"  # cold.fyi Deep Dives pixel; footer note links thirdpolararch.com/privacy

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.environ.get("RW_REPORT", "/home/claude/reports/selector")
OUT = os.environ.get("RW_OUT", "/home/claude/radiowheel")
DOMAIN = "radiowheel.cold.fyi"
SITE = f"https://{DOMAIN}"
NAME = "The Radio Wheel"
NO = 10
PUBLISHED = "2026-11-15"
STRICT = os.environ.get("STRICT") == "1"
E = lambda s: html.escape(str(s if s is not None else ""), quote=True)
slugify = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower().replace("&", " and ").replace("'", "")).strip("-")


URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


def src_url(v):
    """Data rows hold either a bare URL or a whole citation string; return the first URL in it."""
    m = URL_RE.search(str(v or ""))
    return m.group(0).rstrip(".,;") if m else ""


def src_title(v):
    t = re.split(r"\s+-\s+(?:last modified|accessed|undated|\d{4}-\d{2}|https?://)", str(v or ""))[0]
    t = re.sub(r"\s*\((?:per [^()]*(?:\([^()]*\))?[^()]*)\)", "", t).strip(" -")
    return t if t and not t.startswith("http") else ""




def J(p, default=None):
    p = os.path.join(R, p)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def jl(pattern):
    out = []
    for f in sorted(glob.glob(f"{R}/frag/{pattern}")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as ex:
            sys.exit(f"bad json {f}: {ex}")
        out += d if isinstance(d, list) else []
    return out


# ------------------------------------------------------------ sources
src, clash = {}, []
for f in sorted(glob.glob(f"{R}/frag/*-sources.tsv")):
    for ln in open(f, encoding="utf-8"):
        parts = ln.rstrip("\n").split("\t")
        if len(parts) < 3 or not parts[0].strip():
            continue
        k, t, u = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if k in src and src[k][1] != u:
            clash.append(k)
        src.setdefault(k, (t, u))

# ------------------------------------------------------------ games and stations
GAMES = [  # key, display, short, year, city
    ("gta1", "Grand Theft Auto", "GTA", "1997", "Liberty City, San Andreas, Vice City"),
    ("london", "GTA: London 1969", "London", "1999", "London"),
    ("gta2", "Grand Theft Auto 2", "GTA 2", "1999", "Anywhere City"),
    ("gta3", "Grand Theft Auto III", "GTA III", "2001", "Liberty City"),
    ("vc", "Grand Theft Auto: Vice City", "Vice City", "2002", "Vice City"),
    ("sa", "Grand Theft Auto: San Andreas", "San Andreas", "2004", "San Andreas"),
    ("lcs", "GTA: Liberty City Stories", "LCS", "2005", "Liberty City"),
    ("vcs", "GTA: Vice City Stories", "VCS", "2006", "Vice City"),
    ("gta4", "Grand Theft Auto IV and Episodes", "GTA IV", "2008", "Liberty City"),
    ("ctw", "GTA: Chinatown Wars", "Chinatown Wars", "2009", "Liberty City"),
    ("gta5", "Grand Theft Auto V and GTA Online", "GTA V", "2013", "Los Santos"),
    ("gta6", "Grand Theft Auto VI", "GTA VI", "2026", "Leonida"),
]
GK = {g[0]: g for g in GAMES}
GORDER = {g[0]: i for i, g in enumerate(GAMES)}


def game_key(raw):
    s = (raw or "").strip()
    if not s:
        return None
    if re.search(r"\bVI\b|GTA 6|\b6\b", s): return "gta6"
    if "London" in s: return "london"
    if re.search(r"Grand Theft Auto 2|GTA 2\b", s): return "gta2"
    if "Chinatown" in s: return "ctw"
    if "Vice City Stories" in s: return "vcs"
    if "Liberty City Stories" in s: return "lcs"
    if re.search(r"\bIV\b|Lost and Damned|Gay Tony|Episodes from Liberty City", s): return "gta4"
    if re.search(r"\bV\b|Online", s): return "gta5"
    if "San Andreas" in s: return "sa"
    if "Vice City" in s: return "vc"
    if re.search(r"\bIII\b", s): return "gta3"
    if re.search(r"^(Grand Theft Auto|GTA)( \(1997\))?$", s): return "gta1"
    return None


def skey(name):
    name = re.sub(r"\(.*?\)", "", name.split(" - ")[0])
    k = re.sub(r"[^a-z0-9]", "", name.lower())
    k = re.sub(r"^the", "", k)
    return k


STATION_ALIASES = {"musiclocker": "musiclockerradio", "worldwidefm": "worldwidefm", "doublecleffm": "doublecleffm",
                   "blondedlossantos978fm": "blondedlossantos978fm", "blondedlossantos": "blondedlossantos978fm",
                   "kultfm": "kultfm991", "massivebsoundsystem969": "massiveb", "massiveb": "massiveb",
                   "jazznation1085": "jazznationradio1085", "jazznationradio": "jazznationradio1085",
                   "lossantosundergroundradio": "lossantosundergroundradio", "selfradio": "selfradio",
                   "csr1032": "csr1039", "flashback956": "flashback956", "westcoasttalkradio": "wctr", "westcoasttalkradiowctr": "wctr",
                   "headradiofm": "headradio", "osmosisradio": "osmosisfm", "gamefm": "gameradio", "lcfr": "libertycityfreeradio",
                   "if99internationalfunk": "internationalfunk99", "if99": "internationalfunk99", "libertyrockradio978": "libertyrockradio", "plr": "publiclibertyradio",
                   "wkttradio": "wktttalkradio", "wktt": "wktttalkradio", "blainecountytalkradio": "blainecountyradio", "kchat": "kchat", "vcpr": "vcpr", "chatterboxfm109": "chatterboxfm"}
GAME_ALIASES = {("lcs", "doubleclefm"): "doubleclefffm"}


def ckey(name, game=None):
    k = skey(name)
    k = STATION_ALIASES.get(k, k)
    return GAME_ALIASES.get((game, k), k)


raw_tracks = jl("tracks-*.json")
station_meta_rows = jl("stations-*.json")
talk = jl("talk.json")
hosts = jl("hosts.json")
lore = jl("lore.json")
removals = jl("removals.json")
circoloco = jl("circoloco-releases.json")
gta6 = jl("gta6.json")
online = jl("online.json")
people = jl("people.json")

stations = {}  # (game, ckey) -> dict


def station(game, name, create=True):
    k = (game, ckey(name, game))
    if k not in stations and not create:
        return None
    if k not in stations:
        stations[k] = {"game": game, "name": re.sub(r"\s*\(.*?\)", "", name.split(" - ")[0]).strip(), "key": k[1], "tracks": [], "seen": set(), "meta": {}, "talk": [], "hosts": []}
    return stations[k]


unknown_games, dropped_meta = set(), []
for r in raw_tracks:
    g = game_key(r.get("game"))
    if not g:
        unknown_games.add(r.get("game"))
        continue
    st = station(g, r["station"])
    tk = (re.sub(r"\W", "", (r.get("artist") or "").lower()), re.sub(r"\W", "", (r.get("title") or "").lower()))
    if tk in st["seen"]:
        continue
    st["seen"].add(tk)
    st["tracks"].append({k: (r.get(k) or "") for k in ("artist", "title", "year", "added", "removed", "note", "source")} | {"edition": r.get("game", "")})
for r in station_meta_rows:
    g = game_key(r.get("game"))
    if not g or not r.get("station"):
        continue
    st = station(g, r["station"], create=(g == "gta6"))
    if not st:
        dropped_meta.append((g, r["station"]))
        continue
    for k in ("genre", "host", "host_voice", "notes", "source", "year", "year_added"):
        if r.get(k) and not st["meta"].get(k):
            st["meta"][k] = r[k]
for r in talk:
    g = game_key(r.get("game"))
    if g and r.get("station") and not r["station"].startswith("On-demand"):
        station(g, r["station"])["talk"].append(r)
for r in hosts:
    g = game_key(r.get("game"))
    if g and r.get("station"):
        station(g, r["station"])["hosts"].append(r)

SL, SRC_TITLES = [], {}
for (g, k), st in stations.items():
    st["slug"] = f"{g}-{slugify(st['name'])}"
    st["is_talk"] = bool(st["talk"]) or all(t["artist"].lower() == "talk radio" for t in st["tracks"]) and bool(st["tracks"])
    st["songs"] = [t for t in st["tracks"] if t["artist"].lower() != "talk radio"]
    st["n_removed"] = sum(1 for t in st["songs"] if t["removed"])
    st["n_added"] = sum(1 for t in st["songs"] if t["added"])
    raw = [t["source"] for t in st["tracks"]] + [st["meta"].get("source")] + [x.get("source") for x in st["talk"] + st["hosts"]]
    st["sources"] = sorted({src_url(v) for v in raw if src_url(v)})
    for v in raw:
        if src_url(v) and src_title(v):
            SRC_TITLES.setdefault(src_url(v), src_title(v))
    SL.append(st)
SL.sort(key=lambda s: (GORDER[s["game"]], s["name"].lower()))
BY_GAME = {g[0]: [s for s in SL if s["game"] == g[0]] for g in GAMES}
SONGS = [dict(t, game=s["game"], station=s["name"], station_slug=s["slug"]) for s in SL for t in s["songs"]]
N_SONGS = len(SONGS)
N_REMOVED = sum(1 for t in SONGS if t["removed"])


def host_line(st):
    h = st["meta"].get("host") or ", ".join(dict.fromkeys(x.get("host_character", "") for x in st["hosts"] if x.get("host_character")))
    return h


def mono(name):
    stop = {"fm", "radio", "the", "station", "sound", "sounds", "and"}
    words = re.findall(r"[A-Za-z0-9']+", name)
    t = [w for w in words if w.lower() not in stop and not re.fullmatch(r"[\d.]+", w)] or words
    if len(t) == 1:
        return t[0][:4].upper()
    return "".join(w[0] for w in t[:3]).upper()


# ------------------------------------------------------------ editorial data
glossary = sorted({g["term"].lower(): g for g in jl("*-glossary.json")}.values(), key=lambda g: g["term"].lower())
timeline = sorted(jl("*-timeline.json"), key=lambda t: str(t.get("date", "")))
resources = list({r["url"]: r for r in jl("*-resources.json")}.values())
quiz = J("quiz.json", [])
seo = J("seo.json", {})
gaps = J("gaps.json", [])
corrections = J("corrections.json", [])

parts = sorted(glob.glob(f"{R}/parts/*.md"))
lede_md = open(parts[0], encoding="utf-8").read() if parts else "# lede\n"
sections = []
for p in parts[1:]:
    md = open(p, encoding="utf-8").read()
    md = re.sub(r"^\[\[DIAGRAM-IDEA:.*?\]\]\s*$", "", md, flags=re.M)
    md = re.sub(r"^\[\^[^\]]+\]:.*$", "", md, flags=re.M)
    m = re.match(r"\s*##\s+(.+)", md)
    if not m:
        sys.exit(f"{p}: must start with '## Title'")
    slug = re.sub(r"^\d+-", "", os.path.basename(p)[:-3])
    sections.append({"slug": slug, "title": m.group(1).strip(), "md": md[m.end():].strip(), "file": os.path.basename(p)})
SLUGS = [s["slug"] for s in sections]
for i, s in enumerate(sections):
    s["freq"] = f"{88.1 + i * 1.8:.1f}"
faq_by_slug = {}
for f in sorted(glob.glob(f"{R}/frag/*-faq.json")):
    for x in json.load(open(f, encoding="utf-8")):
        if x.get("section"):
            faq_by_slug.setdefault(x["section"], []).append(x)

# ------------------------------------------------------------ footnotes, numbered globally by first use
order, missing = {}, set()


def num(k):
    if k not in src:
        missing.add(k)
        return None
    u = src[k][1]
    if u not in order:
        order[u] = (len(order) + 1, k)
    return order[u][0]


def footnotes(md, page_refs):
    def rep(m):
        n = num(m.group(1))
        if n is None:
            return ""
        page_refs.add(n)
        return f'<sup class="fn"><a href="#src-{n}" data-n="{n}">{n}</a></sup>'
    out = re.sub(r"\[\^([A-Za-z0-9_.:-]+)\]", rep, md)
    return out.replace("</sup><sup class=\"fn\">", "</sup><sup class=\"fn\"><span class=\"fs\">,</span>")


MDX = markdown.Markdown(extensions=["tables", "sane_lists", "attr_list"])


def mdhtml(s):
    MDX.reset()
    return MDX.convert(s)


def heading_ids(h):
    used = set()

    def rep(m):
        lvl, txt = m.group(1), m.group(2)
        base = re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", txt).lower()).strip("-")[:70] or "h"
        sid, i = base, 2
        while sid in used:
            sid, i = f"{base}-{i}", i + 1
        used.add(sid)
        return f'<h{lvl} id="{sid}">{txt}<a class="anchor" href="#{sid}" aria-label="Link to this">#</a></h{lvl}>'
    return re.sub(r"<h([34])>(.*?)</h\1>", rep, h)


SHORT_RE = re.compile(r"^\*\*The short version:\*\*\s*(.+?)\n\n", re.S)


# ------------------------------------------------------------ modules
def mod(kicker, title, intro, inner, id_=""):
    return (f'<section class="mod"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}><div class="mod-head"><p class="kick">{E(kicker)}</p><h3>{E(title)}</h3>'
            f'{f"<p>{E(intro)}</p>" if intro else ""}</div>{inner}</section>')


def js_json(o):
    return json.dumps(o, ensure_ascii=False).replace("</", "<\\/")


def srcu(u):
    u = src_url(u)
    return f' <a class="s" href="{E(u)}" rel="noopener" target="_blank">source</a>' if u else ""


def chips(name, values, attr):
    return (f'<div class="chips" role="group" aria-label="{E(name)}"><button type="button" data-{attr}="" aria-pressed="true">All</button>'
            + "".join(f'<button type="button" data-{attr}="{E(v)}" aria-pressed="false">{E(lbl)}</button>' for v, lbl in values) + "</div>")


def station_cards(game):
    sts = BY_GAME.get(game, [])
    if not sts:
        return ""
    cards = "".join(
        f'<a class="scard{" talk" if s["is_talk"] else ""}" href="/stations/{s["slug"]}/"><span class="mono">{E(mono(s["name"]))}</span><b>{E(s["name"])}</b>'
        f'<span class="g">{E(s["meta"].get("genre") or ("Talk radio" if s["is_talk"] else ""))}</span>'
        f'<span class="n">{len(s["songs"]) or ""}{" songs" if s["songs"] else ""}{f" · {s[chr(110)+chr(95)+chr(114)+chr(101)+chr(109)+chr(111)+chr(118)+chr(101)+chr(100)]} pulled" if s["n_removed"] else ""}</span></a>'
        for s in sts)
    g = GK[game]
    return mod(f"{g[2]} · {g[3]}", f"Every station in {g[1]}", "", f'<div class="sgrid">{cards}</div>', f"stations-{game}")


def m_stations(arg=""):
    if arg:
        return station_cards(arg)
    return "".join(station_cards(g[0]) for g in GAMES)


def m_songs(arg=""):
    gch = chips("Game", [(g[0], g[2]) for g in GAMES if any(s["songs"] for s in BY_GAME[g[0]])], "g")
    inner = (f'<div class="tools"><label class="sr" for="sf-q">Search every song</label><input id="sf-q" type="search" placeholder="Artist, song or station: Hall & Oates, Wildstyle, Kult FM..." autocomplete="off">'
             f'{gch}<label class="tog"><input type="checkbox" id="sf-rm"> Pulled songs only</label><span class="cnt" id="sf-cnt"></span></div>'
             '<div class="tbl"><table class="songs"><thead><tr><th>Artist</th><th>Song</th><th>Station</th><th>Game</th></tr></thead><tbody id="sf-list"></tbody></table></div>'
             '<p class="more" id="sf-more" hidden><button type="button" id="sf-btn">Show more</button></p>'
             '<noscript><p>The song finder needs JavaScript. Every station page lists its songs, and <a href="/tracks.json">tracks.json</a> has them all.</p></noscript>')
    return mod("Song finder", f"{N_SONGS:,} songs on {sum(1 for s in SL if s['songs'])} stations", "", inner, "songs")


def m_removed(arg=""):
    rows = sorted([t for t in SONGS if t["removed"]], key=lambda t: (GORDER[t["game"]], t["station"].lower(), t["artist"].lower()))
    body = "".join(f'<tr data-g="{E(t["game"])}"><td>{E(t["artist"])}</td><td>{E(t["title"])}</td><td><a href="/stations/{t["station_slug"]}/">{E(t["station"])}</a></td>'
                   f'<td class="k">{E(GK[t["game"]][2])}</td><td>{E(t["removed"])}{srcu(t["source"])}</td></tr>' for t in rows)
    gch = chips("Game", [(g[0], g[2]) for g in GAMES if any(t["game"] == g[0] for t in rows)], "g")
    ev = "".join(f'<li><span class="d">{E(r.get("date", ""))}</span><b>{E(r.get("game", ""))}</b> {E(r.get("what_removed", ""))}'
                 + (f' <span class="tag">{E(r["count"])}</span>' if r.get("count") else "") + f'{srcu(r.get("source"))}</li>' for r in sorted(removals, key=lambda r: str(r.get("date", ""))))
    return mod("Pulled from the dial", f"{len(rows)} songs that left the games", "",
               (f'<ol class="tl ev">{ev}</ol>' if ev else "") + gch + f'<div class="tbl"><table class="songs" id="rm-tbl"><thead><tr><th>Artist</th><th>Song</th><th>Station</th><th>Game</th><th>Removed</th></tr></thead><tbody id="rm-list">{body}</tbody></table></div>', "removed")


def m_talk(arg=""):
    rows = sorted(talk, key=lambda r: (GORDER.get(game_key(r.get("game")) or "gta6", 99), r.get("station", ""), r.get("show", "")))
    if not rows:
        return ""
    gch = chips("Game", [(g[0], g[2]) for g in GAMES if any(game_key(r.get("game")) == g[0] for r in rows)], "g")
    items = "".join(
        f'<li data-g="{E(game_key(r.get("game")) or "")}" data-s="{E(" ".join(str(r.get(k, "")) for k in ("show", "host", "voiced_by", "station", "satirises")).lower())}">'
        f'<p class="lcd-s">{E(r.get("station", ""))} · {E(GK.get(game_key(r.get("game")) or "", ("", "", r.get("game", "")))[2])}</p><b>{E(r.get("show", ""))}</b>'
        f'<p>{E(r.get("host", ""))}{(" - voiced by " + E(r["voiced_by"])) if r.get("voiced_by") else ""}</p>'
        + (f'<p class="fmt">{E(r["format"])}</p>' if r.get("format") else "")
        + (f'<p class="sat"><span>Sends up</span> {E(r["satirises"])}</p>' if r.get("satirises") else "")
        + (f'<p class="rec"><span>Recurring</span> {E(r["recurring"] if isinstance(r["recurring"], str) else ", ".join(r["recurring"]))}</p>' if r.get("recurring") else "")
        + f'{srcu(r.get("source"))}</li>' for r in rows)
    return mod("Talk radio directory", f"{len(rows)} talk shows, every game", "", f'<div class="tools"><label class="sr" for="tk-q">Search talk shows</label><input id="tk-q" type="search" placeholder="Lazlow, Chakra Attack, WCTR, conspiracy..." autocomplete="off">{gch}</div><ul class="talkgrid" id="tk-list">{items}</ul>', "talk")


def m_hosts(arg=""):
    rows = sorted(hosts, key=lambda r: (GORDER.get(game_key(r.get("game")) or "gta6", 99), r.get("station", "")))
    if not rows:
        return ""
    body = "".join(f'<tr data-g="{E(game_key(r.get("game")) or "")}" data-s="{E(" ".join(str(r.get(k, "")) for k in ("host_character", "voiced_by", "station")).lower())}"><td>{E(r.get("host_character", ""))}</td><td>{E(r.get("voiced_by", ""))}</td>'
                   f'<td>{E(r.get("station", ""))}</td><td class="k">{E(GK.get(game_key(r.get("game")) or "", ("", "", r.get("game", "")))[2])}</td><td>{E(r.get("notes", ""))}{srcu(r.get("source"))}</td></tr>' for r in rows)
    gch = chips("Game", [(g[0], g[2]) for g in GAMES if any(game_key(r.get("game")) == g[0] for r in rows)], "g")
    return mod("Hosts and voices", f"{len(rows)} DJs and hosts", "", f'<div class="tools"><label class="sr" for="hs-q">Search hosts</label><input id="hs-q" type="search" placeholder="Iggy Pop, Lazlow, Gilles Peterson..." autocomplete="off">{gch}</div><div class="tbl"><table class="songs"><thead><tr><th>Host</th><th>Voiced by</th><th>Station</th><th>Game</th><th>Notes</th></tr></thead><tbody id="hs-list">{body}</tbody></table></div>', "hosts")


def m_lore(arg=""):
    if not lore:
        return ""
    kinds = sorted({r.get("kind", "") for r in lore if r.get("kind")})
    items = "".join(f'<li data-k="{E(r.get("kind", ""))}" data-s="{E((str(r.get("item", "")) + " " + str(r.get("detail", ""))).lower())}"><p class="lcd-s">{E(r.get("kind", ""))} · {E(GK.get(game_key(r.get("game")) or "", ("", "", r.get("game", "")))[2])}</p>'
                    f'<b>{E(r.get("item", ""))}</b><p>{E(r.get("detail", ""))}{srcu(r.get("source"))}</p></li>' for r in lore)
    return mod("Lore", f"{len(lore)} ads, fake bands, bulletins and easter eggs", "", f'<div class="tools"><label class="sr" for="lo-q">Search the lore</label><input id="lo-q" type="search" placeholder="Pißwasser, Love Fist, Sprunk..." autocomplete="off">{chips("Kind", [(k, k) for k in kinds], "k")}</div><ul class="talkgrid" id="lo-list">{items}</ul>', "lore")


def m_circoloco(arg=""):
    if not circoloco:
        return ""
    rows = sorted(circoloco, key=lambda r: (str(r.get("date", "")), str(r.get("cat", ""))))
    body = "".join(f'<tr data-s="{E((str(r.get("artist", "")) + " " + str(r.get("title", "")) + " " + str(r.get("cat", ""))).lower())}"><td class="k">{E(r.get("cat", ""))}</td><td>{E(r.get("date", ""))}</td><td>{E(r.get("artist", ""))}</td><td>{E(r.get("title", ""))}</td><td class="k">{E(r.get("format", ""))}{srcu(r.get("source"))}</td></tr>' for r in rows)
    return mod("Catalog", f"{len(rows)} CircoLoco Records releases", "", f'<div class="tools"><label class="sr" for="cl-q">Search the catalog</label><input id="cl-q" type="search" placeholder="Jamback, Seth Troxler, CLR..." autocomplete="off"></div><div class="tbl"><table class="songs"><thead><tr><th>Cat</th><th>Date</th><th>Artist</th><th>Title</th><th>Format</th></tr></thead><tbody id="cl-list">{body}</tbody></table></div>', "catalog")


STATUS_ORDER = {"official": 0, "reported": 1, "leak": 2, "rumour": 3, "rumor": 3}


def m_gta6(arg=""):
    if not gta6:
        return ""
    rows = sorted(gta6, key=lambda r: str(r.get("date", "")), reverse=True)
    sts = sorted({str(r.get("status", "")).lower() for r in rows}, key=lambda s: STATUS_ORDER.get(s, 9))
    items = "".join(f'<li data-k="{E(str(r.get("status", "")).lower())}"><span class="d">{E(r.get("date", ""))}</span><span class="st st-{E(str(r.get("status", "")).lower())}">{E(r.get("status", ""))}</span>'
                    f'<b>{E(r.get("item", ""))}</b> {E(r.get("detail", ""))}{srcu(r.get("source"))}</li>' for r in rows)
    return mod("GTA VI music tracker", f"{len(rows)} items, each marked official, reported, leak or rumour", "Official means Rockstar, Take-Two or the label said it. Everything else is labelled for what it is.",
               chips("Status", [(s, s) for s in sts], "k") + f'<ol class="tl six" id="six-list">{items}</ol>', "tracker")


def m_online(arg=""):
    if not online:
        return ""
    items = "".join(f'<li><span class="d">{E(r.get("date", ""))}</span><b>{E(r.get("update", ""))}</b> {E(r.get("music_partner", ""))} - {E(r.get("what_it_was", ""))}{srcu(r.get("source"))}</li>' for r in sorted(online, key=lambda r: str(r.get("date", ""))))
    return mod("GTA Online, update by update", f"{len(online)} music drops", "", f'<ol class="tl">{items}</ol>', "updates")


def m_people(arg=""):
    if not people:
        return ""
    body = "".join(f'<tr><td><b>{E(r.get("name", ""))}</b></td><td>{E(r.get("role", ""))}</td><td class="k">{E(r.get("years", ""))}</td><td>{E(", ".join(r["games"]) if isinstance(r.get("games"), list) else r.get("games", ""))}{srcu(r.get("source"))}</td></tr>' for r in people)
    return mod("Credits", f"{len(people)} people behind the radio", "", f'<div class="tbl"><table class="songs"><thead><tr><th>Name</th><th>Role</th><th>Years</th><th>Games</th></tr></thead><tbody>{body}</tbody></table></div>', "people")


def m_timeline(arg=""):
    eras = []
    for t in timeline:
        if t.get("era") and t["era"] not in eras:
            eras.append(t["era"])
    eras.sort()
    items = "".join(f'<li data-era="{E(t.get("era", ""))}"><span class="d">{E(t["date"])}</span><b>{E(t["label"])}</b> {E(t.get("detail", ""))}{srcu(t.get("source_url"))}</li>' for t in timeline)
    seg = '<div class="chips" role="group" aria-label="Era"><button type="button" data-era="" aria-pressed="true">All</button>' + "".join(f'<button type="button" data-era="{E(x)}" aria-pressed="false">{E(x)}</button>' for x in eras) + "</div>"
    return mod("Timeline", f"{len(timeline)} dates, 1997 to now", "", seg + f'<ol class="tl" id="tl-list">{items}</ol>', "timeline")


def m_glossary(arg=""):
    items = "".join(f'<li id="term-{E(slugify(g["term"]))}" data-s="{E((g["term"] + " " + g.get("definition", "")).lower())}"><dfn>{E(g["term"])}</dfn> {E(g.get("definition", ""))}'
                    + (f' <a class="s" href="/{E(g["section"])}/">read more</a>' if g.get("section") in SLUGS else "") + "</li>" for g in glossary)
    return mod("Glossary", f"{len(glossary)} terms", "", f'<div class="tools"><label class="sr" for="gl-q">Search the glossary</label><input id="gl-q" type="search" placeholder="sync licence, stinger, media stick..." autocomplete="off"></div><ul class="gl" id="gl-list">{items}</ul>', "glossary")


def m_resources(arg=""):
    items = "".join(f'<li><a href="{E(r["url"])}" rel="noopener" target="_blank">{E(r["title"])}</a> - {E(r.get("why", ""))}</li>' for r in resources)
    return mod("Further", "Where to go next", "", f'<ul class="res">{items}</ul>', "resources")


def m_quiz(arg=""):
    if not quiz:
        return ""
    return mod("Test yourself", f"{len(quiz)} questions", "", f'<div id="quiz"></div><script type="application/json" id="quiz-data">{js_json(quiz)}</script>', "quiz")


def m_gaps(arg=""):
    items = "".join(f"<li>{E(g)}</li>" for g in gaps) or "<li>None listed.</li>"
    return mod("Still unconfirmed", f"{len(gaps)} open questions", "Know the answer? hello@thirdpolararch.com", f"<ul>{items}</ul>", "gaps")


MODULES = {"stations": m_stations, "songs": m_songs, "removed": m_removed, "talk": m_talk, "hosts": m_hosts, "lore": m_lore, "circoloco": m_circoloco,
           "gta6": m_gta6, "online": m_online, "people": m_people, "timeline": m_timeline, "glossary": m_glossary, "resources": m_resources, "quiz": m_quiz, "gaps": m_gaps}


def modules(h):
    def rep(m):
        k, _, arg = m.group(1).strip().partition(":")
        if k not in MODULES:
            sys.exit(f"unknown module {k}")
        return MODULES[k](arg)
    h = re.sub(r"<p>\[\[MODULE:([a-z0-9:-]+)\]\]</p>", rep, h)
    return re.sub(r"\[\[MODULE:([a-z0-9:-]+)\]\]", rep, h)


# ------------------------------------------------------------ render sections
lede_refs = set()
lede_md = footnotes(re.sub(r"^#\s+.*\n", "", lede_md, count=1), lede_refs)
lede_html = modules(mdhtml(lede_md))
gap_left = []
for s in sections:
    refs = set()
    md = s["md"]
    m = SHORT_RE.match(md + "\n\n")
    s["short"] = re.sub(r"\[\^[^\]]+\]", "", m.group(1)).strip() if m else ""
    for g in re.findall(r"\[\[GAP:(.*?)\]\]", md):
        gap_left.append((s["slug"], g))
    md = re.sub(r"^\[\[GAP:.*?\]\]\s*$", "", md, flags=re.M)
    md = footnotes(md, refs)
    h = mdhtml(md)
    h = h.replace("<p><strong>The short version:</strong>", '<p class="short"><strong>The short version:</strong>', 1)
    h = heading_ids(h)
    h = modules(h)
    s["html"], s["refs"] = h, sorted(refs)
    s["words"] = len(re.sub(r"<[^>]+>", " ", h).split())
    s["mins"] = max(1, round(s["words"] / 230))
    s["h3"] = re.findall(r'<h3 id="([^"]+)">(.*?)<a class="anchor"', h)
if missing:
    msg = "unknown footnote keys: " + ", ".join(sorted(missing))
    if STRICT:
        sys.exit(msg)
    print("WARN", msg)
if gap_left and STRICT:
    sys.exit("GAP markers left: " + "; ".join(f"{a}: {b}" for a, b in gap_left))
def nice_url(u):
    m = re.match(r"https?://(?:www\.)?([^/]+)/(?:w/|wiki/)?(.*)", u)
    if not m:
        return u
    host, path = m.group(1), re.sub(r"[_-]+", " ", m.group(2).strip("/").split("/")[-1].split("?")[0])
    site = {"gta.wiki": "GTA Wiki", "gta.fandom.com": "GTA Wiki (Fandom)", "gtabase.com": "GTABase", "en.wikipedia.org": "Wikipedia", "grandtheftwiki.com": "Grand Theft Wiki"}.get(host, host)
    return f"{site}: {path}" if path else site


# station sources join the numbered list so every page can cite them
for st in SL:
    st["refs"] = []
    for u in st["sources"]:
        if u not in order:
            order[u] = (len(order) + 1, f"station:{st['slug']}")
            src.setdefault(f"station:{st['slug']}:{len(order)}", (SRC_TITLES.get(u) or nice_url(u), u))
        st["refs"].append(order[u][0])
URL_TITLE = {}
for k, (t, u) in src.items():
    if u not in URL_TITLE or URL_TITLE[u] == u:
        URL_TITLE[u] = t
nsrc = {n: (k, (URL_TITLE.get(u, u), u)) for u, (n, k) in order.items()}
WORDS = sum(s["words"] for s in sections) + len(re.sub(r"<[^>]+>", " ", lede_html).split())

# ------------------------------------------------------------ shell
CSS = open(os.path.join(HERE, "style.css"), encoding="utf-8").read()
JS = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
FONTS = [("Bungee", 400, "normal", "bungee-latin-400-normal"), ("VT323", 400, "normal", "vt323-latin-400-normal"),
         ("Source Serif 4", 400, "normal", "source-serif-4-latin-400-normal"), ("Source Serif 4", 400, "italic", "source-serif-4-latin-400-italic"),
         ("Source Serif 4", 600, "normal", "source-serif-4-latin-600-normal"),
         ("IBM Plex Mono", 400, "normal", "ibm-plex-mono-latin-400-normal"), ("IBM Plex Mono", 600, "normal", "ibm-plex-mono-latin-600-normal")]
FONT_CSS = "".join(f"@font-face{{font-family:'{f}';font-style:{st};font-weight:{w};font-display:swap;src:url(/fonts/{fn}.woff2) format('woff2')}}" for f, w, st, fn in FONTS)
STAMP = datetime.date.fromisoformat(os.environ.get("RW_UPDATED", PUBLISHED))
UPDATED = STAMP.strftime("%B %-d, %Y")


def wheel_svg(game, hidden=False):
    """The radio wheel, drawn from scratch: one wedge per station, a monogram in each, a hole for the readout."""
    sts = [s for s in BY_GAME[game] if s["songs"] or s["is_talk"] or game == "gta6"]
    n = len(sts)
    if n < 2:
        return ""
    cx = cy = 200
    ro, ri, gap = 192, 92, 1.6
    out, seen = [], {}
    monos = []
    for s in sts:
        m = mono(s["name"])
        if m in seen:
            words = [w for w in re.findall(r"[A-Za-z0-9']+", s["name"]) if w.lower() not in ("fm", "radio", "the")]
            m = (words[-1] if words else s["name"])[:4].upper()
            if m in seen:
                m = m[:3] + str(len(monos))
        seen[m] = 1
        monos.append(m)
    for i, s in enumerate(sts):
        a0 = -90 + i * 360 / n + gap / 2
        a1 = -90 + (i + 1) * 360 / n - gap / 2
        r0, r1 = math.radians(a0), math.radians(a1)
        large = 1 if (a1 - a0) > 180 else 0
        p = (f"M{cx + ro * math.cos(r0):.1f},{cy + ro * math.sin(r0):.1f} A{ro},{ro} 0 {large} 1 {cx + ro * math.cos(r1):.1f},{cy + ro * math.sin(r1):.1f} "
             f"L{cx + ri * math.cos(r1):.1f},{cy + ri * math.sin(r1):.1f} A{ri},{ri} 0 {large} 0 {cx + ri * math.cos(r0):.1f},{cy + ri * math.sin(r0):.1f}Z")
        am = math.radians((a0 + a1) / 2)
        rm = (ro + ri) / 2
        tx, ty = cx + rm * math.cos(am), cy + rm * math.sin(am)
        fs = 22 if n <= 10 else 18 if n <= 14 else 14 if n <= 19 else 11
        label = f'{s["name"]}: {s["meta"].get("genre") or ("talk radio" if s["is_talk"] else "")}'
        info = js_json({"n": s["name"], "g": s["meta"].get("genre") or ("Talk radio" if s["is_talk"] else ""), "h": host_line(s), "c": len(s["songs"])})
        out.append(f'<a href="/stations/{s["slug"]}/" class="wedge{" talk" if s["is_talk"] else ""}" data-info="{E(info)}" aria-label="{E(label)}">'
                   f'<path d="{p}"/><text x="{tx:.1f}" y="{ty:.1f}" style="font-size:{fs}px">{E(monos[i])}</text></a>')
    g = GK[game]
    n_songs = sum(len(s["songs"]) for s in BY_GAME[game])
    return (f'<div class="wheel" data-game="{game}"{" hidden" if hidden else ""}><svg viewBox="0 0 400 400" role="img" aria-label="Radio wheel for {E(g[1])}">'
            f'<circle cx="200" cy="200" r="198" class="rim"/>{"".join(out)}</svg>'
            f'<div class="lcd" aria-live="polite"><span class="l1">{E(g[2].upper())}</span><span class="l2">{n} stations</span><span class="l3">{f"{n_songs} songs" if n_songs else "out Nov 19, 2026"}</span></div></div>')


def tuner_strip():
    ticks = "".join(f'<span class="f{"  big" if f % 2 == 0 else ""}" style="left:{(f - 88) / 20 * 100:.2f}%">{f if f % 2 == 0 else ""}</span>' for f in range(88, 109))
    return f'<div class="tuner" aria-hidden="true"><div class="scale">{ticks}<i class="needle"></i></div><span class="band">FM</span></div>'


def head(title, desc, path, ld=None, robots="index, follow, max-image-preview:large"):
    canon = SITE + path
    lds = "".join(f'<script type="application/ld+json">{js_json(x)}</script>' for x in (ld or []))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{canon}"><meta name="robots" content="{robots}">
<meta name="theme-color" content="#0b0c10"><meta property="og:type" content="article"><meta property="og:site_name" content="cold.fyi">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="alternate" type="text/plain" href="/llms.txt" title="llms.txt">
<link rel="preload" href="/fonts/bungee-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/source-serif-4-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<script>try{{var t=localStorage.getItem('rw-theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{lds}<style>{FONT_CSS}{CSS}</style></head><body><a class="skip" href="#main">Skip to the text</a><div class="progress" id="progress" aria-hidden="true"></div>
<header class="mast"><span><a href="https://cold.fyi">cold.fyi</a><span class="sep">/</span><a href="/" class="nm">{NAME}</a></span><nav class="mnav"><a href="/stations/">Stations</a><a href="/songs/">Songs</a><a href="/gta-6/">GTA VI</a><button class="theme-btn" id="theme-btn" type="button">Night</button></nav></header>
"""


SISTERS = [("beam", "The Beam", "how laser shows work"), ("flip", "The Flip", "how sampling works"), ("groove", "The Groove", "how a vinyl record is made"), ("polo", "Polo", "how Coachella works"), ("wristband", "The Wristband", "how music festivals work"),
           ("lastcall", "Last Call", "how nightlife works"), ("showfile", "The Show File", "how a dance music show is made"),
           ("tickets", "The Ticket", "how a concert ticket gets from artist to fan"), ("airwaves", "The Airwaves", "every radio signal over a city"),
           ("noise", "The Noise", "every sound in a city"), ("streetcode", "Street Code", "every mark on the street"),
           ("works", "How a City Works", "the systems under every street"), ("penamnesty", "The Pens Went Away", "pharma swag")]


def foot():
    sis = "".join(f'<li><a href="https://{h}.cold.fyi/">{E(n)}</a> <span>- {E(d)}</span></li>' for h, n, d in SISTERS)
    return f"""<footer class="foot"><div class="foot-in"><p class="k">More deep dives from cold.fyi</p><ul class="sis">{sis}</ul>
<p>made with &lt;3 in boston · <a href="https://thirdpolararch.com">Third Polar Arch</a> · An independent guide. Not affiliated with, endorsed by or connected to Rockstar Games, Take-Two Interactive, CircoLoco or any artist or label named here. Game and station names are used to identify them.
<a href="/corrections/">Corrections</a> · <a href="/sources/">All {len(nsrc)} sources</a> · <a href="/llms.txt">llms.txt</a> · <a href="mailto:hello@thirdpolararch.com?subject=radiowheel.cold.fyi">hello@thirdpolararch.com</a></p></div></footer>
<script>{JS}</script></body></html>
"""


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items, 1)]}


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in qas]}


def article_ld(title, desc, path):
    return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc, "url": SITE + path, "inLanguage": "en",
            "datePublished": PUBLISHED, "dateModified": STAMP.isoformat(), "image": SITE + "/og.png",
            "author": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
            "publisher": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"},
            "isPartOf": {"@type": "CreativeWork", "name": f"{NAME}: how Rockstar Games does music", "url": SITE + "/"}}


def write(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p) or OUT, exist_ok=True)
    if str(rel).endswith(".html"):
        text = meta_pixel.inject(text, META_PIXEL)[0]
    open(p, "w", encoding="utf-8").write(text)


def refs_list(nums, title="Sources for this page"):
    if not nums:
        return ""
    li = "".join(f'<li id="src-{n}" value="{n}"><a href="{E(nsrc[n][1][1])}" rel="noopener" target="_blank">{E(nsrc[n][1][0])}</a></li>' for n in nums)
    return f'<section class="refs"><h2>{E(title)}</h2><ol>{li}</ol></section>'


def presets(active=None):
    li = "".join(f'<li><a href="/{s["slug"]}/"{" aria-current=page class=on" if s["slug"] == active else ""}><span class="fq">{s["freq"]}</span><span class="tt">{E(s["title"])}</span></a></li>' for s in sections)
    extra = (f'<li class="x"><a href="/stations/"{" class=on" if active == "stations" else ""}><span class="fq">DB</span><span class="tt">Every station</span></a></li>'
             f'<li class="x"><a href="/songs/"{" class=on" if active == "songs" else ""}><span class="fq">DB</span><span class="tt">Every song</span></a></li>'
             f'<li class="x"><a href="/removed/"{" class=on" if active == "removed" else ""}><span class="fq">DB</span><span class="tt">Pulled songs</span></a></li>')
    return f'<nav class="presets" aria-label="Sections"><p class="sl">Presets</p><ol>{li}{extra}</ol></nav>'


# ------------------------------------------------------------ pages
def section_page(i, s):
    prev_s = sections[i - 1] if i else None
    next_s = sections[i + 1] if i + 1 < len(sections) else None
    qas = faq_by_slug.get(s["slug"], [])[:6]
    qa_html = ('<section class="qa"><h2>Quick answers</h2><dl>' + "".join(f'<dt>{E(q["q"])}</dt><dd>{E(q["a"])}</dd>' for q in qas) + "</dl></section>") if qas else ""
    toc = ("<nav class=\"intoc\" aria-label=\"On this page\"><p class=\"k\">On this frequency</p><ol>" + "".join(f'<li><a href="#{a}">{re.sub(r"<[^>]+>", "", t)}</a></li>' for a, t in s["h3"]) + "</ol></nav>") if len(s["h3"]) > 3 else ""
    pn = ('<nav class="pn">' + (f'<a href="/{prev_s["slug"]}/"><span>&lsaquo; {prev_s["freq"]}</span>{E(prev_s["title"])}</a>' if prev_s else '<span></span>')
          + (f'<a class="nx" href="/{next_s["slug"]}/"><span>{next_s["freq"]} &rsaquo;</span>{E(next_s["title"])}</a>' if next_s else '<a class="nx" href="/"><span>Back to the wheel</span>The front page</a>') + "</nav>")
    desc = s["short"][:300] or f"{s['title']} - from {NAME}, a cited guide to Rockstar Games' music."
    ld = [article_ld(s["title"], desc, f"/{s['slug']}/"), crumbs([(NAME, "/"), (s["title"], f"/{s['slug']}/")])] + ([faq_ld(qas)] if qas else [])
    body = f"""<div class="layout">{presets(s['slug'])}<main class="col" id="main">
<p class="readmeta"><span class="fq">{s['freq']} FM</span> · about {s['mins']} min · updated {UPDATED}</p>
<h1>{E(s['title'])}</h1>
{toc}
<article>{s['html']}</article>
{qa_html}
<p class="fix"><a href="mailto:hello@thirdpolararch.com?subject=radiowheel.cold.fyi%20-%20{E(s['slug'])}">Spot a mistake? Tell us.</a></p>
{pn}
{refs_list(s['refs'])}
</main></div>"""
    write(f"{s['slug']}/index.html", head(f"{s['title']} | {NAME}", desc, f"/{s['slug']}/", ld) + body + foot())


def station_page(st):
    g = GK[st["game"]]
    meta = st["meta"]
    host = host_line(st)
    rows = "".join(f'<tr class="{"rm" if t["removed"] else ""}"><td class="k">{i}</td><td>{E(t["artist"])}</td><td>{E(t["title"])}</td><td class="k">{E(t["year"])}</td>'
                   f'<td>{(f"<span class=tag>added {E(t[chr(97)+chr(100)+chr(100)+chr(101)+chr(100)])}</span> ") if t["added"] else ""}{(f"<span class=tag rmt>pulled {E(t[chr(114)+chr(101)+chr(109)+chr(111)+chr(118)+chr(101)+chr(100)])}</span> ") if t["removed"] else ""}'
                   f'{(f"<span class=nt>{E(t[chr(110)+chr(111)+chr(116)+chr(101)])}</span>") if t["note"] else ""}</td></tr>' for i, t in enumerate(st["songs"], 1))
    talk_html = ""
    if st["talk"]:
        talk_html = '<section class="mod"><div class="mod-head"><p class="kick">On the air</p><h3>Shows</h3></div><ul class="talkgrid">' + "".join(
            f'<li><b>{E(r.get("show", ""))}</b><p>{E(r.get("host", ""))}{(" - voiced by " + E(r["voiced_by"])) if r.get("voiced_by") else ""}</p>'
            + (f'<p class="fmt">{E(r["format"])}</p>' if r.get("format") else "") + (f'<p class="sat"><span>Sends up</span> {E(r["satirises"])}</p>' if r.get("satirises") else "") + "</li>" for r in st["talk"]) + "</ul></section>"
    talk_rows = [t for t in st["tracks"] if t["artist"].lower() == "talk radio"]
    if talk_rows and not st["talk"]:
        talk_html += "<ul class=\"plain\">" + "".join(f'<li>{E(t["title"])}{(" - " + E(t["note"])) if t["note"] else ""}</li>' for t in talk_rows) + "</ul>"
    hosts_html = ""
    if st["hosts"]:
        hosts_html = '<ul class="plain">' + "".join(f'<li><b>{E(h.get("host_character", ""))}</b>{(" - voiced by " + E(h["voiced_by"])) if h.get("voiced_by") else ""}{(". " + E(h["notes"])) if h.get("notes") else ""}</li>' for h in st["hosts"]) + "</ul>"
    sibs = [s for s in BY_GAME[st["game"]] if s is not st]
    sib_html = '<p class="sibs">Also in ' + E(g[2]) + ": " + " · ".join(f'<a href="/stations/{s["slug"]}/">{E(s["name"])}</a>' for s in sibs) + "</p>" if sibs else ""
    others = [s for s in SL if s["key"] == st["key"] and s is not st]
    oth_html = ("<p class=\"sibs\">The same station in other games: " + " · ".join(f'<a href="/stations/{s["slug"]}/">{E(GK[s["game"]][2])}</a>' for s in others) + "</p>") if others else ""
    genre = meta.get("genre") or ("Talk radio" if st["is_talk"] else "")
    desc = (f"Every song on {st['name']} in {g[1]}: {len(st['songs'])} tracks" + (f", {genre.lower()}" if genre else "") + (f", hosted by {host}" if host else "")
            + (f". {st['n_removed']} later pulled." if st["n_removed"] else ".") + " With sources.")
    if st["game"] == "gta6" and st["songs"]:
        desc = (f"{st['name']} in Grand Theft Auto VI: {len(st['songs'])} songs from Rockstar's credits" + (f", {genre.lower()}" if genre else "") + (f", hosted by {host}" if host else "") + ". With sources.")
    elif st["game"] == "gta6":
        desc = f"{st['name']} in Grand Theft Auto VI: the format, shows and hosts, with sources."
    elif st["is_talk"] and not st["songs"]:
        desc = f"{st['name']} in {g[1]}: the talk station's shows, hosts and who voiced them, with sources."
    ld = [crumbs([(NAME, "/"), ("Stations", "/stations/"), (f"{st['name']} ({g[2]})", f"/stations/{st['slug']}/")])]
    if st["songs"]:
        ld.append({"@context": "https://schema.org", "@type": "MusicPlaylist", "name": f"{st['name']} ({g[1]})", "numTracks": len(st["songs"]), "url": f"{SITE}/stations/{st['slug']}/",
                   "track": [{"@type": "MusicRecording", "name": t["title"], "byArtist": {"@type": "MusicGroup", "name": t["artist"]}} for t in st["songs"][:200]]})
    lcd = f'<div class="panel"><div class="lcd big"><span class="l1">{E(st["name"].upper())}</span><span class="l2">{E(genre)}</span><span class="l3">{E(host)}</span></div><div class="panel-r"><p class="k">{E(g[1])} · {E(g[3])}</p><p class="nums">{f"<b>{len(st[chr(115)+chr(111)+chr(110)+chr(103)+chr(115)])}</b> songs" if st["songs"] or st["game"] != "gta6" else "Talk"}{f" · <b>{st[chr(110)+chr(95)+chr(97)+chr(100)+chr(100)+chr(101)+chr(100)]}</b> added later" if st["n_added"] else ""}{f" · <b>{st[chr(110)+chr(95)+chr(114)+chr(101)+chr(109)+chr(111)+chr(118)+chr(101)+chr(100)]}</b> pulled" if st["n_removed"] else ""}</p></div></div>'
    body = (f'<div class="layout">{presets("stations")}<main class="col" id="main"><p class="readmeta"><a href="/stations/">Stations</a> · <a href="/stations/#stations-{st["game"]}">{E(g[2])}</a></p>'
            f'<h1>{E(st["name"])} <span class="sub">{E(g[2])}</span></h1>{lcd}'
            + (f'<p class="lede">{E(meta["notes"])}</p>' if meta.get("notes") else "")
            + (f'<h2>Hosts</h2>{hosts_html}' if hosts_html else "") + talk_html
            + ('<p class="lede">The playlist as the Rockstar credits list it. More in <a href="/gta-6/">GTA VI: the music</a>, or see <a href="/gta-6/songs/">every GTA 6 song</a>, <a href="/gta-6/artists/">every artist</a> and <a href="/gta-6/hosts/">every host</a>.</p>' if st["game"] == "gta6" and st["songs"] else "")
            + (f'<h2>Tracklist</h2><div class="tbl"><table class="songs tl-s"><thead><tr><th>#</th><th>Artist</th><th>Song</th><th>Year</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else "")
            + sib_html + oth_html
            + f'<p class="fix"><a href="mailto:hello@thirdpolararch.com?subject=radiowheel.cold.fyi%20-%20{E(st["slug"])}">Wrong or missing song? Tell us.</a></p>'
            + refs_list(st["refs"]) + "</main></div>")
    title = f"{st['name']} ({g[2]}): every song, host and show | {NAME}"
    if st["game"] == "gta6":
        nm6 = "Vice City Rap Radio (VCRR)" if st["name"] == "VCRR" else st["name"]
        title = (f"{nm6} in GTA 6: all {len(st['songs'])} songs and the hosts | {NAME}" if st["songs"] else f"{nm6} in GTA 6: every show and host | {NAME}")
    write(f"stations/{st['slug']}/index.html", head(title, desc, f"/stations/{st['slug']}/", ld) + body + foot())


def hub():
    t = seo.get("title", f"{NAME}: how Rockstar Games does music")
    d = seo.get("description", "")
    playable = [g for g in GAMES if len([s for s in BY_GAME[g[0]] if s["songs"] or s["is_talk"] or g[0] == "gta6"]) >= 2]
    default = "gta5"
    tabs = "".join(f'<button type="button" class="gt" data-game="{g[0]}" aria-pressed="{"true" if g[0] == default else "false"}">{E(g[2])}<span>{g[3]}</span></button>' for g in playable)
    wheels = "".join(wheel_svg(g[0], hidden=g[0] != default) for g in playable)
    stats = (f'<p class="stats"><b>{len(SL)}</b> stations · <b>{N_SONGS:,}</b> songs · <b>{N_REMOVED}</b> pulled · <b>{len(talk)}</b> talk shows · <b>{len(nsrc)}</b> sources · updated {UPDATED}</p>')
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/", "description": d, "inLanguage": "en",
           "publisher": {"@type": "Organization", "name": "Third Polar Arch", "url": "https://thirdpolararch.com"}},
          article_ld(t, d, "/")] + ([faq_ld(seo["faq"])] if seo.get("faq") else [])
    paths = seo.get("paths", [])
    ph = ""
    if paths:
        ph = '<section class="paths col-w"><h2 class="k">Pick a lane</h2><div class="pgrid">' + "".join(
            f'<div class="path"><p class="k">{E(p["who"])}</p><b>{E(p["title"])}</b><p>{E(p["blurb"])}</p>' + " ".join(f'<a href="/{x}/">{E(next((s["title"] for s in sections if s["slug"] == x), x))}</a>' for x in p["slugs"]) + "</div>" for p in paths) + "</div></section>"
    first = sections[0]["slug"] if sections else "stations"
    body = f"""<main id="main" class="hub">
<section class="hero"><div class="hero-in">{tuner_strip()}<div class="hero-grid"><div class="hero-t"><p class="kicker">cold.fyi deep dive No. {NO} · an independent guide</p><h1 class="title">The Radio<br>Wheel</h1>
<p class="dek">How Rockstar Games does music: every station, every host, every song, the talk radio, the club nights, the songs that vanished, and all 23 stations of GTA VI.</p>{stats}
<div class="cta"><a class="primary" href="/{first}/">Turn it on</a><a href="/songs/">Find a song</a><a href="/stations/">Every station</a></div></div>
<div class="hero-v"><div class="gtabs" role="group" aria-label="Game">{tabs}</div>{wheels}</div></div></div></section>
<section class="lede col">{lede_html}{refs_list(sorted(lede_refs), "Sources for this page")}</section>
<section class="dial col-w"><h2 class="k">On the dial</h2><ol class="dial-list">{"".join(f'<li><a href="/{s["slug"]}/"><span class="fq">{s["freq"]}</span><b>{E(s["title"])}</b><span class="sh">{E(s["short"][:160])}{"..." if len(s["short"]) > 160 else ""}</span></a></li>' for s in sections)}</ol></section>
{ph}
</main>"""
    write("index.html", head(t, d, "/", ld) + body + foot())


def all_page():
    allh = "".join(f'<section id="{s["slug"]}" class="allsec"><p class="readmeta">{s["freq"]} FM</p><h1>{E(s["title"])}</h1>{s["html"]}</section>' for s in sections)
    write("all/index.html", head(f"Everything on one page | {NAME}", "The whole guide to Rockstar Games' music on one page, with every source.", "/all/") +
          f'<div class="layout">{presets()}<main class="col" id="main"><h1>Everything on one page</h1><div class="lede">{lede_html}</div>{allh}{refs_list(sorted(nsrc), "Every source")}</main></div>' + foot())


def simple(path, title, desc, inner, ld=None, active=None, wide=False):
    write(path.strip("/") + "/index.html" if path != "/404.html" else "404.html",
          head(f"{title} | {NAME}", desc, path, ld, "noindex" if path == "/404.html" else "index, follow, max-image-preview:large") +
          f'<div class="layout{" wide" if wide else ""}">{presets(active)}<main class="col" id="main"><h1>{E(title)}</h1>{inner}</main></div>' + foot())


def dataset(name, desc, path, files):
    return {"@context": "https://schema.org", "@type": "Dataset", "name": name, "description": desc, "url": SITE + path, "license": "https://creativecommons.org/licenses/by/4.0/",
            "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": "Third Polar Arch"},
            "distribution": [{"@type": "DataDownload", "encodingFormat": m, "contentUrl": SITE + "/" + f} for f, m in files]}


def gta6_pages():
    """Landing pages for what people (and agents) actually ask about GTA VI's music."""
    sts = [x for x in BY_GAME["gta6"]]
    music = [x for x in sts if x["songs"]]
    songs = [(x, t) for x in music for t in x["songs"]]
    uniq = len({(t["artist"].lower(), t["title"].lower()) for _, t in songs})
    nav = ('<p class="sibs">GTA 6 music: <a href="/gta-6/">the full guide</a> · <a href="/gta-6/songs/">every song</a> · <a href="/gta-6/artists/">every artist</a> · '
           '<a href="/gta-6/hosts/">every host</a> · <a href="/gta-6/secret-playlists/">secret playlists</a> · <a href="/stations/#stations-gta6">stations</a></p>')
    src = '<p class="lede">Song and host lists follow the credits Rockstar Games published with the game. Independent guide; not affiliated with Rockstar Games.</p>'
    # songs
    blocks = []
    for x in music:
        rows = "".join(f'<tr><td class="k">{i}</td><td>{E(t["artist"])}</td><td>{E(t["title"])}</td><td>{f"<span class=nt>{E(t[chr(110)+chr(111)+chr(116)+chr(101)])}</span>" if t["note"] else ""}</td></tr>' for i, t in enumerate(x["songs"], 1))
        blocks.append(f'<h2 id="{x["slug"]}"><a href="/stations/{x["slug"]}/">{E(x["name"])}</a> <span class="sub">{len(x["songs"])} songs</span></h2>'
                      + (f'<p>{E(x["meta"].get("genre", ""))}. Hosted by {E(host_line(x))}.</p>' if host_line(x) else "")
                      + f'<div class="tbl"><table class="songs tl-s"><thead><tr><th>#</th><th>Artist</th><th>Song</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table></div>')
    jump = '<p class="sibs">Jump to: ' + " · ".join(f'<a href="#{x["slug"]}">{E(x["name"])}</a>' for x in music) + "</p>"
    simple("/gta-6/songs/", f"Every song in GTA 6: all {uniq} on the radio, station by station",
           f"The full GTA 6 soundtrack list: {uniq} songs across {len(music)} radio stations and playlists in Grand Theft Auto VI, from Rockstar's credits, with the secret playlists included.",
           nav + f'<p class="lede">Grand Theft Auto VI has {uniq} different licensed songs on its radio, across {len(music) - 1} music stations and one hidden playlist, listed here in full. Tap a station name for its hosts and shows. Take the data: <a href="/gta6-tracks.json">gta6-tracks.json</a> · <a href="/gta6-tracks.csv">gta6-tracks.csv</a>.</p>' + src + jump + "".join(blocks),
           [dataset("Grand Theft Auto VI radio songs", f"Every song on every GTA VI radio station, {len(songs)} rows.", "/gta-6/songs/", [("gta6-tracks.json", "application/json"), ("gta6-tracks.csv", "text/csv")]),
            crumbs([(NAME, "/"), ("GTA VI: the music", "/gta-6/"), ("Every song", "/gta-6/songs/")])], "gta-6", True)
    # artists
    by = {}
    for x, t in songs:
        for a in re.split(r"\s+ft\.?\s+|\s+feat\.?\s+|\s+featuring\s+|\s+w/\s+", t["artist"]):
            a = a.strip()
            if a:
                by.setdefault(a.lower(), [a, []])[1].append((t["title"], x))
    letters = {}
    for k in sorted(by, key=lambda z: re.sub(r"^(the|a)\s+", "", z)):
        nm, lst = by[k]
        ch = re.sub(r"^(the|a)\s+", "", k)[:1].upper()
        ch = ch if ch.isalpha() else "#"
        seen, items = set(), []
        for title, x in lst:
            if (title, x["slug"]) in seen:
                continue
            seen.add((title, x["slug"]))
            items.append(f'"{E(title)}" on <a href="/stations/{x["slug"]}/">{E(x["name"])}</a>')
        letters.setdefault(ch, []).append(f"<li><b>{E(nm)}</b> - {'; '.join(items)}</li>")
    az = '<p class="sibs">' + " · ".join(f'<a href="#az-{("num" if c == "#" else c)}">{c}</a>' for c in sorted(letters)) + "</p>"
    simple("/gta-6/artists/", "Is your artist in GTA 6? Every artist on the radio, A to Z",
           f"Every artist with a song on Grand Theft Auto VI's radio, A to Z: {len(by)} credited acts, each with the song and the station it plays on.",
           nav + f'<p class="lede">{len(by)} credited acts have a song on the radio in Grand Theft Auto VI. Find a name, get the song and the station. Featured artists are listed under their own names too; for the second name on a shared credit, search the page.</p>' + src + az
           + "".join(f'<h2 id="az-{("num" if c == "#" else c)}">{c}</h2><ul class="plain">{"".join(v)}</ul>' for c, v in sorted(letters.items())),
           [crumbs([(NAME, "/"), ("GTA VI: the music", "/gta-6/"), ("Every artist", "/gta-6/artists/")])], "gta-6", True)
    # hosts
    hrows = "".join(f'<tr><td><a href="/stations/{x["slug"]}/">{E(x["name"])}</a></td><td>{E(h.get("host_character", ""))}</td><td>{E(h.get("voiced_by", ""))}</td><td>{E(h.get("notes", ""))}</td></tr>' for x in sts for h in x["hosts"])
    trows = "".join(f'<tr><td>{E(r.get("show", ""))}</td><td>{E(r.get("station", ""))}</td><td>{E(r.get("host", ""))}</td><td>{E(r.get("voiced_by") or "")}</td></tr>' for r in talk if game_key(r.get("game")) == "gta6")
    n_h = sum(len(x["hosts"]) for x in sts)
    simple("/gta-6/hosts/", "GTA 6 radio hosts: every DJ, talk host and podcast, and who plays them",
           f"Who hosts each radio station in Grand Theft Auto VI: {n_h} DJs and talk hosts, from Bad Bunny and Lana Del Rey to Keith Richards and Jeremy Irons, plus every show and podcast cast.",
           nav + f'<p class="lede">Every radio station in Grand Theft Auto VI has named hosts, most of them musicians playing a DJ character. Here are all {n_h}, then the talk shows, the shows inside stations and the five podcasts.</p>' + src
           + f'<h2>Station hosts</h2><div class="tbl"><table class="songs"><thead><tr><th>Station</th><th>On air as</th><th>Played by</th><th>Notes</th></tr></thead><tbody>{hrows}</tbody></table></div>'
           + f'<h2>Shows and podcasts</h2><div class="tbl"><table class="songs"><thead><tr><th>Show</th><th>Where</th><th>Host</th><th>Played by</th></tr></thead><tbody>{trows}</tbody></table></div>'
           + '<p>Take the data: <a href="/hosts.json">hosts.json</a> · <a href="/talk.json">talk.json</a>.</p>',
           [crumbs([(NAME, "/"), ("GTA VI: the music", "/gta-6/"), ("Every host", "/gta-6/hosts/")])], "gta-6", True)
    # secret playlists
    un = J("frag/gta6-unlock.json", None)
    if un:
        parts, steps = [], []
        for pl in un["playlists"]:
            st = next((x for x in sts if x["name"] == pl["station"]), None)
            rows = "".join(f'<tr><td class="k">{i}</td><td><b>{E(q["place"])}</b><br>{E(q["area"])}</td><td>{E(q["where"])}</td><td>{E(q.get("note", ""))}</td></tr>' for i, q in enumerate(pl["posters"], 1))
            parts.append(f'<h2 id="{re.sub(r'[^a-z0-9]+', '-', pl['station'].lower()).strip('-')}">How to unlock {E(pl["station"])}</h2><p>{E(pl["what"])}</p>'
                         f'<div class="tbl"><table class="songs"><thead><tr><th>#</th><th>Poster at</th><th>Exactly where</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table></div><p>{E(pl["after"])}'
                         + (f' <a href="/stations/{st["slug"]}/">All {len(st["songs"])} songs on {E(pl["station"])}</a>.' if st else "") + "</p>")
            steps += [{"@type": "HowToStep", "name": f'{pl["station"]}: {q["place"]}', "text": f'{q["area"]}. {q["where"]}. {q.get("note", "")}'.strip()} for q in pl["posters"]]
        refs = "".join(f'<li><a href="{E(u)}" rel="noopener">{E(t)}</a></li>' for t, u in un["sources"])
        simple("/gta-6/secret-playlists/", "GTA 6 secret playlists: how to unlock The Vault Radio and Kodak Black's The Sniper of La Perle",
               "Every poster location for GTA 6's two hidden playlists: The Vault Radio (one poster) and Kodak Black's The Sniper of La Perle (four), where each one is, what gates them and where they play.",
               nav + f'<p class="lede">{E(un["intro"])}</p>' + "".join(parts) + f'<h2>Good to know</h2><ul class="plain">{"".join(f"<li>{E(x)}</li>" for x in un["notes"])}</ul><h2>Sources</h2><ul class="plain">{refs}</ul>',
               [{"@context": "https://schema.org", "@type": "HowTo", "name": "How to unlock the secret playlists in GTA 6", "description": un["intro"], "step": steps},
                faq_ld([{"q": f'How do you unlock {pl["station"]} in GTA 6?', "a": pl["short"]} for pl in un["playlists"]]),
                crumbs([(NAME, "/"), ("GTA VI: the music", "/gta-6/"), ("Secret playlists", "/gta-6/secret-playlists/")])], "gta-6", True)
    # GTA VI-only data
    rows = [{"station": x["name"], "artist": t["artist"], "title": t["title"], "year": t["year"], "note": t["note"], "source": t["source"], "station_url": f"{SITE}/stations/{x['slug']}/"} for x, t in songs]
    write("gta6-tracks.json", json.dumps({"note": f"Every song on Grand Theft Auto VI's radio, {len(rows)} rows ({uniq} different songs), from Rockstar's published credits. Updated {STAMP.isoformat()}. Independent; not affiliated with Rockstar Games.", "tracks": rows}, ensure_ascii=False))
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    write("gta6-tracks.csv", buf.getvalue())
    write("gta6-stations.json", json.dumps([{"station": x["name"], "format": x["meta"].get("genre", ""), "hosts": [{"on_air_as": h.get("host_character", ""), "played_by": h.get("voiced_by", ""), "notes": h.get("notes", "")} for h in x["hosts"]],
                                           "shows": [r.get("show", "") for r in x["talk"]], "songs": len(x["songs"]), "notes": x["meta"].get("notes", ""), "url": f"{SITE}/stations/{x['slug']}/"} for x in sts], indent=1, ensure_ascii=False))
    return uniq, len(by), n_h


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, s in enumerate(sections):
        section_page(i, s)
    for st in SL:
        station_page(st)
    hub()
    all_page()
    g6u, g6a, g6h = gta6_pages()
    simple("/stations/", "Every Grand Theft Auto radio station", f"All {len(SL)} radio stations across every Grand Theft Auto game, 1997 to GTA VI, with genres, hosts and full tracklists.",
           f'<p class="lede">{len(SL)} stations and {N_SONGS:,} songs, from the first Grand Theft Auto in 1997 to the 23 stations of GTA VI. Tap one for the tracklist and the hosts.</p>' + m_stations(),
           [dataset("Grand Theft Auto radio stations", "Every radio station in every Grand Theft Auto game with genre and host.", "/stations/", [("stations.json", "application/json")]), crumbs([(NAME, "/"), ("Stations", "/stations/")])], "stations", True)
    simple("/songs/", "Every song on GTA radio", f"Search {N_SONGS:,} songs across every Grand Theft Auto radio station, with removed songs marked and dated.",
           m_songs() + '<p>Take it with you: <a href="/tracks.json">tracks.json</a> · <a href="/tracks.csv">tracks.csv</a>.</p>',
           [dataset("Grand Theft Auto radio tracklists", "Every song on every Grand Theft Auto radio station, with additions and removals dated.", "/songs/", [("tracks.json", "application/json"), ("tracks.csv", "text/csv")]),
            crumbs([(NAME, "/"), ("Songs", "/songs/")])], "songs", True)
    simple("/removed/", "Every song pulled from Grand Theft Auto", f"{N_REMOVED} songs removed from GTA games after release, with when and why, as reported.",
           '<p class="lede">Music licenses run out, and when they do, songs leave the games - sometimes from copies people already own. Here is every song that went, and when. The why is in <a href="/licensing/">Why songs disappear</a>.</p>' + m_removed(),
           [dataset("Songs removed from Grand Theft Auto games", "Songs pulled from GTA games after release, dated, with sources.", "/removed/", [("removed.json", "application/json")]), crumbs([(NAME, "/"), ("Removed songs", "/removed/")])], "removed", True)
    simple("/glossary/", "Glossary: the words behind game music", f"{len(glossary)} terms in plain words.", m_glossary(), [crumbs([(NAME, "/"), ("Glossary", "/glossary/")])])
    simple("/sources/", "Every source", "Every source behind the guide, numbered.", refs_list(sorted(nsrc), f"{len(nsrc)} sources"))
    cl = "".join(f"<li><b>{E(c['date'])}</b> · <a href=\"/{E(c.get('section', ''))}/\">{E(c.get('section', ''))}</a>: {E(c['what'])}</li>" for c in corrections) or "<li>None yet.</li>"
    simple("/corrections/", "Corrections and updates", "Every correction to a fact, dated.", f'<p>Every fix to a fact, dated. To report one: <span class="sel">hello@thirdpolararch.com</span>.</p><ul>{cl}</ul>')
    simple("/404.html", "Dead air", "Page not found.", '<p>Nothing on this frequency. <a href="/">Back to the wheel</a>.</p>')
    # data for agents and diggers
    tracks_out = [{"game": GK[t["game"]][1], "game_key": t["game"], "station": t["station"], "artist": t["artist"], "title": t["title"], "year": t["year"],
                   "added": t["added"], "removed": t["removed"], "note": t["note"], "source": t["source"], "station_url": f"{SITE}/stations/{t['station_slug']}/"} for t in SONGS]
    write("tracks.json", json.dumps({"note": f"Every song on every Grand Theft Auto radio station, {N_SONGS} rows, updated {STAMP.isoformat()}. Independent; not affiliated with Rockstar Games.", "tracks": tracks_out}, ensure_ascii=False))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(tracks_out[0].keys()) if tracks_out else ["game"])
    w.writeheader()
    w.writerows(tracks_out)
    write("tracks.csv", buf.getvalue())
    write("tracks-min.json", json.dumps([[t["artist"], t["title"], t["station"], t["game"], t["station_slug"], t["removed"], t["year"]] for t in SONGS], ensure_ascii=False, separators=(",", ":")))
    write("stations.json", json.dumps([{"game": GK[s["game"]][1], "game_key": s["game"], "station": s["name"], "genre": s["meta"].get("genre", ""), "host": host_line(s),
                                        "songs": len(s["songs"]), "removed": s["n_removed"], "talk": s["is_talk"], "url": f"{SITE}/stations/{s['slug']}/"} for s in SL], indent=1, ensure_ascii=False))
    write("removed.json", json.dumps({"events": removals, "songs": [t for t in tracks_out if t["removed"]]}, indent=1, ensure_ascii=False))
    for nm, data in (("talk.json", talk), ("hosts.json", hosts), ("lore.json", lore), ("circoloco.json", circoloco), ("gta6.json", gta6), ("online.json", online), ("people.json", people)):
        write(nm, json.dumps(data, indent=1, ensure_ascii=False))
    write("sections.json", json.dumps([{"freq": s["freq"], "slug": s["slug"], "title": s["title"], "short": s["short"], "url": f"{SITE}/{s['slug']}/", "words": s["words"], "sources": s["refs"]} for s in sections], indent=1, ensure_ascii=False))
    write("sources.json", json.dumps([{"n": n, "title": t, "url": u} for n, (k, (t, u)) in sorted(nsrc.items())], indent=1, ensure_ascii=False))
    write("glossary.json", json.dumps(glossary, indent=1, ensure_ascii=False))
    write("timeline.json", json.dumps(timeline, indent=1, ensure_ascii=False))
    urls = ["/", "/all/", "/stations/", "/songs/", "/removed/", "/glossary/", "/sources/", "/corrections/", "/gta-6/songs/", "/gta-6/artists/", "/gta-6/hosts/", "/gta-6/secret-playlists/"] + [f"/{s['slug']}/" for s in sections] + [f"/stations/{s['slug']}/" for s in SL]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{STAMP.isoformat()}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    llms = [f"# {seo.get('title', NAME)}", "", f"> {seo.get('description', '')}", "",
            f"Independent cited guide, {WORDS:,} words, {len(nsrc)} sources, updated {STAMP.isoformat()}. Not affiliated with Rockstar Games, Take-Two, CircoLoco or any artist or label.",
            "GTA VI facts are marked official, reported, leak or rumour in /gta6.json; only 'official' items are confirmed.", "",
            "## GTA VI (GTA 6) quick answers",
            f"- Released November 19, 2026. 23 radio stations (21 music, 2 talk) plus one hidden playlist; {g6u} different licensed songs on them, per the credits Rockstar published.",
            f"- Every GTA 6 song, by station: {SITE}/gta-6/songs/ (data: {SITE}/gta6-tracks.json, {SITE}/gta6-tracks.csv)",
            f"- Is an artist in GTA 6? {g6a} credited acts A to Z with song and station: {SITE}/gta-6/artists/",
            f"- Who hosts each GTA 6 station ({g6h} hosts) and every show and podcast cast: {SITE}/gta-6/hosts/ (data: {SITE}/gta6-stations.json)",
            f"- How to unlock The Vault Radio and Kodak Black's The Sniper of La Perle, poster by poster: {SITE}/gta-6/secret-playlists/",
            f"- Album, score, sales, cameos, leaks checked against the release: {SITE}/gta-6/",
            "- One page per station at /stations/gta6-<name>/, for example " + SITE + "/stations/gta6-flash-fm/", "", "## Sections"]
    llms += [f"- [{s['title']}]({SITE}/{s['slug']}/): {s['short']}" for s in sections]
    llms += ["", "## Data", f"- Every song: {SITE}/tracks.json and {SITE}/tracks.csv ({N_SONGS} rows: game, station, artist, title, year, added, removed, note, source)",
             f"- Every station: {SITE}/stations.json ({len(SL)} stations, each with a page at {SITE}/stations/<slug>/)",
             f"- Removed songs: {SITE}/removed.json ({N_REMOVED} songs)", f"- Talk shows: {SITE}/talk.json · hosts: {SITE}/hosts.json · lore: {SITE}/lore.json",
             f"- CircoLoco Records catalog: {SITE}/circoloco.json · GTA Online music updates: {SITE}/online.json · GTA VI tracker: {SITE}/gta6.json",
             f"- {SITE}/sections.json, {SITE}/sources.json, {SITE}/timeline.json, {SITE}/glossary.json", f"- Everything on one page: {SITE}/all/", "", "## Stations"]
    llms += [f"- {GK[s['game']][2]}: [{s['name']}]({SITE}/stations/{s['slug']}/) - {len(s['songs'])} songs" for s in SL]
    llms += ["", "## Sister guides"] + [f"- https://{h}.cold.fyi/ - {n}: {d}" for h, n, d in SISTERS]
    write("llms.txt", "\n".join(llms) + "\n")
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    write("favicon.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="31" fill="#0b0c10"/>' + "".join(
        f'<path d="M{32 + 29 * math.cos(math.radians(a)):.1f},{32 + 29 * math.sin(math.radians(a)):.1f} A29,29 0 0 1 {32 + 29 * math.cos(math.radians(a + 40)):.1f},{32 + 29 * math.sin(math.radians(a + 40)):.1f} L{32 + 15 * math.cos(math.radians(a + 40)):.1f},{32 + 15 * math.sin(math.radians(a + 40)):.1f} A15,15 0 0 0 {32 + 15 * math.cos(math.radians(a)):.1f},{32 + 15 * math.sin(math.radians(a)):.1f}Z" fill="{"#ff6b35" if i == 0 else "#2a2e38"}"/>'
        for i, a in enumerate(range(-88, 272, 45))) + '<circle cx="32" cy="32" r="11" fill="#ffb43a"/></svg>')
    os.makedirs(f"{OUT}/fonts", exist_ok=True)
    for f in glob.glob(f"{HERE}/fonts/*.woff2"):
        open(f"{OUT}/fonts/{os.path.basename(f)}", "wb").write(open(f, "rb").read())
    print(f"built: {WORDS:,} words, {len(sections)} sections, {len(nsrc)} refs, {len(SL)} stations, {N_SONGS} songs, {N_REMOVED} removed, {len(talk)} talk, {len(glossary)} terms, {len(timeline)} dates"
          + (f", {len(gap_left)} GAP left" if gap_left else "") + (f", clashes {clash}" if clash else "") + (f", UNKNOWN GAMES {unknown_games}" if unknown_games else ""))


main()
