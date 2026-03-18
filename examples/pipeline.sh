#!/bin/bash
# Pipeline: Find new papers on arXiv, then check if they have GitHub repos
# Usage: ./pipeline.sh "transformer SLAM" --since 2025-01-01

set -e

QUERY="$1"
shift
EXTRA_ARGS="$@"

echo "=== Step 1: Search arXiv for papers ==="
arxiv-curator search $QUERY $EXTRA_ARGS --format json > /tmp/curator-papers.json
echo ""

echo "=== Step 2: Extract GitHub URLs from paper abstracts ==="
# Parse the JSON and grep for github.com URLs in abstracts
python3 -c "
import json, re, sys
with open('/tmp/curator-papers.json') as f:
    papers = json.loads(f.read())
urls = set()
for p in papers:
    found = re.findall(r'https?://github\.com/[\w-]+/[\w.-]+', p.get('abstract', ''))
    urls.update(found)
if urls:
    print(f'Found {len(urls)} GitHub repos mentioned in papers:')
    for u in sorted(urls):
        print(f'  {u}')
    # Write to a markdown file for github-curator
    with open('/tmp/curator-repos.md', 'w') as f:
        f.write('# Repos from arXiv papers\n\n')
        for u in sorted(urls):
            f.write(f'- [{u.split(\"/\")[-1]}]({u})\n')
else:
    print('No GitHub repos found in paper abstracts.')
    sys.exit(0)
"
echo ""

echo "=== Step 3: Check repo health with github-curator ==="
if [ -f /tmp/curator-repos.md ]; then
    github-curator health /tmp/curator-repos.md 2>/dev/null || echo "(Some repos may not be accessible)"
fi

echo ""
echo "=== Done ==="
