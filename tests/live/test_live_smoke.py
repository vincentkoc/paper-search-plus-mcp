import os

import pytest

from paper_search_plus_mcp.academic_platforms.arxiv import ArxivSearcher
from paper_search_plus_mcp.academic_platforms.biorxiv import BioRxivSearcher
from paper_search_plus_mcp.academic_platforms.core import CoreSearcher
from paper_search_plus_mcp.academic_platforms.crossref import CrossRefSearcher
from paper_search_plus_mcp.academic_platforms.dblp import DBLPSearcher
from paper_search_plus_mcp.academic_platforms.europe_pmc import EuropePMCSearcher
from paper_search_plus_mcp.academic_platforms.hal import HALSearcher
from paper_search_plus_mcp.academic_platforms.iacr import IACRSearcher
from paper_search_plus_mcp.academic_platforms.medrxiv import MedRxivSearcher
from paper_search_plus_mcp.academic_platforms.openalex import OpenAlexSearcher
from paper_search_plus_mcp.academic_platforms.pmc import PMCSearcher
from paper_search_plus_mcp.academic_platforms.pubmed import PubMedSearcher
from paper_search_plus_mcp.academic_platforms.semantic import SemanticSearcher
from paper_search_plus_mcp.academic_platforms.zenodo import ZenodoSearcher


pytestmark = pytest.mark.skipif(
    os.environ.get("PAPER_SEARCH_PLUS_LIVE_SMOKE") != "1",
    reason="set PAPER_SEARCH_PLUS_LIVE_SMOKE=1 to run live provider checks",
)


@pytest.mark.parametrize(
    ("name", "callable_"),
    [
        ("arxiv", lambda: ArxivSearcher().search("transformers", max_results=1)),
        ("pubmed", lambda: PubMedSearcher().search("ocular microbiome", max_results=1)),
        ("biorxiv", lambda: BioRxivSearcher().search("genomics", max_results=1, search_mode="category")),
        ("medrxiv", lambda: MedRxivSearcher().search("epidemiology", max_results=1)),
        ("iacr", lambda: IACRSearcher().search("zero knowledge", 1, False)),
        ("crossref", lambda: CrossRefSearcher().search("graph neural networks", max_results=1)),
        ("semantic", lambda: SemanticSearcher().search("machine learning", max_results=1)),
        ("openalex", lambda: OpenAlexSearcher().search("machine learning", max_results=1)),
        ("pmc", lambda: PMCSearcher().search("covid", max_results=1)),
        ("core", lambda: CoreSearcher().search("machine learning", max_results=1)),
        ("europe_pmc", lambda: EuropePMCSearcher().search("covid", max_results=1)),
        ("dblp", lambda: DBLPSearcher().search("transformers", max_results=1)),
        ("hal", lambda: HALSearcher().search("transformers", max_results=1)),
        ("zenodo", lambda: ZenodoSearcher().search("machine learning", max_results=1)),
    ],
)
def test_live_search_smoke(name, callable_):
    results = callable_()
    assert isinstance(results, list), name
