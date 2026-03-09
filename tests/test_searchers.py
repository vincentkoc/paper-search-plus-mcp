from types import SimpleNamespace

import pytest

from paper_search_plus_mcp.academic_platforms.arxiv import ArxivSearcher
from paper_search_plus_mcp.academic_platforms.biorxiv import BioRxivSearcher
from paper_search_plus_mcp.academic_platforms.pubmed import PubMedSearcher


class MockResponse:
    def __init__(self, *, content=b"", json_data=None, status_code=200):
        self.content = content
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("request failed")

    def json(self):
        return self._json_data


def test_arxiv_search_uses_configurable_query_shape(monkeypatch):
    params_seen = {}

    def fake_get(url, params=None, timeout=30):
        params_seen.update(params)
        return MockResponse(content=b"<feed/>")

    def fake_parse(_content):
        entry = SimpleNamespace(
            id="http://arxiv.org/abs/1234.5678v1",
            title="Example",
            summary="Abstract",
            authors=[SimpleNamespace(name="Ada")],
            links=[SimpleNamespace(type="application/pdf", href="https://arxiv.org/pdf/1234.5678.pdf")],
            tags=[SimpleNamespace(term="cs.AI")],
            published="2024-01-01T00:00:00Z",
            updated="2024-01-02T00:00:00Z",
            get=lambda _key, default="": default,
        )
        return SimpleNamespace(entries=[entry])

    monkeypatch.setattr("paper_search_plus_mcp.academic_platforms.arxiv.requests.get", fake_get)
    monkeypatch.setattr("paper_search_plus_mcp.academic_platforms.arxiv.feedparser.parse", fake_parse)

    papers = ArxivSearcher().search(
        "transformers",
        max_results=25,
        sort_by="relevance",
        sort_order="ascending",
        search_field="ti",
    )

    assert params_seen["search_query"] == "ti:transformers"
    assert params_seen["max_results"] == 25
    assert params_seen["sortBy"] == "relevance"
    assert params_seen["sortOrder"] == "ascending"
    assert papers[0].paper_id == "1234.5678v1"


def test_pubmed_search_defaults_to_relevance(monkeypatch):
    requests_seen = []

    def fake_get(url, params=None, timeout=30):
        requests_seen.append((url, params))
        if "esearch" in url:
            return MockResponse(content=b"<eSearchResult><IdList><Id>123</Id></IdList></eSearchResult>")
        return MockResponse(
            content=(
                b"<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>"
                b"<Article><ArticleTitle>Example</ArticleTitle><Abstract><AbstractText>Body</AbstractText></Abstract>"
                b"<AuthorList><Author><LastName>Lovelace</LastName><Initials>A</Initials></Author></AuthorList>"
                b"<Journal><JournalIssue><PubDate><Year>2024</Year><Month>01</Month><Day>02</Day></PubDate></JournalIssue></Journal>"
                b"</Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType='doi'>10.1000/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"
            )
        )

    monkeypatch.setattr("paper_search_plus_mcp.academic_platforms.pubmed.requests.get", fake_get)

    papers = PubMedSearcher().search("ocular microbiome", max_results=5)

    assert requests_seen[0][1]["sort"] == "relevance"
    assert papers[0].doi == "10.1000/example"
    assert papers[0].authors == ["Lovelace A"]


def test_biorxiv_search_uses_official_category_mode(monkeypatch):
    seen = {}

    def fake_get(url, timeout=30):
        seen["url"] = url
        return MockResponse(
            json_data={
                "collection": [
                    {
                        "doi": "10.1101/2024.01.01.123456",
                        "title": "Example bioRxiv paper",
                        "authors": "Ada Lovelace; Alan Turing",
                        "abstract": "Example abstract",
                        "date": "2024-02-01",
                        "version": "1",
                        "category": "genomics",
                    }
                ]
            }
        )

    searcher = BioRxivSearcher()
    monkeypatch.setattr(searcher.session, "get", fake_get)

    papers = searcher.search("genomics", max_results=1, search_mode="category", days=7)

    assert "category=genomics" in seen["url"]
    assert papers[0].source == "biorxiv"
    assert papers[0].doi == "10.1101/2024.01.01.123456"


def test_biorxiv_rejects_unsupported_search_modes():
    with pytest.raises(ValueError):
        BioRxivSearcher().search("llm", search_mode="text")
