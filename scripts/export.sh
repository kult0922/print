#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p output
for part in card base fit_test text_test; do
  QT_QPA_PLATFORM=offscreen openscad -D "part=\"${part}\"" \
    -o "output/${part}.stl" models/nikko_trophy.scad
done
