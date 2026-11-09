#!/usr/bin/env bash
# Unpack results_and_intermediate_files.zip and move its contents into place.
#
# The archive mirrors the repository layout under a single top-level folder:
#   results_and_intermediate_files/output_agent/...        -> output_agent/...
#   results_and_intermediate_files/output_baseline/...     -> output_baseline/...
#   results_and_intermediate_files/eval_agent/...          -> eval_agent/...
#   results_and_intermediate_files/eval_baseline/...       -> eval_baseline/...
#   results_and_intermediate_files/categorize_errors/...   -> categorize_errors/...
#   results_and_intermediate_files/summarize_results/...   -> summarize_results/...
#
# Usage:
#   ./unpack_results.sh [--force] [--delete-zip] [path/to/zip]
#
#   --force       overwrite files that already exist (default: keep existing files)
#   --delete-zip  remove the zip after a successful unpack
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="$REPO_DIR/results_and_intermediate_files.zip"
TOP_DIR="results_and_intermediate_files"
FORCE=0
DELETE_ZIP=0

for arg in "$@"; do
    case "$arg" in
        --force)      FORCE=1 ;;
        --delete-zip) DELETE_ZIP=1 ;;
        -h|--help)    sed -n '2,18p' "$0"; exit 0 ;;
        -*)           echo "Unknown option: $arg" >&2; exit 1 ;;
        *)            ZIP_PATH="$(realpath "$arg")" ;;
    esac
done

command -v unzip >/dev/null || { echo "unzip is not installed" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync is not installed" >&2; exit 1; }
[[ -f "$ZIP_PATH" ]] || { echo "Zip not found: $ZIP_PATH" >&2; exit 1; }

# Sanity check: every entry must live under the expected top-level folder
# and must not try to escape it.
if unzip -Z1 "$ZIP_PATH" | grep -vqE "^${TOP_DIR}/"; then
    echo "Unexpected layout: not all entries are under ${TOP_DIR}/" >&2
    exit 1
fi
if unzip -Z1 "$ZIP_PATH" | grep -qE '(^|/)\.\.(/|$)'; then
    echo "Refusing to unpack: archive contains '..' paths" >&2
    exit 1
fi

# Extract into a temp dir inside the repo (same filesystem -> fast moves).
TMP_DIR="$(mktemp -d "$REPO_DIR/.unpack_tmp.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Extracting $(basename "$ZIP_PATH") ..."
unzip -q "$ZIP_PATH" -d "$TMP_DIR"

SRC="$TMP_DIR/$TOP_DIR/"
RSYNC_OPTS=(-a --remove-source-files)
if [[ $FORCE -eq 0 ]]; then
    RSYNC_OPTS+=(--ignore-existing)
fi

echo "Moving files into place:"
for d in "$SRC"*/; do
    echo "  $(basename "$d")/  ($(find "$d" -type f | wc -l) files)"
done

rsync "${RSYNC_OPTS[@]}" "$SRC" "$REPO_DIR/"

# Anything left behind already existed and was skipped.
SKIPPED=$(find "$SRC" -type f | wc -l)
if [[ $SKIPPED -gt 0 ]]; then
    echo "Skipped $SKIPPED file(s) that already exist (use --force to overwrite)."
fi

if [[ $DELETE_ZIP -eq 1 ]]; then
    rm -f "$ZIP_PATH"
    echo "Deleted $ZIP_PATH"
fi

echo "Done."
