#!/usr/bin/env bash
# Render every chapter composition to out/<chapter_id>.mp4.
# Resumable: an existing non-empty output file is skipped, so the batch can be
# re-run after an interruption without redoing finished chapters.
set -u

cd "$(dirname "$0")"
mkdir -p out

STORYBOARD="public/storyboard.json"
CHAPTER_IDS=$(node -e "
const s = require('./$STORYBOARD');
const ids = [...new Set(s.map(x => x.chapter_id))];
console.log(ids.join(' '));
")

total=$(echo "$CHAPTER_IDS" | wc -w)
i=0
failed=""

for chapter_id in $CHAPTER_IDS; do
  i=$((i + 1))
  composition_id="${chapter_id//_/-}"
  out_file="out/${chapter_id}.mp4"

  if [ -s "$out_file" ]; then
    echo "[$i/$total] $chapter_id — already rendered, skipping"
    continue
  fi

  echo "[$i/$total] $chapter_id — rendering..."
  if npx remotion render src/index.ts "$composition_id" "$out_file" \
      --log=error >> "render-all.log" 2>&1; then
    echo "[$i/$total] $chapter_id — done ($(du -h "$out_file" | cut -f1))"
  else
    echo "[$i/$total] $chapter_id — FAILED (see render-all.log)"
    failed="$failed $chapter_id"
    rm -f "$out_file"
  fi
done

echo
if [ -n "$failed" ]; then
  echo "Finished with failures:$failed"
  exit 1
fi
echo "All $total chapters rendered to out/"
