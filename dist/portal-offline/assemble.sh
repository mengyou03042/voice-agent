#!/usr/bin/env bash
# Copyright (c) Microsoft. All rights reserved.
# Verify and reassemble the split offline Voice Agent portal delivery archive on Linux or macOS.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="d112175c0dcb"
ARCHIVE_NAME="voice-agent-portal-delivery-${VERSION}.zip"
OUT_ZIP="${HERE}/${ARCHIVE_NAME}"
EXTRACT=0
EXTRACT_DIR="${HERE}"

usage() {
  cat <<'EOF'
Usage: ./assemble.sh [options]

Verifies every split part against SHA256SUMS, joins them into
voice-agent-portal-delivery-d112175c0dcb.zip, and verifies the final archive SHA-256.

Options:
  --output FILE       Write the reassembled .zip to FILE (default: ./voice-agent-portal-delivery-d112175c0dcb.zip)
  --extract           Also extract the reassembled .zip after verification
  --extract-to DIR    Directory to extract into (implies --extract; default: current folder)
  -h, --help          Show this help message
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$1" | awk '{print $NF}'
  else
    die "No SHA-256 tool found (expected sha256sum, shasum, or openssl)."
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      [[ $# -ge 2 ]] || die "--output requires a file path"
      OUT_ZIP="$2"
      shift 2
      ;;
    --extract)
      EXTRACT=1
      shift
      ;;
    --extract-to)
      [[ $# -ge 2 ]] || die "--extract-to requires a directory path"
      EXTRACT=1
      EXTRACT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "Unknown option: $1"
      ;;
  esac
done

[[ -f "${HERE}/SHA256SUMS" ]] || die "Missing ${HERE}/SHA256SUMS"
[[ -f "${HERE}/${ARCHIVE_NAME}.sha256" ]] || die "Missing ${HERE}/${ARCHIVE_NAME}.sha256"

printf '==> Verifying split parts against SHA256SUMS...\n'
PART_FILES=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"
  [[ -z "$line" ]] && continue
  expected="${line%% *}"
  rel_path="${line#*  }"
  full_path="${HERE}/${rel_path}"
  [[ -f "$full_path" ]] || die "Missing part file: ${full_path}"
  actual="$(sha256_file "$full_path")"
  if [[ "$actual" != "$expected" ]]; then
    die "Checksum mismatch for ${rel_path}: expected ${expected}, got ${actual}"
  fi
  printf '  OK  %s\n' "$rel_path"
  PART_FILES+=("$full_path")
done < "${HERE}/SHA256SUMS"

[[ ${#PART_FILES[@]} -gt 0 ]] || die "No part entries found in SHA256SUMS"

mkdir -p "$(dirname "$OUT_ZIP")"
TMP_ZIP="${OUT_ZIP}.tmp.$$"
trap 'rm -f "$TMP_ZIP"' EXIT

printf '==> Joining %d parts into %s...\n' "${#PART_FILES[@]}" "$OUT_ZIP"
cat "${PART_FILES[@]}" > "$TMP_ZIP"

EXPECTED_ARCHIVE_SHA="$(awk '{gsub(/\r$/, ""); print $1; exit}' "${HERE}/${ARCHIVE_NAME}.sha256")"
ACTUAL_ARCHIVE_SHA="$(sha256_file "$TMP_ZIP")"
if [[ "$ACTUAL_ARCHIVE_SHA" != "$EXPECTED_ARCHIVE_SHA" ]]; then
  die "Archive checksum mismatch: expected ${EXPECTED_ARCHIVE_SHA}, got ${ACTUAL_ARCHIVE_SHA}"
fi

mv -f "$TMP_ZIP" "$OUT_ZIP"
trap - EXIT
printf '  OK  %s (sha256: %s)\n' "$OUT_ZIP" "$ACTUAL_ARCHIVE_SHA"

if [[ "$EXTRACT" -eq 1 ]]; then
  mkdir -p "$EXTRACT_DIR"
  printf '==> Extracting %s into %s...\n' "$OUT_ZIP" "$EXTRACT_DIR"
  if command -v unzip >/dev/null 2>&1; then
    unzip -q -o "$OUT_ZIP" -d "$EXTRACT_DIR"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -I - "$OUT_ZIP" "$EXTRACT_DIR" <<'PY'
import os
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1])
dest_root = Path(sys.argv[2]).resolve()

with zipfile.ZipFile(zip_path) as zf:
    for info in zf.infolist():
        target = (dest_root / info.filename).resolve()
        if dest_root != target and dest_root not in target.parents:
            raise RuntimeError(f"Unsafe path in archive: {info.filename}")
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as dst:
            while True:
                buf = src.read(1024 * 1024)
                if not buf:
                    break
                dst.write(buf)
        mode = (info.external_attr >> 16) & 0o777
        if mode:
            os.chmod(target, mode)
PY
  else
    die "Archive verified at ${OUT_ZIP}, but neither 'unzip' nor 'python3' is installed to extract it."
  fi
  printf '==> Ready: %s/voice-agent-portal-delivery-%s/README.md\n' "$EXTRACT_DIR" "$VERSION"
else
  printf '==> Done. Run "%s --extract" (or unzip "%s") to unpack.\n' "$0" "$OUT_ZIP"
fi
