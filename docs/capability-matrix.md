# Capability Matrix

| Source | Search | Download | Read | Extra Tools | Notes |
| --- | --- | --- | --- | --- | --- |
| arXiv | Yes | Yes | Yes | None | Official API with configurable sort and field targeting. |
| PubMed | Yes | No | No | None | Metadata and abstracts only. |
| bioRxiv | Yes | Yes | Yes | None | Official API; category/date retrieval and DOI lookup. |
| medRxiv | Yes | Yes | Yes | None | Official API. |
| IACR | Yes | Yes | Yes | None | IACR ePrint archive. |
| CrossRef | Yes | No | No | `get_crossref_paper_by_doi` | Metadata and DOI lookup. |
| Semantic Scholar | Yes | Yes | Yes | citations, references, related, author search | Citation graph traversal. |
| OpenAlex | Yes | Yes | Yes | lookup, citations, references, related, author search | Open catalog and DOI lookup. |
| PMC | Yes | Yes | Yes | `get_pmc_paper` | Full-text PMC adapter. |
| CORE | Yes | Yes | Yes | None | Optional API key for higher limits. |
| Europe PMC | Yes | Yes | Yes | paper lookup, citations, related | Biomedical literature and preprints. |
| DBLP | Yes | No | No | `get_dblp_bibtex` | Bibliography-only integration. |
| HAL | Yes | Yes | Yes | None | French open archive. |
| Zenodo | Yes | Yes | Yes | record details, file listing | Official Zenodo records API. |

## Excluded From Default Surface

- Google Scholar: scraping-based and timeout-prone.
- Sci-Hub: legally risky.
- SSRN: currently scraping-based rather than an official API-backed integration.
