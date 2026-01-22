"""DBLP API integration for computer science bibliography.

DBLP indexes major computer science conference papers, journal articles, and book chapters.
API Documentation: https://dblp.org/faq/How+to+use+the+dblp+API.html
"""
from typing import List, Optional, Dict
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
import re
import logging
import urllib.parse

from ..paper import Paper

logger = logging.getLogger(__name__)


class DBLPSearcher:
    """Searcher for DBLP computer science bibliography.

    DBLP indexes:
    - Conference papers (major CS conferences)
    - Journal articles
    - Book chapters
    - PhD theses
    - Editorship
    """

    BASE_URL = "https://dblp.org"
    SEARCH_URL = f"{BASE_URL}/search/publ/api"
    BIB_URL = f"{BASE_URL}/bib"

    def __init__(self):
        """Initialize DBLP searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0',
            'Accept': 'application/xml, application/x-bibtex'
        })

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        venue_type: Optional[str] = None,  # conference, journal, book, thesis
        venue: Optional[str] = None,       # specific venue like "CVPR", "ICML"
        author: Optional[str] = None
    ) -> List[Paper]:
        """Search DBLP for publications.

        Args:
            query: Search query (title/keyword search)
            max_results: Maximum number of papers (max: 1000)
            year: Optional year filter
            venue_type: Filter by type - 'conference', 'journal', 'book', 'thesis'
            venue: Filter by venue/conference/journal name
            author: Filter by author name

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            # Build search query
            search_params = {
                "q": query,
                "h": min(max_results, 1000),
                "format": "xml"
            }

            # Add author filter
            if author:
                search_params["author"] = author

            # Add year filter
            if year:
                if "-" in year:
                    from_year, to_year = year.split("-")
                    search_params["yearMin"] = from_year.strip()
                    search_params["yearMax"] = to_year.strip()
                else:
                    search_params["yearMin"] = year.strip()
                    search_params["yearMax"] = year.strip()

            response = self.session.get(self.SEARCH_URL, params=search_params, timeout=30)

            if response.status_code == 204:
                logger.info(f"No DBLP results for query: {query}")
                return papers

            response.raise_for_status()

            papers = self._parse_xml(response.content, query)

            # Apply venue_type and venue filters
            if venue_type or venue:
                filtered = []
                for paper in papers:
                    if venue_type:
                        pub_type = paper.extra.get("type", "").lower()
                        if venue_type.lower() == "conference" and pub_type not in ["conference", "proceedings"]:
                            continue
                        elif venue_type.lower() == "journal" and pub_type != "journal":
                            continue
                        elif venue_type.lower() == "book" and pub_type != "book":
                            continue

                    if venue:
                        venue_lower = venue.lower()
                        paper_venue = paper.extra.get("venue", "").lower()
                        if venue_lower not in paper_venue and venue_lower not in paper.extra.get("venue_abbrev", "").lower():
                            continue

                    filtered.append(paper)
                papers = filtered[:max_results]

            logger.info(f"DBLP search: found {len(papers)} papers for '{query}'")

        except Exception as e:
            logger.error(f"DBLP search error: {e}")

        return papers[:max_results]

    def search_advanced(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        venue: Optional[str] = None,
        year: Optional[str] = None,
        max_results: int = 10
    ) -> List[Paper]:
        """Advanced search with specific fields.

        Args:
            title: Title keyword
            author: Author name
            venue: Venue/conference/journal
            year: Year or year range
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        query_parts = []
        if title:
            query_parts.append(title)
        if author:
            query_parts.append(f"author:{author}")
        if venue:
            query_parts.append(f"venue:{venue}")

        query = " ".join(query_parts) if query_parts else "*"
        return self.search(query, max_results, year)

    def get_paper_by_key(self, key: str) -> Optional[Paper]:
        """Get paper by DBLP key.

        Args:
            key: DBLP key (e.g., 'conf/icml/GuptaM20')

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.BASE_URL}/rec/papers/{key}.xml"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()

            papers = self._parse_xml(response.content, key)
            return papers[0] if papers else None

        except Exception as e:
            logger.error(f"Error fetching DBLP paper {key}: {e}")
            return None

    def search_by_author(
        self,
        author_name: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search for papers by author name.

        Args:
            author_name: Name of the author
            max_results: Maximum papers
            year: Optional year filter

        Returns:
            List of Paper objects
        """
        return self.search("", max_results, year, author=author_name)

    def get_author_publications(self, author_id: str) -> List[Paper]:
        """Get all publications for an author DBLP ID.

        Args:
            author_id: DBLP author ID (e.g., 'author/12345')

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            url = f"{self.BASE_URL}/pers/{author_id}.xml"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return papers
            response.raise_for_status()

            papers = self._parse_xml(response.content, author_id)

        except Exception as e:
            logger.error(f"Error fetching author publications for {author_id}: {e}")

        return papers

    def search_venue(self, venue_name: str, max_results: int = 50) -> List[Paper]:
        """Search publications from a specific venue.

        Args:
            venue_name: Venue name (e.g., "CVPR", "ICML", "NeurIPS")
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        return self.search(f"venue:{venue_name}", max_results)

    def get_venue_info(self, venue_key: str) -> Optional[Dict]:
        """Get information about a venue (conference/journal).

        Args:
            venue_key: Venue key (e.g., 'conf/cvpr', 'journals/tocs')

        Returns:
            Venue info dict or None
        """
        try:
            url = f"{self.BASE_URL}/{venue_key}.xml"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()

            root = ET.fromstring(response.content)

            info = {
                "key": venue_key,
                "name": "",
                "abbreviation": "",
                "type": "",
                "year": ""
            }

            name_elem = root.find(".//venue")
            if name_elem is not None:
                info["name"] = name_elem.get("name", "")
                info["abbreviation"] = name_elem.get("short", "")
                info["type"] = name_elem.get("type", "")

            return info

        except Exception as e:
            logger.error(f"Error fetching venue info for {venue_key}: {e}")
            return None

    def get_series(self, series_name: str, max_results: int = 50) -> List[Paper]:
        """Search publications in a book series (LNCS, etc.).

        Args:
            series_name: Series name (e.g., 'Lecture Notes in Computer Science')
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        return self.search(f"series:{series_name}", max_results)

    def get_top_conferences(self) -> List[Dict]:
        """Get list of major computer science conferences.

        Returns:
            List of conference info dicts
        """
        conferences = [
            {"key": "conf/aaai", "name": "AAAI Conference on Artificial Intelligence"},
            {"key": "conf/acl", "name": "ACL: Association for Computational Linguistics"},
            {"key": "conf/cav", "name": "CAV: Computer Aided Verification"},
            {"key": "conf/cvpr", "name": "CVPR: Computer Vision and Pattern Recognition"},
            {"key": "conf/icml", "name": "ICML: International Conference on Machine Learning"},
            {"key": "conf/icra", "name": "ICRA: International Conference on Robotics and Automation"},
            {"key": "conf/ijcai", "name": "IJCAI: International Joint Conference on AI"},
            {"key": "conf/interspeech", "name": "INTERSPEECH"},
            {"key": "conf/kdd", "name": "KDD: Knowledge Discovery and Data Mining"},
            {"key": "conf/mobicom", "name": "MobiCom: Mobile Computing and Networking"},
            {"key": "conf/neurips", "name": "NeurIPS: Neural Information Processing Systems"},
            {"key": "conf/osdi", "name": "OSDI: Operating Systems Design and Implementation"},
            {"key": "conf/pldi", "name": "PLDI: Programming Language Design and Implementation"},
            {"key": "conf/popl", "name": "POPL: Principles of Programming Languages"},
            {"key": "conf/rss", "name": "RSS: Robotics: Science and Systems"},
            {"key": "conf/siggraph", "name": "SIGGRAPH"},
            {"key": "conf/sigmod", "name": "SIGMOD: Management of Data"},
            {"key": "conf/sosp", "name": "SOSP: Operating Systems Principles"},
            {"key": "conf/uai", "name": "UAI: Uncertainty in AI"},
            {"key": "conf/usenix", "name": "USENIX Security Symposium"},
        ]
        return conferences

    def get_top_journals(self) -> List[Dict]:
        """Get list of major computer science journals.

        Returns:
            List of journal info dicts
        """
        journals = [
            {"key": "journals/ai", "name": "Artificial Intelligence"},
            {"key": "journals/cacm", "name": "Communications of the ACM"},
            {"key": "journals/cav", "name": "Formal Methods in System Design"},
            {"key": "journals/cog", "name": "Cognitive Science"},
            {"key": "journals/comcom", "name": "Computer Communications"},
            {"key": "journals/csc", "name": "Computer Science and Communications"},
            {"key": "journals/csi", "name": "Computing and Informatics"},
            {"key": "journals/dcc", "name": "Data & Knowledge Engineering"},
            {"key": "journals/dke", "name": "Discrete Mathematics & Theoretical Computer Science"},
            {"key": "journals/ejc", "name": "European Journal of Control"},
            {"key": "journals/entropy", "name": "Entropy"},
            {"key": "journals/esa", "name": "Embedded Systems and Applications"},
            {"key": "journals/fss", "name": "Future Generation Computer Systems"},
            {"key": "journals/iandc", "name": "Information and Computation"},
            {"key": "journals/iam", "name": "Intelligent Automation & Soft Computing"},
            {"key": "journals/ijgi", "name": "International Journal of Geographic Information"},
            {"key": "journals/infsof", "name": "Information and Software Technology"},
            {"key": "journals/ijcis", "name": "International Journal of Computer and Information"},
            {"key": "journals/ijhis", "name": "International Journal of High Integrity Systems"},
            {"key": "journals/ijprai", "name": "International Journal of Pattern Recognition"},
        ]
        return journals

    def download_bibtex(self, key: str) -> Optional[str]:
        """Download BibTeX entry for a paper.

        Args:
            key: DBLP key

        Returns:
            BibTeX string or None
        """
        try:
            url = f"{self.BASE_URL}/rec/papers/{key}.bib"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()

            return response.text

        except Exception as e:
            logger.error(f"Error fetching BibTeX for {key}: {e}")
            return None

    def _parse_xml(self, xml_content: bytes, query: str) -> List[Paper]:
        """Parse DBLP XML response into Paper objects."""
        papers = []

        try:
            root = ET.fromstring(xml_content)

            for hit in root.findall(".//hit"):
                try:
                    paper = self._parse_hit(hit)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing DBLP hit: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing DBLP XML: {e}")

        return papers

    def _parse_hit(self, hit: ET.Element) -> Optional[Paper]:
        """Parse a single DBLP hit element."""
        try:
            # Extract DBLP key
            key = hit.get("key", "")

            # Title
            title = ""
            title_elem = hit.find("title")
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()

            # Skip if no title
            if not title:
                return None

            # Authors
            authors = []
            for author in hit.findall("author"):
                if author.text:
                    authors.append(author.text.strip())

            # Year
            year = None
            year_elem = hit.find("year")
            if year_elem is not None and year_elem.text:
                try:
                    year = int(year_elem.text.strip())
                except:
                    pass

            # Publication type
            pub_type = hit.get("type", "article")

            # Venue
            venue = ""
            venue_elem = hit.find("journal")
            if venue_elem is not None and venue_elem.text:
                venue = venue_elem.text.strip()
                pub_type = "journal"

            venue_elem = hit.find("booktitle")
            if venue_elem is not None and venue_elem.text:
                venue = venue_elem.text.strip()
                pub_type = "conference"

            venue_elem = hit.find("school")
            if venue_elem is not None and venue_elem.text:
                venue = venue_elem.text.strip()
                pub_type = "thesis"

            # Volume, number, pages
            volume = hit.findtext("volume", "")
            number = hit.findtext("number", "")
            pages = hit.findtext("pages", "")

            # DOI
            doi = hit.findtext("ee", "")
            if doi and "doi.org" in doi:
                doi = doi.replace("https://doi.org/", "")

            # URL
            url = f"https://dblp.org/rec/{key}.html"

            # Abstract (DBLP doesn't have abstracts, but we can use the note if present)
            abstract = ""
            note_elem = hit.find("note")
            if note_elem is not None and note_elem.text:
                abstract = note_elem.text.strip()[:2000]

            # ISBN
            isbn = hit.findtext("isbn", "")

            # Publisher
            publisher = hit.findtext("publisher", "")

            published_date = datetime(year, 1, 1) if year else datetime.min

            return Paper(
                paper_id=key,
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                published_date=published_date,
                pdf_url="",  # DBLP doesn't host PDFs
                url=url,
                source="dblp",
                categories=[venue] if venue else [],
                keywords=[],
                citations=0,
                references=[],
                extra={
                    "dblp_key": key,
                    "type": pub_type,
                    "venue": venue,
                    "venue_abbrev": key.split("/")[1] if "/" in key else "",
                    "volume": volume,
                    "number": number,
                    "pages": pages,
                    "isbn": isbn,
                    "publisher": publisher
                }
            )

        except Exception as e:
            logger.error(f"Error parsing DBLP hit: {e}")
            return None


if __name__ == "__main__":
    # Test DBLP searcher
    searcher = DBLPSearcher()

    print("Testing DBLP search...")
    papers = searcher.search("transformer attention", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title[:80]}...")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print(f"   Venue: {paper.extra.get('venue', 'N/A')}")
        print()
