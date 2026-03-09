from __future__ import annotations

from datetime import datetime
import os
from typing import List

import feedparser
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


class ArxivSearcher(PaperSource):
    """Official arXiv API adapter."""

    BASE_URL = "http://export.arxiv.org/api/query"
    SORT_BY_VALUES = {"relevance", "lastUpdatedDate", "submittedDate"}
    SORT_ORDER_VALUES = {"ascending", "descending"}
    SEARCH_FIELDS = {
        "all",
        "ti",
        "au",
        "abs",
        "co",
        "jr",
        "cat",
        "rn",
        "id",
    }

    def _build_query(self, query: str, search_field: str) -> str:
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")
        if ":" in query:
            return query
        if search_field not in self.SEARCH_FIELDS:
            raise ValueError(f"Unsupported search_field: {search_field}")
        return query if search_field == "all" else f"{search_field}:{query}"

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: str = "relevance",
        sort_order: str = "descending",
        search_field: str = "all",
    ) -> List[Paper]:
        if sort_by not in self.SORT_BY_VALUES:
            raise ValueError(f"Unsupported sort_by: {sort_by}")
        if sort_order not in self.SORT_ORDER_VALUES:
            raise ValueError(f"Unsupported sort_order: {sort_order}")

        params = {
            "search_query": self._build_query(query, search_field),
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        response = requests.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        papers: List[Paper] = []
        for entry in feed.entries:
            try:
                papers.append(
                    Paper(
                        paper_id=entry.id.split("/")[-1],
                        title=entry.title.strip(),
                        authors=[author.name for author in entry.authors],
                        abstract=entry.summary.strip(),
                        url=entry.id,
                        pdf_url=next(
                            (
                                link.href
                                for link in entry.links
                                if getattr(link, "type", "") == "application/pdf"
                            ),
                            "",
                        ),
                        published_date=datetime.strptime(
                            entry.published, "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        updated_date=datetime.strptime(
                            entry.updated, "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        source="arxiv",
                        categories=[tag.term for tag in getattr(entry, "tags", [])],
                        keywords=[],
                        doi=entry.get("doi", ""),
                    )
                )
            except Exception as exc:
                print(f"Error parsing arXiv entry: {exc}")
        return papers

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        response = requests.get(f"https://arxiv.org/pdf/{paper_id}.pdf", timeout=30)
        response.raise_for_status()
        os.makedirs(save_path, exist_ok=True)
        output_file = os.path.join(save_path, f"{paper_id}.pdf")
        with open(output_file, "wb") as file:
            file.write(response.content)
        return output_file

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        pdf_path = os.path.join(save_path, f"{paper_id}.pdf")
        if not os.path.exists(pdf_path):
            pdf_path = self.download_pdf(paper_id, save_path)

        try:
            reader = PdfReader(pdf_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            print(f"Error reading PDF for paper {paper_id}: {exc}")
            return ""
