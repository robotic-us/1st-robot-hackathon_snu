#!/usr/bin/env bash
# Create a small, representative, non-duplicate image collection for GitHub.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="$ROOT/sample_images"

if [[ -e "$OUTPUT" ]]; then
  echo "Refusing to overwrite existing $OUTPUT" >&2
  exit 1
fi
mkdir -p "$OUTPUT"

sample_dir() {
  local source="$1" destination="$2" limit="$3"
  local -a files=()
  local count take index
  mkdir -p "$destination"
  mapfile -d '' files < <(find "$source" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print0 | sort -z)
  count="${#files[@]}"
  (( count == 0 )) && return
  take=$(( count < limit ? count : limit ))
  for ((index = 0; index < take; index++)); do
    # Evenly distribute examples through an automatic-capture sequence.
    cp -- "${files[$(( index * count / take ))]}" "$destination/"
  done
}

# Final Blender set and older synthetic set: train and validation samples.
sample_dir "$ROOT/generated/white_gray_pose_1000/images/train" "$OUTPUT/final_synthetic/train" 10
sample_dir "$ROOT/generated/white_gray_pose_1000/images/val" "$OUTPUT/final_synthetic/val" 10
sample_dir "$ROOT/synthetic_shoes/images/train" "$OUTPUT/legacy_synthetic/train" 10
sample_dir "$ROOT/synthetic_shoes/images/val" "$OUTPUT/legacy_synthetic/val" 10

# Every original real-capture folder, including the newer gray pair.
for source in "$ROOT"/real_shoes/raw/* "$ROOT"/real_shoes/replacement_gray_pair/raw/*; do
  [[ -d "$source" ]] || continue
  sample_dir "$source" "$OUTPUT/real/$(basename "$source")" 10
done

# Small source/reference folders are copied in full when they contain <10 files.
sample_dir "$ROOT/floor" "$OUTPUT/floor" 10
for source in "$ROOT"/obj_files/*; do
  [[ -d "$source" ]] || continue
  sample_dir "$source" "$OUTPUT/asset_references/$(basename "$source")" 10
done

echo "Created $(find "$OUTPUT" -type f | wc -l) sample images in $OUTPUT"
