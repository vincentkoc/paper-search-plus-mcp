"""Supported academic source adapters for paper-search-plus-mcp."""

from .arxiv import ArxivSearcher
from .biorxiv import BioRxivSearcher
from .core import CoreSearcher
from .crossref import CrossRefSearcher
from .dblp import DBLPSearcher
from .europe_pmc import EuropePMCSearcher
from .hal import HALSearcher
from .iacr import IACRSearcher
from .medrxiv import MedRxivSearcher
from .openalex import OpenAlexSearcher
from .pmc import PMCSearcher
from .pubmed import PubMedSearcher
from .semantic import SemanticSearcher
from .zenodo import ZenodoSearcher

__all__ = [
    "ArxivSearcher",
    "BioRxivSearcher",
    "CoreSearcher",
    "CrossRefSearcher",
    "DBLPSearcher",
    "EuropePMCSearcher",
    "HALSearcher",
    "IACRSearcher",
    "MedRxivSearcher",
    "OpenAlexSearcher",
    "PMCSearcher",
    "PubMedSearcher",
    "SemanticSearcher",
    "ZenodoSearcher",
]
