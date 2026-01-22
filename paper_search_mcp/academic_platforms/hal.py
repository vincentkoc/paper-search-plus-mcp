"""HAL API integration for French open archive of scientific documents.

HAL is a multi-disciplinary open archive for scientific documents.
API Documentation: https://api.archives-ouvertes.fr/docs
"""
from typing import List, Optional, Dict
from datetime import datetime
import requests
import logging
import os

from ..paper import Paper

logger = logging.getLogger(__name__)


class HALSearcher:
    """Searcher for HAL open archive.

    HAL provides access to scientific documents from French institutions.
    Coverage includes:
    - Theses and dissertations
    - Preprints
    - Conference papers
    - Journal articles
    - Book chapters
    - Reports
    """

    BASE_URL = "https://api.archives-ouvertes.fr"
    SEARCH_URL = f"{BASE_URL}/search"
    DOCUMENT_URL = f"{BASE_URL}/document"
    AUTHOR_URL = f"{BASE_URL}/author"

    def __init__(self):
        """Initialize HAL searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'paper-search-mcp/1.0',
            'Accept': 'application/json'
        })

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        doc_type: Optional[str] = None,  # thesis, preprint, article, communication, report, book
        collection: Optional[str] = None,  # CNRS, INRIA, HAL, etc.
        language: Optional[str] = None,    # en, fr, de, etc.
        domain: Optional[str] = None,      # e.g., "info:shs", "info:math", "physique"
        author_id: Optional[str] = None    # HAL author ID
    ) -> List[Paper]:
        """Search HAL for documents.

        Args:
            query: Search query string
            max_results: Maximum number of documents (max: 1000)
            year: Optional year filter
            doc_type: Document type filter
            collection: Collection filter (institution)
            language: Language filter
            domain: Research domain filter
            author_id: Filter by author HAL ID

        Returns:
            List of Paper objects
        """
        papers = []

        try:
            # Build search parameters
            params = {
                "q": query,
                "rows": min(max_results, 1000),
                "wt": "json"
            }

            # Add filters
            filters = []

            if year:
                if "-" in year:
                    filters.append(f"producedDate_s:[{year.split('-')[0].strip()} TO {year.split('-')[1].strip()}]")
                else:
                    filters.append(f"producedDate_s:{year.strip()}")

            if doc_type:
                doc_type_map = {
                    "thesis": "THESE",
                    "preprint": "PREPRINT",
                    "article": "ART",
                    "communication": "COMM",
                    "report": "REPORT",
                    "book": "OUV",
                    "chapter": "COUV"
                }
                doc_type_val = doc_type_map.get(doc_type.lower(), doc_type.upper())
                filters.append(f"docType_s:{doc_type_val}")

            if collection:
                filters.append(f"collCode_s:{collection}")

            if language:
                filters.append(f"language_s:{language}")

            if domain:
                filters.append(f"domain_s:{domain}")

            if author_id:
                filters.append(f"authorId_i:{author_id}")

            if filters:
                params["fq"] = " AND ".join(filters)

            response = self.session.get(self.SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            docs = data.get("response", {}).get("docs", [])

            for doc in docs:
                try:
                    paper = self._parse_doc(doc)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing HAL document: {e}")
                    continue

            logger.info(f"HAL search: found {len(papers)} results for '{query}'")

        except Exception as e:
            logger.error(f"HAL search error: {e}")

        return papers

    def search_advanced(
        self,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        author: Optional[str] = None,
        keyword: Optional[str] = None,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Advanced search with specific fields.

        Args:
            title: Title search
            abstract: Abstract search
            author: Author search
            keyword: Keyword search
            max_results: Maximum results
            year: Year filter

        Returns:
            List of Paper objects
        """
        query_parts = []

        if title:
            query_parts.append(f'title_s:"{title}"')
        if abstract:
            query_parts.append(f'abstract_s:"{abstract}"')
        if author:
            query_parts.append(f'authorName_s:"{author}"')
        if keyword:
            query_parts.append(f'keyword_s:"{keyword}"')

        query = " AND ".join(query_parts) if query_parts else "*"
        return self.search(query, max_results, year)

    def get_document_by_id(self, doc_id: str) -> Optional[Paper]:
        """Get a document by its HAL ID.

        Args:
            doc_id: HAL document ID

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.DOCUMENT_URL}/{doc_id}"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            if data.get("response", {}).get("numFound", 0) > 0:
                doc = data["response"]["docs"][0]
                return self._parse_doc(doc)

            return None

        except Exception as e:
            logger.error(f"Error fetching HAL document {doc_id}: {e}")
            return None

    def get_documents_by_author(
        self,
        author_id: str,
        max_results: int = 50
    ) -> List[Paper]:
        """Get all documents for an author.

        Args:
            author_id: HAL author ID
            max_results: Maximum results

        Returns:
            List of Paper objects
        """
        return self.search("", max_results, author_id=author_id)

    def search_by_doi(self, doi: str) -> Optional[Paper]:
        """Search for document by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        doi = doi.replace("https://doi.org/", "").replace("doi:", "").strip()

        results = self.search(f"doi_s:{doi}", max_results=1)
        return results[0] if results else None

    def search_by_author_name(
        self,
        author_name: str,
        max_results: int = 10,
        year: Optional[str] = None
    ) -> List[Paper]:
        """Search documents by author name.

        Args:
            author_name: Name of the author
            max_results: Maximum results
            year: Optional year filter

        Returns:
            List of Paper objects
        """
        return self.search(f'authorName_s:"{author_name}"', max_results, year)

    def search_theses(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        university: Optional[str] = None
    ) -> List[Paper]:
        """Search for theses and dissertations.

        Args:
            query: Search query
            max_results: Maximum results
            year: Year filter
            university: University name filter

        Returns:
            List of Paper objects
        """
        papers = self.search(query, max_results, year, doc_type="thesis")

        if university:
            filtered = []
            for paper in papers:
                inst = paper.extra.get("institution", "").lower()
                if university.lower() in inst:
                    filtered.append(paper)
            papers = filtered

        return papers

    def search_preprints(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        domain: Optional[str] = None
    ) -> List[Paper]:
        """Search for preprints.

        Args:
            query: Search query
            max_results: Maximum results
            year: Year filter
            domain: Research domain

        Returns:
            List of Paper objects
        """
        return self.search(query, max_results, year, doc_type="preprint", domain=domain)

    def get_collections(self) -> List[Dict]:
        """Get list of available collections.

        Returns:
            List of collection info dicts
        """
        collections = [
            {"code": "CNRS", "name": "Centre National de la Recherche Scientifique"},
            {"code": "INRIA", "name": "Institut National de Recherche en Informatique"},
            {"code": "INSMI", "name": "Institut National des Sciences Mathématiques"},
            {"code": "INP", "name": "Institut Polytechnique de Paris"},
            {"code": "UNIV-PARIS", "name": "Université Paris"),
            {"code": "UNIV-LYON", "name": "Université de Lyon"},
            {"code": "UNIV-RENNES", "name": "Université de Rennes"},
            {"code": "UNIV-STRAS", "name": "Université de Strasbourg"},
            {"code": "UNIV-TOULOUSE", "name": "Université de Toulouse"},
            {"code": "UNIV-BORDEAUX", "name": "Université de Bordeaux"},
        ]
        return collections

    def get_domains(self) -> Dict[str, str]:
        """Get list of research domains.

        Returns:
            Dict of domain codes to names
        """
        return {
            "info:math": "Mathematics",
            "info:info": "Computer Science",
            "info:shs": "Humanities and Social Sciences",
            "info:phys": "Physics",
            "info:chim": "Chemistry",
            "info:bio": "Biology",
            "info:sde": "Earth Sciences",
            "info:sdu": "Space Sciences",
            "info:stat": "Statistics",
            "info:eng": "Engineering"
        }

    def get_author(self, author_id: str) -> Optional[Dict]:
        """Get author information by HAL ID.

        Args:
            author_id: HAL author ID

        Returns:
            Author info dict or None
        """
        try:
            url = f"{self.AUTHOR_URL}/{author_id}"
            response = self.session.get(url, timeout=30)

            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

            if data.get("response", {}).get("numFound", 0) > 0:
                return data["response"]["docs"][0]

            return None

        except Exception as e:
            logger.error(f"Error fetching HAL author {author_id}: {e}")
            return None

    def download_file(self, doc_id: str, save_path: str = "./downloads") -> str:
        """Download a file from HAL.

        Args:
            doc_id: HAL document ID
            save_path: Directory to save

        Returns:
            Path to downloaded file or error message
        """
        try:
            os.makedirs(save_path, exist_ok=True)

            # Get document info to find file URL
            doc = self.get_document_by_id(doc_id)
            if not doc:
                return f"Document {doc_id} not found"

            file_url = doc.extra.get("fileUrl", "")
            if not file_url:
                return f"No file available for {doc_id}"

            response = self.session.get(file_url, timeout=60)
            response.raise_for_status()

            # Determine filename
            filename = doc.extra.get("filename", f"hal_{doc_id}.pdf")
            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            return file_path

        except Exception as e:
            logger.error(f"Error downloading HAL file: {e}")
            return f"Failed to download file: {e}"

    def read_paper(self, doc_id: str, save_path: str = "./downloads") -> str:
        """Get abstract text for a document.

        Args:
            doc_id: HAL document ID

        Returns:
            Abstract text or empty string
        """
        doc = self.get_document_by_id(doc_id)
        if doc:
            return doc.abstract
        return ""

    def _parse_doc(self, doc: Dict) -> Optional[Paper]:
        """Parse HAL document into Paper object."""
        try:
            # Extract ID
            doc_id = str(doc.get("docId", doc.get("halId_s", "")))

            # Title
            title = ""
            if doc.get("title_s"):
                if isinstance(doc["title_s"], list):
                    # Prefer English title if available
                    title = doc["title_s"][0]
                    for t in doc["title_s"]:
                        if t.lower().startswith("a ") or t.lower().startswith("the "):
                            title = t
                            break
                else:
                    title = doc["title_s"]

            if not title:
                return None

            # Authors
            authors = []

            # Try different author fields
            for field in ["authorName_s", "author_s"]:
                if doc.get(field):
                    if isinstance(doc[field], list):
                        authors.extend(doc[field])
                    else:
                        authors.append(doc[field])

            # Authors from structured field
            if doc.get("authors_s"):
                for author in doc["authors_s"]:
                    if isinstance(author, str) and author not in authors:
                        authors.append(author)

            # Abstract
            abstract = ""
            if doc.get("abstract_s"):
                if isinstance(doc["abstract_s"], list):
                    abstract = doc["abstract_s"][0]
                else:
                    abstract = doc["abstract_s"]

            # DOI
            doi = ""
            if doc.get("doi_s"):
                doi = doc["doi_s"]
            elif doc.get("doiId_s"):
                doi = doc["doiId_s"]

            # URL
            url = doc.get("url_s", "") or f"https://hal.science/{doc_id}"

            # PDF URL
            pdf_url = ""
            if doc.get("fileUrl_s"):
                pdf_url = doc["fileUrl_s"]

            # Publication date
            published_date = None
            date_str = doc.get("producedDate_s", "")
            if date_str:
                try:
                    published_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except:
                    try:
                        published_date = datetime.strptime(date_str[:4], "%Y")
                    except:
                        pass

            # Document type
            doc_type = doc.get("docType_s", "").lower()
            type_map = {
                "these": "thesis",
                "preprint": "preprint",
                "art": "article",
                "comm": "communication",
                "report": "report",
                "ouv": "book",
                "couv": "chapter"
            }
            paper_type = type_map.get(doc_type, doc_type)

            # Journal/Venue
            journal = doc.get("journalTitle_s", "")
            if not journal:
                journal = doc.get("bookTitle_s", "")

            # Conference
            conference = doc.get("conference_s", "")

            # Institution (for theses)
            institution = doc.get("institution_s", doc.get("institutionName_s", ""))

            # Keywords
            keywords = []
            if doc.get("keyword_s"):
                keywords = doc["keyword_s"] if isinstance(doc["keyword_s"], list) else [doc["keyword_s"]]

            # Language
            language = doc.get("language_s", "")

            # Collection
            collection = doc.get("collCode_s", "")

            # Domain
            domain = doc.get("domain_s", "")

            # Pagination
            pages = ""
            if doc.get("page_s"):
                pages = doc["page_s"]

            return Paper(
                paper_id=doc_id,
                title=title,
                authors=authors,
                abstract=abstract[:5000] if abstract else "",
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source="hal",
                categories=[domain] if domain else [],
                keywords=keywords[:10],
                citations=0,
                references=[],
                extra={
                    "hal_id": doc_id,
                    "type": paper_type,
                    "journal": journal,
                    "conference": conference,
                    "institution": institution,
                    "language": language,
                    "collection": collection,
                    "domain": domain,
                    "pages": pages,
                    "fileUrl": doc.get("fileUrl_s", ""),
                    "filename": doc.get("filename_s", "")
                }
            )

        except Exception as e:
            logger.error(f"Error parsing HAL document: {e}")
            return None


if __name__ == "__main__":
    # Test HAL searcher
    searcher = HALSearcher()

    print("Testing HAL search...")
    papers = searcher.search("deep learning", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title[:80]}...")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print(f"   URL: {paper.url}")
        print()
