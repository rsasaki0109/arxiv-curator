# arxiv-curator

[![PyPI](https://img.shields.io/pypi/v/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![Python](https://img.shields.io/pypi/pyversions/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

awesome-xxx リストに載せるべき新着論文を arXiv から自動で見つける CLI ツールです。
リポジトリ名からキーワードを抽出し、既存エントリとの重複を除いた上で新着論文を提案します。

```bash
# awesome-list の URL を渡すだけ。リポ名からキーワードを自動抽出し、
# 既存 329 件と重複チェックした上で、新着論文だけを提案してくれる。
$ arxiv-curator suggest https://github.com/KwanWaiPang/Awesome-Transformer-based-SLAM

Extracted keywords: Transformer, SLAM
Found 329 existing entries in README.
5 new papers (filtered 0 duplicates).
```

姉妹プロジェクト [github-curator](https://github.com/rsasaki0109/github-curator)（GitHub リポジトリの星数更新・リンク切れチェック）と組み合わせて使えます。

---

## 日本語

### 概要

| こんな課題 | arxiv-curator の解決策 |
|---|---|
| arXiv の新着論文を毎日チェックする時間がない | `search` コマンドでキーワード検索を一発実行 |
| awesome-list に追加すべき論文を見逃す | `suggest` コマンドで既存リストと重複しない新着だけを提案 |
| 特定カテゴリ (cs.CV, cs.RO) に絞りたい | `--category` フィルタで絞り込み |
| 定期的に新着をウォッチしたい | `watch` コマンド + GitHub Actions で週次自動チェック |
| 結果を awesome-list 形式でそのまま貼りたい | `--format markdown` で awesome-list 互換の Markdown 出力 |

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

### 実行サンプル

#### キーワード検索

```
$ arxiv-curator search transformer SLAM --since 2025-01-01 --max-results 5
Found 5 papers.

                                  arXiv Papers
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ #    ┃ Title                   ┃ Authors             ┃ Published    ┃ Categories     ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 1    │ SLAM Adversarial Lab    │ Mohamed Hefny et al.│ 2026-03-17   │ cs.RO, cs.CV   │
│ 2    │ eNavi: Event-based ...  │ Prithvi Jai Ramesh  │ 2026-03-15   │ cs.RO          │
│ 3    │ AIM-SLAM: Dense ...     │ Jinwoo Jeon et al.  │ 2026-03-05   │ cs.RO          │
│ 4    │ FLIGHT: Fibonacci ...   │ David Dirnfeld ...  │ 2026-02-26   │ cs.CV, cs.RO   │
│ 5    │ SceneVGGT: VGGT-based...│ Anna Gelencsér...   │ 2026-02-12   │ cs.RO, eess.IV │
└──────┴─────────────────────────┴─────────────────────┴──────────────┴────────────────┘
```

#### カテゴリフィルタ

```
$ arxiv-curator search "image matching" --category cs.CV --max-results 3
Found 3 papers.
# cs.CV カテゴリの論文のみ表示されます
```

#### awesome-list への新着論文提案

```
$ arxiv-curator suggest https://github.com/KwanWaiPang/Awesome-Transformer-based-SLAM --since 2025-01-01 --max-results 5 --format markdown
Extracted keywords: Transformer, SLAM
Found 329 existing entries in README.
5 new papers (filtered 0 duplicates).

# arXiv Papers

- **[SLAM Adversarial Lab: An Extensible Framework...](http://arxiv.org/abs/2603.17165v1)** - Mohamed Hefny et al. (2026-03-17)
- **[AIM-SLAM: Dense Monocular SLAM...](http://arxiv.org/abs/2603.05097v2)** - Jinwoo Jeon et al. (2026-03-05)
- **[SceneVGGT: VGGT-based online 3D semantic SLAM...](http://arxiv.org/abs/2602.15899v2)** - Anna Gelencsér-Horváth et al. (2026-02-12)
...
```

---

## English

### Overview

A CLI tool that finds new arXiv papers for your awesome-xxx list.
It extracts keywords from the repository name, searches arXiv, and suggests papers not already in your list.

| Feature | Description |
|---|---|
| Keyword search | `search` command with date and category filters |
| New paper suggestions | `suggest` auto-extracts keywords from repo name, deduplicates against existing entries |
| Category filter | `--category cs.CV` etc. |
| Periodic watch | `watch` command + GitHub Actions for weekly checks |
| Awesome-list output | `--format markdown` for direct copy-paste |

Works alongside [github-curator](https://github.com/rsasaki0109/github-curator) (star count updates, broken link checks).

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

### Examples

#### Keyword search

```
$ arxiv-curator search transformer SLAM --since 2025-01-01 --max-results 5
Found 5 papers.

                                  arXiv Papers
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ #    ┃ Title                   ┃ Authors             ┃ Published    ┃ Categories     ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 1    │ SLAM Adversarial Lab    │ Mohamed Hefny et al.│ 2026-03-17   │ cs.RO, cs.CV   │
│ 2    │ eNavi: Event-based ...  │ Prithvi Jai Ramesh  │ 2026-03-15   │ cs.RO          │
│ 3    │ AIM-SLAM: Dense ...     │ Jinwoo Jeon et al.  │ 2026-03-05   │ cs.RO          │
│ 4    │ FLIGHT: Fibonacci ...   │ David Dirnfeld ...  │ 2026-02-26   │ cs.CV, cs.RO   │
│ 5    │ SceneVGGT: VGGT-based...│ Anna Gelencsér...   │ 2026-02-12   │ cs.RO, eess.IV │
└──────┴─────────────────────────┴─────────────────────┴──────────────┴────────────────┘
```

#### Category filter

```
$ arxiv-curator search "image matching" --category cs.CV --max-results 3
Found 3 papers.
# Only papers in cs.CV category are shown
```

#### Suggest new papers for an awesome-list

```
$ arxiv-curator suggest https://github.com/KwanWaiPang/Awesome-Transformer-based-SLAM --since 2025-01-01 --max-results 5 --format markdown
Extracted keywords: Transformer, SLAM
Found 329 existing entries in README.
5 new papers (filtered 0 duplicates).

# arXiv Papers

- **[SLAM Adversarial Lab: An Extensible Framework...](http://arxiv.org/abs/2603.17165v1)** - Mohamed Hefny et al. (2026-03-17)
- **[AIM-SLAM: Dense Monocular SLAM...](http://arxiv.org/abs/2603.05097v2)** - Jinwoo Jeon et al. (2026-03-05)
- **[SceneVGGT: VGGT-based online 3D semantic SLAM...](http://arxiv.org/abs/2602.15899v2)** - Anna Gelencsér-Horváth et al. (2026-02-12)
...
```

### Data Format

The JSON output follows a shared schema compatible with [github-curator](https://github.com/rsasaki0109/github-curator), enabling interoperability between the two tools.

## License

MIT
