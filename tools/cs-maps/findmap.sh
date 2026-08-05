#!/usr/bin/env bash
# Hunt for one specific map by name fragment, across every source at once.
#
#   ./findmap.sh little
#   ./findmap.sh fy_little
#   DOMAIN=some-other-site.com ./findmap.sh caminito
#
# Written for the case where you remember uploading something but no search
# engine has heard of it: the CDX server matches on the URL itself, so it finds
# files that were never linked from a page a crawler indexed.
set -euo pipefail
cd "$(dirname "$0")"
. ./lib.sh
mkdirs

Q="${1:?usage: ./findmap.sh <name-fragment>}"
esc=$(printf '%s' "$Q" | sed 's/[.[\*^$()+?{}|]/\\&/g')
tmp=$(mktemp)

echo "=============================================================="
echo " Hunting: $Q"
echo "=============================================================="

echo
echo "[1] $DOMAIN, all years (URL regex match)"
if wb_get "$CDX?url=$DOMAIN&matchType=domain&fl=timestamp,original,mimetype,statuscode,length&collapse=digest&filter=original:.*(?i)$esc.*" "$tmp"; then
  if [ -s "$tmp" ]; then cat "$tmp"; else echo "  (no captures)"; fi
fi

echo
echo "[2] Local catalogue built by this toolkit"
for f in "$DATA"/reports/catalogue.csv "$DATA"/reports/gaps.csv; do
  [ -s "$f" ] && { echo "  -- $(basename "$f")"; grep -i -- "$Q" "$f" || echo "     (no match)"; }
done

echo
echo "[3] The 2001 'Mods and Maps - Counter-Strike' CD-ROM listings"
for d in A B; do
  l="$DATA/sources/mam-counter-strike__MAMCS_${d}_files.txt"
  [ -s "$l" ] || curl -sS --max-time 120 -A "$UA" \
      "https://archive.org/download/mam-counter-strike/MAMCS_${d}_files.txt" -o "$l" || true
  [ -s "$l" ] && grep -i -- "$Q" "$l" | sed "s/^/  disc $d: /" || true
done | grep . || echo "  (no match on either disc)"

echo
echo "[4] Internet Archive items with a fully enumerated file listing"
# Some items expose every internal path through the metadata API, which makes
# them searchable without downloading gigabytes. Items stored as one solid .7z
# do not, and are listed as manual leads at the end instead.
for item in hl-counter-strike half-life-won-1110-and-hl-1-mods-collection cstrike_202503; do
  meta="$DATA/sources/${item}__metadata.json"
  [ -s "$meta" ] || curl -sS --max-time 120 -A "$UA" \
      "https://archive.org/metadata/$item" -o "$meta" || true
  [ -s "$meta" ] && python3 - "$meta" "$item" "$Q" <<'PY'
import json, sys
meta, item, q = sys.argv[1], sys.argv[2], sys.argv[3].lower()
try:
    names = [f.get("name", "") for f in json.load(open(meta)).get("files", [])]
except Exception:
    sys.exit(0)
hits = [n for n in names if q in n.lower()]
print(f"  {item}: {len(hits)} of {len(names)} paths match")
for h in hits[:12]:
    print(f"      {h}")
PY
done

echo
echo "[5] Internet Archive full-text / item search"
curl -sS --max-time 60 -A "$UA" \
  "https://archive.org/advancedsearch.php?q=$(printf '%s' "$Q" | sed 's/ /+/g')&fl%5B%5D=identifier&fl%5B%5D=title&rows=8&output=json" \
  | python3 -c "
import json,sys
try:
    docs=json.load(sys.stdin)['response']['docs']
except Exception:
    docs=[]
print('\n'.join(f\"  {d['identifier']}  -  {str(d.get('title',''))[:70]}\" for d in docs) or '  (no items)')
"

echo
echo "[6] GameBanana (open search API)"
curl -sS --max-time 40 -A "$UA" \
  "https://gamebanana.com/apiv11/Util/Search/Results?_sModelName=Mod&_sSearchString=$Q&_nPerpage=10" \
  | python3 -c "
import json,sys
try: recs=json.load(sys.stdin).get('_aRecords',[])
except Exception: recs=[]
print('\n'.join(f\"  {r.get('_sName')}\" for r in recs) or '  (no mods)')
"

echo
echo "Manual leads (these block scripted access - open in a browser):"
echo "  https://www.17buddies.rocks/    search '$Q' - deepest CS 1.6 map database"
echo "  https://www.gamemaps.com/cs/maps"
echo "  https://csm.dev/  and  https://twhl.info/  - mapper communities, old threads"
rm -f "$tmp"
