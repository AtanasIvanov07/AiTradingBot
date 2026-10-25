"""Checks on the real downloaded data (PROJECT_PLAN.md §4.4). Skipped when data/clean is empty,
e.g. in CI. Run after every refresh: python -m aitradingbot.ingest all && pytest."""

import pandas as pd
import pytest

from aitradingbot.ingest import funding
from aitradingbot.ingest.common import Dataset, list_clean_datasets
from aitradingbot.splits import RESEARCH_END, RESEARCH_START
from aitradingbot.validate.checks import assess_from, validate, validate_funding

DATASETS = list_clean_datasets()
LONG_HISTORY_SOURCES = {"binance", "kraken"}  # must span the whole research period

pytestmark = pytest.mark.skipif(not DATASETS, reason="no downloaded data in data/clean")


@pytest.mark.parametrize("dataset", DATASETS, ids=lambda d: f"{d.source}-{d.stem}")
def test_dataset_has_no_errors(dataset: Dataset) -> None:
    report = validate(dataset.load(), dataset.timeframe, assess_from=assess_from(dataset.source))
    assert report.ok, [f.message for f in report.errors]


@pytest.mark.parametrize(
    "dataset",
    [d for d in DATASETS if d.source in LONG_HISTORY_SOURCES],
    ids=lambda d: f"{d.source}-{d.stem}",
)
def test_long_history_covers_research_period(dataset: Dataset) -> None:
    report = validate(dataset.load(), dataset.timeframe)
    assert report.covers(RESEARCH_START, RESEARCH_END), (report.first, report.last)


FUNDING_SYMBOLS = funding.list_symbols()


@pytest.mark.parametrize("symbol", FUNDING_SYMBOLS)
def test_funding_series_has_no_errors_and_covers_research(symbol: str) -> None:
    report = validate_funding(funding.load(symbol))
    assert report.ok, [f.message for f in report.errors]
    start = pd.Timestamp(f"{funding.ARCHIVE_START}-01", tz="UTC")
    assert report.covers(start, RESEARCH_END), (report.first, report.last)
