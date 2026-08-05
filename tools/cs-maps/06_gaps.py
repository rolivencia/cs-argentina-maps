#!/usr/bin/env python3
"""Step 6 - Close the gaps from other archives.

Whatever the Wayback Machine could not give us, something else probably can.
cs-maps.co.uk was a mirror, not an origin: the same 2001 map files were pressed
onto shovelware CDs and re-packed into map packs that are still online.

The single best match is the two-disc "Mods and Maps - Counter-Strike" CD-ROM
(Internet Archive item `mam-counter-strike`, 2001), which ships ~1,155 map zips
plus a screenshot for each - the same vintage and largely the same names as the
cs-maps.co.uk catalogue. Its per-disc file listings are plain text and are read
directly here, so coverage can be measured before downloading 1.3 GB of disc
images.

Writes data/reports/gaps.csv: every catalogue map, whether we already have it,
and which external source is known to carry it.
"""
import csv
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA", os.path.join(HERE, "data"))
CACHE = os.path.join(DATA, "sources")

# item identifier -> file listings inside it that we can read cheaply
LISTINGS = {
    "mam-counter-strike": ["MAMCS_A_files.txt", "MAMCS_B_files.txt"],
}

# Larger collections worth a manual look; no machine-readable listing, so they
# are reported as leads rather than matched automatically.
LEADS = [
    ("archive.org item", "cs-1.6-mega-map-pack-v-2018.1.7z", "3.2 GB single .7z, 2018 aggregate pack"),
    ("archive.org item", "hl-counter-strike", "4.0 GB Half-Life/CS collection"),
    ("archive.org item", "half-life-won-1110-and-hl-1-mods-collection", "WON-era mods and maps"),
    ("website", "https://www.17buddies.rocks/", "large curated CS 1.6 custom-map database, per-map pages"),
    ("website", "https://gamebanana.com/games/100", "CS 1.6 section, has an open search API"),
    ("website", "https://www.gamemaps.com/cs/maps", "custom CS map mirror"),
]

VERSION_NOISE = re.compile(
    r"(_|-)?(final|full|fix|fixed|new|old|orig|"
    r"beta\d*|b\d+|alpha\d*|a\d+|rc\d+|v\d+(\.\d+)*|\d*k\d*|"
    r"zp|small|lite|update|test\d*)$", re.I)

# Gametype prefixes. A stem may never be stripped back to one of these: without
# the guard cs_alpha and cs_final both reduce to "cs" and then match each other
# and every other cs_ map.
PREFIXES = {"cs", "de", "as", "fy", "awp", "es", "ka", "aim", "he", "gg",
            "zm", "surf", "kz", "pa", "an", "csde"}


def canon(name):
    """Collapse a map filename to its identity, dropping version churn.

    cs_dust_b6 and cs_dust-final both reduce to cs_dust, so a map is not
    reported missing when only a different beta of it survives.
    """
    n = os.path.splitext(name.lower())[0]
    n = re.sub(r"[^a-z0-9_]+", "_", n).strip("_")
    prev = None
    while n != prev:
        prev = n
        stripped = VERSION_NOISE.sub("", n).rstrip("_-")
        if not stripped or stripped in PREFIXES or len(stripped) < 4:
            break
        n = stripped
    return n


def fetch(item, fname):
    os.makedirs(CACHE, exist_ok=True)
    local = os.path.join(CACHE, f"{item}__{fname}")
    if not os.path.exists(local):
        url = f"https://archive.org/download/{item}/{fname}"
        print(f"  fetching {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "cs-maps-archival/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(local, "wb") as fh:
            fh.write(r.read())
    with open(local, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def build_index():
    """canonical name -> list of 'item:filename'"""
    idx = {}
    for item, files in LISTINGS.items():
        for fname in files:
            try:
                text = fetch(item, fname)
            except Exception as exc:                     # offline / item moved
                print(f"  ! {item}/{fname}: {exc}", file=sys.stderr)
                continue
            for hit in re.findall(r"[A-Za-z0-9_()+.\-]+\.(?:zip|exe|rar|bsp)", text):
                idx.setdefault(canon(hit), []).append(f"{item}:{hit}")
    return idx


def main():
    cat_path = os.path.join(DATA, "reports", "catalogue.csv")
    if not os.path.exists(cat_path):
        print("Run ./03_parse.py first.", file=sys.stderr)
        return 1
    with open(cat_path, encoding="utf-8") as fh:
        catalogue = list(csv.DictReader(fh))

    have = set()
    man_path = os.path.join(DATA, "reports", "manifest.csv")
    if os.path.exists(man_path):
        with open(man_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["status"] == "ok":
                    have.add(canon(os.path.basename(row["file"])))

    print("==> indexing external sources")
    idx = build_index()
    print(f"  {len(idx)} distinct map names indexed from CD-ROM listings")

    rows, recovered, elsewhere, lost = [], 0, 0, 0
    for rec in catalogue:
        key = canon(rec["file"])
        got = key in have
        ext = idx.get(key, [])
        if got:
            state, recovered = "recovered", recovered + 1
        elif ext:
            state, elsewhere = "available-elsewhere", elsewhere + 1
        else:
            state, lost = "not-located", lost + 1
        rows.append({
            "map": rec["map"], "file": rec["file"], "category": rec["category"],
            "canonical": key, "state": state,
            "external_sources": "; ".join(sorted(set(ext))[:4]),
            "first_seen": rec["first_seen"],
            "payload_url": rec["payload_url"],
        })

    out = os.path.join(DATA, "reports", "gaps.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else
                           ["map", "file", "category", "canonical", "state",
                            "external_sources", "first_seen", "payload_url"])
        w.writeheader()
        w.writerows(rows)

    total = len(rows) or 1
    print(f"\n{len(rows)} maps in the cs-maps.co.uk catalogue")
    print(f"  recovered from Wayback      {recovered:5d}  ({recovered*100//total}%)")
    print(f"  available from a mirror     {elsewhere:5d}  ({elsewhere*100//total}%)")
    print(f"  not located anywhere yet    {lost:5d}  ({lost*100//total}%)")
    print(f"-> {out}")
    print("\nLeads for the 'not located' tail:")
    for kind, ref, why in LEADS:
        print(f"  [{kind}] {ref}\n      {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
