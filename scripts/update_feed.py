#!/usr/bin/env python3
"""Daily feed updater for the HKGA Players 2026 dashboard.

Pulls recent Hong Kong golf tournament results & news from public sources,
merges them into data/feed.json (deduped, newest first, capped at 60 items).

Runs inside GitHub Actions (see .github/workflows/daily.yml).
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED = ROOT / "data" / "feed.json"
UA = {"User-Agent": "hkga-dashboard-feed/1.0 (+github actions; personal project)"}
TIMEOUT = 30

# Squad surnames/keywords used to flag likely GAHKC-relevant items
KEYWORDS = re.compile(
    r"hong\s*kong|gahkc|hkga|arianna lau|sabrina wong|felicia hughes|jun tian|tian jun|"
    r"jeffrey shen|siuue wu|sophie han|peiqi hou|doris sung|joseph cao|alanna tee|"
    r"markus lam|isaac lee|lander lee|zabby|leung hei|hanny wang|elin wang|vivianne kan|"
    r"kitty tang|sonya wong|esmeralda zhou|isaac timso|ricardo fu|taichi kho|jason hak",
    re.I,
)


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def safe(fn, label):
    try:
        items = fn()
        print(f"[ok] {label}: {len(items)} items")
        return items
    except Exception as e:  # noqa: BLE001 - keep the feed alive on any source failure
        print(f"[warn] {label} failed: {e}", file=sys.stderr)
        return []


def wp_posts(base, source, search=None, per_page=20):
    """WordPress REST API sources (apgc.online, agif.asia)."""
    url = f"{base}/wp-json/wp/v2/posts?per_page={per_page}&_fields=title,link,date_gmt"
    if search:
        url += f"&search={search}"
    posts = json.loads(fetch(url))
    out = []
    for p in posts:
        title = re.sub(r"<[^>]+>", "", p.get("title", {}).get("rendered", "")).strip()
        title = title.replace("&#8217;", "'").replace("&#8216;", "'").replace("&amp;", "&") \
                     .replace("&#8211;", "–").replace("&#8220;", '"').replace("&#8221;", '"')
        if not title:
            continue
        if search is None and not KEYWORDS.search(title):
            continue
        out.append({
            "date": p.get("date_gmt", "") + "Z" if p.get("date_gmt") else "",
            "source": source,
            "title": title,
            "url": p.get("link", ""),
            "kind": "result" if re.search(r"win|champion|title|crown|triumph|result|lead", title, re.I) else "news",
        })
    return out


def hkga_news():
    """GAHKC latest-news is JS-rendered; r.jina.ai returns a markdown render."""
    md = fetch("https://r.jina.ai/https://www.hkga.com/latest-news/")
    out = []
    for m in re.finditer(r"\[([^\]\[]{10,120})\]\((https://www\.hkga\.com/post/[a-z0-9-]+)\)", md):
        title, url = m.group(1).strip(), m.group(2)
        if title.lower() in {"read more", "latest news"} or title.startswith("!"):
            continue
        out.append({"date": "", "source": "hkga.com", "title": title, "url": url, "kind": "news"})
    # de-dup within page, keep order
    seen, uniq = set(), []
    for it in out:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    return uniq[:12]


def hkga_local_tournaments():
    """New local tournament pages (results are posted onto these pages)."""
    md = fetch("https://r.jina.ai/https://www.hkga.com/tournaments/local")
    out = []
    for m in re.finditer(r"\[([^\]\[]{10,120})\]\((https://www\.hkga\.com/tournaments/local/[a-z0-9-]+)\)", md):
        title, url = m.group(1).strip(), m.group(2)
        if "2026" not in title and "2026" not in url:
            continue
        out.append({"date": "", "source": "GAHKC tournaments", "title": title, "url": url, "kind": "result"})
    seen, uniq = set(), []
    for it in out:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        uniq.append(it)
    return uniq[:15]


def google_news():
    xml = fetch("https://news.google.com/rss/search?q=%22Hong%20Kong%22%20golf%20(junior%20OR%20amateur%20OR%20championship)&hl=en-US&gl=US&ceid=US:en")
    root = ET.fromstring(xml)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        src = item.findtext("source") or "Google News"
        if not title or not re.search(r"golf", title, re.I):
            continue
        try:
            date = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            date = ""
        out.append({"date": date, "source": src, "title": title, "url": link, "kind": "news"})
    return out[:15]


def main():
    existing = {"items": []}
    if FEED.exists():
        try:
            existing = json.loads(FEED.read_text())
        except Exception:
            pass

    new_items = []
    new_items += safe(lambda: wp_posts("https://www.apgc.online", "APGC"), "apgc")
    new_items += safe(lambda: wp_posts("https://agif.asia", "AGIF", search="hong%20kong"), "agif")
    new_items += safe(hkga_news, "hkga news")
    new_items += safe(hkga_local_tournaments, "hkga tournaments")
    new_items += safe(google_news, "google news")

    # merge with existing, dedupe by url (fallback title)
    def key(it):
        return it.get("url") or it.get("title", "")

    merged, seen = [], set()
    for it in new_items + existing.get("items", []):
        k = key(it)
        if not k or k in seen:
            continue
        seen.add(k)
        merged.append(it)

    # sort: dated items newest first, undated keep insertion order after dated
    dated = [i for i in merged if i.get("date")]
    undated = [i for i in merged if not i.get("date")]
    dated.sort(key=lambda i: i["date"], reverse=True)
    merged = (dated + undated)[:60]

    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "items": merged,
    }, ensure_ascii=False, indent=1))
    print(f"[done] wrote {len(merged)} items")


if __name__ == "__main__":
    main()
