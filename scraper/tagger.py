"""
Auto-tagger — assigns sector and sub-sector labels to articles using
keyword matching against config/keywords.yaml.
"""
import logging
import os
from functools import lru_cache
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

KEYWORDS_PATH = os.environ.get("NEWSR0_KEYWORDS_PATH", "config/keywords.yaml")


@lru_cache(maxsize=1)
def _load_keyword_map() -> dict[str, list[str]]:
    with open(KEYWORDS_PATH, "r") as f:
        data = yaml.safe_load(f)
    return data.get("sector_keywords", {})


def _text_contains_keyword(text: str, keyword: str) -> bool:
    return keyword.lower() in text.lower()


def tag_article(title: str, excerpt: str, default_sector: Optional[str] = None,
                default_sub_sector: Optional[str] = None) -> tuple[str, list[str]]:
    """
    Determine the best sector and list of sub-sectors for an article.

    Returns (sector, sub_sectors_list).
    """
    keyword_map = _load_keyword_map()
    combined_text = f"{title} {excerpt}"

    matched_sectors: dict[str, int] = {}  # sector_key -> match count

    for sector_key, keywords in keyword_map.items():
        count = sum(1 for kw in keywords if _text_contains_keyword(combined_text, kw))
        if count > 0:
            matched_sectors[sector_key] = count

    if not matched_sectors:
        # Fall back to source-level defaults
        sector = default_sector or "Macroeconomic"
        sub_sectors = [default_sub_sector] if default_sub_sector else []
        return sector, sub_sectors

    # Sort by match count descending; most specific match wins
    ranked = sorted(matched_sectors.items(), key=lambda x: (-len(x[0].split(".")), -x[1]))

    # The first ranked entry is our primary match
    primary_key = ranked[0][0]
    parts = primary_key.split(".")
    sector = parts[0]

    sub_sectors: list[str] = []
    # Collect all matched sub-sector paths
    for key, _ in ranked:
        key_parts = key.split(".")
        if key_parts[0] == sector and len(key_parts) > 1:
            sub_sectors.append(".".join(key_parts[1:]))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_sub_sectors: list[str] = []
    for s in sub_sectors:
        if s not in seen:
            seen.add(s)
            unique_sub_sectors.append(s)

    return sector, unique_sub_sectors
