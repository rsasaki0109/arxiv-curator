#!/bin/bash
# Suggest new papers for an awesome list and check the health of existing repos
# Usage: ./suggest_and_check.sh https://github.com/xxx/Awesome-SLAM

set -e

AWESOME_URL="$1"
SINCE="${2:---since $(date -d '30 days ago' +%Y-%m-%d)}"

echo "=== arxiv-curator: New paper suggestions ==="
arxiv-curator suggest "$AWESOME_URL" $SINCE --max-results 10
echo ""

# Download the awesome list README for github-curator
OWNER_REPO=$(echo "$AWESOME_URL" | sed 's|https://github.com/||')
RAW_URL="https://raw.githubusercontent.com/${OWNER_REPO}/main/README.md"
curl -sL "$RAW_URL" -o /tmp/awesome-readme.md

echo "=== github-curator: Health check ==="
github-curator health /tmp/awesome-readme.md --only-problems
echo ""

echo "=== github-curator: Link check ==="
github-curator check-links /tmp/awesome-readme.md
