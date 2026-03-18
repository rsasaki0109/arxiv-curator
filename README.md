# arxiv-curator

[![PyPI](https://img.shields.io/pypi/v/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![Python](https://img.shields.io/pypi/pyversions/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

arXiv 論文検索・キュレーション CLI ツール / arXiv paper search & curation CLI tool

---

## 日本語

### 概要

`arxiv-curator` は arXiv の論文をキーワードで検索し、awesome-list 形式で整理するための CLI ツールです。
GitHub の awesome リポジトリと連携し、既存論文と重複しない新着論文を提案できます。

姉妹プロジェクト [github-curator](https://github.com/rsasaki0109/github-curator) と組み合わせることで、論文とリポジトリの両方を効率的にキュレーションできます。

### インストール

```bash
pip install arxiv-curator
```

### 使い方

#### 論文検索

```bash
# キーワードで検索
arxiv-curator search SLAM LiDAR

# 日付フィルタ付き
arxiv-curator search transformer SLAM --since 2025-01-01

# 出力形式を指定 (table / json / markdown)
arxiv-curator search "visual odometry" --format markdown --max-results 10
```

#### awesome-list への新着論文提案

```bash
# awesome-list リポジトリの URL を指定して、新着論文を提案
arxiv-curator suggest https://github.com/xxx/Awesome-Transformer-based-SLAM

# 日付フィルタ付き
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --since 2025-01-01 --format markdown
```

#### Web デモ

```bash
pip install arxiv-curator[web]
streamlit run app.py
```

#### エクスポート

```bash
# Markdown ファイルに出力
arxiv-curator export SLAM LiDAR --output papers.md --since 2025-01-01

# JSON ファイルに出力
arxiv-curator export SLAM LiDAR --output papers.json
```

---

## English

### Overview

`arxiv-curator` is a CLI tool for searching arXiv papers by keywords and curating them in awesome-list format.
It integrates with GitHub awesome repositories to suggest new papers that are not already listed.

Use it alongside the companion project [github-curator](https://github.com/rsasaki0109/github-curator) to curate both papers and repositories efficiently.

### Installation

```bash
pip install arxiv-curator
```

### Usage

#### Search papers

```bash
# Search by keywords
arxiv-curator search SLAM LiDAR

# With date filter
arxiv-curator search transformer SLAM --since 2025-01-01

# Specify output format (table / json / markdown)
arxiv-curator search "visual odometry" --format markdown --max-results 10
```

#### Suggest new papers for an awesome-list

```bash
# Provide an awesome-list repo URL to get suggestions for new papers
arxiv-curator suggest https://github.com/xxx/Awesome-Transformer-based-SLAM

# With date filter
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --since 2025-01-01 --format markdown
```

#### Web Demo

```bash
pip install arxiv-curator[web]
streamlit run app.py
```

#### Export results

```bash
# Export to Markdown
arxiv-curator export SLAM LiDAR --output papers.md --since 2025-01-01

# Export to JSON
arxiv-curator export SLAM LiDAR --output papers.json
```

### Data Format

The JSON output follows a shared schema compatible with [github-curator](https://github.com/rsasaki0109/github-curator), enabling interoperability between the two tools.

## License

MIT
