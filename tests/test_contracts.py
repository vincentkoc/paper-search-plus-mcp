from datetime import datetime

from paper_search_plus_mcp.catalog import EXPERIMENTAL_SOURCES, SOURCE_CAPABILITIES
from paper_search_plus_mcp.paper import Paper

from .conftest import load_fixture


def test_paper_to_dict_matches_golden_contract():
    paper = Paper(
        paper_id="1234.5678",
        title="Example Paper",
        authors=["Ada Lovelace", "Alan Turing"],
        abstract="Example abstract",
        doi="10.1000/example",
        published_date=datetime(2024, 1, 2),
        pdf_url="https://example.org/paper.pdf",
        url="https://example.org/paper",
        source="arxiv",
        updated_date=datetime(2024, 1, 3),
        categories=["cs.AI", "cs.LG"],
        keywords=["llm", "search"],
        citations=3,
        references=["10.1000/ref1", "10.1000/ref2"],
        extra={"license": "cc-by"},
    )

    assert paper.to_dict() == load_fixture("paper_record.json")


def test_source_capabilities_match_golden_contract():
    assert {
        "supported": SOURCE_CAPABILITIES,
        "experimental": EXPERIMENTAL_SOURCES,
    } == load_fixture("source_capabilities.json")
