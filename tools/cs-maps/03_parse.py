#!/usr/bin/env python3
"""Step 3 - Build the catalogue.

Two independent sources are merged into one list of maps:

  1. The CDX rows for the download gateways. cs-maps.co.uk never linked a zip
     directly; it went through a counter script, and the real path is sitting
     in the query string:

       /cgi-bin/leech.cgi?imaps/asmaps/as_alpine.zip&        (2001 layout)
       /cgi-bin/load.cgi?http://www.cs-maps.co.uk/imaps/cs/cs_bank.zip  (2007)

     Every one of those is a map that existed on the site, whether or not the
     bytes were ever crawled. This yields the authoritative name list.

  2. The catalogue HTML fetched in step 2, for the surrounding prose - author,
     description, review text. Scraped generically (link plus row text) because
     the 2001 and 2007 templates differ.

Writes data/reports/catalogue.csv and data/reports/payload_urls.txt.
"""
import csv
import html
import os
import re
import sys
import urllib.parse
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA", os.path.join(HERE, "data"))

GATEWAY = re.compile(r"/cgi-bin/(?:leech|load)\.cgi\?(.+)$", re.I)
MAPFILE = re.compile(r"([A-Za-z0-9_()+.\-]+\.(?:zip|exe|rar|bsp))", re.I)


def payload_from_gateway(url):
    """Return the absolute URL of the file a gateway link pointed at."""
    m = GATEWAY.search(url)
    if not m:
        return None
    arg = urllib.parse.unquote(m.group(1)).rstrip("&")
    if arg.lower().startswith("http"):
        return arg.split("&")[0]
    arg = arg.split("&")[0].lstrip("/")
    if not MAPFILE.search(arg):
        return None
    return "http://www.cs-maps.co.uk/" + arg


def read_cdx(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 4:
                yield parts  # timestamp original mimetype statuscode [digest length]


def scrape_pages(pagedir):
    """map filename -> free text seen near a link to it."""
    notes = defaultdict(set)
    if not os.path.isdir(pagedir):
        return notes
    row_re = re.compile(r"<tr\b.*?</tr>", re.I | re.S)
    tag_re = re.compile(r"<[^>]+>")
    for name in sorted(os.listdir(pagedir)):
        try:
            with open(os.path.join(pagedir, name), encoding="utf-8",
                      errors="replace") as fh:
                doc = fh.read()
        except OSError:
            continue
        # Table rows are the natural record boundary in both site templates.
        for chunk in row_re.findall(doc) or [doc]:
            files = {f.lower() for f in MAPFILE.findall(chunk)}
            if not files:
                continue
            text = html.unescape(tag_re.sub(" ", chunk))
            text = " ".join(text.split())
            if 0 < len(text) <= 600:
                for f in files:
                    notes[f].add(text)
    return notes


def main():
    maps = {}          # basename -> record
    payload_urls = {}  # absolute url -> category

    for src in ("inventory", "prefix_imaps", "prefix_packs"):
        for row in read_cdx(os.path.join(DATA, "cdx", f"{src}.tsv")):
            ts, url, mime, status = row[0], row[1], row[2], row[3]
            target = payload_from_gateway(url)
            direct = None
            if target is None and MAPFILE.search(url) and "/cgi-bin/" not in url:
                direct = url.split("?")[0]
            best = target or direct
            if not best:
                continue
            path = urllib.parse.urlparse(best).path
            base = os.path.basename(path).lower()
            category = path.strip("/").split("/")
            category = category[1] if len(category) > 2 else (category[0] if category else "")
            rec = maps.setdefault(base, {
                "map": os.path.splitext(base)[0],
                "file": base,
                "category": category,
                "payload_url": best,
                "first_seen": ts,
                "last_seen": ts,
                "gateway_captures": 0,
                "direct_captures": 0,
                "direct_status": "",
                "direct_mime": "",
                "notes": "",
            })
            rec["first_seen"] = min(rec["first_seen"], ts)
            rec["last_seen"] = max(rec["last_seen"], ts)
            if direct:
                rec["direct_captures"] += 1
                # A 200 that is not text/html means the actual bytes are held.
                if status == "200" and "text/html" not in mime:
                    rec["direct_status"] = "200"
                    rec["direct_mime"] = mime
            else:
                rec["gateway_captures"] += 1
            payload_urls[best] = category

    notes = scrape_pages(os.path.join(DATA, "pages"))
    for base, rec in maps.items():
        if base in notes:
            rec["notes"] = " | ".join(sorted(notes[base]))[:1000]

    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    out = os.path.join(DATA, "reports", "catalogue.csv")
    cols = ["map", "file", "category", "payload_url", "first_seen", "last_seen",
            "gateway_captures", "direct_captures", "direct_status",
            "direct_mime", "notes"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for base in sorted(maps):
            w.writerow(maps[base])

    with open(os.path.join(DATA, "reports", "payload_urls.txt"), "w",
              encoding="utf-8") as fh:
        for url in sorted(payload_urls):
            fh.write(url + "\n")

    have = sum(1 for r in maps.values() if r["direct_status"] == "200")
    print(f"catalogue: {len(maps)} distinct map files")
    print(f"  with archived bytes (direct 200, non-HTML): {have}")
    print(f"  known only as a gateway link:               {len(maps) - have}")
    by_cat = defaultdict(int)
    for r in maps.values():
        by_cat[r["category"]] += 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"    {cat or '(root)':12s} {n}")
    print(f"-> {out}")
    if not maps:
        print("No maps found - did step 1 write data/cdx/inventory.tsv?",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
