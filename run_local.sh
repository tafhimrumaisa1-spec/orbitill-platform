#!/usr/bin/env sh
set -eu
PLATFORM_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$PLATFORM_DIR/modules/earthsync_runtime:$PLATFORM_DIR/modules/aquasense_runtime:$PLATFORM_DIR/modules/terralens_runtime:$PLATFORM_DIR"
cd "$PLATFORM_DIR"
printf '%s\n' 'ORBITILL: http://127.0.0.1:8400/' 'RootShift demo: http://127.0.0.1:8400/planner.html' 'TerraLens: http://127.0.0.1:8400/terralens/'
python3 -B -m services.science_api.server
