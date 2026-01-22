"""Europe PMC API integration for biomedical and life sciences literature.

Europe PMC indexes PubMed articles, PMC full-text, and preprints.
API Documentation: https://www.ebi.ac.uk/europepmc/webservices/rest/search
"""
from typing import List, Optional, Dict
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
import os
import logging
import re

from ..paper import Paper

logger = logging.getLogger(__name__)


class EuropePMCSearcher:
    """Searcher for Europe PMC - comprehensive life sciences literature.

    Europe PMC provides access to:
    - PubMed abstracts (27M+)
    - PMC full-text articles
    - Preprints from bioRxiv, medRxiv, etc.
    - Patents and grants
    """

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"
    SEARCH_URL = f"{BASE_URL}/search"
    FULLTEXT_URL = f"{BASE_URL}/fullTextSearch"
    DETAILS_URL = f"{BASE_URL}/{{article_id}}/fullTextXML"

    def __init__(self):
        """Initialize Europe PMC searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0',
            'Accept': 'application/json, application/xml'
        })

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        result_type: str = "all",  # all, pubmed, pmc, preprints
        sort_by: str = "relevance"
    ) -> List[Paper]:
        """Search Europe PMC for papers.

        Args:
            query: Search query (supports EPMC query syntax)
            max_results: Maximum number of papers (max 1000)
            year: Optional year filter (e.g., '2020' or '2018-2022')
            result_type: Filter by type - 'all', 'pubmed', 'pmc', 'preprints'
            sort_by: Sort by - 'relevance', 'date', 'cited'

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            params = {
                "query": query,
                "resultType": result_type,
                "format": "json",
                "pageSize": min(max_results, 1000),
                "formatType": "json",
                "sort": sort_by,
                "expand": "authors,languages"
            }

            # Add year filter
            if year:
                if "-" in year:
                    params["fromDate"] = year.split("-")[0].strip()
                    params["toDate"] = year.split("-")[1].strip()
                else:
                    params["fromDate"] = year
                    params["toDate"] = year

            # Pagination
            cursor_mark = "*"
            collected = 0

            while collected < max_results:
                params["cursorMark"] = cursor_mark
                response = self.session.get(self.SEARCH_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                results = data.get("result", {}).get("hits", [])
                if not results:
                    break

                total_count = data.get("hitCount", 0)
                logger.info(f"EuropePMC search: found {total_count} results for '{query}'")

                for item in results:
                    if collected >= max_results:
                        break
                    try:
                        paper = self._parse_result(item)
                        if paper:
                            papers.append(paper)
                            collected += 1
                    except Exception as e:
                        logger.warning(f"Error parsing EuropePMC result: {e}")
                        continue

                # Check for more pages
                next_cursor = data.get("nextCursorMark", "")
                if next_cursor and next_cursor != cursor_mark:
                    cursor_mark = next_cursor
                else:
                    break

        except Exception as e:
            logger.error(f"EuropePMC search error: {e}")

        return papers

    def search_advanced(
        self,
        query: str,
        max_results: int = 10,
        sections: List[str] = None,  # title, abstract, fullText
        topics: List[str] = None,    # disease, genes, organisms, drugs
        open_access: bool = True
    ) -> List[Paper]:
        """Advanced search with specific sections and topics.

        Args:
            query: Search query
            max_results: Maximum results
            sections: Which sections to search - ['title', 'abstract', 'fullText']
            topics: Filter by topics - ['disease', 'genes', 'organisms', 'drugs', etc.]
            open_access: Only open access results

        Returns:
            List of Paper objects
        """
        papers = []
        sections = sections or ["title", "abstract"]

        # Build advanced query
        advanced_query = query
        if open_access:
            advanced_query += " AND open_access:true"
        if topics:
            for topic in topics:
                advanced_query += f" AND topic:{topic}"

        try:
            params = {
                "query": advanced_query,
                "resultType": "fullText" if "fullText" in sections else "all",
                "format": "json",
                "pageSize": min(max_results, 1000),
                "formatType": "json"
            }

            response = self.session.get(self.FULLTEXT_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("result", {}).get("hits", [])

            for item in results:
                try:
                    paper = self._parse_result(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing EuropePMC result: {e}")
                    continue

        except Exception as e:
            logger.error(f"EuropePMC advanced search error: {e}")

        return papers

    def get_paper_by_id(self, article_id: str) -> Optional[Paper]:
        """Get paper by Europe PMC article ID.

        Args:
            article_id: Europe PMC article ID (e.g., 'PMC1234567' or internal ID)

        Returns:
            Paper object or None
        """
        try:
            # Try as PMC ID first
            if article_id.startswith("PMC"):
                url = f"{self.BASE_URL}/PMC/{article_id.replace('PMC', '')}/fullTextXML"
            else:
                url = f"{self.BASE_URL}/{article_id}/fullTextXML"

            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            response.raise_for_status()

            return self._parse_xml(response.content, article_id)

        except Exception as e:
            logger.error(f"Error fetching EuropePMC paper {article_id}: {e}")
            return None

    def search_by_pubmed_id(self, pubmed_id: str) -> Optional[Paper]:
        """Get paper by PubMed ID.

        Args:
            pubmed_id: PubMed ID

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.BASE_URL}/MED/{pubmed_id}/fullTextXML"
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            response.raise_for_status()

            return self._parse_xml(response.content, f"MED{pubmed_id}")

        except Exception as e:
            logger.error(f"Error fetching PubMed paper {pubmed_id}: {e}")
            return None

    def search_preprints(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        server: Optional[str] = None  # biorxiv, medrxiv, chemrxiv
    ) -> List[Paper]:
        """Search for preprints.

        Args:
            query: Search query
            max_results: Maximum results
            year: Optional year filter
            server: Specific preprint server

        Returns:
            List of Paper objects
        """
        # Build preprint query
        preprint_query = "type:preprint"
        if server:
            preprint_query += f" AND server:{server}"
        preprint_query += f" AND ({query})"

        return self.search(preprint_query, max_results, year, result_type="preprints")

    def get_citations(self, article_id: str, max_results: int = 50) -> List[Paper]:
        """Get papers that cite this paper.

        Args:
            article_id: Europe PMC or PubMed ID
            max_results: Maximum citations

        Returns:
            List of citing Paper objects
        """
        papers = []

        try:
            # Get ID type
            if article_id.startswith("PMC"):
                id_type = "PMCID"
                search_id = article_id.replace("PMC", "")
            elif article_id.isdigit():
                id_type = "MED"
                search_id = article_id
            else:
                id_type = "DOI"
                search_id = article_id

            params = {
                "query": f"has_reference:{search_id} AND {id_type}:{search_id}",
                "resultType": "all",
                "format": "json",
                "pageSize": min(max_results, 1000),
                "formatType": "json"
            }

            response = self.session.get(self.SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("result", {}).get("hits", [])

            for item in results:
                try:
                    paper = self._parse_result(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing citation: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching citations for {article_id}: {e}")

        return papers

    def get_related_articles(
        self,
        article_id: str,
        max_results: int = 10
    ) -> List[Paper]:
        """Get related articles based on content similarity.

        Args:
            article_id: Europe PMC or PubMed ID
            max_results: Maximum results

        Returns:
            List of related Paper objects
        """
        papers = []

        try:
            if article_id.startswith("PMC"):
                url = f"{self.BASE_URL}/PMC{article_id.replace('PMC', '')}/similar"
            else:
                url = f"{self.BASE_URL}/{article_id}/similar"

            params = {
                "format": "json",
                "pageSize": min(max_results, 100)
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("result", {}).get("hits", [])

            for item in results:
                try:
                    paper = self._parse_result(item)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing related article: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching related articles for {article_id}: {e}")

        return papers

    def search_by_author(
        self,
        author_name: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search for papers by author name.

        Args:
            author_name: Author name (supports various formats)
            max_results: Maximum results
            year: Optional year filter

        Returns:
            List of Paper objects
        """
        # Europe PMC uses different author field names
        search_query = f"author:{author_name}"
        return self.search(search_query, max_results, year)

    def search_by_doi(self, doi: str) -> Optional[Paper]:
        """Search for paper by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        doi = doi.replace("https://doi.org/", "").replace("doi:", "").strip()

        results = self.search(f"doi:{doi}", max_results=1)
        return results[0] if results else None

    def get_grants(self, article_id: str) -> List[Dict]:
        """Get funding/grant information for a paper.

        Args:
            article_id: Europe PMC or PubMed ID

        Returns:
            List of grant information dicts
        """
        grants = []

        try:
            if article_id.startswith("PMC"):
                url = f"{self.BASE_URL}/PMC{article_id.replace('PMC', '')}/grants"
            else:
                url = f"{self.BASE_URL}/{article_id}/grants"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            grants = data.get("grant", [])
        except Exception as e:
            logger.error(f"Error fetching grants for {article_id}: {e}")

        return grants

    def download_pdf(self, article_id: str, save_path: str = "./downloads") -> str:
        """Download PDF for PMC article.

        Args:
            article_id: PMC ID
            save_path: Directory to save

        Returns:
            Path to PDF or error message
        """
        try:
            os.makedirs(save_path, exist_ok=True)

            if article_id.startswith("PMC"):
                pmc_id = article_id.replace("PMC", "")
            else:
                pmc_id = article_id

            pdf_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{pmc_id}/fullTextPDF"

            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()

            if response.headers.get("Content-Type", "").startswith("application/pdf"):
                filename = f"europepmc_{article_id}.pdf"
                file_path = os.path.join(save_path, filename)

                with open(file_path, 'wb') as f:
                    f.write(response.content)

                return file_path
            else:
                return f"PDF not available for {article_id}"

        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return f"Failed to download PDF: {e}"

    def read_paper(self, article_id: str, save_path: str = "./downloads") -> str:
        """Read and extract text from a paper's full-text XML.

        Args:
            article_id: Europe PMC or PMC ID
            save_path: Directory for downloads

        Returns:
            Extracted text content or empty string
        """
        try:
            # Get full text XML
            if article_id.startswith("PMC"):
                url = f"{self.BASE_URL}/{article_id}/fullTextXML"
            else:
                url = f"{self.BASE_URL}/{article_id}/fullTextXML"

            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return ""
            response.raise_for_status()

            return self._extract_text_from_xml(response.content)

        except Exception as e:
            logger.error(f"Error reading paper {article_id}: {e}")
            return ""

    def _parse_result(self, item: Dict) -> Optional[Paper]:
        """Parse Europe PMC JSON result into Paper object."""
        try:
            # Extract ID
            pmcid = item.get("pmcid", "") or ""
            pubmed_id = item.get("pubmedId", "") or ""
            doi = item.get("doi", "") or ""

            if pmcid and not pmcid.startswith("PMC"):
                pmcid = f"PMC{pmcid}"

            paper_id = pmcid or pubmed_id or doi or item.get("id", "")

            # Title
            title = item.get("title", "") or ""

            # Authors
            authors = []
            for author in item.get("authors", []):
                full_name = author.get("fullName", "") or author.get("name", "")
                if full_name:
                    authors.append(full_name)

            # Abstract
            abstract = item.get("abstract", "") or ""

            # Journal
            journal = item.get("journalTitle", "") or item.get("journal", "") or ""

            # Publication date
            published_date = None
            pub_date = item.get("publicationDate", "") or item.get("publishedDate", "")
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        published_date = datetime.strptime(pub_date[:10], "%Y-%m-%d")
                    else:
                        year = pub_date.get("year", 1)
                        month = pub_date.get("month", 1)
                        day = pub_date.get("day", 1)
                        published_date = datetime(year, month, day)
                except:
                    pass

            # URL
            if pmcid:
                url = f"https://europepmc.org/article/PMC/{pmcid.replace('PMC', '')}"
            elif pubmed_id:
                url = f"https://europepmc.org/abstract/MED/{pubmed_id}"
            elif doi:
                url = f"https://doi.org/{doi}"
            else:
                url = f"https://europepmc.org/article/MED/{paper_id}"

            # PDF URL (only for PMC articles)
            pdf_url = ""
            if pmcid:
                pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"

            # Categories/subjects
            categories = []
            for keyword in item.get("meshTerms", []):
                term = keyword.get("term", "")
                if term:
                    categories.append(term)

            # Keywords
            keywords = item.get("keywords", [])

            # Source type
            source_type = item.get("type", "article").lower()
            source = "europepmc"
            if source_type == "preprint":
                source = "europepmc_preprint"
            elif source_type == "patent":
                source = "europepmc_patent"

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract[:5000] if abstract else "",
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source=source,
                categories=categories[:10],
                keywords=keywords[:10],
                citations=item.get("citedByCount", 0),
                references=[],
                extra={
                    "europepmc_id": paper_id,
                    "pmcid": pmcid,
                    "pubmed_id": pubmed_id,
                    "journal": journal,
                    "article_type": source_type,
                    "open_access": item.get("openAccess", False)
                }
            )

        except Exception as e:
            logger.error(f"Error parsing EuropePMC result: {e}")
            return None

    def _parse_xml(self, xml_content: bytes, article_id: str) -> Optional[Paper]:
        """Parse Europe PMC XML into Paper object."""
        try:
            root = ET.fromstring(xml_content)

            # Title
            title = ""
            title_elem = root.find(".//article-title")
            if title_elem is not None:
                title = "".join(title_elem.itertext()).strip()

            # Abstract
            abstract = ""
            abstract_elem = root.find(".//abstract")
            if abstract_elem is not None:
                abstract = "".join(abstract_elem.itertext()).strip()

            # Authors
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

            # DOI
            doi = ""
            doi_elem = root.find(".//article-id[@pub-id-type='doi']")
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text.strip()

            # Journal
            journal = ""
            journal_elem = root.find(".//journal-title")
            if journal_elem is not None and journal_elem.text:
                journal = journal_elem.text.strip()

            # Publication date
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

            # Build URLs
            url = f"https://europepmc.org/article/MED/{article_id}" if article_id.startswith("MED") else \
                  f"https://europepmc.org/article/PMC/{article_id.replace('PMC', '')}"

            pdf_url = ""
            if article_id.startswith("PMC"):
                pdf_url = f"https://europepmc.org/articles/{article_id}?pdf=render"

            return Paper(
                paper_id=article_id,
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source="europepmc",
                categories=[],
                keywords=[],
                citations=0,
                references=[],
                extra={
                    "europepmc_id": article_id,
                    "journal": journal
                }
            )

        except Exception as e:
            logger.error(f"Error parsing EuropePMC XML: {e}")
            return None

    def _extract_text_from_xml(self, xml_content: bytes) -> str:
        """Extract plain text from full-text XML."""
        try:
            root = ET.fromstring(xml_content)
            text_parts = []

            for elem in root.iter():
                if elem.tag in ["p", "sec-title", "title"]:
                    text = "".join(elem.itertext()).strip()
                    if text:
                        text_parts.append(text)

            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extracting text from XML: {e}")
            return ""


if __name__ == "__main__":
    # Test Europe PMC searcher
    searcher = EuropePMCSearcher()

    print("Testing Europe PMC search...")
    papers = searcher.search("CRISPR gene editing", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title[:80]}...")
        print(f"   DOI: {paper.doi}")
        print(f"   Source: {paper.source}")
        print()
