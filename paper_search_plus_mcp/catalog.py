"""Stable source capability contracts for the curated public surface."""

SOURCE_CAPABILITIES = {
    "arxiv": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "Official arXiv API with configurable sort and field targeting.",
    },
    "pubmed": {
        "search": True,
        "download": False,
        "read": False,
        "extras": [],
        "notes": "Official NCBI metadata search with relevance sorting by default.",
    },
    "biorxiv": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "Official bioRxiv API; supports category retrieval and DOI lookup rather than free-text search.",
    },
    "medrxiv": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "Official medRxiv API.",
    },
    "iacr": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "IACR ePrint archive.",
    },
    "crossref": {
        "search": True,
        "download": False,
        "read": False,
        "extras": ["get_crossref_paper_by_doi"],
        "notes": "CrossRef metadata and DOI lookups.",
    },
    "semantic": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [
            "get_semantic_citations",
            "get_semantic_references",
            "get_semantic_related",
            "search_semantic_by_author",
        ],
        "notes": "Semantic Scholar search plus citation graph traversal.",
    },
    "openalex": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [
            "get_openalex_paper",
            "get_openalex_paper_by_doi",
            "get_openalex_citations",
            "get_openalex_references",
            "get_openalex_related",
            "search_openalex_by_author",
        ],
        "notes": "OpenAlex catalog, citations, references, related papers, and DOI lookups.",
    },
    "pmc": {
        "search": True,
        "download": True,
        "read": True,
        "extras": ["get_pmc_paper"],
        "notes": "PubMed Central full-text search and download.",
    },
    "core": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "CORE open-access search. API key optional for higher limits.",
    },
    "europe_pmc": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [
            "get_europe_pmc_paper",
            "get_europe_pmc_citations",
            "get_europe_pmc_related",
        ],
        "notes": "Europe PMC search, citations, related articles, and full text where available.",
    },
    "dblp": {
        "search": True,
        "download": False,
        "read": False,
        "extras": ["get_dblp_bibtex"],
        "notes": "DBLP bibliography and BibTeX export.",
    },
    "hal": {
        "search": True,
        "download": True,
        "read": True,
        "extras": [],
        "notes": "HAL open archive search and downloads.",
    },
    "zenodo": {
        "search": True,
        "download": True,
        "read": True,
        "extras": ["get_zenodo_record", "list_zenodo_files"],
        "notes": "Zenodo record search, files, downloads, and metadata inspection.",
    },
}

EXPERIMENTAL_SOURCES = {
    "google_scholar": "Excluded from the default surface because the adapter is scraping-based and timeout-prone.",
    "sci_hub": "Excluded from the default surface because it is legally risky.",
    "ssrn": "Imported for later evaluation only; excluded because it depends on unsupported scraping rather than an official API.",
}
