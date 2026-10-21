#!/usr/bin/env python3
"""Daily content update for Harkhowal Online.

Pulls:
  * latest videos from the YouTube channel's public feed (no API key)
  * Babaji's katha folders and recordings from gurmatveechar.com
  * optionally, Instagram posts via a Behold.so JSON feed (for the Yatra section)

Writes data/videos.json, data/audio.json and data/instagram.json.
Uses only the Python standard library. If a source can't be reached, the
previous data is kept, so a bad day never empties the website.
"""
import json, re, sys, time, html
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
GMV = "https://www.gurmatveechar.com"
UA = "HarkhowalOnline-updater/1.0 (+https://www.harkhowal.com; once-daily)"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d")
MAX_REQUESTS = 150      # hard cap on Gurmatveechar page fetches per run
DELAY = 1.0             # seconds between Gurmatveechar requests, to be polite

_requests = 0


def fetch(url, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # network error, 5xx, timeout
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def load(name, default):
    p = DATA / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(name, obj):
    DATA.mkdir(exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- YouTube
def parse_youtube_feed(xml_text):
    ns = {"a": "http://www.w3.org/2005/Atom",
          "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", ns):
        vid = e.findtext("yt:videoId", default="", namespaces=ns)
        if not vid:
            continue
        desc = e.findtext("media:group/media:description", default="", namespaces=ns) or ""
        out.append({
            "id": vid,
            "title": (e.findtext("a:title", default="", namespaces=ns) or "").strip(),
            "published": (e.findtext("a:published", default="", namespaces=ns) or "")[:10],
            "description": desc.strip()[:280],
        })
    return out


def update_youtube():
    cid = CONFIG.get("youtube_channel_id")
    if not cid:
        return
    old = load("videos.json", {"videos": []})
    try:
        fresh = parse_youtube_feed(fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
    except Exception as e:
        print(f"YouTube: kept previous data ({e})", file=sys.stderr)
        return
    # The feed only carries the latest 15 uploads, so merge with what we
    # already have: the archive on the site keeps growing over time.
    by_id = {v["id"]: v for v in old.get("videos", [])}
    for v in fresh:
        by_id[v["id"]] = v
    videos = sorted(by_id.values(), key=lambda v: v.get("published", ""), reverse=True)
    save("videos.json", {"updated": NOW, "channel_url": CONFIG.get("youtube_url", ""), "videos": videos})
    print(f"YouTube: {len(fresh)} in feed, {len(videos)} total")


# ---------------------------------------------------------- Gurmatveechar
# Links on Gurmatveechar are sometimes quoted and sometimes not, so accept both.
FOLDER_RE = re.compile(r'href=["\']?([^"\'\s>]*audio\.php\?q=f&(?:amp;)?f=([^"\'\s>&#]+))', re.I)
MP3_RE = re.compile(r'href=["\']?([^"\'\s>]*?/audios/[^"\'\s>]+?\.mp3)', re.I)


def folder_url(path):
    return f"{GMV}/audio.php?q=f&f={urllib.parse.quote_plus(path)}"


def player_url(path):
    return f"{GMV}/audio.php?q=m&m={urllib.parse.quote_plus(path)}"


def nice(segment):
    s = urllib.parse.unquote_plus(segment)
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip()


def track_title(mp3_path):
    name = urllib.parse.unquote(mp3_path.rsplit("/", 1)[-1])
    name = re.sub(r"\.mp3$", "", name, flags=re.I)
    name = re.sub(r"^Baba\.Jagjit\.Singh\.\(Harkhowal\.wale\)--", "", name)
    name = name.replace("--", " – ").replace("_", " ").replace(".", " ")
    return re.sub(r"\s+", " ", name).strip()


def parse_listing(page_html, current_path):
    """Return (child_folder_paths, mp3_paths) directly under current_path."""
    page_html = html.unescape(page_html)
    cur = current_path.rstrip("/")
    folders, files = [], []
    for _, enc in FOLDER_RE.findall(page_html):
        p = urllib.parse.unquote_plus(enc)
        if p.startswith(cur + "/") and "/" not in p[len(cur) + 1:] and p not in folders:
            folders.append(p)
    for href in MP3_RE.findall(page_html):
        p = urllib.parse.urlparse(href).path          # /audios/Katha/...mp3 (still %-encoded)
        p = urllib.parse.unquote(p)
        rel = p[len("/audios"):] if p.startswith("/audios") else p
        parent = rel.rsplit("/", 1)[0]
        if parent == cur and rel not in files:
            files.append(rel)
    return folders, files


def crawl(path, depth=0):
    global _requests
    if _requests >= MAX_REQUESTS:
        raise RuntimeError("request cap reached")
    _requests += 1
    if _requests > 1:
        time.sleep(DELAY)
    folders, files = parse_listing(fetch(folder_url(path)), path)
    node = {"path": path, "files": files, "children": []}
    if depth < 3:
        for f in folders:
            node["children"].append(crawl(f, depth + 1))
    return node


def flatten(node, group=""):
    items = [{"title": track_title(f), "group": group, "path": f} for f in node["files"]]
    for c in node["children"]:
        g = nice(c["path"].rsplit("/", 1)[-1])
        items += flatten(c, f"{group} · {g}" if group else g)
    return items


def category_for(path):
    for cat in CONFIG.get("audio_categories", []):
        if any(m.lower() in path.lower() for m in cat["match"]):
            return cat["name"]
    return "Other"


def update_audio():
    root = CONFIG.get("gurmatveechar_root")
    if not root:
        return
    old = load("audio.json", {"series": [], "loose": []})
    first_seen = {}
    for s in old.get("series", []):
        for t in s.get("tracks", []):
            first_seen[t["path"]] = t.get("added", "")
    for t in old.get("loose", []):
        first_seen[t["path"]] = t.get("added", "")
    seeded = not first_seen  # first ever run: don't flag everything as "new"

    try:
        tree = crawl(root)
    except Exception as e:
        print(f"Gurmatveechar: kept previous data ({e})", file=sys.stderr)
        return

    def stamp(t):
        t["added"] = first_seen.get(t["path"]) or ("" if seeded else NOW)
        t["mp3"] = GMV + "/audios" + urllib.parse.quote(t["path"])
        t["player"] = player_url(t["path"])
        return t

    series = []
    for child in tree["children"]:
        tracks = [stamp(t) for t in flatten(child)]
        series.append({
            "title": nice(child["path"].rsplit("/", 1)[-1]),
            "category": category_for(child["path"]),
            "page": folder_url(child["path"]),
            "count": len(tracks),
            "tracks": tracks,
        })
    loose = [stamp({"title": track_title(f), "group": "", "path": f}) for f in tree["files"]]

    new_total = sum(s["count"] for s in series) + len(loose)
    old_total = sum(s.get("count", 0) for s in old.get("series", [])) + len(old.get("loose", []))
    if old_total and new_total < old_total * 0.5:
        print(f"Gurmatveechar: only {new_total} of {old_total} tracks found, kept previous data", file=sys.stderr)
        return
    save("audio.json", {"updated": NOW, "source": folder_url(root),
                        "stream": bool(CONFIG.get("stream_audio_on_site")),
                        "series": series, "loose": loose})
    print(f"Gurmatveechar: {len(series)} series, {new_total} recordings ({_requests} pages)")


# -------------------------------------------------------- Instagram (Behold)
def update_instagram():
    url = CONFIG.get("behold_feed_url")
    if not url:
        return
    try:
        raw = json.loads(fetch(url))
    except Exception as e:
        print(f"Instagram: kept previous data ({e})", file=sys.stderr)
        return
    posts_in = raw.get("posts", []) if isinstance(raw, dict) else raw
    posts = []
    for p in posts_in[:12]:
        sizes = p.get("sizes") or {}
        img = ((sizes.get("medium") or {}).get("mediaUrl")
               or p.get("thumbnailUrl") or p.get("mediaUrl") or "")
        posts.append({
            "url": p.get("permalink", ""),
            "image": img,
            "caption": (p.get("prunedCaption") or p.get("caption") or "").strip()[:300],
            "date": (p.get("timestamp") or "")[:10],
        })
    save("instagram.json", {"updated": NOW, "posts": posts})
    print(f"Instagram: {len(posts)} posts")


if __name__ == "__main__":
    for step in (update_youtube, update_audio, update_instagram):
        try:
            step()
        except Exception as e:  # one failing source never blocks the others
            print(f"{step.__name__} failed: {e}", file=sys.stderr)
