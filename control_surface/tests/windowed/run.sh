#!/usr/bin/env bash
# Run one windowed check (or all) in the pinned Blender and print its JSON result.
# Usage: ./run.sh [check_*.py ...]     (from WSL; the checks move the real mouse)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
B=${CONTROL_SURFACE_BLENDER:-/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe}
CONFIG=$(dirname "$B")/portable/config/control_surface_window.json
OUT=$(mktemp -d)
checks=("$@"); [ ${#checks[@]} -eq 0 ] && checks=("$HERE"/check_*.py)
for c in "${checks[@]}"; do
  c=$(cd "$(dirname "$c")" 2>/dev/null && pwd)/$(basename "$c"); [ -f "$c" ] || c="$HERE/$(basename "$c")"
  echo "== $(basename "$c")"
  timeout 150 "$B" --factory-startup --python "$(wslpath -w "$c")" -- "$(wslpath -w "$ROOT")" "$(wslpath -w "$OUT")" > "$OUT/$(basename "$c").log" 2>&1 || true
  for j in "$OUT"/*.json; do [ -f "$j" ] && { cat "$j"; echo; rm "$j"; }; done
  rm -f "$CONFIG"   # the checks must not leave a 4-Mix window position behind
done
echo "screenshots and logs: $OUT"
