"""SSRN API integration for preprints and early-stage research.

SSRN is a repository specializing in preprints from social sciences, law, business, and humanities.
Note: SSRN doesn't have a public API, so we use web scraping with proper rate limiting.
"""
from typing import List, Optional, Dict
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import os
import logging
import time

from ..paper import Paper

logger = logging.getLogger(__name__)


class SSFNSearcher:
    """Searcher for SSRN preprints and early research.

    SSRN covers:
    - Economics and finance
    - Law and legal studies
    - Business (management, marketing, accounting)
    - Social sciences
    - Humanities
    - Computer science
    """

    BASE_URL = "https://papers.ssrn.com"
    SOLR_URL = "https://api.ssrn.com"
    ABSTRACT_URL = f"{BASE_URL}/abstract"
    DOWNLOAD_URL = f"{BASE_URL}/cgi-bin/works"

    def __init__(self):
        """Initialize SSRN searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; paper-search-mcp/1.0)',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9'
        })
        self.last_request_time = 0

    def _rate_limit(self, delay: float = 1.0):
        """Apply rate limiting to avoid being blocked."""
        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        topic: Optional[str] = None,  # Economics, Finance, Law, Business, etc.
        author_id: Optional[str] = None
    ) -> List[Paper]:
        """Search SSRN for papers.

        Args:
            query: Search query string
            max_results: Maximum number of papers (max: 100)
            year: Optional year filter
            topic: Topic/category filter
            author_id: Filter by author SSRN ID

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            self._rate_limit()

            # Build search URL
            params = {
                "query": query,
                "pg": 1
            }

            if author_id:
                params["authorId"] = author_id

            response = self.session.get(f"{self.ABSTRACT_URL}/search.cfm", params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"SSRN search failed with status {response.status_code}")
                return papers

            soup = BeautifulSoup(response.content, 'lxml')

            # Parse results
            results = self._parse_search_results(soup, query)

            # Apply filters
            if year or topic:
                filtered = []
                for paper in results:
                    # Year filter
                    if year:
                        paper_year = paper.published_date.year if paper.published_date else 0
                        if "-" in year:
                            parts = year.split("-")
                            if paper_year < int(parts[0].strip()) or paper_year > int(parts[1].strip()):
                                continue
                        elif paper_year != int(year):
                            continue

                    # Topic filter
                    if topic:
                        paper_categories = [c.lower() for c in paper.categories]
                        if topic.lower() not in paper_categories:
                            continue

                    filtered.append(paper)
                results = filtered

            papers = results[:max_results]
            logger.info(f"SSRN search: found {len(papers)} papers for '{query}'")

        except Exception as e:
            logger.error(f"SSRN search error: {e}")

        return papers

    def search_by_doi(self, doi: str) -> Optional[Paper]:
        """Search for paper by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        # SSRN doesn't directly support DOI search via API
        # Try searching by DOI string
        clean_doi = doi.replace("https://doi.org/", "").replace("doi:", "").strip()
        results = self.search(clean_doi, max_results=1)

        for paper in results:
            if clean_doi.lower() in paper.doi.lower():
                return paper

        return None

    def search_by_author(
        self,
        author_name: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search for papers by author.

        Args:
            author_name: Name of the author
            max_results: Maximum results
            year: Optional year filter

        Returns:
            List of Paper objects
        """
        return self.search(f'author:"{author_name}"', max_results, year)

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """Get a specific paper by its SSRN ID.

        Args:
            paper_id: SSRN paper ID

        Returns:
            Paper object or None
        """
        try:
            self._rate_limit()

            url = f"{self.ABSTRACT_URL}/{paper_id}.html"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()

            return self._parse_paper_page(response.content, paper_id)

        except Exception as e:
            logger.error(f"Error fetching SSRN paper {paper_id}: {e}")
            return None

    def get_author_by_id(self, author_id: str) -> Optional[Dict]:
        """Get author information by SSRN ID.

        Args:
            author_id: SSRN author ID

        Returns:
            Author info dict or None
        """
        try:
            self._rate_limit()

            url = f"{self.BASE_URL}/sol3/Authors.cfm?action=search&txt_Query={author_id}"
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'lxml')

            # Parse author info
            author_info = {"author_id": author_id}

            name_elem = soup.find("div", {"class": "author-name"})
            if name_elem:
                author_info["name"] = name_elem.get_text(strip=True)

            return author_info

        except Exception as e:
            logger.error(f"Error fetching SSRN author {author_id}: {e}")
            return None

    def get_author_papers(self, author_id: str, max_results: int = 50) -> List[Paper]:
        """Get all papers by an author.

        Args:
            author_id: SSRN author ID
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        return self.search("", max_results, author_id=author_id)

    def get_top_papers(
        self,
        topic: Optional[str] = None,
        timeframe: str = "month",  # week, month, year, all
        max_results: int = 10
    ) -> List[Paper]:
        """Get top papers by downloads or recent activity.

        Args:
            topic: Topic filter
            timeframe: Time period
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        try:
            self._rate_limit()

            url = f"{self.ABSTRACT_URL}/topPapers.cfm"

            params = {}
            if topic:
                params["topic"] = topic
            if timeframe:
                params["time"] = timeframe

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, 'lxml')

            return self._parse_search_results(soup, "top papers")

        except Exception as e:
            logger.error(f"Error fetching top papers: {e}")
            return []

    def get_new_papers(
        self,
        topic: Optional[str] = None,
        max_results: int = 10
    ) -> List[Paper]:
        """Get newest papers on SSRN.

        Args:
            topic: Topic filter
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        try:
            self._rate_limit()

            url = f"{self.ABSTRACT_URL}/newPapers.cfm"

            params = {}
            if topic:
                params["topic"] = topic

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.content, 'lxml')

            return self._parse_search_results(soup, "new papers")

        except Exception as e:
            logger.error(f"Error fetching new papers: {e}")
            return []

    def download_pdf(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Download PDF from SSRN.

        Args:
            paper_id: SSRN paper ID
            save_path: Directory to save

        Returns:
            Path to PDF or error message
        """
        try:
            os.makedirs(save_path, exist_ok=True)

            self._rate_limit()

            # Get download link
            paper = self.get_paper_by_id(paper_id)
            if not paper:
                return f"Paper {paper_id} not found"

            # SSRN typically requires login for downloads
            # We'll try the direct download link
            download_url = f"{self.DOWNLOAD_URL}?download=yes&paper_id={paper_id}"

            response = self.session.get(download_url, timeout=60)

            if response.status_code != 200:
                return f"PDF download not available for {paper_id}"

            content_type = response.headers.get("Content-Type", "")

            if "pdf" in content_type.lower() or len(response.content) > 1000:
                filename = f"ssrn_{paper_id}.pdf"
                file_path = os.path.join(save_path, filename)

                with open(file_path, 'wb') as f:
                    f.write(response.content)

                return file_path

            return f"PDF not available for {paper_id}"

        except Exception as e:
            logger.error(f"Error downloading SSRN PDF: {e}")
            return f"Failed to download PDF: {e}"

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read abstract and metadata from a paper.

        Args:
            paper_id: SSRN paper ID

        Returns:
            Abstract text or empty string
        """
        paper = self.get_paper_by_id(paper_id)
        if paper:
            return paper.abstract
        return ""

    def _parse_search_results(self, soup: BeautifulSoup, query: str) -> List[Paper]:
        """Parse search results page into Paper objects."""
        papers = []

        # Find all paper entries
        for entry in soup.find_all("div", {"class": "paper-card"}):
            try:
                paper = self._parse_paper_entry(entry)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"Error parsing SSRN paper entry: {e}")
                continue

        # Alternative parsing for table format
        if not papers:
            for row in soup.find_all("tr", {"class": "data"}):
                try:
                    paper = self._parse_paper_row(row)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing SSRN paper row: {e}")
                    continue

        return papers

    def _parse_paper_entry(self, entry) -> Optional[Paper]:
        """Parse a paper card entry."""
        try:
            # Find paper ID and title link
            link = entry.find("a", {"class": "title"})
            if not link:
                return None

            href = link.get("href", "")
            match = re.search(r"abstract[=/](\d+)", href)
            if not match:
                match = re.search(r"/(\d+)\.html", href)

            paper_id = match.group(1) if match else ""

            title = link.get_text(strip=True)
            if not title:
                return None

            # Authors
            authors = []
            author_elem = entry.find("span", {"class": "authors"})
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                authors = [a.strip() for a in author_text.split(",") if a.strip()]

            # Abstract
            abstract = ""
            abstract_elem = entry.find("div", {"class": "abstract"})
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)

            # Date
            published_date = None
            date_elem = entry.find("span", {"class": "date"})
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    published_date = datetime.strptime(date_text, "%B %d, %Y")
                except:
                    try:
                        published_date = datetime.strptime(date_text, "%B %Y")
                    except:
                        pass

            # URL
            url = f"{self.ABSTRACT_URL}/{paper_id}.html"

            # Categories/Topics
            categories = []
            for topic in entry.find_all("a", {"class": "topic"}):
                topic_text = topic.get_text(strip=True)
                if topic_text:
                    categories.append(topic_text)

            # PDF URL (if available)
            pdf_url = ""
            pdf_link = entry.find("a", {"class": "download"})
            if pdf_link:
                pdf_href = pdf_link.get("href", "")
                if "download" in pdf_href.lower():
                    pdf_url = pdf_href

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract[:3000] if abstract else "",
                doi="",  # SSRN doesn't use DOIs
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source="ssrn",
                categories=categories[:5],
                keywords=[],
                citations=0,
                references=[],
                extra={
                    "ssrn_id": paper_id,
                    "topics": categories,
                    "download_url": pdf_url
                }
            )

        except Exception as e:
            logger.error(f"Error parsing SSRN entry: {e}")
            return None

    def _parse_paper_row(self, row) -> Optional[Paper]:
        """Parse a paper table row."""
        try:
            # Find title link
            link = row.find("a", href=re.compile(r"abstract|rec=\d+"))
            if not link:
                return None

            href = link.get("href", "")
            match = re.search(r"(?:abstract)?[=/](\d+)", href)
            paper_id = match.group(1) if match else ""

            title = link.get_text(strip=True)
            if not title:
                return None

            # Authors
            cells = row.find_all("td")
            authors = []
            if len(cells) > 1:
                author_text = cells[1].get_text(strip=True)
                authors = [a.strip() for a in author_text.split(",") if a.strip()]

            # Date
            published_date = datetime.min
            if len(cells) > 2:
                date_text = cells[2].get_text(strip=True)
                try:
                    published_date = datetime.strptime(date_text, "%m/%d/%Y")
                except:
                    try:
                        published_date = datetime.strptime(date_text, "%Y-%m-%d")
                    except:
                        pass

            url = f"{self.ABSTRACT_URL}/{paper_id}.html"

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract="",
                doi="",
                published_date=published_date,
                pdf_url="",
                url=url,
                source="ssrn",
                categories=[],
                keywords=[],
                citations=0,
                references=[],
                extra={"ssrn_id": paper_id}
            )

        except Exception as e:
            logger.error(f"Error parsing SSRN row: {e}")
            return None

    def _parse_paper_page(self, content: bytes, paper_id: str) -> Optional[Paper]:
        """Parse a paper detail page."""
        try:
            soup = BeautifulSoup(content, 'lxml')

            # Title
            title = ""
            title_elem = soup.find("h1", {"class": "title"})
            if not title_elem:
                title_elem = soup.find("meta", {"property": "og:title"})
            if title_elem:
                if hasattr(title_elem, 'get_text'):
                    title = title_elem.get_text(strip=True)
                else:
                    title = title_elem.get("content", "")

            if not title:
                return None

            # Authors
            authors = []
            author_section = soup.find("div", {"class": "authors"})
            if author_section:
                for link in author_section.find_all("a"):
                    name = link.get_text(strip=True)
                    if name:
                        authors.append(name)

            # Abstract
            abstract = ""
            abstract_elem = soup.find("div", {"class": "abstract"})
            if abstract_elem:
                abstract = abstract_elem.get_text(strip=True)

            # Date
            published_date = datetime.min
            date_elem = soup.find("div", {"class": "date"})
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    published_date = datetime.strptime(date_text, "%B %d, %Y")
                except:
                    try:
                        published_date = datetime.strptime(date_text, "%B %Y")
                    except:
                        pass

            # Keywords
            keywords = []
            keywords_elem = soup.find("div", {"class": "keywords"})
            if keywords_elem:
                keyword_text = keywords_elem.get_text(strip=True)
                keywords = [k.strip() for k in keyword_text.split(",")]

            # Categories
            categories = []
            for topic in soup.find_all("a", {"class": "topic"}):
                topic_text = topic.get_text(strip=True)
                if topic_text:
                    categories.append(topic_text)

            # URL
            url = f"{self.ABSTRACT_URL}/{paper_id}.html"

            # PDF URL
            pdf_url = ""
            pdf_link = soup.find("a", {"class": "download"})
            if pdf_link:
                pdf_url = pdf_link.get("href", "")

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract[:3000] if abstract else "",
                doi="",
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source="ssrn",
                categories=categories[:5],
                keywords=keywords[:10],
                citations=0,
                references=[],
                extra={
                    "ssrn_id": paper_id,
                    "topics": categories,
                    "download_url": pdf_url
                }
            )

        except Exception as e:
            logger.error(f"Error parsing SSRN page: {e}")
            return None


if __name__ == "__main__":
    # Test SSRN searcher
    searcher = SSFNSearcher()

    print("Testing SSRN search...")
    papers = searcher.search("blockchain", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title[:80]}...")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print(f"   URL: {paper.url}")
        print()
