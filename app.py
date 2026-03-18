"""Streamlit web demo for arxiv-curator."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

import streamlit as st

from arxiv_curator.arxiv_api import search_papers
from arxiv_curator.formatter import format_as_json, format_as_markdown
from arxiv_curator.models import Paper
from arxiv_curator.parser import parse_awesome_readme, parse_awesome_url

st.set_page_config(page_title="arxiv-curator", page_icon=":books:", layout="wide")

st.title("arxiv-curator")
st.caption("arXiv paper search & curation tool")


def _papers_to_dataframe(papers: list[Paper]) -> list[dict]:
    """Convert papers to a list of dicts suitable for st.dataframe."""
    rows = []
    for paper in papers:
        authors_str = ", ".join(paper.authors[:3])
        if len(paper.authors) > 3:
            authors_str += " et al."
        rows.append(
            {
                "Title": paper.title,
                "Authors": authors_str,
                "Published": paper.published.strftime("%Y-%m-%d"),
                "Categories": ", ".join(paper.categories[:3]),
                "arXiv URL": paper.arxiv_url,
                "PDF URL": paper.pdf_url,
            }
        )
    return rows


def _fetch_readme(github_url: str) -> str | None:
    """Fetch README from a GitHub repo URL."""
    import requests
    from urllib.parse import urlparse

    parsed = urlparse(github_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        return None
    owner, repo = path_parts[0], path_parts[1]
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    try:
        resp = requests.get(raw_url, timeout=15)
        if resp.ok:
            return resp.text
    except requests.RequestException:
        pass
    return None


# --- Tabs ---
tab_search, tab_suggest, tab_about = st.tabs(["Search", "Suggest", "About"])

# ===== Search Tab =====
with tab_search:
    st.header("Search arXiv Papers")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Keywords",
            placeholder="e.g. SLAM LiDAR transformer",
            help="Enter keywords separated by spaces. They will be combined with AND.",
        )
    with col2:
        max_results = st.slider("Max results", min_value=5, max_value=100, value=20, step=5)

    since_date = st.date_input(
        "Published since",
        value=datetime.now().date() - timedelta(days=30),
        help="Only show papers published on or after this date.",
    )

    if st.button("Search", type="primary", key="search_btn"):
        if not search_query.strip():
            st.warning("Please enter at least one keyword.")
        else:
            keywords = search_query.strip().split()
            query = " AND ".join(keywords)
            since_dt = datetime(since_date.year, since_date.month, since_date.day)

            with st.spinner("Searching arXiv..."):
                papers = search_papers(query, max_results=max_results, since_date=since_dt)

            if not papers:
                st.info("No papers found.")
            else:
                st.success(f"Found {len(papers)} papers.")
                st.session_state["search_papers"] = papers

    # Display results if available
    if "search_papers" in st.session_state:
        papers = st.session_state["search_papers"]
        rows = _papers_to_dataframe(papers)
        st.dataframe(
            rows,
            column_config={
                "arXiv URL": st.column_config.LinkColumn("arXiv URL"),
                "PDF URL": st.column_config.LinkColumn("PDF URL"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Download buttons
        col_md, col_json = st.columns(2)
        with col_md:
            md_content = format_as_markdown(papers)
            st.download_button(
                "Download as Markdown",
                data=md_content,
                file_name="arxiv_papers.md",
                mime="text/markdown",
            )
        with col_json:
            json_content = format_as_json(papers)
            st.download_button(
                "Download as JSON",
                data=json_content,
                file_name="arxiv_papers.json",
                mime="application/json",
            )

# ===== Suggest Tab =====
with tab_suggest:
    st.header("Suggest New Papers for Awesome-List")

    awesome_url = st.text_input(
        "Awesome-list GitHub URL",
        placeholder="https://github.com/xxx/Awesome-Transformer-based-SLAM",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        suggest_max = st.slider("Max results", min_value=5, max_value=100, value=20, step=5, key="suggest_max")
    with col2:
        suggest_since = st.date_input(
            "Published since",
            value=datetime.now().date() - timedelta(days=30),
            key="suggest_since",
        )

    if st.button("Suggest Papers", type="primary", key="suggest_btn"):
        if not awesome_url.strip():
            st.warning("Please enter a GitHub URL.")
        else:
            keywords = parse_awesome_url(awesome_url.strip())
            if not keywords:
                st.error("Could not extract keywords from the URL.")
            else:
                st.info(f"Extracted keywords: **{', '.join(keywords)}**")

                # Fetch existing entries
                existing: set[str] = set()
                with st.spinner("Fetching README for deduplication..."):
                    readme_text = _fetch_readme(awesome_url.strip())
                    if readme_text:
                        existing = parse_awesome_readme(readme_text)
                        st.write(f"Found {len(existing)} existing entries in README.")
                    else:
                        st.warning("Could not fetch README; skipping deduplication.")

                query = " AND ".join(keywords)
                since_dt = datetime(suggest_since.year, suggest_since.month, suggest_since.day)

                with st.spinner("Searching arXiv..."):
                    papers = search_papers(query, max_results=suggest_max, since_date=since_dt)

                # Deduplicate
                new_papers = []
                for p in papers:
                    arxiv_id_match = re.search(r"\d{4}\.\d{4,5}", p.arxiv_url)
                    arxiv_id = arxiv_id_match.group() if arxiv_id_match else ""
                    if p.title.lower() not in existing and arxiv_id not in existing:
                        new_papers.append(p)

                if not new_papers:
                    st.info("No new papers found.")
                else:
                    filtered = len(papers) - len(new_papers)
                    st.success(f"{len(new_papers)} new papers (filtered {filtered} duplicates).")
                    st.session_state["suggest_papers"] = new_papers

    # Display results if available
    if "suggest_papers" in st.session_state:
        papers = st.session_state["suggest_papers"]
        rows = _papers_to_dataframe(papers)
        st.dataframe(
            rows,
            column_config={
                "arXiv URL": st.column_config.LinkColumn("arXiv URL"),
                "PDF URL": st.column_config.LinkColumn("PDF URL"),
            },
            use_container_width=True,
            hide_index=True,
        )

        col_md, col_json = st.columns(2)
        with col_md:
            md_content = format_as_markdown(papers)
            st.download_button(
                "Download as Markdown",
                data=md_content,
                file_name="suggest_papers.md",
                mime="text/markdown",
                key="suggest_dl_md",
            )
        with col_json:
            json_content = format_as_json(papers)
            st.download_button(
                "Download as JSON",
                data=json_content,
                file_name="suggest_papers.json",
                mime="application/json",
                key="suggest_dl_json",
            )

# ===== About Tab =====
with tab_about:
    st.header("About")
    st.markdown(
        """
**arxiv-curator** is a tool for searching arXiv papers by keywords and curating them
in awesome-list format. It integrates with GitHub awesome repositories to suggest
new papers that are not already listed.

### Features

- Search arXiv papers by keywords with date filtering
- Suggest new papers for awesome-list repositories (with deduplication)
- Export results as Markdown or JSON
- CLI and Web UI

### Related Projects

| Project | Description |
|---------|-------------|
| [arxiv-curator](https://github.com/rsasaki0109/arxiv-curator) | arXiv paper search & curation |
| [github-curator](https://github.com/rsasaki0109/github-curator) | GitHub repository curation |

The JSON output follows a shared schema compatible with github-curator,
enabling interoperability between the two tools.

### License

MIT
"""
    )
