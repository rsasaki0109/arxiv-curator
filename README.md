# arxiv-curator

[![PyPI](https://img.shields.io/pypi/v/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![Python](https://img.shields.io/pypi/pyversions/arxiv-curator)](https://pypi.org/project/arxiv-curator/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

トピックを渡すだけで論文リストを自動生成できる CLI ツールです。
arXiv 検索、Semantic Scholar による引用数・コード有無の付加、サブトピック分類、Markdown テーブル出力まで、コマンド一発で完結します。

```bash
# トピックを渡すだけで論文リストを自動生成
$ arxiv-curator generate "3D gaussian splatting" --since 2023-01-01 --max 50 -o awesome-3dgs.md
```

週次ダイジェストも同様にコマンド一発で取得できます。

```bash
$ arxiv-curator digest "3D gaussian splatting" --days 7
Found 12 papers on arXiv.

┌──────────────────────────────────────────────┐
│              Weekly Digest                   │
│  3D gaussian splatting                       │
│  2026-03-17 -> 2026-03-24                    │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│              Overview                        │
│  12 new papers this period                   │
│  Categories: cs.CV: 8, cs.GR: 4             │
│  2 papers have code available                │
│  Top venues: CVPR (3), ICCV (2)             │
└──────────────────────────────────────────────┘
        Must Read (Top 3 by score)
┏━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃  Rank ┃ Score ┃ Title                       ┃  Citations ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│     1 │   119 │ 3D Gaussian Splatting for...│       7412 │
│     2 │    85 │ GaussianEditor: Swift ...   │        342 │
│     3 │    72 │ DreamGaussian: Generati...  │        298 │
└───────┴───────┴─────────────────────────────┴────────────┘
┌──────────────────────────────────────────────┐
│  Hidden Gems (recent + code, low citations)  │
│  StreetFormer: Perceiving Dynamic Street...  │
│  (0 citations, 2 days old)                   │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│              Hot Topics                      │
│  "real-time" (4 papers)                      │
│  "editing" (3 papers)                        │
└──────────────────────────────────────────────┘
```

`digest` 以外にも、キーワード検索・カテゴリフィルタ・論文リスト向けの新着提案など多彩なコマンドを備えています。
GitHub 上の論文リストの URL を渡すと、リポ名からキーワードを自動抽出し、既存エントリと重複しない新着だけを提案する `suggest` コマンドもあります。

姉妹プロジェクト [github-curator](https://github.com/rsasaki0109/github-curator)（GitHub リポジトリの健全性チェック）と組み合わせて使えます。

---

## 日本語

### 機能

| 機能 | 説明 |
|---|---|
| `generate` | トピックを渡すだけで論文リストを自動生成（arXiv 検索 → Semantic Scholar → 分類 → Markdown 出力） |
| `digest` | 研究分野の週次ダイジェストをコマンド一発で生成（注目論文・Hidden Gems・トレンド） |
| `search` | キーワード・カテゴリ・日付で arXiv 論文を検索 |
| `suggest` | GitHub の論文リストURL を渡すと、載っていない新着論文を提案 |
| `enrich` | Semantic Scholar API で引用数・学会名・コードリンクを付加 |
| `map` | 研究トピックの論文マップを生成（論文・コード・学会・年別トレンド） |
| `watch` | 定期実行用。新着論文を差分検出して JSON に蓄積 |
| `export` | 検索結果を Markdown / JSON ファイルに出力 |
| `rank` | 引用数・新しさ・コード有無・学会をスコア化し「今読むべき論文」をランキング |

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

#### 論文リスト自動生成 (generate)

```bash
# トピックを渡すだけで論文リストを自動生成
arxiv-curator generate "3D gaussian splatting" --since 2023-01-01 --max 50 -o awesome-3dgs.md

# カテゴリフィルタ付き
arxiv-curator generate "visual SLAM" --since 2024-01-01 --category cs.RO -o awesome-slam.md

# strict モード OFF: タイトルにキーワードを含まない論文も含める
arxiv-curator generate "transformer SLAM" --no-strict -o papers.md
```

`generate` コマンドは以下を自動実行します:
1. arXiv からキーワード検索（relevance 順）
2. Strict フィルタ（デフォルト ON: タイトルにキーワードを含む論文のみ）
3. Semantic Scholar で引用数・学会・コードリンクを付加
4. スコアリングとランキング
5. サブトピック別に自動分類
6. Markdown テーブル付きのドキュメントとして出力

#### 週次ダイジェスト (digest)

```bash
# 過去7日間の 3D gaussian splatting 論文のダイジェストを生成
arxiv-curator digest "3D gaussian splatting" --days 7

# カテゴリフィルタ付き
arxiv-curator digest "visual SLAM" --days 14 --category cs.RO

# Markdown レポートとしてファイルに保存
arxiv-curator digest "3D gaussian splatting" --days 7 --output digest.md
```

`digest` コマンドの出力には以下が含まれます:
- **Must Read**: スコア上位3論文（引用数・新しさ・コード有無・学会で算出）
- **Hidden Gems**: 最近の論文でコード公開済みだが引用が少ない「隠れた良論文」
- **Hot Topics**: 論文タイトルの頻出キーワードから抽出したトレンド
- **Overview**: カテゴリ別・学会別の集計、コード公開率

#### 論文検索

```bash
# キーワードで検索
arxiv-curator search SLAM LiDAR

# 日付フィルタ付き
arxiv-curator search transformer SLAM --since 2025-01-01

# 出力形式を指定 (table / json / markdown)
arxiv-curator search "visual odometry" --format markdown --max-results 10

# ソート順を指定 (relevance / date / title)
arxiv-curator search transformer SLAM --sort date

# Semantic Scholar の引用数・学会情報を付加
arxiv-curator search transformer SLAM --enrich
```

#### 論文リストへの新着論文提案

```bash
# GitHub 上の論文リストの URL を指定して、新着論文を提案
# リポジトリの README に載っている論文と重複しないものだけを提案します
arxiv-curator suggest https://github.com/xxx/Awesome-Transformer-based-SLAM

# 日付フィルタ付き
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --since 2025-01-01 --format markdown

# 結果を Markdown ファイルに追記
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --append-to new_papers.md
```

#### 定期監視 (watch)

```bash
# キーワードで新着論文を定期チェックし、差分を JSON に蓄積
arxiv-curator watch SLAM LiDAR --days 7 --output-dir ./results

# awesome-list URL からキーワードを自動抽出して監視
arxiv-curator watch --from-awesome https://github.com/xxx/Awesome-SLAM --days 14
```

#### 論文マップ (map)

```bash
# SLAM 分野の論文マップを生成
arxiv-curator map transformer SLAM --since 2024-01-01 --max-results 50

# Markdown レポートとして出力
arxiv-curator map transformer SLAM --markdown

# Markdown ファイルに保存
arxiv-curator map transformer SLAM --output field_map.md

# JSON で保存
arxiv-curator map "3D generation" --output field_map.json
```

`map` コマンドの出力には以下の分析が含まれます:
- **Topic Clusters**: 論文タイトルのキーワードに基づくトピック別グループ化
- **Code Availability Trend**: 年ごとのコード公開率の推移
- **Key Papers**: 引用数トップの重要論文
- **Gaps & Opportunities**: コード公開率が低いトピック・年、活動が少ない年の検出

#### 論文ランキング

```bash
# 今読むべき SLAM 論文をランキング
arxiv-curator rank transformer SLAM --since 2024-01-01 --top 10

# カテゴリフィルタ付き
arxiv-curator rank "visual odometry" --category cs.RO --top 5

# JSON ファイルにスコア詳細を保存
arxiv-curator rank transformer SLAM --top 10 --output ranking.json
```

ランキング出力には以下の情報が含まれます:
- **Percentile**: 全論文中の相対順位（Top 5% など）
- **Category**: スコアに基づくラベル（Must read / Recommended / Worth checking / Low priority）
- **Hidden gem**: 最近の論文でコード公開済みだが引用が少ない「隠れた良論文」を自動検出
- **Summary**: Must read 数、コード公開率、平均引用数などの統計情報

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

#### 論文ランキング

```
$ arxiv-curator rank "3D gaussian splatting" --since 2023-06-01 --max-results 5 --top 5
Found 4 papers on arXiv.

                                 Ranked Papers
┏━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃  Rank ┃   Score ┃ Percentile ┃ Category        ┃  Citations ┃ Published   ┃
┡━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│     1 │     119 │     Top 1% │ Must read       │       7412 │ 2023-08-08  │
│     2 │      41 │    Top 25% │ Worth checking  │         60 │ 2024-06-17  │
│     3 │      10 │    Top 50% │ Low priority    │          0 │ 2025-09-09  │
│     4 │       0 │    Top 75% │ Low priority    │          0 │ 2023-12-01  │
└───────┴─────────┴────────────┴─────────────────┴────────────┴─────────────┘

Summary:
  Must read: 1 papers
  Recommended: 0 papers
  With code: 0/4 (0%)
  Top venue papers: 0
  Average citations: 1868.0
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

A CLI tool that gives researchers a weekly field summary in one command.
Search arXiv, enrich with Semantic Scholar data, and get a newsletter-style digest with must-reads, hidden gems, and trends.

| Feature | Description |
|---|---|
| Generate paper list | `generate` command auto-generates a complete curated paper list (arXiv search + Semantic Scholar + categorization + Markdown output) |
| Weekly digest | `digest` command generates a newsletter-style summary: must-reads, hidden gems, and trends |
| Keyword search | `search` command with date and category filters |
| New paper suggestions | `suggest` auto-extracts keywords from repo name, deduplicates against existing entries |
| Category filter | `--category cs.CV` etc. |
| Periodic watch | `watch` command + GitHub Actions for weekly checks |
| Markdown output | `--format markdown` for direct copy-paste into paper lists |
| Semantic Scholar enrichment | `enrich` command or `--enrich` flag adds citation counts, venue, and open access info |
| Field map | `map` command builds a structured overview: papers, code links, venues, yearly trends |
| Paper ranking | `rank` command scores papers by citations, recency, code availability, and venue |

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

#### Generate a curated paper list

```bash
# One command to generate a complete paper list
arxiv-curator generate "3D gaussian splatting" --since 2023-01-01 --max 50 -o awesome-3dgs.md

# With category filter
arxiv-curator generate "visual SLAM" --since 2024-01-01 --category cs.RO -o awesome-slam.md

# Disable strict mode to include papers without query keywords in title
arxiv-curator generate "transformer SLAM" --no-strict -o papers.md
```

The `generate` command runs the full pipeline:
1. Search arXiv by relevance
2. Strict filter (default ON: only papers with query keywords in title)
3. Enrich with Semantic Scholar (citations, venues, code links)
4. Score and rank papers
5. Auto-categorize by sub-topic
6. Output as a Markdown document with tables and code links

#### Weekly digest

```bash
# Generate a digest of 3D gaussian splatting papers from the last 7 days
arxiv-curator digest "3D gaussian splatting" --days 7

# With category filter
arxiv-curator digest "visual SLAM" --days 14 --category cs.RO

# Save as Markdown report
arxiv-curator digest "3D gaussian splatting" --days 7 --output digest.md
```

The `digest` output includes:
- **Must Read**: top 3 papers by composite score (citations, recency, code, venue)
- **Hidden Gems**: recent papers with code available but low citations
- **Hot Topics**: trending keywords extracted from paper titles
- **Overview**: category breakdown, venue stats, code availability

#### Search papers

```bash
# Search by keywords
arxiv-curator search SLAM LiDAR

# With date filter
arxiv-curator search transformer SLAM --since 2025-01-01

# Specify output format (table / json / markdown)
arxiv-curator search "visual odometry" --format markdown --max-results 10

# Sort results (relevance / date / title)
arxiv-curator search transformer SLAM --sort date

# Enrich with Semantic Scholar citation counts and venue info
arxiv-curator search transformer SLAM --enrich
```

#### Suggest new papers for a paper list

```bash
# Pass a GitHub repo URL that has a README listing papers.
# Keywords are extracted from the repo name, and only papers
# not already in the README are suggested.
arxiv-curator suggest https://github.com/xxx/Awesome-Transformer-based-SLAM

# With date filter
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --since 2025-01-01 --format markdown

# Append results to a Markdown file
arxiv-curator suggest https://github.com/xxx/Awesome-SLAM --append-to new_papers.md
```

#### Watch for new papers

```bash
# Periodically check for new papers and accumulate results in a JSON file
arxiv-curator watch SLAM LiDAR --days 7 --output-dir ./results

# Auto-extract keywords from an awesome-list URL
arxiv-curator watch --from-awesome https://github.com/xxx/Awesome-SLAM --days 14
```

#### Field map

```bash
# Generate a field map for SLAM research
arxiv-curator map transformer SLAM --since 2024-01-01 --max-results 50

# Output as Markdown report
arxiv-curator map transformer SLAM --markdown

# Save as Markdown file
arxiv-curator map transformer SLAM --output field_map.md

# Save as JSON
arxiv-curator map "3D generation" --output field_map.json
```

The `map` command output includes:
- **Topic Clusters**: groups papers by dominant keywords in titles
- **Code Availability Trend**: code sharing ratio by year
- **Key Papers**: top papers by citation count
- **Gaps & Opportunities**: identifies years/topics with low code availability or activity

#### Rank papers

```bash
# Rank SLAM papers you should read now
arxiv-curator rank transformer SLAM --since 2024-01-01 --top 10

# With category filter
arxiv-curator rank "visual odometry" --category cs.RO --top 5

# Save detailed scoring results to JSON
arxiv-curator rank transformer SLAM --top 10 --output ranking.json
```

The rank output includes:
- **Percentile**: relative position among all papers (e.g. Top 5%)
- **Category**: score-based label (Must read / Recommended / Worth checking / Low priority)
- **Hidden gem**: auto-detects recent papers with code but low citations — underappreciated papers worth checking
- **Summary**: statistics including Must read count, code availability ratio, average citations

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

#### Paper ranking

```
$ arxiv-curator rank "3D gaussian splatting" --since 2023-06-01 --max-results 5 --top 5
Found 4 papers on arXiv.

                                 Ranked Papers
┏━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃  Rank ┃   Score ┃ Percentile ┃ Category        ┃  Citations ┃ Published   ┃
┡━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│     1 │     119 │     Top 1% │ Must read       │       7412 │ 2023-08-08  │
│     2 │      41 │    Top 25% │ Worth checking  │         60 │ 2024-06-17  │
│     3 │      10 │    Top 50% │ Low priority    │          0 │ 2025-09-09  │
│     4 │       0 │    Top 75% │ Low priority    │          0 │ 2023-12-01  │
└───────┴─────────┴────────────┴─────────────────┴────────────┴─────────────┘

Summary:
  Must read: 1 papers
  Recommended: 0 papers
  With code: 0/4 (0%)
  Top venue papers: 0
  Average citations: 1868.0
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
