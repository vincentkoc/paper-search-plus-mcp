from __future__ import annotations

from datetime import datetime, timedelta
import os
from typing import List

from PyPDF2 import PdfReader
import requests

from ..paper import Paper


class PaperSource:
    def search(self, query: str, **kwargs) -> List[Paper]:
        raise NotImplementedError

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError

    def read_paper(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError


class BioRxivSearcher(PaperSource):
    """Official bioRxiv API adapter.

    bioRxiv does not support free-text search through its public endpoint. This
    adapter supports category/date-range retrieval and DOI lookup.
    """

    BASE_URL = "https://api.biorxiv.org/details/biorxiv"

    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def _build_url(self, query: str, search_mode: str, days: int) -> str:
        if search_mode == "doi":
            return f"{self.BASE_URL}/{query}/na/json"
        if search_mode != "category":
            raise ValueError("search_mode must be 'category' or 'doi'")

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        category = query.lower().replace(" ", "_")
        return f"{self.BASE_URL}/{start_date}/{end_date}/0/json?category={category}"

    def search(
        self,
        query: str,
        max_results: int = 10,
        days: int = 30,
        search_mode: str = "category",
    ) -> List[Paper]:
        response = self.session.get(
            self._build_url(query, search_mode, days),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        papers: List[Paper] = []
        for item in data.get("collection", [])[:max_results]:
            try:
                published = datetime.strptime(item["date"], "%Y-%m-%d")
                version = item.get("version", "1")
                doi = item["doi"]
                papers.append(
                    Paper(
                        paper_id=doi,
                        title=item["title"],
                        authors=item["authors"].split("; "),
                        abstract=item["abstract"],
                        url=f"https://www.biorxiv.org/content/{doi}v{version}",
                        pdf_url=f"https://www.biorxiv.org/content/{doi}v{version}.full.pdf",
                        published_date=published,
                        updated_date=published,
                        source="biorxiv",
                        categories=[item.get("category", "")] if item.get("category") else [],
                        keywords=[],
                        doi=doi,
                    )
                )
            except Exception as exc:
                print(f"Error parsing bioRxiv entry: {exc}")
        return papers

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        response = self.session.get(
            f"https://www.biorxiv.org/content/{paper_id}v1.full.pdf",
            timeout=self.timeout,
            headers={"User-Agent": "paper-search-plus-mcp/0.2.0"},
        )
        response.raise_for_status()
        os.makedirs(save_path, exist_ok=True)
        output_file = os.path.join(save_path, f"{paper_id.replace('/', '_')}.pdf")
        with open(output_file, "wb") as file:
            file.write(response.content)
        return output_file

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        pdf_path = os.path.join(save_path, f"{paper_id.replace('/', '_')}.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = self.download_pdf(paper_id, save_path)

        try:
            reader = PdfReader(pdf_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            print(f"Error reading PDF for paper {paper_id}: {exc}")
            return ""
