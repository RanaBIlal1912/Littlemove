#!/usr/bin/env bash
# Download self-hosted woff2 fonts for Urdu and Arabic
set -e
FONT_DIR="$(dirname "$0")/../static/fonts"
mkdir -p "$FONT_DIR"

echo "Downloading Noto Nastaliq Urdu..."
curl -L "https://fonts.gstatic.com/s/notonastaliqurdu/v23/LhWNMUPbN-oZdNFcBy1-DJYsEoTq5pudQ9L940pGPkB3Qt_-PK-V2t_8.woff2" -o "$FONT_DIR/noto-nastaliq-urdu-400.woff2"

echo "Downloading Noto Naskh Arabic..."
curl -L "https://fonts.gstatic.com/s/notonaskharabic/v44/RrQ5bpV-9Dd1b1OAGA6M9PkyDuVBePeKNaxcsss0Y7bwvc5Urqcyx_M.woff2" -o "$FONT_DIR/noto-naskh-arabic-400.woff2"

echo "Done."
