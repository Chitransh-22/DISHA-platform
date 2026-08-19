"""
DISHA Data Sources Package
Provides dedicated, modular data ingestors and scrapers for external disaster intelligence sources.
"""

from app.sources.riseq import (
    RISEQScraper,
    scrape_riseq_earthquakes,
    parse_riseq_html,
    generate_earthquake_event_id,
    classify_india_relevance,
)

__all__ = [
    "RISEQScraper",
    "scrape_riseq_earthquakes",
    "parse_riseq_html",
    "generate_earthquake_event_id",
    "classify_india_relevance",
]
