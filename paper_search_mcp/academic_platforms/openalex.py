"""OpenAlex API integration for comprehensive academic paper search.

OpenAlex is a free and open catalog of the global research system.
It indexes over 200M works, 90M authors, and provides comprehensive citation data.
API Documentation: https://docs.openalex.org/
"""
from typing import List, Optional
from datetime import datetime
import time
import requests
from ..paper import Paper
from PyPDF2 import PdfReader
import os


class OpenAlexSearcher:
    """Searcher for OpenAlex academic database.

    OpenAlex provides access to hundreds of millions of works across all disciplines,
    with comprehensive citation data, author information, and concept mappings.
    """

    BASE_URL = "https://api.openalex.org"
    EMAIL_PARAM = "mailto:paper-search-mcp@example.com"  # Polite identification

    def __init__(self, email: Optional[str] = None):
        """Initialize OpenAlex searcher.

        Args:
            email: Optional email for API identification (helps with rate limiting)
        """
        if email:
            self.EMAIL_PARAM = f"mailto:{email}"

    def search(
        self,
        query: str,
        max_results: int = 10,
        year: Optional[str] = None,
        **kwargs
    ) -> List[Paper]:
        """Search for papers in OpenAlex.

        Args:
            query: Search query string (supports Boolean operators, filters)
            max_results: Maximum number of papers to return (default: 10, max: 200 per page)
            year: Optional year filter (e.g., '2020', '2018-2022')
            **kwargs: Additional search parameters:
                - filter: OpenAlex filter string (e.g., 'has_fulltext:true,type:journal-article')
                - sort: Sort field (e.g., 'cited_by_count:desc', 'publication_date:desc')
                - fields: Comma-separated list of fields to return

        Returns:
            List of Paper objects

        Examples:
            searcher.search("machine learning", 20)
            searcher.search("quantum computing", year="2020-2023")
            searcher.search("climate change", filter="has_fulltext:true,from_publication_date:2020")
        """
        papers = []
        per_page = min(max_results, 200)  # OpenAlex max is 200

        # Build API URL
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": per_page,
            "mailto": self.EMAIL_PARAM
        }

        # Add year filter if provided
        if year:
            if "-" in year:
                # Year range
                params["filter"] = f"from_publication_date:{year}"
            else:
                # Single year
                params["filter"] = f"publication_year:{year}"

        # Add additional filters from kwargs
        if "filter" in kwargs:
            existing_filter = params.get("filter", "")
            params["filter"] = f"{existing_filter},{kwargs['filter']}" if existing_filter else kwargs["filter"]

        # Add sort parameter
        if "sort" in kwargs:
            params["sort"] = kwargs["sort"]

        # Add fields parameter (for optimization)
        if "fields" in kwargs:
            params["fields"] = kwargs["fields"]

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "results" not in data:
                return papers

            for work in data["results"]:
                try:
                    paper = self._parse_work(work)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    print(f"Error parsing OpenAlex work: {e}")
                    continue

        except Exception as e:
            print(f"Error searching OpenAlex: {e}")

        return papers

    def get_paper_by_id(self, openalex_id: str) -> Optional[Paper]:
        """Get a specific paper by its OpenAlex ID.

        Args:
            openalex_id: OpenAlex ID (e.g., 'W3124567890' or 'https://openalex.org/W3124567890')

        Returns:
            Paper object or None if not found
        """
        # Clean ID to just the numeric part if it's a URL
        if openalex_id.startswith("http"):
            openalex_id = openalex_id.split("/")[-1]

        url = f"{self.BASE_URL}/works/{openalex_id}"
        params = {"mailto": self.EMAIL_PARAM}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._parse_work(data)
        except Exception as e:
            print(f"Error fetching paper {openalex_id}: {e}")
            return None

    def get_paper_by_doi(self, doi: str) -> Optional[Paper]:
        """Get a specific paper by its DOI.

        Args:
            doi: Digital Object Identifier (e.g., '10.1038/nature12373')

        Returns:
            Paper object or None if not found
        """
        # URL encode the DOI
        from urllib.parse import quote
        encoded_doi = quote(doi, safe='')

        url = f"{self.BASE_URL}/works/doi:{encoded_doi}"
        params = {"mailto": self.EMAIL_PARAM}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._parse_work(data)
        except Exception as e:
            print(f"Error fetching paper with DOI {doi}: {e}")
            return None

    def get_citations(self, openalex_id: str, max_results: int = 20) -> List[Paper]:
        """Get papers that cite this work (forward citations).

        Args:
            openalex_id: OpenAlex ID
            max_results: Maximum number of citing papers to return

        Returns:
            List of Paper objects that cite the given paper
        """
        if openalex_id.startswith("http"):
            openalex_id = openalex_id.split("/")[-1]

        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"cites:{openalex_id}",
            "per-page": max_results,
            "sort": "publication_date:desc",
            "mailto": self.EMAIL_PARAM
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                paper = self._parse_work(work)
                if paper:
                    papers.append(paper)
            return papers
        except Exception as e:
            print(f"Error fetching citations: {e}")
            return []

    def get_references(self, openalex_id: str, max_results: int = 20) -> List[Paper]:
        """Get papers referenced by this work (backward citations).

        Args:
            openalex_id: OpenAlex ID
            max_results: Maximum number of referenced papers to return

        Returns:
            List of Paper objects referenced by the given paper
        """
        if openalex_id.startswith("http"):
            openalex_id = openalex_id.split("/")[-1]

        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"referenced_by:{openalex_id}",
            "per-page": max_results,
            "mailto": self.EMAIL_PARAM
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                paper = self._parse_work(work)
                if paper:
                    papers.append(paper)
            return papers
        except Exception as e:
            print(f"Error fetching references: {e}")
            return []

    def search_by_author(
        self,
        author_name: str,
        max_results: int = 20,
        **kwargs
    ) -> List[Paper]:
        """Search for papers by a specific author.

        Args:
            author_name: Name of the author (e.g., 'Geoffrey Hinton')
            max_results: Maximum number of papers to return
            **kwargs: Additional search parameters (year, filter, sort, fields)

        Returns:
            List of Paper objects by the author
        """
        # First, find the author
        author_url = f"{self.BASE_URL}/authors"
        author_params = {
            "search": author_name,
            "per-page": 1,
            "mailto": self.EMAIL_PARAM
        }

        try:
            response = requests.get(author_url, params=author_params, timeout=30)
            response.raise_for_status()
            author_data = response.json()

            if not author_data.get("results"):
                return []

            author_id = author_data["results"][0]["id"].split("/")[-1]

            # Now get papers by this author
            url = f"{self.BASE_URL}/works"
            params = {
                "filter": f"author.id:{author_id}",
                "per-page": max_results,
                "sort": "publication_date:desc",
                "mailto": self.EMAIL_PARAM
            }

            # Add additional filters
            if "year" in kwargs:
                params["filter"] += f",publication_year:{kwargs['year']}"

            if "filter" in kwargs:
                params["filter"] += f",{kwargs['filter']}"

            if "sort" in kwargs:
                params["sort"] = kwargs["sort"]

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                paper = self._parse_work(work)
                if paper:
                    papers.append(paper)
            return papers

        except Exception as e:
            print(f"Error searching by author: {e}")
            return []

    def get_related_papers(self, openalex_id: str, max_results: int = 20) -> List[Paper]:
        """Get papers related to this work based on shared concepts and references.

        Args:
            openalex_id: OpenAlex ID
            max_results: Maximum number of related papers to return

        Returns:
            List of related Paper objects
        """
        if openalex_id.startswith("http"):
            openalex_id = openalex_id.split("/")[-1]

        url = f"{self.BASE_URL}/works"
        params = {
            "filter": f"has_concepts:{openalex_id}",
            "per-page": max_results,
            "sort": "cited_by_count:desc",
            "mailto": self.EMAIL_PARAM
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            papers = []
            for work in data.get("results", []):
                paper = self._parse_work(work)
                if paper and paper.paper_id != openalex_id:
                    papers.append(paper)
            return papers
        except Exception as e:
            print(f"Error fetching related papers: {e}")
            return []

    def _parse_work(self, work: dict) -> Optional[Paper]:
        """Parse OpenAlex work data into a Paper object.

        Args:
            work: Work data from OpenAlex API

        Returns:
            Paper object or None if parsing fails
        """
        try:
            # Basic metadata
            paper_id = work.get("id", "").split("/")[-1]
            title = work.get("title", "")

            # Authors
            authors = []
            authorships = work.get("authorships", [])
            for authorship in authorships:
                author_name = authorship.get("author", {}).get("display_name", "")
                if author_name:
                    authors.append(author_name)

            # Publication date
            pub_date = work.get("publication_date")
            published_date = None
            if pub_date:
                try:
                    published_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except:
                    pass

            # DOI and URL
            doi = work.get("doi", "")
            url = work.get("id", "")
            if url.startswith("http"):
                url = url.replace("api.openalex.org", "openalex.org")

            # PDF URL - check locations
            pdf_url = ""
            locations = work.get("locations", [])
            for location in locations:
                source = location.get("source", {})
                if source.get("type") == "repository" or source.get("type") == "journal":
                    pdf_url = location.get("landing_page_url", "") or location.get("pdf_url", "")
                    if pdf_url:
                        break

            # If no PDF in locations, check best location
            if not pdf_url and work.get("best_oa_location"):
                best_loc = work["best_oa_location"]
                pdf_url = best_loc.get("pdf_url", "") or best_loc.get("landing_page_url", "")

            # Abstract
            abstract = work.get("abstract_inverted_index")
            abstract_text = ""
            if abstract:
                # Reconstruct abstract from inverted index
                try:
                    index_to_word = {}
                    for word, positions in abstract.items():
                        for pos in positions:
                            index_to_word[pos] = word

                    # Sort by position and join
                    sorted_indices = sorted(index_to_word.keys())
                    abstract_text = " ".join([index_to_word[i] for i in sorted_indices])
                except:
                    abstract_text = ""

            # Keywords/Concepts
            keywords = []
            concepts = work.get("concepts", [])
            for concept in concepts[:10]:  # Top 10 concepts
                concept_name = concept.get("display_name", "")
                if concept_name:
                    keywords.append(concept_name)

            # Categories (from concepts with high score)
            categories = []
            for concept in concepts[:5]:
                if concept.get("score", 0) > 0.5:
                    categories.append(concept.get("display_name", ""))

            # Citation count
            citations = work.get("cited_by_count", 0)

            # References
            references = []
            ref_list = work.get("referenced_works", [])
            for ref in ref_list[:50]:  # Limit to first 50
                if ref:
                    references.append(ref.split("/")[-1] if "/" in ref else ref)

            # Type
            work_type = work.get("type", "")
            source = f"openalex_{work_type}" if work_type else "openalex"

            return Paper(
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract_text,
                doi=doi,
                published_date=published_date or datetime.min,
                pdf_url=pdf_url,
                url=url,
                source=source,
                categories=categories,
                keywords=keywords,
                citations=citations,
                references=references,
                extra={
                    "openalex_id": paper_id,
                    "work_type": work_type,
                    "concepts": concepts[:10],
                    "has_fulltext": work.get("has_fulltext", False),
                    "open_access": work.get("open_access", {})
                }
            )

        except Exception as e:
            print(f"Error parsing work: {e}")
            return None

    def download_pdf(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Download PDF of an OpenAlex paper.

        Args:
            paper_id: OpenAlex paper ID
            save_path: Directory to save the PDF

        Returns:
            Path to downloaded PDF or error message

        Note:
            OpenAlex doesn't directly host PDFs. This attempts to find and download
            from available open access sources.
        """
        # Get paper details to find PDF URL
        paper = self.get_paper_by_id(paper_id)
        if not paper:
            return f"Paper {paper_id} not found"

        pdf_url = paper.pdf_url
        if not pdf_url:
            # Try to get PDF from best_oa_location
            return "No PDF URL available for this paper"

        try:
            os.makedirs(save_path, exist_ok=True)
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            filename = f"{paper_id.replace('/', '_')}.pdf"
            file_path = os.path.join(save_path, filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            return file_path
        except Exception as e:
            return f"Failed to download PDF: {e}"

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        """Read and extract text from an OpenAlex paper PDF.

        Args:
            paper_id: OpenAlex paper ID
            save_path: Directory for PDF storage

        Returns:
            Extracted text content or empty string on failure
        """
        pdf_path = self.download_pdf(paper_id, save_path)

        if pdf_path.startswith("Failed") or pdf_path.startswith("No PDF"):
            return ""

        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""


if __name__ == "__main__":
    # Test OpenAlex searcher
    searcher = OpenAlexSearcher()

    print("Testing OpenAlex search...")
    papers = searcher.search("machine learning transformers", 5)
    print(f"Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"{i}. {paper.title}")
        print(f"   Citations: {paper.citations}")
        print(f"   Authors: {', '.join(paper.authors[:3])}")
        print()
