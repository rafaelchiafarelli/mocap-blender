#!/usr/bin/env bash
# Prepare Blender 5.2.2 for the MPFB <-> opensew-2 link test.
#
#   ./setup.sh            (uses `blender` on PATH)
#   BLENDER=/path/to/blender ./setup.sh
#
# 1. clones opensew-2 at the pinned commit into .cache/ and applies patches/
# 2. links the patched clothing_design add-on into Blender's user add-ons
# 3. checks that MPFB is installed (it is NOT installed by this script)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER="${BLENDER:-blender}"
OPENSEW_URL="https://github.com/MarcelloMorettoni/opensew-2.git"
OPENSEW_PIN="86b4322"          # upstream main, 2026-08-26
SRC="$HERE/.cache/opensew-2"

command -v "$BLENDER" >/dev/null || { echo "Blender not found: set BLENDER=/path/to/blender"; exit 1; }

ver="$("$BLENDER" -b --factory-startup --python-expr 'import bpy; print("BLVER", bpy.app.version_string)' 2>/dev/null | sed -n 's/^BLVER //p')"
echo "Blender: $ver"
case "$ver" in 5.2.2*) ;; *) echo "WARNING: Mocap Studio pins Blender 5.2.2; this is $ver" ;; esac

if [ ! -d "$SRC/.git" ]; then
    mkdir -p "$HERE/.cache"
    git clone -q "$OPENSEW_URL" "$SRC"
fi
git -C "$SRC" fetch -q origin
git -C "$SRC" checkout -q -B mpfb-link "$OPENSEW_PIN"
git -C "$SRC" -c user.name=setup -c user.email=setup@localhost am -q "$HERE"/patches/*.patch
echo "opensew-2 $OPENSEW_PIN + $(ls "$HERE"/patches | wc -l) patch(es) -> $SRC"

ADDONS="$("$BLENDER" -b --python-expr \
  'import bpy; print("ADDONS", bpy.utils.user_resource("SCRIPTS", path="addons", create=True))' \
  2>/dev/null | sed -n 's/^ADDONS //p')"
[ -n "$ADDONS" ] || { echo "Could not ask Blender for its add-ons folder"; exit 1; }
if [ -e "$ADDONS/clothing_design" ] && [ ! -L "$ADDONS/clothing_design" ]; then
    echo "$ADDONS/clothing_design exists and is not our link - move it away first"; exit 1
fi
ln -sfn "$SRC/clothing_design" "$ADDONS/clothing_design"
echo "clothing_design -> $ADDONS/clothing_design"

mpfb="$("$BLENDER" -b --python-expr '
import bpy
for m in ("bl_ext.blender_org.mpfb", "bl_ext.user_default.mpfb", "mpfb"):
    try:
        bpy.ops.preferences.addon_enable(module=m); print("MPFB", m); break
    except Exception:
        pass
' 2>/dev/null | sed -n 's/^MPFB //p')"
if [ -z "$mpfb" ]; then
    echo "MPFB is not installed. In Blender: Edit > Preferences > Get Extensions > search 'MPFB' > Install."
    exit 1
fi
echo "MPFB: $mpfb"
echo "Ready. Run: ./run_test.sh   (add --drape for the cloth simulation, ~6 min)"
