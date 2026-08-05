# cs-maps.co.uk retrieval toolkit

Recovers what is left of the Counter-Strike map archive that ran at
cs-maps.co.uk from 2000 to 2007. Background, findings and the reasoning behind
each step: [`docs/cs-maps-co-uk-retrieval-plan.md`](../../docs/cs-maps-co-uk-retrieval-plan.md).

Requires `bash`, `curl`, `python3` (stdlib only), and GNU coreutils.

## Run

```bash
cd tools/cs-maps
./01_inventory.sh     # Wayback CDX harvest          -> data/cdx/
./02_catalogue.sh     # index pages + screenshots    -> data/pages/, data/screens/
./03_parse.py         # map list with metadata       -> data/reports/catalogue.csv
./04_payloads.sh      # the .zip files, if archived  -> data/payloads/
./05_verify.py        # integrity + dedupe           -> data/reports/manifest.csv
./06_gaps.py          # what is missing, and where   -> data/reports/gaps.csv
```

Every step is resumable — already-downloaded files are skipped, so re-running
after an interruption picks up where it stopped. Expect a full run to take
hours: requests are paced at 1/second on purpose.

Look for one specific map across all sources:

```bash
./findmap.sh little
```

## Knobs

| Variable | Default | Meaning |
|---|---|---|
| `FROM` / `TO` | `2000` / `2007` | Year range for the domain-wide inventory. Prefix scans ignore it deliberately. |
| `PACE` | `1` | Seconds between requests. Leave it alone. |
| `MAX_TRIES` | `6` | Retries per request, exponential backoff on 429/503. |
| `DATA` | `./data` | Output root. |
| `DOMAIN` | `cs-maps.co.uk` | The scripts are not hardcoded to this site. |

## Output

```
data/
  cdx/       raw CDX index rows: the inventory and per-prefix scans
  pages/     catalogue and review HTML, one file per capture, original bytes
  screens/   map screenshots
  payloads/  map archives, mirroring the site's own directory layout
  sources/   cached file listings from external archives
  reports/   catalogue.csv, manifest.csv, gaps.csv  <- the deliverables
```

`data/` is gitignored — it is a few GB of third-party files. Commit the
`reports/` CSVs if you want the findings tracked.

## Notes

- All fetches use the Wayback `id_` raw-replay form, which returns the original
  bytes without the archive toolbar injected. Without it, binaries arrive
  corrupted.
- `01_inventory.sh` paginates the CDX server with resume keys. A plain browser
  query silently truncates at the row cap, which is how a site like this looks
  much smaller than it is.
- The site routed all downloads through `/cgi-bin/leech.cgi?<path>&`, so map
  filenames must be decoded out of query strings rather than read from links.
  `03_parse.py` does this.
- `05_verify.py` exists because the Wayback Machine returns 200 for soft-404s.
  Trust `manifest.csv`, not the file count.
