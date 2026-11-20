#!/usr/bin/env bash
# Delete stale clips from the live Anki collection so a re-import can replace them.
#
# Anki's package importer matches media by NAME and skips any name already sitting in
# `collection.media`, so a regenerated clip never reaches an existing collection until the old
# file is gone — the note keeps pointing at the same filename and the learner keeps hearing the
# old take. This removes the named files before the import.
#
# Usage:
#   ./clear-anki-media.sh col_d1e334e5-present-example col_b5aa9739-explanation
#   ./clear-anki-media.sh --all col_d1e334e5        # every clip of one entry
#   ANKI_MEDIA="/some/profile/collection.media" ./clear-anki-media.sh ...
#
# Names may be given with or without the .mp3 extension. Missing files are not an error, so the
# script is safe to run twice.
set -euo pipefail

all=0
names=()
for arg in "$@"; do
  case "$arg" in
    --all) all=1 ;;
    -h | --help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) names+=("$arg") ;;
  esac
done

if ((${#names[@]} == 0)); then
  echo "nothing to delete: pass a clip name such as col_d1e334e5-present-example" >&2
  exit 2
fi

# Anki rewrites collection.media on exit and can resurrect what we delete mid-session.
if pgrep -x Anki >/dev/null; then
  echo "Anki is running — quit it first, then re-run." >&2
  exit 1
fi

media_dir=${ANKI_MEDIA:-}
if [[ -z $media_dir ]]; then
  shopt -s nullglob
  candidates=("$HOME/Library/Application Support/Anki2/"*/collection.media)
  shopt -u nullglob
  case ${#candidates[@]} in
    0)
      echo "no collection.media found under ~/Library/Application Support/Anki2/" >&2
      exit 1
      ;;
    1) media_dir=${candidates[0]} ;;
    *)
      printf 'several profiles found, pick one with ANKI_MEDIA:\n' >&2
      printf '  %s\n' "${candidates[@]}" >&2
      exit 1
      ;;
  esac
fi

shopt -s nullglob
removed=0
absent=0
for name in "${names[@]}"; do
  base=${name%.mp3}
  if ((all)); then
    targets=("$media_dir/$base-"*.mp3)
  elif [[ -f $media_dir/$base.mp3 ]]; then
    targets=("$media_dir/$base.mp3")
  else
    targets=()
  fi
  if ((${#targets[@]} == 0)); then
    echo "absent   $name"
    absent=$((absent + 1))
    continue
  fi
  for target in "${targets[@]}"; do
    size=$(wc -c <"$target" | tr -d ' ')
    rm -f "$target"
    printf 'removed  %-52s %8s bytes\n' "$(basename "$target")" "$size"
    removed=$((removed + 1))
  done
done
shopt -u nullglob

echo
echo "$removed file(s) removed, $absent absent — re-import the package to write the new ones."
