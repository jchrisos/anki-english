#!/usr/bin/env bash
# Compact, readable listing of open GitHub issues for the current repo (or -R owner/repo).
#
# Usage:
#   ./list-issues.sh                       # 50 most recently updated open issues
#   ./list-issues.sh --label bug           # any `gh issue list` filter passes through
#   ./list-issues.sh --assignee @me --limit 100
#   ./list-issues.sh -R owner/repo --state all
#
# Output is one row per issue: number, last update, title, labels, assignees.
set -euo pipefail

limit=50
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -L | --limit)
      limit="$2"
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

# Fail loudly with gh's own message if there is no repo or no auth.
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

rows=$(
  gh issue list --limit "$limit" \
    --json number,title,labels,updatedAt,assignees ${args[@]+"${args[@]}"} \
    --jq '.[] | "#\(.number)\tat \(.updatedAt[0:10])\t\(.title)\t\([.labels[].name] | join(","))\t\([.assignees[].login] | join(","))"'
)

if [[ -z "$rows" ]]; then
  echo "No issues in $repo match those filters."
  exit 0
fi

echo "$repo — $(printf '%s\n' "$rows" | wc -l | tr -d ' ') issue(s)"
printf '%s\n' "$rows" | column -t -s $'\t'
