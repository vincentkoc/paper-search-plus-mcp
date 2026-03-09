from datetime import datetime

from paper_search_plus_mcp.deduplication import (
    deduplicate_paper_dicts,
    find_duplicates,
    merge_paper_group,
)
from paper_search_plus_mcp.paper import Paper


def make_paper(source: str, doi: str, title: str, abstract: str = ""):
    return Paper(
        paper_id=f"{source}-1",
        title=title,
        authors=["Ada Lovelace", "Alan Turing"],
        abstract=abstract,
        doi=doi,
        published_date=datetime(2024, 1, 1),
        pdf_url="",
        url=f"https://example.org/{source}",
        source=source,
    )


def test_deduplicate_paper_dicts_prefers_best_metadata():
    first = make_paper("arxiv", "10.1000/example", "Example Paper")
    second = make_paper(
        "openalex",
        "https://doi.org/10.1000/example",
        "Example Paper",
        abstract="More complete abstract",
    )

    result = deduplicate_paper_dicts([first.to_dict(), second.to_dict()], keep="best")

    assert len(result) == 1
    assert result[0]["abstract"] == "More complete abstract"


def test_find_duplicates_groups_same_paper():
    first = make_paper("arxiv", "10.1000/example", "Example Paper")
    second = make_paper("pubmed", "10.1000/example", "Example Paper")

    groups = find_duplicates([first, second])

    assert len(groups) == 1
    assert groups[0][0].source == "arxiv"
    assert groups[0][1][0].source == "pubmed"


def test_merge_paper_group_combines_sources_and_metadata():
    first = make_paper("arxiv", "10.1000/example", "Example Paper")
    second = make_paper("openalex", "10.1000/example", "Example Paper", abstract="Merged abstract")

    merged = merge_paper_group([first, second])

    assert merged.abstract == "Merged abstract"
    assert merged.extra["merged_from"] == ["arxiv", "openalex"]
