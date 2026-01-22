# paper_search_mcp/server.py
from typing import List, Dict, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from .academic_platforms.arxiv import ArxivSearcher
from .academic_platforms.pubmed import PubMedSearcher
from .academic_platforms.biorxiv import BioRxivSearcher
from .academic_platforms.medrxiv import MedRxivSearcher
from .academic_platforms.google_scholar import GoogleScholarSearcher
from .academic_platforms.iacr import IACRSearcher
from .academic_platforms.semantic import SemanticSearcher
from .academic_platforms.crossref import CrossRefSearcher
from .academic_platforms.openalex import OpenAlexSearcher

# from .academic_platforms.hub import SciHubSearcher
from .paper import Paper

# Initialize MCP server
mcp = FastMCP("paper_search_server")

# Instances of searchers
arxiv_searcher = ArxivSearcher()
pubmed_searcher = PubMedSearcher()
biorxiv_searcher = BioRxivSearcher()
medrxiv_searcher = MedRxivSearcher()
google_scholar_searcher = GoogleScholarSearcher()
iacr_searcher = IACRSearcher()
semantic_searcher = SemanticSearcher()
crossref_searcher = CrossRefSearcher()
openalex_searcher = OpenAlexSearcher()
# scihub_searcher = SciHubSearcher()


# Asynchronous helper to adapt synchronous searchers
async def async_search(searcher, query: str, max_results: int, **kwargs) -> List[Dict]:
    async with httpx.AsyncClient() as client:
        # Assuming searchers use requests internally; we'll call synchronously for now
        if 'year' in kwargs:
            papers = searcher.search(query, year=kwargs['year'], max_results=max_results)
        else:
            papers = searcher.search(query, max_results=max_results)
        return [paper.to_dict() for paper in papers]


# Tool definitions
@mcp.tool()
async def search_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from arXiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    papers = await async_search(arxiv_searcher, query, max_results)
    return papers if papers else []


@mcp.tool()
async def search_pubmed(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from PubMed.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    papers = await async_search(pubmed_searcher, query, max_results)
    return papers if papers else []


@mcp.tool()
async def search_biorxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from bioRxiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    papers = await async_search(biorxiv_searcher, query, max_results)
    return papers if papers else []


@mcp.tool()
async def search_medrxiv(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from medRxiv.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    papers = await async_search(medrxiv_searcher, query, max_results)
    return papers if papers else []


@mcp.tool()
async def search_google_scholar(query: str, max_results: int = 10) -> List[Dict]:
    """Search academic papers from Google Scholar.

    Args:
        query: Search query string (e.g., 'machine learning').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    papers = await async_search(google_scholar_searcher, query, max_results)
    return papers if papers else []


@mcp.tool()
async def search_iacr(
    query: str, max_results: int = 10, fetch_details: bool = True
) -> List[Dict]:
    """Search academic papers from IACR ePrint Archive.

    Args:
        query: Search query string (e.g., 'cryptography', 'secret sharing').
        max_results: Maximum number of papers to return (default: 10).
        fetch_details: Whether to fetch detailed information for each paper (default: True).
    Returns:
        List of paper metadata in dictionary format.
    """
    async with httpx.AsyncClient() as client:
        papers = iacr_searcher.search(query, max_results, fetch_details)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def download_arxiv(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of an arXiv paper.

    Args:
        paper_id: arXiv paper ID (e.g., '2106.12345').
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        Path to the downloaded PDF file.
    """
    async with httpx.AsyncClient() as client:
        return arxiv_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def download_pubmed(paper_id: str, save_path: str = "./downloads") -> str:
    """Attempt to download PDF of a PubMed paper.

    Args:
        paper_id: PubMed ID (PMID).
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        str: Message indicating that direct PDF download is not supported.
    """
    try:
        return pubmed_searcher.download_pdf(paper_id, save_path)
    except NotImplementedError as e:
        return str(e)


@mcp.tool()
async def download_biorxiv(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of a bioRxiv paper.

    Args:
        paper_id: bioRxiv DOI.
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        Path to the downloaded PDF file.
    """
    return biorxiv_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def download_medrxiv(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of a medRxiv paper.

    Args:
        paper_id: medRxiv DOI.
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        Path to the downloaded PDF file.
    """
    return medrxiv_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def download_iacr(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of an IACR ePrint paper.

    Args:
        paper_id: IACR paper ID (e.g., '2009/101').
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        Path to the downloaded PDF file.
    """
    return iacr_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def read_arxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an arXiv paper PDF.

    Args:
        paper_id: arXiv paper ID (e.g., '2106.12345').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return arxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


@mcp.tool()
async def read_pubmed_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a PubMed paper.

    Args:
        paper_id: PubMed ID (PMID).
        save_path: Directory where the PDF would be saved (unused).
    Returns:
        str: Message indicating that direct paper reading is not supported.
    """
    return pubmed_searcher.read_paper(paper_id, save_path)


@mcp.tool()
async def read_biorxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a bioRxiv paper PDF.

    Args:
        paper_id: bioRxiv DOI.
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return biorxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


@mcp.tool()
async def read_medrxiv_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a medRxiv paper PDF.

    Args:
        paper_id: medRxiv DOI.
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return medrxiv_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


@mcp.tool()
async def read_iacr_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an IACR ePrint paper PDF.

    Args:
        paper_id: IACR paper ID (e.g., '2009/101').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return iacr_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


@mcp.tool()
async def search_semantic(query: str, year: Optional[str] = None, max_results: int = 10) -> List[Dict]:
    """Search academic papers from Semantic Scholar.

    Args:
        query: Search query string (e.g., 'machine learning').
        year: Optional year filter (e.g., '2019', '2016-2020', '2010-', '-2015').
        max_results: Maximum number of papers to return (default: 10).
    Returns:
        List of paper metadata in dictionary format.
    """
    kwargs = {}
    if year is not None:
        kwargs['year'] = year
    papers = await async_search(semantic_searcher, query, max_results, **kwargs)
    return papers if papers else []


@mcp.tool()
async def download_semantic(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of a Semantic Scholar paper.    

    Args:
        paper_id: Semantic Scholar paper ID, Paper identifier in one of the following formats:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI:<doi> (e.g., "DOI:10.18653/v1/N18-3011")
            - ARXIV:<id> (e.g., "ARXIV:2106.15928")
            - MAG:<id> (e.g., "MAG:112218234")
            - ACL:<id> (e.g., "ACL:W12-3903")
            - PMID:<id> (e.g., "PMID:19872477")
            - PMCID:<id> (e.g., "PMCID:2323736")
            - URL:<url> (e.g., "URL:https://arxiv.org/abs/2106.15928v1")
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        Path to the downloaded PDF file.
    """ 
    return semantic_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def read_semantic_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from a Semantic Scholar paper.

    Args:
        paper_id: Semantic Scholar paper ID, Paper identifier in one of the following formats:
            - Semantic Scholar ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
            - DOI:<doi> (e.g., "DOI:10.18653/v1/N18-3011")
            - ARXIV:<id> (e.g., "ARXIV:2106.15928")
            - MAG:<id> (e.g., "MAG:112218234")
            - ACL:<id> (e.g., "ACL:W12-3903")
            - PMID:<id> (e.g., "PMID:19872477")
            - PMCID:<id> (e.g., "PMCID:2323736")
            - URL:<url> (e.g., "URL:https://arxiv.org/abs/2106.15928v1")
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: The extracted text content of the paper.
    """
    try:
        return semantic_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


@mcp.tool()
async def get_semantic_citations(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers that cite this Semantic Scholar paper (forward citations).

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of citing papers to return (default: 20)

    Returns:
        List of papers that cite the given paper.

    Example:
        await get_semantic_citations("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = semantic_searcher.get_citations(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_semantic_references(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers referenced by this Semantic Scholar paper (backward citations).

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of referenced papers to return (default: 20)

    Returns:
        List of papers referenced by the given paper.

    Example:
        await get_semantic_references("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = semantic_searcher.get_references(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_semantic_related(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers related to this Semantic Scholar paper based on citations and concepts.

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "649def34f8be52c8b66281af98ae884c09aef38b")
        max_results: Maximum number of related papers to return (default: 20)

    Returns:
        List of related papers.

    Example:
        await get_semantic_related("5bbfdf2e62f0508c65ba6de9c72fe2066fd98138", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = semantic_searcher.get_related_papers(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_semantic_by_author(
    author_name: str,
    max_results: int = 20
) -> List[Dict]:
    """Search for papers by a specific author in Semantic Scholar.

    Args:
        author_name: Name of the author (e.g., 'Geoffrey Hinton')
        max_results: Maximum number of papers to return (default: 20)

    Returns:
        List of papers by the author.

    Example:
        await search_semantic_by_author("Yann LeCun", 15)
    """
    async with httpx.AsyncClient() as client:
        papers = semantic_searcher.search_by_author(author_name, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_crossref(query: str, max_results: int = 10, **kwargs) -> List[Dict]:
    """Search academic papers from CrossRef database.
    
    CrossRef is a scholarly infrastructure organization that provides 
    persistent identifiers (DOIs) for scholarly content and metadata.
    It's one of the largest citation databases covering millions of 
    academic papers, journals, books, and other scholarly content.

    Args:
        query: Search query string (e.g., 'machine learning', 'climate change').
        max_results: Maximum number of papers to return (default: 10, max: 1000).
        **kwargs: Additional search parameters:
            - filter: CrossRef filter string (e.g., 'has-full-text:true,from-pub-date:2020')
            - sort: Sort field ('relevance', 'published', 'updated', 'deposited', etc.)
            - order: Sort order ('asc' or 'desc')
    Returns:
        List of paper metadata in dictionary format.
        
    Examples:
        # Basic search
        search_crossref("deep learning", 20)
        
        # Search with filters
        search_crossref("climate change", 10, filter="from-pub-date:2020,has-full-text:true")
        
        # Search sorted by publication date
        search_crossref("neural networks", 15, sort="published", order="desc")
    """
    papers = await async_search(crossref_searcher, query, max_results, **kwargs)
    return papers if papers else []


@mcp.tool()
async def get_crossref_paper_by_doi(doi: str) -> Dict:
    """Get a specific paper from CrossRef by its DOI.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/nature12373').
    Returns:
        Paper metadata in dictionary format, or empty dict if not found.
        
    Example:
        get_crossref_paper_by_doi("10.1038/nature12373")
    """
    async with httpx.AsyncClient() as client:
        paper = crossref_searcher.get_paper_by_doi(doi)
        return paper.to_dict() if paper else {}


@mcp.tool()
async def download_crossref(paper_id: str, save_path: str = "./downloads") -> str:
    """Attempt to download PDF of a CrossRef paper.

    Args:
        paper_id: CrossRef DOI (e.g., '10.1038/nature12373').
        save_path: Directory to save the PDF (default: './downloads').
    Returns:
        str: Message indicating that direct PDF download is not supported.
        
    Note:
        CrossRef is a citation database and doesn't provide direct PDF downloads.
        Use the DOI to access the paper through the publisher's website.
    """
    try:
        return crossref_searcher.download_pdf(paper_id, save_path)
    except NotImplementedError as e:
        return str(e)


@mcp.tool()
async def read_crossref_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Attempt to read and extract text content from a CrossRef paper.

    Args:
        paper_id: CrossRef DOI (e.g., '10.1038/nature12373').
        save_path: Directory where the PDF is/will be saved (default: './downloads').
    Returns:
        str: Message indicating that direct paper reading is not supported.

    Note:
        CrossRef is a citation database and doesn't provide direct paper content.
        Use the DOI to access the paper through the publisher's website.
    """
    return crossref_searcher.read_paper(paper_id, save_path)


# ============================================================================
# OpenAlex Tools
# ============================================================================

@mcp.tool()
async def search_openalex(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    **kwargs
) -> List[Dict]:
    """Search academic papers from OpenAlex.

    OpenAlex is a free and open catalog of the global research system with
    over 200M works, comprehensive citation data, and author information.

    Args:
        query: Search query string (e.g., 'machine learning transformers').
        max_results: Maximum number of papers to return (default: 10, max: 200).
        year: Optional year filter (e.g., '2020', '2018-2022').
        **kwargs: Additional search parameters:
            - filter: OpenAlex filter (e.g., 'has_fulltext:true,type:journal-article')
            - sort: Sort field (e.g., 'cited_by_count:desc', 'publication_date:desc')
            - fields: Comma-separated list of fields to return

    Returns:
        List of paper metadata in dictionary format.

    Examples:
        # Basic search
        await search_openalex("deep learning", 20)

        # Search with year filter
        await search_openalex("quantum computing", 15, year="2020-2023")

        # Search with filters
        await search_openalex("climate change", 10, filter="has_fulltext:true")
    """
    search_kwargs = {}
    if year:
        search_kwargs['year'] = year
    if 'filter' in kwargs:
        search_kwargs['filter'] = kwargs['filter']
    if 'sort' in kwargs:
        search_kwargs['sort'] = kwargs['sort']

    papers = await async_search(openalex_searcher, query, max_results, **search_kwargs)
    return papers if papers else []


@mcp.tool()
async def get_openalex_paper(paper_id: str) -> Dict:
    """Get a specific paper from OpenAlex by its ID.

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890' or 'https://openalex.org/W3124567890')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_openalex_paper("W3108360596")
    """
    async with httpx.AsyncClient() as client:
        paper = openalex_searcher.get_paper_by_id(paper_id)
        return paper.to_dict() if paper else {}


@mcp.tool()
async def get_openalex_paper_by_doi(doi: str) -> Dict:
    """Get a specific paper from OpenAlex by its DOI.

    Args:
        doi: Digital Object Identifier (e.g., '10.1038/nature12373')

    Returns:
        Paper metadata in dictionary format, or empty dict if not found.

    Example:
        await get_openalex_paper_by_doi("10.1038/nature12373")
    """
    async with httpx.AsyncClient() as client:
        paper = openalex_searcher.get_paper_by_doi(doi)
        return paper.to_dict() if paper else {}


@mcp.tool()
async def get_openalex_citations(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers that cite this OpenAlex work (forward citations).

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of citing papers to return (default: 20)

    Returns:
        List of papers that cite the given paper.

    Example:
        await get_openalex_citations("W3108360596", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = openalex_searcher.get_citations(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_openalex_references(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers referenced by this OpenAlex work (backward citations).

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of referenced papers to return (default: 20)

    Returns:
        List of papers referenced by the given paper.

    Example:
        await get_openalex_references("W3108360596", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = openalex_searcher.get_references(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def search_openalex_by_author(
    author_name: str,
    max_results: int = 20,
    **kwargs
) -> List[Dict]:
    """Search for papers by a specific author in OpenAlex.

    Args:
        author_name: Name of the author (e.g., 'Geoffrey Hinton')
        max_results: Maximum number of papers to return (default: 20)
        **kwargs: Additional search parameters (year, filter, sort)

    Returns:
        List of papers by the author.

    Example:
        await search_openalex_by_author("Yann LeCun", 15)
    """
    async with httpx.AsyncClient() as client:
        papers = openalex_searcher.search_by_author(author_name, max_results, **kwargs)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def get_openalex_related(paper_id: str, max_results: int = 20) -> List[Dict]:
    """Get papers related to this OpenAlex work based on concepts and references.

    Args:
        paper_id: OpenAlex ID (e.g., 'W3124567890')
        max_results: Maximum number of related papers to return (default: 20)

    Returns:
        List of related papers.

    Example:
        await get_openalex_related("W3108360596", 10)
    """
    async with httpx.AsyncClient() as client:
        papers = openalex_searcher.get_related_papers(paper_id, max_results)
        return [paper.to_dict() for paper in papers] if papers else []


@mcp.tool()
async def download_openalex(paper_id: str, save_path: str = "./downloads") -> str:
    """Download PDF of an OpenAlex paper.

    Args:
        paper_id: OpenAlex paper ID (e.g., 'W3124567890')
        save_path: Directory to save the PDF (default: './downloads')

    Returns:
        Path to downloaded PDF or error message.

    Note:
        OpenAlex doesn't directly host PDFs. This attempts to find and download
        from available open access sources.
    """
    return openalex_searcher.download_pdf(paper_id, save_path)


@mcp.tool()
async def read_openalex_paper(paper_id: str, save_path: str = "./downloads") -> str:
    """Read and extract text content from an OpenAlex paper PDF.

    Args:
        paper_id: OpenAlex paper ID (e.g., 'W3124567890')
        save_path: Directory where the PDF is/will be saved (default: './downloads')

    Returns:
        The extracted text content of the paper.
    """
    try:
        return openalex_searcher.read_paper(paper_id, save_path)
    except Exception as e:
        print(f"Error reading paper {paper_id}: {e}")
        return ""


if __name__ == "__main__":
    mcp.run(transport="stdio")
