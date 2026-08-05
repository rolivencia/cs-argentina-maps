# Shared helpers for the cs-maps.co.uk retrieval toolkit.
# Sourced by the numbered scripts; not meant to be run directly.

WB="https://web.archive.org"
CDX="$WB/cdx/search/cdx"
DOMAIN="${DOMAIN:-cs-maps.co.uk}"
FROM="${FROM:-2000}"
TO="${TO:-2007}"
UA="${UA:-cs-maps-archival/1.0 (personal archival research; contact via repo)}"

# The Wayback Machine throttles hard and returns 429/503 under load. Every
# request goes through here so one polite retry policy covers the whole run.
PACE="${PACE:-1}"        # seconds between requests
MAX_TRIES="${MAX_TRIES:-6}"

DATA="${DATA:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/data}"

wb_get() {
  # wb_get <url> <output-file>
  local url="$1" out="$2" try=1 code delay
  while [ "$try" -le "$MAX_TRIES" ]; do
    code=$(curl -sS --compressed --max-time 180 -A "$UA" -o "$out" -w '%{http_code}' "$url" || echo 000)
    case "$code" in
      200) sleep "$PACE"; return 0 ;;
      404|403) echo "  ! $code $url" >&2; return 1 ;;
      *)   delay=$(( 5 * (2 ** (try - 1)) ))
           echo "  . $code, retry ${try}/${MAX_TRIES} in ${delay}s" >&2
           sleep "$delay"; try=$((try + 1)) ;;
    esac
  done
  echo "  ! gave up on $url" >&2
  return 1
}

# Raw, unrewritten original bytes. Without the `id_` suffix the Wayback Machine
# injects its toolbar into HTML and rewrites links, which corrupts binaries and
# makes HTML harder to parse.
raw_url() { printf '%sweb/%sid_/%s' "$WB/" "$1" "$2"; }

# Paginated CDX harvest. The CDX server caps a single response, so we page with
# showResumeKey: the last non-empty line of each page is the key for the next.
cdx_harvest() {
  # cdx_harvest <cdx-query-string-without-resumeKey> <output-file>
  local q="$1" out="$2" page=0 key="" tmp n
  tmp=$(mktemp)
  : > "$out"
  while :; do
    page=$((page + 1))
    local url="$CDX?$q&limit=20000&showResumeKey=true"
    [ -n "$key" ] && url="$url&resumeKey=$key"
    echo "  page $page${key:+ (resume $key)}" >&2
    wb_get "$url" "$tmp" || break
    n=$(wc -l < "$tmp")
    # When more rows remain, the page ends with: <blank line>\n<resumeKey>.
    if [ "$n" -ge 2 ] && [ -z "$(tail -n 2 "$tmp" | head -n 1 | tr -d '[:space:]')" ]; then
      key=$(tail -n 1 "$tmp")
      head -n "$((n - 2))" "$tmp" >> "$out"
    else
      cat "$tmp" >> "$out"
      break
    fi
  done
  rm -f "$tmp"
  sed -i '/^$/d' "$out"
  echo "  -> $(wc -l < "$out") rows in $out" >&2
}

mkdirs() { mkdir -p "$DATA"/{cdx,pages,payloads,screens,reports}; }
