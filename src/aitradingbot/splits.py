"""Research data splits (PROJECT_PLAN.md §5.1). Dates are inclusive, UTC.

The holdout is a lockbox: it is downloaded and quality-checked like everything else, but strategy
results on it are looked at exactly once, at the end of Phase 2.
"""

import pandas as pd

WARMUP_START = pd.Timestamp("2017-08-01", tz="UTC")  # extra history for indicator warm-up only

DEVELOPMENT = (pd.Timestamp("2018-01-01", tz="UTC"), pd.Timestamp("2022-12-31", tz="UTC"))
VALIDATION = (pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2024-12-31", tz="UTC"))
HOLDOUT = (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-09-30", tz="UTC"))

RESEARCH_START = DEVELOPMENT[0]
RESEARCH_END = HOLDOUT[1]
