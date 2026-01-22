"""CORE API integration for accessing 200M+ academic papers.

CORE (COnnecting REpositories) aggregates open access research
papers from thousands of repositories worldwide.
API Documentation: https://api.core.ac.uk/docs
"""
from typing import List, Optional, Dict
from datetime import datetime
import requests
import os
from ..paper import Paper
from PyPDF2 import PdfReader
import logging
import time

logger = logging.getLogger(__name__)


class CoreSearcher:
    """Searcher for CORE academic paper repository.

    CORE provides access to over 200M open access papers from
    repositories worldwide including arXiv, PubMed Central, and more.
    """

    BASE_URL = "https://api.core.ac.uk/v5"
    # Free tier: 1000 requests per day
    DAILY_LIMIT = 1000

    def __init__(self, api_key: Optional[str] = None):
        """Initialize CORE searcher.

        Args:
            api_key: Optional CORE API key for higher limits
                    Get one at https://core.ac.uk/api-keys
        """
        self.api_key = api_key or os.environ.get("CORE_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0',
            'Accept': 'application/json'
        })
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        repository_id: Optional[int] = None,
        **kwargs
    ) -> List[Paper]:
        """Search for papers in CORE.

        Args:
            query: Search query string
            max_results: Maximum number of papers to return (default: 10, max: 100)
            year: Optional year filter (e.g., '2020' or '2018-2022')
            repository_id: Optional CORE repository ID to filter by
            **kwargs: Additional parameters (offset, orderBy, etc.)

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            # Build search URL
            url = f"{self.BASE_URL}/search"

            params = {
                "q": query,
                "limit": min(max_results, 100),
                "offset": kwargs.get("offset", 0)
            }

            # Add year filter
            if year:
                if "-" in year:
                    from_year, to_year = year.split("-")
                    params["fromDate"] = f"{from_year.strip()}-01-01"
                    params["toDate"] = f"{to_year.strip()}-12-31"
                else:
                    params["fromDate"] = f"{year.strip()}-01-01"
                    params["toDate"] = f"{year.strip()}-12-31"

            # Filter by repository
            if repository_id:
                params["repositoryId"] = repository_id

            # Add sorting
            if "sort" in kwargs:
                params["sort"] = kwargs["sort"]
            else:
                params["sort"] = "relevance"

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            total_count = data.get("totalCount", 0)

            logger.info(f"CORE search: found {total_count} results for '{query}'")

            for item in results:
                try:
                    paper = self._parse_result(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing CORE result: {e}")
                    continue

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning("CORE rate limit exceeded")
            else:
                logger.error(f"CORE API error: {e}")
        except Exception as e:
            logger.error(f"CORE search error: {e}")

        return papers

    def _parse_result(self, item: Dict) -> Optional[Paper]:
        """Parse a CORE search result into a Paper object.

        Args:
            item: CORE API result item

        Returns:
            Paper object or None
        """
        try:
            # Extract basic metadata
            paper_id = str(item.get("id", ""))

            title = item.get("title", "") or ""

            # Authors
            authors = []
            for author in item.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)

            # Abstract
            abstract = item.get("abstract", "") or ""

            # DOI
            doi = ""
            for identifier in item.get("identifiers", []):
                if identifier.get("type", "").lower() == "doi":
                    doi = identifier.get("id", "")
                    break

            # Publication date
            published_date = None
            published_date_str = item.get("publishedDate", "")
            if published_date_str:
                try:
                    # Try different date formats
                    for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
                        try:
                            published_date = datetime.strptime(published_date_str[:10], fmt)
                            break
                        except:
                            continue
                except:
                    pass

            # URL and PDF
            url = item.get("downloadUrl", "") or item.get("hostedUrl", "")
            pdf_url = ""

            # Prefer direct PDF links
            if url:
                if url.endswith(".pdf"):
                    pdf_url = url
                else:
                    # Check for PDF in links
                    for link in item.get("links", []):
                        if link.get("type", "").lower() == "pdf":
                            pdf_url = link.get("url", "")
                            break

            # Repository info
            repository = item.get("repository", {})
            source_name = repository.get("name", "CORE") if repository else "CORE"

            # Categories/subjects
            categories = []
            for topic in item.get("topics", []):
                name = topic.get("name", "")
                if name:
                    categories.append(name)

            # Keywords
            keywords = []
            for keyword in item.get("keywords", []):
                if keyword:
                    keywords.append(keyword)

            # Citation count (if available)
            citations = 0
            # CORE may have citation data in extra fields

            # References (if available)
            references = []

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract[:5000] if abstract else "",  # Limit abstract length
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url or f"https://core.ac.uk/reader/{paper_id}",
                source=f"core_{source_name.lower().replace(' ', '_')}",
                categories=categories[:10],  # Limit categories
                keywords=keywords[:10],
                citations=citations,
                references=references,
                extra={
                    "core_id": paper_id,
                    "source_repository": source_name,
                    "hosted_url": item.get("hostedUrl", ""),
                    "download_url": item.get("downloadUrl", ""),
                    "type": item.get("type", ""),
                    "language": item.get("language", ""),
                    "year": item.get("year", None)
                }
            )

        except Exception as e:
            logger.error(f"Error parsing CORE result: {e}")
            return None

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get a specific paper by its CORE ID.

        Args:
            paper_id: CORE paper ID

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.BASE_URL}/works/{paper_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._parse_result(data)
        except Exception as e:
            logger.error(f"Error fetching CORE paper {paper_id}: {e}")
            return None

    def search_by_doi(self, doi: str) -> Optional[Paper]:
        """Search for a paper by its DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("doi:", "").strip()

        # Search using DOI
        results = self.search(f'doi:{doi}', max_results=1)
        return results[0] if results else None

    def search_by_author(
        self,
        author_name: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search for papers by a specific author.

        Args:
            author_name: Name of the author
            max_results: Maximum number of papers
            year: Optional year filter

        Returns:
            List of Paper objects
        """
        return self.search(f'author:"{author_name}"', max_results, year)

    def get_repository(self, repository_id: int) -> Optional[Dict]:
        """Get information about a CORE repository.

        Args:
            repository_id: CORE repository ID

        Returns:
            Repository info dict or None
        """
        try:
            url = f"{self.BASE_URL}/repositories/{repository_id}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching repository {repository_id}: {e}")
            return None

    def search_repositories(
        self,
        query: str = "",
        max_results: int = 10
    ) -> List[Dict]:
        """Search CORE repositories.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of repository info dicts
        """
        try:
            url = f"{self.BASE_URL}/repositories"
            params = {
                "q": query,
                "limit": min(max_results, 100)
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error searching repositories: {e}")
            return []

    def download_pdf(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Download PDF from CORE.

        Args:
            paper_id: CORE paper ID
            save_path: Directory to save

        Returns:
            Path to downloaded PDF or error message
        """
        paper = self.get_paper_by_id(paper_id)
        if not paper or not paper.pdf_url:
            return f"Paper {paper_id} not found or no PDF available"

        try:
            import os
            os.makedirs(save_path, exist_ok=True)

            response = self.session.get(paper.pdf_url, timeout=60)
            response.raise_for_status()

            if response.headers.get("Content-Type", "").startswith("application/pdf"):
                filename = f"core_{paper_id}.pdf"
                file_path = os.path.join(save_path, filename)

                with open(file_path, 'wb') as f:
                    f.write(response.content)

                return file_path
            else:
                return f"URL does not point to a PDF: {paper.pdf_url}"

        except Exception as e:
            logger.error(f"Error downloading CORE PDF: {e}")
            return f"Failed to download PDF: {e}"

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read and extract text from a CORE paper PDF.

        Args:
            paper_id: CORE paper ID
            save_path: Directory for PDF storage

        Returns:
            Extracted text or empty string
        """
        pdf_path = self.download_pdf(paper_id, save_path)
        if pdf_path.startswith("Failed") or "not found" in pdf_path.lower():
            return ""

        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error reading CORE PDF: {e}")
            return ""


if __name__ == "__main__":
    # Test CORE searcher
    searcher = CoreSearcher()

    print("Testing CORE search...")
    papers = searcher.search("machine learning", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title[:80]}...")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print(f"   Source: {paper.source}")
        print()
