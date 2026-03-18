# arxiv-curator

[![PyPI](https://img.shields.io/pypi/v/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![Python](https://img.shields.io/pypi/pyversions/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

arXiv の論文をキーワードで検索し、Markdown 形式で出力する CLI ツールです。
GitHub 上の論文リストの URL を渡すと、リポジトリ名からキーワードを自動抽出し、リストにまだ載っていない新着論文を提案します。

```bash
# 論文リストの URL を渡すだけ。リポ名からキーワードを自動抽出し、
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
| GitHub 上の論文リストに追加すべき論文を見逃す | `suggest` コマンドで既存リストと重複しない新着だけを提案 |
| 特定カテゴリ (cs.CV, cs.RO) に絞りたい | `--category` フィルタで絞り込み |
| 定期的に新着をウォッチしたい | `watch` コマンド + GitHub Actions で週次自動チェック |
| 結果を Markdown でそのまま貼りたい | `--format markdown` で論文リスト互換の Markdown 出力 |

### arXiv API を直接使う場合との違い

arXiv API は公開されていて誰でも使えますが、論文リストのメンテナンスに使うにはそのままだと手間がかかります。
arxiv-curator はその間を埋めるツールです。

| やりたいこと | arXiv API を直接使う場合 | arxiv-curator |
|---|---|---|
| 論文を検索する | API の Atom XML をパースするコードを書く | `arxiv-curator search transformer SLAM` |
| 論文リストの新着を探す | キーワードを自分で考え、既存リストと手動で突き合わせる | `arxiv-curator suggest <論文リストの URL>` でリポ名からキーワード自動抽出＋重複除去 |
| 結果を Markdown で貼る | 自分でフォーマットを整形 | `--format markdown` で論文リスト互換出力 |
| 定期的にチェックする | cron + スクリプトを自作 | `watch` コマンド + GitHub Actions テンプレート付き |
| カテゴリで絞る | クエリ構文を調べて `cat:cs.CV` を組み立てる | `--category cs.CV` |
| 結果を JSON で保存 | レスポンスの XML→JSON 変換を実装 | `--format json` / `export` コマンド |

### Semantic Scholar 連携

`enrich` コマンドまたは `--enrich` フラグを使うと、Semantic Scholar API 経由で以下の情報を取得できます。

| 情報 | 説明 |
|---|---|
| 引用数 | 論文の被引用回数 |
| 学会・ジャーナル情報 | 掲載先（CVPR, ICRA 等） |
| オープンアクセス | OA 状態の確認 |
| コードリンク | Papers with Code 経由（利用可能な場合） |

```bash
# enrich コマンド: arXiv 検索 + Semantic Scholar で情報付加
arxiv-curator enrich "transformer SLAM" --max-results 5

# 既存コマンドに --enrich フラグを付けても同様
arxiv-curator search transformer SLAM --enrich
```

### arXiv API の制限事項

arXiv API の仕様上、以下は直接取得できません（Semantic Scholar 連携で一部対応済み）。

| 情報 | arXiv API | Semantic Scholar 連携 |
|---|---|---|
| 引用数 | 取得不可 | `enrich` / `--enrich` で取得可能 |
| 学会・ジャーナル情報 | 取得不可 | `enrich` / `--enrich` で取得可能 |
| コード実装の有無 | 取得不可 | Papers with Code 経由で一部取得可能 |
| 全文検索 | タイトルと要旨のみ | — |
| セマンティック検索 | キーワード一致ベースのみ | — |

> GitHub リポジトリ側の情報（スター数・言語・更新日）は [github-curator](https://github.com/rsasaki0109/github-curator) で取得できます。

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

#### 論文リストへの新着論文提案

```bash
# GitHub 上の論文リストの URL を指定して、新着論文を提案
# リポジトリの README に載っている論文と重複しないものだけを提案します
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

#### 論文リストへの新着論文提案

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

### github-curator とのパイプライン

[github-curator](https://github.com/rsasaki0109/github-curator) と組み合わせることで、論文検索からリポジトリのヘルスチェックまで一気通貫で実行できます。

#### 論文からGitHubリポジトリを抽出してチェック

```bash
# arXiv論文を検索し、アブストラクトからGitHub URLを抽出、リポジトリの健全性をチェック
./examples/pipeline.sh "transformer SLAM" --since 2025-01-01
```

#### 論文リストの新着提案＋既存リポジトリのヘルスチェック

```bash
# 新着論文の提案と、既存リポジトリのリンク切れ・健全性チェックを同時実行
./examples/suggest_and_check.sh https://github.com/xxx/Awesome-SLAM
```

詳細は [examples/](./examples/) を参照してください。

---

## English

### Overview

A CLI tool that searches arXiv for papers by keyword and outputs results in Markdown format.
Pass a URL of a GitHub repository containing a paper list (Markdown with paper links), and it automatically extracts keywords from the repository name, then suggests new papers not already in the list.

| Feature | Description |
|---|---|
| Keyword search | `search` command with date and category filters |
| New paper suggestions | `suggest` auto-extracts keywords from repo name, deduplicates against existing entries |
| Category filter | `--category cs.CV` etc. |
| Periodic watch | `watch` command + GitHub Actions for weekly checks |
| Markdown output | `--format markdown` for direct copy-paste into paper lists |
| Semantic Scholar enrichment | `enrich` command or `--enrich` flag adds citation counts, venue, and open access info |

Works alongside [github-curator](https://github.com/rsasaki0109/github-curator) (star count updates, broken link checks).

### How This Differs from Using the arXiv API Directly

The arXiv API is publicly available, but using it to maintain a curated paper list on GitHub requires extra work. arxiv-curator bridges that gap.

| Task | Raw arXiv API | arxiv-curator |
|---|---|---|
| Search papers | Write code to parse Atom XML | `arxiv-curator search transformer SLAM` |
| Find new papers for a list | Manually decide keywords, cross-check against existing entries | `arxiv-curator suggest <URL>` — auto-extracts keywords from repo name + deduplicates |
| Format as Markdown | Build your own formatter | `--format markdown` (paper list compatible) |
| Run periodic checks | Write cron + custom script | `watch` command + GitHub Actions template included |
| Filter by category | Look up query syntax, build `cat:cs.CV` | `--category cs.CV` |
| Save as JSON | Implement XML-to-JSON conversion | `--format json` / `export` command |

### Semantic Scholar Integration

Use the `enrich` command or `--enrich` flag to fetch additional metadata from Semantic Scholar API:

| Info | Description |
|---|---|
| Citation counts | Number of citations for each paper |
| Conference/journal | Publication venue (CVPR, ICRA, etc.) |
| Open access | Whether the paper is open access |
| Code link | Via Papers with Code (when available) |

```bash
# enrich command: arXiv search + Semantic Scholar metadata
arxiv-curator enrich "transformer SLAM" --max-results 5

# Or add --enrich flag to existing commands
arxiv-curator search transformer SLAM --enrich
```

### arXiv API Limitations

The following cannot be retrieved from arXiv API directly (some now available via Semantic Scholar integration):

| Info | arXiv API | Semantic Scholar Integration |
|---|---|---|
| Citation counts | Not available | Available via `enrich` / `--enrich` |
| Conference/journal info | Not available | Available via `enrich` / `--enrich` |
| Code availability | Not available | Partially available via Papers with Code |
| Full-text search | Title and abstract only | — |
| Semantic search | Keyword matching only | — |

> GitHub repository info (stars, language, last updated) is available via [github-curator](https://github.com/rsasaki0109/github-curator).

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

#### Suggest new papers for a paper list

```bash
# Pass a GitHub repo URL that has a README listing papers.
# Keywords are extracted from the repo name, and only papers
# not already in the README are suggested.
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

#### Suggest new papers for a paper list

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

### Pipeline with github-curator

Combine with [github-curator](https://github.com/rsasaki0109/github-curator) to go from paper search to repository health checks in one flow.

#### Extract GitHub repos from papers and check them

```bash
# Search arXiv, extract GitHub URLs from abstracts, and check repo health
./examples/pipeline.sh "transformer SLAM" --since 2025-01-01
```

#### Suggest new papers + health-check existing repos

```bash
# Suggest new papers and check existing repo health/links
./examples/suggest_and_check.sh https://github.com/xxx/Awesome-SLAM
```

See [examples/](./examples/) for full scripts.

### Data Format

The JSON output follows a shared schema compatible with [github-curator](https://github.com/rsasaki0109/github-curator), enabling interoperability between the two tools.

## License

MIT
