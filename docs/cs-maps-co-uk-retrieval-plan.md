# Recovering cs-maps.co.uk (2000–2007)

A plan for tracking down and retrieving what is left of cs-maps.co.uk, the
British Counter-Strike custom-map archive. Tooling lives in
[`tools/cs-maps/`](../tools/cs-maps/).

## What is actually still there

**The domain is gone but the site is not.** `cs-maps.co.uk` resolves today to
`51.38.84.144` and serves a Grav CMS site for "Rich Lee Handyman" in
Maidenhead. Nothing of the map archive survives at the origin — every capture
from roughly 2013 onward belongs to unrelated owners. The live site is not a
source; ignore it.

**The Wayback Machine holds the site, and holds it densely for exactly the
period of interest.** The heaviest crawling ran March–July 2001, with the
crawler walking the alphabetical map index page by page — thousands of distinct
URLs, one per map. Coverage thins after 2002 but continues through to December
2007, which is the tail end of the window.

**The catalogue is recoverable with high confidence.** Map names, categories,
review pages and screenshots are all present as `text/html` and `image/jpeg`
captures.

**Whether the map files themselves are recoverable is the open question**, and
it turns on one detail of how the site was built (below).

## The site's anatomy, reconstructed

Worth understanding before crawling, because it dictates the whole approach.

| Area | URLs |
|---|---|
| Front page | `/index.htm`, `/first.shtml`, `/first.asp`, `/nav.htm`, `/nav2.htm`, `/header.htm` |
| Map indexes (2001) | `/cgi-bin/index.cgi`, `indexas.cgi`, `indexcs.cgi`, `indexcsa2d.cgi`, `indexcse2m.cgi`, `indexcss2z.cgi`, `indexde.cgi` |
| Reviews | `/reviews1.htm` … `/reviews5.htm`, `/maps/previews.html` |
| Screenshots | `/screens/*.jpg`, `/pics/*.jpg` |
| Map packs | `/packs.htm`, `/packs/*.zip`, `/packs/*.exe` |
| Other | `/clans.htm`, `/csdownloads.htm`, `/imapdownloads.htm`, `/leech.htm`, `/game.htm`, `/forum.htm` |

The `cs` category was split alphabetically into `a2d` / `e2m` / `s2z` — a
detail that matters, because a crawl that missed one of those three index pages
missed a third of the CS maps.

**Downloads never linked to a file directly.** They went through a counter
script, and the real path is in the query string:

```
2001:  /cgi-bin/leech.cgi?imaps/asmaps/as_alpine.zip&
       /cgi-bin/leech.cgi?imaps/csmaps/a2d/cs_bank.zip&
       /cgi-bin/leech.cgi?imaps/demaps/de_dust3.zip&
       /cgi-bin/leech.cgi?packs/Map-Pack-V2.zip&

2007:  /cgi-bin/load.cgi?http://www.cs-maps.co.uk/imaps/cs/cs_bank.zip
       /cgi-bin/load.cgi?http://www.cs-maps.co.uk/imaps/de/de_rats.zip
```

Note the 2007 rename: `imaps/csmaps/a2d/` became a flat `imaps/cs/`.

This indirection is the crux. **Every archived gateway URL is recorded as
`text/html`** — the crawler saved the counter script's response page, not the
zip behind it. Two possibilities follow, and the first thing the pipeline does
is decide between them:

- The crawler also fetched `/imaps/**/*.zip` directly (from a sitemap, another
  site's hotlink, or a later crawl). Then the files are there and downloadable.
- It never did. Then the Wayback Machine holds a complete *card catalogue* of
  the library with none of the books, and the files have to come from mirrors.

Either way the gateway URLs are valuable: they enumerate every map the site
ever carried, with a first-seen date. That name list is the real asset.

## The plan

Six steps, each a script in `tools/cs-maps/`, each writing to `data/` so a run
can be stopped and resumed.

```
cd tools/cs-maps
./01_inventory.sh     # CDX harvest -> data/cdx/*.tsv
./02_catalogue.sh     # index pages, reviews, screenshots
./03_parse.py         # -> data/reports/catalogue.csv
./04_payloads.sh      # the map archives, if they exist
./05_verify.py        # -> data/reports/manifest.csv
./06_gaps.py          # -> data/reports/gaps.csv
```

**1 — Inventory.** Harvest the full CDX index for the domain with resume-key
pagination, so nothing is lost to the row cap that truncates a plain browser
query. Also runs prefix scans over `/imaps/`, `/packs/`, `/screens/` *without*
a date filter, because a zip may have been crawled in a year the pages were
not. Its closing line reports the archived non-HTML payload count — that is the
answer to the crux question above.

**2 — Catalogue.** Fetch one capture per URL per year (the site was re-crawled
constantly; a year apart is where the catalogue actually changed) plus every
screenshot. Uses the `id_` raw-replay form so you get original bytes without
the Wayback toolbar injected. **Do this step even if step 4 finds nothing** —
the descriptions, reviews and screenshots are the part of cs-maps.co.uk that
exists nowhere else, and they are what makes a recovered zip identifiable.

**3 — Parse.** Decode every gateway URL back into the file it pointed at, merge
with the scraped page text, and emit `catalogue.csv`: map, category, payload
URL, first/last seen, whether real bytes were captured, surrounding prose.

**4 — Payloads.** Download every capture under `/imaps/` and `/packs/` that
returned 200 with a non-HTML content type. If there are none, the script says
so plainly and hands off to step 6.

**5 — Verify.** The Wayback Machine serves soft-404s and truncated transfers
with a 200. Each file is opened: zip integrity tested, `.bsp` members checked
for the GoldSrc version-30 header, SHA-256 recorded, byte-identical duplicates
flagged. Only files that pass count as recovered.

**6 — Close the gaps.** Everything still missing gets matched against other
archives by canonical name (version suffixes like `_b6`, `_beta2`, `2k`, `-ZP`
normalised away, so a surviving beta counts as a find).

## Where the files come from if Wayback does not have them

cs-maps.co.uk was a mirror, not an origin. The same 2001 files were pressed onto
shovelware CDs and re-packed for years afterward.

**Best match, and already verified: [`mam-counter-strike`](https://archive.org/details/mam-counter-strike)**
— the two-disc *Mods and Maps: Counter-Strike* CD-ROM (X Media Publishing,
2001), 1.67 GB. It carries **1,155 map zips, each with a matching screenshot**,
laid out as `data/cs_maps/`, `de_maps/`, `as_maps/`. Same vintage, overlapping
population.

I measured the overlap rather than assuming it: taking a 172-name sample of the
cs-maps.co.uk catalogue drawn from its `as`/`cs`/`de` gateway URLs, **139 (80%)
are present on those two discs**, most by exact filename. Several of the
remaining 33 are version variants (`cs_747_b6` vs `cs_747`) that a looser match
would also resolve. Both discs publish a plain-text file listing, so
`06_gaps.py` reads the index and computes coverage before you download a single
byte of the 1.3 GB of disc images.

Secondary sources, in rough order of usefulness:

| Source | Notes |
|---|---|
| [`cs-1.6-mega-map-pack-v-2018.1.7z`](https://archive.org/details/cs-1.6-mega-map-pack-v-2018.1.7z) | **1,745 maps**, the largest single lead. Stored as one solid `.7z`, so it cannot be searched remotely — the Internet Archive's in-archive viewer returns only a partial index and will not extract the `Map List.txt` manifest sitting inside it. Downloading all 3.2 GB is the only way to search it |
| [`hl-counter-strike`](https://archive.org/details/hl-counter-strike) | 4.0 GB, 418 paths, curated **by mapper name** with screenshots and source files. Fully enumerated through the metadata API, so `findmap.sh` searches it directly |
| [`half-life-won-1110-and-hl-1-mods-collection`](https://archive.org/details/half-life-won-1110-and-hl-1-mods-collection) | WON-era, right period |
| [17buddies.rocks](https://www.17buddies.rocks/) | Deepest curated CS 1.6 map database, per-map pages. Blocks scripted access — browser only |
| [GameBanana](https://gamebanana.com/games/100) | Open search API, used by `findmap.sh` |
| [GameMaps](https://www.gamemaps.com/cs/maps), [gamemodding.com](https://gamemodding.com/en/counter-strike-1-6/maps/) | Modern mirrors, mostly popular maps only |
| Magazine cover discs | `pc-action-05-01`, `pcgcd-0502` and similar on archive.org — 2001–2002 German/UK PC mags shipped CS map compilations |

## Practical notes

- **Run it from your own machine.** This container cannot reach
  `web.archive.org` at all (blocked by the sandbox network policy), and
  `archive.org`'s availability API rate-limits the shared egress IP to a
  permanent 429. Everything here was therefore written to be run locally,
  against sources I could verify by other means.
- **Be polite.** `lib.sh` paces requests at 1/second with exponential backoff on
  429/503. Do not raise it. A full run is a few thousand requests and will take
  hours; that is the correct speed.
- **`head -n -N` is GNU.** On macOS, `brew install coreutils` or run under
  Linux.
- **Expect a partial result and treat that as success.** A realistic outcome is
  the complete catalogue with descriptions and screenshots, most of the map
  files sourced from the 2001 CD-ROM, and a tail of a few hundred one-off betas
  that no longer exist anywhere. Recording what is *confirmed lost* is a real
  result too — `gaps.csv` is designed to be that record.
- **Licensing.** These are fan-made maps from 2000–2007, distributed freely at
  the time, with no consistent licence and mostly untraceable authors. Keep the
  original readme from inside each zip — it is usually the only attribution
  that exists — and credit the mapper by whatever handle it gives.

## Finding one specific map

`findmap.sh` searches all sources at once for a name fragment. It queries the
CDX server with a URL regex, which matters: it finds files by their *path*, so
it turns up things that were never linked from any page a search engine
indexed.

```
cd tools/cs-maps
./findmap.sh little
```

### On `fy_little` / `cs_little` / `*_little2k`

I checked every source reachable from here, under both prefixes, and found no
trace of any of them:

| Source | `fy_little` | `cs_little` |
|---|---|---|
| 2001 CD-ROM, both discs (1,155 maps) | no | no |
| `hl-counter-strike` (418 paths, by mapper) | no | no |
| GameBanana search API | 0 records | 0 records |
| csdownload.net `fy_` list (107 maps) | no | n/a |
| Web search | no | no |
| `cs-1.6-mega-map-pack` (1,745 maps) | **undetermined** — cannot be searched remotely | **undetermined** |

Two details make the `cs_little` negative stronger than a plain "not found".
The disc's `cs_l*` run is dense and continuous — `cs_lab`, `cs_labor_beta1`,
`cs_laboratorium`, `cs_labs`, `cs_labyrinth`, `cs_lager`, `cs_lambda_cruser`,
`cs_lan`, `cs_lasab`, `cs_lastfight`, `cs_lastman_beta3`, `cs_lawfirm`,
`cs_lazy`, `cs_legend`, `cs_library`, `cs_lifts`, `cs_lighthouse`, `cs_LNL1`,
`cs_lnl2`, `cs_lnl4`, `cs_longrun` — and nothing sits between `cs_lifts` and
`cs_lnl2`, which is exactly where `cs_little` would sort. So the map was not in
circulation on the shovelware channel as of 2001.

For `fy_`, the same disc contains **zero** `fy_` maps of any kind, which fits
the timeline: the fight-yard genre took off with `fy_iceworld` around 2002,
after the disc was pressed. A `fy_` map therefore cannot predate 2002, which
puts it in the *thin* part of the Wayback record.

The only `little` found anywhere is `de_little-city` on disc B — a different
map.

The one source that could still hold it and that I could not check is the
1,745-map mega pack, because a solid `.7z` cannot be indexed over HTTP. If the
CDX search below comes up empty, downloading that 3.2 GB and grepping its
`Map List.txt` is the next concrete step.

None of that is evidence of absence — it is evidence that the modern mirrors
never picked it up, which is the normal fate of a map uploaded once to one site.
That makes cs-maps.co.uk's own CDX index the strongest remaining lead, and the
gateway-URL trick the right tool: if you uploaded it there, the upload path is
in the index whether or not anyone ever linked to it.

Two things worth knowing before you run it. The dense 2001 crawl predates the
`fy_` genre, so a 2002–2007 upload sits in the *thin* part of the archive.
And the 2007 layout used flat `imaps/cs/` and `imaps/de/` directories — so an
`fy_` map most likely lived at `imaps/fy/`, a path worth probing directly:

```
cd tools/cs-maps
./findmap.sh little
./findmap.sh fy_
./findmap.sh cs_l

# and the direct prefix probe, all years, no date filter:
curl -sS 'https://web.archive.org/cdx/search/cdx?url=cs-maps.co.uk/imaps/fy/*&matchType=prefix&fl=timestamp,original,mimetype,statuscode'
```

If it turns up in the CDX index but only as a gateway capture, the last resort
is the mapper community rather than the archives: the old-timers at
[17buddies](https://www.17buddies.rocks/) and [TWHL](https://twhl.info/) keep
private collections far deeper than anything indexed, and a "does anyone have
this 2003 map" thread has a genuinely decent hit rate.
