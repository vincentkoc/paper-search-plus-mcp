"""PubMed Central (PMC) API integration for full-text biomedical papers.

PMC is a free full-text archive of biomedical and life sciences journal literature
at the U.S. National Institutes of Health's National Library of Medicine (NIH/NLM).
API Documentation: https://www.ncbi.nlm.nih.gov/pmc/tools/oai/
"""
from typing import List, Optional
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from ..paper import Paper
from PyPDF2 import PdfReader
import os
import logging
import re

logger = logging.getLogger(__name__)


class PMCSearcher:
    """Searcher for PubMed Central (PMC) full-text biomedical papers.

    PMC provides free access to full-text biomedical and life sciences literature.
    Unlike PubMed (which only has abstracts), PMC often has complete articles.
    """

    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
    EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PMCID_PREFIX = "PMC"

    def __init__(self):
        """Initialize PMC searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; paper-search-mcp/1.0)'
        })

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search for papers in PubMed Central.

        Note: PMC uses OAI-PMH protocol which has limited search capabilities.
        For advanced search, consider using ESearch API with pmc filter.

        Args:
            query: Search query string
            max_results: Maximum number of papers to return
            year: Optional year filter (e.g., '2020' or '2018-2022')

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            # Use ESearch API for better search functionality
            search_url = f"{self.EUTILS_BASE}/esearch.fcgi"
            params = {
                "db": "pmc",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "tool": "paper_search_mcp",
                "email": "paper-search-mcp@example.com"
            }

            # Add year filter if provided
            if year:
                if "-" in year:
                    # Year range
                    params["datetype"] = "pubmed"
                    params["reldate"] = year
                else:
                    # Single year
                    params["datetype"] = "pubmed"
                    params["mindate"] = f"{year}/01/01"
                    params["maxdate"] = f"{year}/12/31"

            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            pmcids = data.get("esearchresult", {}).get("idlist", [])

            if not pmcids:
                logger.info(f"No PMC papers found for query: {query}")
                return papers

            # Fetch details for each paper
            for pmcid in pmcids[:max_results]:
                try:
                    paper = self.get_paper_by_pmcid(pmcid)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error fetching paper {pmcid}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error searching PMC: {e}")

        return papers

    def get_paper_by_pmcid(self, pmcid: str) -> Optional[Paper]:
        """Get a specific paper by its PMCID.

        Args:
            pmcid: PubMed Central ID (e.g., 'PMC1234567' or just '1234567')

        Returns:
            Paper object or None if not found
        """
        # Clean PMCID
        pmcid = pmcid.replace("PMC", "").strip()

        try:
            # Use EFetch API to get paper details
            fetch_url = f"{self.EUTILS_BASE}/efetch.fcgi"
            params = {
                "db": "pmc",
                "id": pmcid,
                "retmode": "xml",
                "tool": "paper_search_mcp",
                "email": "paper-search-mcp@example.com"
            }

            response = self.session.get(fetch_url, params=params, timeout=30)
            response.raise_for_status()

            return self._parse_pmc_xml(response.content, pmcid)

        except Exception as e:
            logger.error(f"Error fetching paper {pmcid}: {e}")
            return None

    def _parse_pmc_xml(self, xml_content: bytes, pmcid: str) -> Optional[Paper]:
        """Parse PMC XML response into a Paper object.

        Args:
            xml_content: XML content from PMC API
            pmcid: PMCID for this paper

        Returns:
            Paper object or None if parsing fails
        """
        try:
            root = ET.fromstring(xml_content)

            # Namespace handling
            namespaces = {
                'mml': 'http://www.w3.org/1998/Math/MathML',
                'xlink': 'http://www.w3.org/1999/xlink',
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
            }

            # Extract title
            title = ""
            title_elem = root.find(".//article-title")
            if title_elem is not None:
                title = "".join(title_elem.itertext()).strip()

            # Extract abstract
            abstract = ""
            abstract_elem = root.find(".//abstract")
            if abstract_elem is not None:
                abstract = "".join(abstract_elem.itertext()).strip()

            # Extract authors
            authors = []
            for contrib in root.findall(".//contrib"):
                if contrib.get("contrib-type") == "author":
                    name_elem = contrib.find(".//name")
                    if name_elem is not None:
                        given = name_elem.findtext("given-names", "")
                        surname = name_elem.findtext("surname", "")
                        if given and surname:
                            authors.append(f"{given} {surname}")
                        elif surname:
                            authors.append(surname)

            # Extract publication date
            published_date = None
            pub_date_elem = root.find(".//pub-date")
            if pub_date_elem is not None:
                year = pub_date_elem.findtext("year")
                month = pub_date_elem.findtext("month")
                day = pub_date_elem.findtext("day")
                if year:
                    try:
                        month_int = int(month) if month and month.isdigit() else 1
                        day_int = int(day) if day and day.isdigit() else 1
                        published_date = datetime(int(year), month_int, day_int)
                    except:
                        published_date = datetime(int(year), 1, 1)

            # Extract DOI
            doi = ""
            for doi_elem in root.findall(".//article-id[@pub-id-type='doi']"):
                if doi_elem is not None and doi_elem.text:
                    doi = doi_elem.text.strip()
                    break

            # Extract journal/title info
            journal = ""
            journal_elem = root.find(".//journal-title")
            if journal_elem is not None and journal_elem.text:
                journal = journal_elem.text.strip()

            # Build URLs
            full_pmcid = f"{self.PMCID_PREFIX}{pmcid}"
            url = f"https://www.ncbi.nlm.nih.gov/pmc/{full_pmcid}"
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{full_pmcid}/pdf/"

            return Paper(
                paper_id=full_pmcid,
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source="pmc",
                categories=[journal] if journal else [],
                keywords=[],
                citations=0,
                references=[],
                extra={
                    "pmcid": full_pmcid,
                    "journal": journal
                }
            )

        except Exception as e:
            logger.error(f"Error parsing PMC XML: {e}")
            return None

    def download_pdf(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Download PDF of a PMC paper.

        Args:
            paper_id: PMC ID (e.g., 'PMC1234567' or '1234567')
            save_path: Directory to save the PDF

        Returns:
            Path to downloaded PDF or error message
        """
        # Clean PMCID
        pmcid = paper_id.replace("PMC", "").strip()
        full_pmcid = f"{self.PMCID_PREFIX}{pmcid}"

        try:
            os.makedirs(save_path, exist_ok=True)
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{full_pmcid}/pdf/"

            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()

            filename = f"{full_pmcid}.pdf"
            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            return file_path

        except Exception as e:
            logger.error(f"Error downloading PDF for {paper_id}: {e}")
            return f"Failed to download PDF: {e}"

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read and extract text from a PMC paper PDF.

        Args:
            paper_id: PMC ID (e.g., 'PMC1234567' or '1234567')
            save_path: Directory for PDF storage

        Returns:
            Extracted text content or empty string on failure
        """
        pdf_path = self.download_pdf(paper_id, save_path)

        if pdf_path.startswith("Failed"):
            return ""

        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return ""

    def get_full_text_xml(self, paper_id: str) -> Optional[str]:
        """Get the full text XML of a PMC paper.

        Args:
            paper_id: PMC ID (e.g., 'PMC1234567' or '1234567')

        Returns:
            XML content as string or None if not found
        """
        # Clean PMCID
        pmcid = paper_id.replace("PMC", "").strip()

        try:
            fetch_url = f"{self.EUTILS_BASE}/efetch.fcgi"
            params = {
                "db": "pmc",
                "id": pmcid,
                "retmode": "xml",
                "tool": "paper_search_mcp",
                "email": "paper-search-mcp@example.com"
            }

            response = self.session.get(fetch_url, params=params, timeout=30)
            response.raise_for_status()

            return response.text.decode('utf-8')

        except Exception as e:
            logger.error(f"Error fetching full text XML for {paper_id}: {e}")
            return None


if __name__ == "__main__":
    # Test PMC searcher
    searcher = PMCSearcher()

    print("Testing PMC search...")
    papers = searcher.search("cancer immunotherapy", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title}")
        print(f"   PMCID: {paper.paper_id}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print()
