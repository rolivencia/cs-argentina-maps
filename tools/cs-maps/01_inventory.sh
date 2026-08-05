#!/usr/bin/env bash
# Step 1 - Inventory. Harvest the complete Wayback CDX index for the domain.
#
# This is the map of everything the Internet Archive holds. Nothing else in the
# pipeline talks to the CDX server for the whole-domain view; every later step
# reads data/cdx/inventory.tsv.
#
#   ./01_inventory.sh            # 2000-2007 (the CS era)
#   FROM=2000 TO=2012 ./01_inventory.sh
set -euo pipefail
cd "$(dirname "$0")"
. ./lib.sh
mkdirs

FIELDS="timestamp,original,mimetype,statuscode,digest,length"

echo "==> Whole-domain inventory ($DOMAIN, $FROM-$TO)"
cdx_harvest "url=$DOMAIN&matchType=domain&from=$FROM&to=$TO&fl=$FIELDS&collapse=digest" \
  "$DATA/cdx/inventory.tsv"

# Payload directories, queried separately and unfiltered by date. The download
# gateways (leech.cgi / load.cgi) point at these paths, and a zip may have been
# crawled in a year the HTML pages were not.
for prefix in imaps packs screens maps pics images; do
  echo "==> Prefix scan: /$prefix/"
  cdx_harvest "url=$DOMAIN/$prefix/*&matchType=prefix&fl=$FIELDS&collapse=digest" \
    "$DATA/cdx/prefix_$prefix.tsv" || true
done

echo
echo "Inventory summary"
echo "-----------------"
awk '{print $3}' "$DATA/cdx/inventory.tsv" | sort | uniq -c | sort -rn | head -15
echo
echo "Captures per year:"
awk '{print substr($1,1,4)}' "$DATA/cdx/inventory.tsv" | sort | uniq -c
echo
echo "Archived payload candidates (non-HTML under the prefix scans):"
cat "$DATA"/cdx/prefix_*.tsv 2>/dev/null \
  | awk '$4=="200" && $3 !~ /text\/html/ {n++} END{print "  " n+0 " captures"}'
