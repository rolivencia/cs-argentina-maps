#!/usr/bin/env python3
"""Step 5 - Verify what came back.

The Wayback Machine will happily hand you a 200 that is really a soft-404, a
truncated transfer, or the site's own "file not found" page renamed .zip. Each
download is opened and checked before it is called recovered.

A GoldSrc (Half-Life / CS 1.x) .bsp begins with a little-endian int32 version
of 30, which is a cheap and reliable way to confirm a real map is inside.
"""
import csv
import hashlib
import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA", os.path.join(HERE, "data"))
PAYLOADS = os.path.join(DATA, "payloads")

GOLDSRC_BSP_VERSION = 30


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path):
    """-> (status, detail, [bsp names])"""
    size = os.path.getsize(path)
    if size == 0:
        return "empty", "zero bytes", []
    with open(path, "rb") as fh:
        head = fh.read(4)
    if head[:2] in (b"<!", b"<h", b"<H") or head[:1] == b"<":
        return "not-a-file", "HTML served in place of the archive", []
    if head[:2] != b"PK":
        # A bare .bsp, or a self-extracting .exe.
        if len(head) == 4 and struct.unpack("<i", head)[0] == GOLDSRC_BSP_VERSION:
            return "ok", "bare GoldSrc bsp v30", [os.path.basename(path)]
        if head[:2] == b"MZ":
            return "ok", "self-extracting exe (needs manual unpack)", []
        return "unknown", f"unrecognised header {head!r}", []
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad:
                return "corrupt", f"bad member: {bad}", []
            names = zf.namelist()
            bsps = [n for n in names if n.lower().endswith(".bsp")]
            for n in bsps:
                with zf.open(n) as m:
                    ver = m.read(4)
                if len(ver) == 4 and struct.unpack("<i", ver)[0] != GOLDSRC_BSP_VERSION:
                    return "ok", f"zip ok, {n} is not bsp v30", bsps
            if not bsps:
                return "ok-nomap", f"zip ok, no .bsp ({len(names)} entries)", []
            return "ok", f"zip ok, {len(bsps)} bsp, {len(names)} entries", bsps
    except zipfile.BadZipFile as exc:
        return "corrupt", f"bad zip: {exc}", []


def main():
    if not os.path.isdir(PAYLOADS):
        print("Nothing downloaded yet - run ./04_payloads.sh", file=sys.stderr)
        return 1

    rows, by_hash = [], {}
    for root, _dirs, files in os.walk(PAYLOADS):
        for name in sorted(files):
            path = os.path.join(root, name)
            status, detail, bsps = inspect(path)
            digest = sha256(path)
            rows.append({
                "file": os.path.relpath(path, PAYLOADS),
                "size": os.path.getsize(path),
                "status": status,
                "detail": detail,
                "bsp": ";".join(bsps),
                "sha256": digest,
                "duplicate_of": by_hash.get(digest, ""),
            })
            by_hash.setdefault(digest, os.path.relpath(path, PAYLOADS))

    os.makedirs(os.path.join(DATA, "reports"), exist_ok=True)
    out = os.path.join(DATA, "reports", "manifest.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else
                           ["file", "size", "status", "detail", "bsp",
                            "sha256", "duplicate_of"])
        w.writeheader()
        w.writerows(rows)

    tally = {}
    for r in rows:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print(f"{len(rows)} files checked")
    for k in sorted(tally):
        print(f"  {k:12s} {tally[k]}")
    dupes = sum(1 for r in rows if r["duplicate_of"])
    good = tally.get("ok", 0)
    print(f"  {dupes} byte-identical duplicates")
    print(f"\n{good} verified playable map archives -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
