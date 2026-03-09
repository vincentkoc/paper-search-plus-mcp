from __future__ import annotations

from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET

import requests

from ..paper import Paper


class PaperSource:
    def search(self, query: str, **kwargs) -> List[Paper]:
        raise NotImplementedError

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError

    def read_paper(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError


class PubMedSearcher(PaperSource):
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    SORT_VALUES = {"relevance", "pub date", "first author", "journal"}

    def _extract_abstract(self, article: ET.Element) -> str:
        parts = []
        for node in article.findall(".//AbstractText"):
            label = node.attrib.get("Label")
            text = "".join(node.itertext()).strip()
            if not text:
                continue
            parts.append(f"{label}: {text}" if label else text)
        return "\n".join(parts)

    def _extract_authors(self, article: ET.Element) -> List[str]:
        authors: List[str] = []
        for author in article.findall(".//Author"):
            last_name = author.findtext("LastName", default="").strip()
            initials = author.findtext("Initials", default="").strip()
            collective = author.findtext("CollectiveName", default="").strip()
            if last_name or initials:
                authors.append(" ".join(part for part in [last_name, initials] if part))
            elif collective:
                authors.append(collective)
        return authors

    def _extract_published_date(self, article: ET.Element) -> datetime | None:
        year = article.findtext(".//PubDate/Year")
        month = article.findtext(".//PubDate/Month", default="1")
        day = article.findtext(".//PubDate/Day", default="1")
        if not year:
            return None
        month_lookup = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        try:
            month_value = int(month)
        except ValueError:
            month_value = month_lookup.get(month[:3], 1)
        try:
            return datetime(int(year), month_value, int(day))
        except ValueError:
            return datetime(int(year), month_value, 1)

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
    ) -> List[Paper]:
        if sort not in self.SORT_VALUES:
            raise ValueError(f"Unsupported sort: {sort}")

        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "xml",
            "sort": sort,
        }
        search_response = requests.get(self.SEARCH_URL, params=search_params, timeout=30)
        search_response.raise_for_status()
        search_root = ET.fromstring(search_response.content)
        ids = [node.text for node in search_root.findall(".//Id") if node.text]
        if not ids:
            return []

        fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        fetch_response = requests.get(self.FETCH_URL, params=fetch_params, timeout=30)
        fetch_response.raise_for_status()
        fetch_root = ET.fromstring(fetch_response.content)

        papers: List[Paper] = []
        for article in fetch_root.findall(".//PubmedArticle"):
            try:
                pmid = article.findtext(".//PMID", default="")
                title = "".join(article.find(".//ArticleTitle").itertext()).strip()
                published = self._extract_published_date(article)
                doi = (
                    article.findtext('.//ELocationID[@EIdType="doi"]', default="")
                    or article.findtext('.//ArticleId[@IdType="doi"]', default="")
                )
                papers.append(
                    Paper(
                        paper_id=pmid,
                        title=title,
                        authors=self._extract_authors(article),
                        abstract=self._extract_abstract(article),
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        pdf_url="",
                        published_date=published,
                        updated_date=published,
                        source="pubmed",
                        categories=[],
                        keywords=[],
                        doi=doi,
                    )
                )
            except Exception as exc:
                print(f"Error parsing PubMed article: {exc}")
        return papers

    def download_pdf(self, paper_id: str, save_path: str) -> str:
        raise NotImplementedError(
            "PubMed does not provide direct PDF downloads. Use the DOI or URL instead."
        )

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        return (
            "PubMed only exposes metadata and abstracts through this adapter. "
            "Use the DOI or publisher URL for full text."
        )
