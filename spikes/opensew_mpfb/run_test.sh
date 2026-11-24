#!/usr/bin/env bash
# Run the MPFB <-> opensew-2 link test headless. Extra arguments go to the test:
#
#   ./run_test.sh                       # default rig, both figures, no cloth sim
#   ./run_test.sh --drape               # + sew and drape T-shirt and trousers
#   ./run_test.sh --rig rigify --figure WOMAN
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER="${BLENDER:-blender}"
exec "$BLENDER" -b --python "$HERE/test_mpfb_opensew.py" -- --out "$HERE/out" "$@"
