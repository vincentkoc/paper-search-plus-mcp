import argparse
import asyncio
import json
from typing import Any, Iterable, Optional

from mcp.server.fastmcp import FastMCP

from .academic_platforms.arxiv import ArxivSearcher
from .academic_platforms.biorxiv import BioRxivSearcher
from .academic_platforms.core import CoreSearcher
from .academic_platforms.crossref import CrossRefSearcher
from .academic_platforms.dblp import DBLPSearcher
from .academic_platforms.europe_pmc import EuropePMCSearcher
from .academic_platforms.hal import HALSearcher
from .academic_platforms.iacr import IACRSearcher
from .academic_platforms.medrxiv import MedRxivSearcher
from .academic_platforms.openalex import OpenAlexSearcher
from .academic_platforms.pmc import PMCSearcher
from .academic_platforms.pubmed import PubMedSearcher
from .academic_platforms.semantic import SemanticSearcher
from .academic_platforms.zenodo import ZenodoSearcher
from .catalog import EXPERIMENTAL_SOURCES, SOURCE_CAPABILITIES
from .paper import Paper

mcp = FastMCP("paper-search-plus-mcp")

arxiv_searcher = ArxivSearcher()
pubmed_searcher = PubMedSearcher()
biorxiv_searcher = BioRxivSearcher()
medrxiv_searcher = MedRxivSearcher()
iacr_searcher = IACRSearcher()
semantic_searcher = SemanticSearcher()
crossref_searcher = CrossRefSearcher()
openalex_searcher = OpenAlexSearcher()
pmc_searcher = PMCSearcher()
core_searcher = CoreSearcher()
europe_pmc_searcher = EuropePMCSearcher()
dblp_searcher = DBLPSearcher()
hal_searcher = HALSearcher()
zenodo_searcher = ZenodoSearcher()


def _paper_list(papers: Iterable[Paper]) -> list[dict[str, Any]]:
    return [paper.to_dict() for paper in papers]


def _paper_or_empty(paper: Optional[Paper]) -> dict[str, Any]:
    return paper.to_dict() if paper else {}


def _safe_download(searcher: Any, paper_id: str, save_path: str) -> str:
    try:
        return searcher.download_pdf(paper_id, save_path)
    except NotImplementedError as exc:
        return str(exc)


def _safe_read(searcher: Any, paper_id: str, save_path: str) -> str:
    try:
        return searcher.read_paper(paper_id, save_path)
    except NotImplementedError as exc:
        return str(exc)
    except Exception as exc:
        print(f"Error reading paper {paper_id}: {exc}")
        return ""


def _tool_names() -> list[str]:
    return sorted(tool.name for tool in asyncio.run(mcp.list_tools()))


@mcp.tool()
async def get_source_capabilities() -> dict[str, Any]:
    """Return the curated public source contract used by the MCP server."""

    return {
        "supported": SOURCE_CAPABILITIES,
        "experimental": EXPERIMENTAL_SOURCES,
    }


@mcp.tool()
async def search_arxiv(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    sort_order: str = "descending",
    search_field: str = "all",
) -> list[dict[str, Any]]:
    return _paper_list(
        arxiv_searcher.search(
            query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
            search_field=search_field,
        )
    )


@mcp.tool()
async def search_pubmed(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
) -> list[dict[str, Any]]:
    return _paper_list(pubmed_searcher.search(query, max_results=max_results, sort=sort))


@mcp.tool()
async def search_biorxiv(
    query: str,
    max_results: int = 10,
    days: int = 30,
    search_mode: str = "category",
) -> list[dict[str, Any]]:
    return _paper_list(
        biorxiv_searcher.search(
            query,
            max_results=max_results,
            days=days,
            search_mode=search_mode,
        )
    )


@mcp.tool()
async def search_medrxiv(
    query: str,
    max_results: int = 10,
    days: int = 30,
) -> list[dict[str, Any]]:
    return _paper_list(medrxiv_searcher.search(query, max_results=max_results, days=days))


@mcp.tool()
async def search_iacr(
    query: str,
    max_results: int = 10,
    fetch_details: bool = True,
) -> list[dict[str, Any]]:
    return _paper_list(iacr_searcher.search(query, max_results, fetch_details))


@mcp.tool()
async def search_crossref(
    query: str,
    max_results: int = 10,
    filter: str = "",
    sort: str = "relevance",
    order: str = "desc",
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {"sort": sort, "order": order}
    if filter:
        kwargs["filter"] = filter
    return _paper_list(crossref_searcher.search(query, max_results=max_results, **kwargs))


@mcp.tool()
async def get_crossref_paper_by_doi(doi: str) -> dict[str, Any]:
    return _paper_or_empty(crossref_searcher.get_paper_by_doi(doi))


@mcp.tool()
async def search_semantic(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
) -> list[dict[str, Any]]:
    return _paper_list(semantic_searcher.search(query, year=year, max_results=max_results))


@mcp.tool()
async def get_semantic_citations(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(semantic_searcher.get_citations(paper_id, max_results=max_results))


@mcp.tool()
async def get_semantic_references(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(semantic_searcher.get_references(paper_id, max_results=max_results))


@mcp.tool()
async def get_semantic_related(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(semantic_searcher.get_related_papers(paper_id, max_results=max_results))


@mcp.tool()
async def search_semantic_by_author(
    author_name: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(semantic_searcher.search_by_author(author_name, max_results=max_results))


@mcp.tool()
async def search_openalex(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    filter: str = "",
    sort: str = "",
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if filter:
        kwargs["filter"] = filter
    if sort:
        kwargs["sort"] = sort
    return _paper_list(openalex_searcher.search(query, max_results=max_results, year=year, **kwargs))


@mcp.tool()
async def get_openalex_paper(paper_id: str) -> dict[str, Any]:
    return _paper_or_empty(openalex_searcher.get_paper_by_id(paper_id))


@mcp.tool()
async def get_openalex_paper_by_doi(doi: str) -> dict[str, Any]:
    return _paper_or_empty(openalex_searcher.get_paper_by_doi(doi))


@mcp.tool()
async def get_openalex_citations(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(openalex_searcher.get_citations(paper_id, max_results=max_results))


@mcp.tool()
async def get_openalex_references(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(openalex_searcher.get_references(paper_id, max_results=max_results))


@mcp.tool()
async def get_openalex_related(
    paper_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(openalex_searcher.get_related_papers(paper_id, max_results=max_results))


@mcp.tool()
async def search_openalex_by_author(
    author_name: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(openalex_searcher.search_by_author(author_name, max_results=max_results))


@mcp.tool()
async def search_pmc(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    return _paper_list(pmc_searcher.search(query, max_results=max_results))


@mcp.tool()
async def get_pmc_paper(pmcid: str) -> dict[str, Any]:
    return _paper_or_empty(pmc_searcher.get_paper_by_pmcid(pmcid))


@mcp.tool()
async def search_core(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    repository_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    return _paper_list(
        core_searcher.search(
            query,
            max_results=max_results,
            year=year,
            repository_id=repository_id,
        )
    )


@mcp.tool()
async def search_europe_pmc(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    result_type: str = "all",
    sort_by: str = "relevance",
) -> list[dict[str, Any]]:
    return _paper_list(
        europe_pmc_searcher.search(
            query,
            max_results=max_results,
            year=year,
            result_type=result_type,
            sort_by=sort_by,
        )
    )


@mcp.tool()
async def get_europe_pmc_paper(article_id: str) -> dict[str, Any]:
    return _paper_or_empty(europe_pmc_searcher.get_paper_by_id(article_id))


@mcp.tool()
async def get_europe_pmc_citations(
    article_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(europe_pmc_searcher.get_citations(article_id, max_results=max_results))


@mcp.tool()
async def get_europe_pmc_related(
    article_id: str,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    return _paper_list(
        europe_pmc_searcher.get_related_articles(article_id, max_results=max_results)
    )


@mcp.tool()
async def search_dblp(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    venue_type: Optional[str] = None,
    venue: Optional[str] = None,
    author: Optional[str] = None,
) -> list[dict[str, Any]]:
    return _paper_list(
        dblp_searcher.search(
            query,
            max_results=max_results,
            year=year,
            venue_type=venue_type,
            venue=venue,
            author=author,
        )
    )


@mcp.tool()
async def get_dblp_bibtex(key: str) -> str:
    return dblp_searcher.download_bibtex(key) or ""


@mcp.tool()
async def search_hal(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    doc_type: Optional[str] = None,
    domain: Optional[str] = None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if doc_type:
        kwargs["doc_type"] = doc_type
    if domain:
        kwargs["domain"] = domain
    return _paper_list(hal_searcher.search(query, max_results=max_results, year=year, **kwargs))


@mcp.tool()
async def search_zenodo(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    resource_type: Optional[str] = None,
    sort: str = "bestmatch",
) -> list[dict[str, Any]]:
    return _paper_list(
        zenodo_searcher.search(
            query,
            max_results=max_results,
            year=year,
            resource_type=resource_type,
            sort=sort,
        )
    )


@mcp.tool()
async def get_zenodo_record(record_id: str) -> dict[str, Any]:
    return zenodo_searcher.get_record_details(record_id) or {}


@mcp.tool()
async def list_zenodo_files(record_id: str) -> list[dict[str, Any]]:
    return zenodo_searcher.list_files(record_id)


@mcp.tool()
async def deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from .deduplication import deduplicate_paper_dicts as dedup

    return dedup(papers)


@mcp.tool()
async def find_duplicate_groups(papers: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    from .deduplication import dict_to_paper, find_duplicates

    groups = []
    paper_objects = [dict_to_paper(paper) for paper in papers]
    for canonical, duplicates in find_duplicates(paper_objects):
        groups.append([canonical.to_dict(), *[paper.to_dict() for paper in duplicates]])
    return groups


@mcp.tool()
async def merge_papers(papers: list[dict[str, Any]]) -> dict[str, Any]:
    from .deduplication import dict_to_paper, merge_paper_group

    return merge_paper_group([dict_to_paper(paper) for paper in papers]).to_dict()


@mcp.tool()
async def download_arxiv(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(arxiv_searcher, paper_id, save_path)


@mcp.tool()
async def read_arxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(arxiv_searcher, paper_id, save_path)


@mcp.tool()
async def download_pubmed(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(pubmed_searcher, paper_id, save_path)


@mcp.tool()
async def read_pubmed_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(pubmed_searcher, paper_id, save_path)


@mcp.tool()
async def download_biorxiv(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(biorxiv_searcher, paper_id, save_path)


@mcp.tool()
async def read_biorxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(biorxiv_searcher, paper_id, save_path)


@mcp.tool()
async def download_medrxiv(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(medrxiv_searcher, paper_id, save_path)


@mcp.tool()
async def read_medrxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(medrxiv_searcher, paper_id, save_path)


@mcp.tool()
async def download_iacr(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(iacr_searcher, paper_id, save_path)


@mcp.tool()
async def read_iacr_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(iacr_searcher, paper_id, save_path)


@mcp.tool()
async def download_semantic(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(semantic_searcher, paper_id, save_path)


@mcp.tool()
async def read_semantic_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(semantic_searcher, paper_id, save_path)


@mcp.tool()
async def download_openalex(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(openalex_searcher, paper_id, save_path)


@mcp.tool()
async def read_openalex_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(openalex_searcher, paper_id, save_path)


@mcp.tool()
async def download_pmc(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(pmc_searcher, paper_id, save_path)


@mcp.tool()
async def read_pmc_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(pmc_searcher, paper_id, save_path)


@mcp.tool()
async def download_core(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(core_searcher, paper_id, save_path)


@mcp.tool()
async def read_core_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(core_searcher, paper_id, save_path)


@mcp.tool()
async def download_europe_pmc(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(europe_pmc_searcher, paper_id, save_path)


@mcp.tool()
async def read_europe_pmc_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(europe_pmc_searcher, paper_id, save_path)


@mcp.tool()
async def download_hal(paper_id: str, save_path: str = "./downloads") -> str:
    return hal_searcher.download_file(paper_id, save_path)


@mcp.tool()
async def read_hal_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(hal_searcher, paper_id, save_path)


@mcp.tool()
async def download_zenodo(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_download(zenodo_searcher, paper_id, save_path)


@mcp.tool()
async def read_zenodo_paper(paper_id: str, save_path: str = "./downloads") -> str:
    return _safe_read(zenodo_searcher, paper_id, save_path)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="paper-search-plus-mcp")
    parser.add_argument("--transport", default="stdio", choices=["stdio"])
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.list_tools:
        payload: Any = _tool_names()
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("\n".join(payload))
        return 0

    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
