#!/usr/bin/env bash
# Step 4 - Payloads. Pull down whatever map archives the Wayback Machine
# actually holds the bytes for.
#
# The decisive question for the whole project is answered here: the site linked
# every download through /cgi-bin/leech.cgi, and those gateway captures are
# text/html. If the crawler never followed through to the .zip underneath, no
# amount of Wayback work will produce the files and step 6 takes over.
set -euo pipefail
cd "$(dirname "$0")"
. ./lib.sh
mkdirs

LIST="$DATA/cdx/payload_captures.tsv"

# Real files only: HTTP 200, and a content type that is not the site's HTML
# error/gateway page.
cat "$DATA"/cdx/prefix_imaps.tsv "$DATA"/cdx/prefix_packs.tsv 2>/dev/null \
  | awk '$4=="200" && $3 !~ /text\/html/ && $2 ~ /\.(zip|exe|rar|bsp|wad)$/i {
           if (!seen[$2]++) print $1 "\t" $2 "\t" $3 "\t" $6
         }' | sort -k2 > "$LIST" || true

n=$(wc -l < "$LIST" 2>/dev/null || echo 0)
echo "==> $n archived map archives available"

if [ "$n" -eq 0 ]; then
  cat <<'MSG'

None of the .zip payloads were captured with real content.

That is the expected outcome if the crawler only ever walked the gateway links
(/cgi-bin/leech.cgi?...) and never dereferenced them. The catalogue, the
reviews and the screenshots are still recoverable from steps 2-3 - and the
files themselves are recoverable from the mirrors in step 6, keyed by the
name list this pipeline just produced.

Run: ./06_gaps.py
MSG
  exit 0
fi

echo "Total bytes: $(awk -F'\t' '{s+=$4} END{printf "%.1f MB", s/1048576}' "$LIST")"
i=0
while IFS=$'\t' read -r ts url mime len; do
  i=$((i + 1))
  rel=$(printf '%s' "$url" | sed -e 's#^https\?://[^/]*/##')
  out="$DATA/payloads/$rel"
  mkdir -p "$(dirname "$out")"
  [ -s "$out" ] && continue
  printf '[%d/%d] %s (%s)\n' "$i" "$n" "$rel" "$mime"
  wb_get "$(raw_url "$ts" "$url")" "$out" || rm -f "$out"
done < "$LIST"

echo "Done. Files under $DATA/payloads - now run ./05_verify.py"
