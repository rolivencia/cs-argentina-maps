#!/usr/bin/env bash
# Step 2 - Catalogue pages. Download the human-readable side of the site:
# the alphabetical map indexes, the review pages and the screenshots.
#
# These are what actually carry the knowledge - map name, author, description,
# review score, release date. Even if no single .zip survives, this is the part
# of cs-maps.co.uk worth saving, and it is the part most likely to be intact.
set -euo pipefail
cd "$(dirname "$0")"
. ./lib.sh
mkdirs

INV="$DATA/cdx/inventory.tsv"
[ -s "$INV" ] || { echo "Run ./01_inventory.sh first." >&2; exit 1; }

# One capture per (url, year): the site was re-crawled often and consecutive
# captures are usually identical, but a year apart the catalogue had grown.
awk '$4=="200" && $3 ~ /text\/(html|plain)/ {
       if ($2 ~ /cgi-bin\/(leech|load)\.cgi/) next   # gateways, handled in step 4
       key = substr($1,1,4) "\t" $2
       if (!(key in seen)) { seen[key]=1; print $1 "\t" $2 }
     }' "$INV" | sort > "$DATA/cdx/pages.tsv"

total=$(wc -l < "$DATA/cdx/pages.tsv")
echo "==> $total page captures to fetch"

i=0
while IFS=$'\t' read -r ts url; do
  i=$((i + 1))
  safe=$(printf '%s' "$url" | sed -e 's#^https\?://##' -e 's#[^A-Za-z0-9._-]#_#g')
  out="$DATA/pages/${ts}__${safe}.html"
  [ -s "$out" ] && continue
  printf '[%d/%d] %s %s\n' "$i" "$total" "$ts" "$url"
  wb_get "$(raw_url "$ts" "$url")" "$out" || rm -f "$out"
done < "$DATA/cdx/pages.tsv"

# Screenshots are small, numerous, and irreplaceable - many maps survive only
# as somebody's 2001 screenshot.
awk '$4=="200" && $3 ~ /^image\// {print $1 "\t" $2}' \
  "$INV" "$DATA"/cdx/prefix_screens.tsv "$DATA"/cdx/prefix_pics.tsv 2>/dev/null \
  | sort -u > "$DATA/cdx/images.tsv"

echo "==> $(wc -l < "$DATA/cdx/images.tsv") image captures"
while IFS=$'\t' read -r ts url; do
  safe=$(printf '%s' "$url" | sed -e 's#^https\?://##' -e 's#[^A-Za-z0-9._-]#_#g')
  out="$DATA/screens/${safe}"
  [ -s "$out" ] && continue
  wb_get "$(raw_url "$ts" "$url")" "$out" || rm -f "$out"
done < "$DATA/cdx/images.tsv"

echo "Done. Pages in $DATA/pages, images in $DATA/screens"
