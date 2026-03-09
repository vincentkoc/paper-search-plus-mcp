"""Paper deduplication utility for removing duplicates across multiple sources.

Same papers often appear in multiple sources (arXiv, Semantic Scholar, OpenAlex, etc.).
This module provides utilities to identify and remove duplicates based on:
- DOI matching (primary method)
- Title similarity (secondary method)
- Author + year matching (tertiary method)
"""
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from .paper import Paper


def normalize_doi(doi: str) -> str:
    """Normalize DOI for comparison."""
    if not doi:
        return ""
    # Remove URL prefix if present
    doi = doi.lower()
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:", "doi.org/"]:
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    # Remove any trailing slashes or spaces
    return doi.strip().rstrip("/")


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    if not title:
        return ""
    # Convert to lowercase
    title = title.lower()
    # Remove common punctuation
    for char in [".", ",", "!", "?", ";", ":", "-", "(", ")", "[", "]", "{", "}"]:
        title = title.replace(char, " ")
    # Remove extra whitespace
    title = " ".join(title.split())
    return title


def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles using SequenceMatcher.

    Returns:
        float: Similarity score between 0 and 1
    """
    if not title1 or not title2:
        return 0.0
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def are_titles_similar(title1: str, title2: str, threshold: float = 0.9) -> bool:
    """Check if two titles are similar enough to be considered duplicates.

    Args:
        title1: First title
        title2: Second title
        threshold: Similarity threshold (default: 0.9)

    Returns:
        bool: True if titles are similar enough
    """
    return title_similarity(title1, title2) >= threshold


def are_same_paper(paper1: Paper, paper2: Paper) -> bool:
    """Check if two papers are the same using multiple criteria.

    Priority:
    1. DOI match (exact, after normalization)
    2. Title similarity (>= 0.9)
    3. Author + year match

    Args:
        paper1: First paper
        paper2: Second paper

    Returns:
        bool: True if papers are likely the same
    """
    # Check DOI match (most reliable)
    doi1 = normalize_doi(paper1.doi)
    doi2 = normalize_doi(paper2.doi)
    if doi1 and doi2 and doi1 == doi2:
        return True

    # Check title similarity
    if are_titles_similar(paper1.title, paper2.title):
        # Additional check: at least one author in common
        if paper1.authors and paper2.authors:
            authors1 = [a.lower().strip() for a in paper1.authors]
            authors2 = [a.lower().strip() for a in paper2.authors]
            if any(a1 in a2 or a2 in a1 for a1 in authors1 for a2 in authors2):
                return True

    # Check author + year match
    if paper1.authors and paper2.authors:
        authors1 = [a.lower().strip() for a in paper1.authors]
        authors2 = [a.lower().strip() for a in paper2.authors]
        # Check if at least 2 authors match
        matching_authors = sum(1 for a1 in authors1 for a2 in authors2 if a1 in a2 or a2 in a1)
        if matching_authors >= 2:
            # Check publication year
            year1 = paper1.published_date.year if paper1.published_date else None
            year2 = paper2.published_date.year if paper2.published_date else None
            if year1 and year2 and year1 == year2:
                return True

    return False


def deduplicate_papers(papers: List[Paper], keep: str = "first") -> List[Paper]:
    """Remove duplicate papers from a list.

    Args:
        papers: List of papers to deduplicate
        keep: Which duplicate to keep ('first', 'last', or 'best')
            - 'first': Keep the first occurrence (default)
            - 'last': Keep the last occurrence
            - 'best': Keep the one with most complete metadata

    Returns:
        List[Paper]: Deduplicated list of papers
    """
    if not papers:
        return []

    # Build groups of duplicates
    groups: List[List[Paper]] = []
    seen_indices: Set[int] = set()

    for i, paper in enumerate(papers):
        if i in seen_indices:
            continue

        # Start a new group with this paper
        group = [paper]
        seen_indices.add(i)

        # Look for duplicates
        for j in range(i + 1, len(papers)):
            if j in seen_indices:
                continue
            if are_same_paper(paper, papers[j]):
                group.append(papers[j])
                seen_indices.add(j)

        groups.append(group)

    # Select which paper to keep from each group
    result = []
    for group in groups:
        if keep == "first":
            result.append(group[0])
        elif keep == "last":
            result.append(group[-1])
        elif keep == "best":
            # Select paper with most complete metadata
            def completeness_score(p: Paper) -> int:
                score = 0
                if p.title: score += 1
                if p.abstract: score += 2
                if p.doi: score += 2
                if p.authors: score += 1
                if p.pdf_url: score += 2
                if p.categories: score += 1
                return score

            result.append(max(group, key=completeness_score))
        else:
            result.append(group[0])

    return result


def deduplicate_paper_dicts(paper_dicts: List[Dict], keep: str = "first") -> List[Dict]:
    """Remove duplicate papers from a list of paper dictionaries.

    This is a convenience function that converts dicts to Paper objects,
    deduplicates, and converts back to dicts.

    Args:
        paper_dicts: List of paper dictionaries to deduplicate
        keep: Which duplicate to keep ('first', 'last', or 'best')

    Returns:
        List[Dict]: Deduplicated list of paper dictionaries
    """
    if not paper_dicts:
        return []

    # Convert dicts to Paper objects
    papers = []
    for d in paper_dicts:
        try:
            papers.append(dict_to_paper(d))
        except Exception:
            # If conversion fails, skip this entry
            continue

    # Deduplicate
    deduped = deduplicate_papers(papers, keep)

    # Convert back to dicts
    return [p.to_dict() for p in deduped]


def merge_duplicate_papers(papers: List[Paper]) -> List[Paper]:
    """Merge duplicate papers by combining their metadata.

    When duplicates are found, create a merged paper with the best metadata
    from all duplicates. Priority given to fields with actual data.

    Args:
        papers: List of papers to deduplicate and merge

    Returns:
        List[Paper]: List with duplicates merged
    """
    if not papers:
        return []

    # Build groups of duplicates
    groups: List[List[Paper]] = []
    seen_indices: Set[int] = set()

    for i, paper in enumerate(papers):
        if i in seen_indices:
            continue

        group = [paper]
        seen_indices.add(i)

        for j in range(i + 1, len(papers)):
            if j in seen_indices:
                continue
            if are_same_paper(paper, papers[j]):
                group.append(papers[j])
                seen_indices.add(j)

        groups.append(group)

    # Merge each group
    result = []
    for group in groups:
        if len(group) == 1:
            result.append(group[0])
        else:
            result.append(merge_paper_group(group))

    return result


def merge_paper_group(group: List[Paper]) -> Paper:
    """Merge a group of duplicate papers into a single paper.

    Args:
        group: List of papers that are duplicates

    Returns:
        Paper: Merged paper with combined metadata
    """
    # Use the first paper as base
    base = group[0]

    # Prefer fields with actual data
    def choose_field(field_name: str):
        for paper in group:
            value = getattr(paper, field_name, None)
            if value:
                return value
        return getattr(base, field_name, None)

    def choose_list(field_name: str):
        # Combine all non-empty lists, avoiding duplicates
        seen = set()
        result = []
        for paper in group:
            value = getattr(paper, field_name, None)
            if value:
                for item in value:
                    if item and item not in seen:
                        seen.add(item)
                        result.append(item)
        return result if result else getattr(base, field_name, None)

    # Choose best fields
    title = choose_field("title")
    abstract = choose_field("abstract")
    doi = choose_field("doi")
    pdf_url = choose_field("pdf_url")
    url = choose_field("url")

    # Use earliest published date
    published_date = base.published_date
    for paper in group[1:]:
        if paper.published_date and paper.published_date < published_date:
            published_date = paper.published_date

    # Combine authors and categories
    authors = choose_list("authors")
    categories = choose_list("categories")
    keywords = choose_list("keywords")
    references = choose_list("references")

    # Combine extra data
    extra = {}
    for paper in group:
        if paper.extra:
            extra.update(paper.extra)

    # Use max citation count
    citations = max((p.citations for p in group), default=0)

    # Keep source from all duplicates
    all_sources = [p.source for p in group]
    source = base.source
    extra["merged_from"] = all_sources

    return Paper(
        paper_id=base.paper_id,
        title=title,
        authors=authors,
        abstract=abstract,
        doi=doi,
        published_date=published_date,
        pdf_url=pdf_url,
        url=url,
        source=source,
        categories=categories,
        keywords=keywords,
        citations=citations,
        references=references,
        extra=extra if extra else None
    )


def dict_to_paper(d: Dict) -> Paper:
    """Convert a dictionary back to a Paper object.

    Args:
        d: Dictionary from Paper.to_dict()

    Returns:
        Paper object
    """
    from datetime import datetime

    # Parse dates
    published_date = None
    if d.get("published_date"):
        try:
            published_date = datetime.fromisoformat(d["published_date"])
        except:
            pass

    updated_date = None
    if d.get("updated_date"):
        try:
            updated_date = datetime.fromisoformat(d["updated_date"])
        except:
            pass

    # Parse lists
    def parse_list(field: str) -> List[str]:
        val = d.get(field, "")
        if isinstance(val, list):
            return val
        if val:
            return [s.strip() for s in val.split(";") if s.strip()]
        return []

    # Parse extra
    extra = d.get("extra")
    if isinstance(extra, str):
        try:
            import json
            extra = json.loads(extra)
        except:
            extra = {}

    return Paper(
        paper_id=d.get("paper_id", ""),
        title=d.get("title", ""),
        authors=parse_list("authors"),
        abstract=d.get("abstract", ""),
        doi=d.get("doi", ""),
        published_date=published_date or datetime.min,
        pdf_url=d.get("pdf_url", ""),
        url=d.get("url", ""),
        source=d.get("source", ""),
        updated_date=updated_date,
        categories=parse_list("categories"),
        keywords=parse_list("keywords"),
        citations=int(d.get("citations", 0)),
        references=parse_list("references"),
        extra=extra
    )


def find_duplicates(papers: List[Paper]) -> List[Tuple[Paper, List[Paper]]]:
    """Find groups of duplicate papers without removing them.

    Useful for analyzing what duplicates exist before deciding how to handle them.

    Args:
        papers: List of papers to analyze

    Returns:
        List of tuples (canonical_paper, duplicate_papers)
    """
    if not papers:
        return []

    groups: List[Tuple[Paper, List[Paper]]] = []
    seen_indices: Set[int] = set()

    for i, paper in enumerate(papers):
        if i in seen_indices:
            continue

        duplicates = []
        seen_indices.add(i)

        for j in range(i + 1, len(papers)):
            if j in seen_indices:
                continue
            if are_same_paper(paper, papers[j]):
                duplicates.append(papers[j])
                seen_indices.add(j)

        if duplicates:
            groups.append((paper, duplicates))

    return groups
