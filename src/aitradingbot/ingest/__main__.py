"""Command line: python -m aitradingbot.ingest {binance,kraken,bitvavo,all} [options]

Examples:
    python -m aitradingbot.ingest all
    python -m aitradingbot.ingest binance --symbols BTCUSDT ETHUSDT --timeframes 1d
    python -m aitradingbot.ingest kraken --zip D:/downloads/Kraken_OHLCVT_Full.zip
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from aitradingbot.ingest import binance, bitvavo, kraken
from aitradingbot.ingest.common import TIMEFRAMES

DEFAULT_TIMEFRAMES = ["1d", "4h", "1h"]
DEFAULT_START = "2017-08-01"  # warm-up history before the development split (2018-01-01)


def run_binance(args: argparse.Namespace) -> None:
    end = args.end or binance.last_complete_month()
    binance.ingest(args.symbols, args.timeframes, args.start[:7], end[:7])


def run_kraken(args: argparse.Namespace) -> None:
    if args.zip:
        archives = [kraken.open_local(Path(p)) for p in args.zip]
    else:
        archives = kraken.default_remote_archives()
    kraken.ingest(archives, args.pairs, args.timeframes)


def run_bitvavo(args: argparse.Namespace) -> None:
    bitvavo.ingest(args.markets, args.timeframes, args.start, args.end)


def run_all(args: argparse.Namespace) -> None:
    for runner in (run_binance, run_kraken, run_bitvavo):
        runner(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m aitradingbot.ingest",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--timeframes", nargs="+", default=DEFAULT_TIMEFRAMES, choices=list(TIMEFRAMES)
    )
    common.add_argument(
        "--start", default=DEFAULT_START, help="YYYY-MM-DD (Binance uses the month)"
    )
    common.add_argument("--end", default=None, help="YYYY-MM-DD; default: latest available")

    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("binance", parents=[common], help="Binance public monthly klines (USDT)")
    b.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    b.set_defaults(run=run_binance)

    k = sub.add_parser("kraken", parents=[common], help="Kraken OHLCVT history (EUR)")
    k.add_argument(
        "--pairs", nargs="+", default=list(kraken.KRAKEN_NAMES), choices=list(kraken.KRAKEN_NAMES)
    )
    k.add_argument(
        "--zip", nargs="+", help="local zip(s) instead of reading remotely; later files win"
    )
    k.set_defaults(run=run_kraken)

    v = sub.add_parser("bitvavo", parents=[common], help="Bitvavo candles API (EUR)")
    v.add_argument("--markets", nargs="+", default=["BTC-EUR", "ETH-EUR"])
    v.set_defaults(run=run_bitvavo)

    a = sub.add_parser("all", parents=[common], help="all three sources with default pairs")
    a.set_defaults(
        run=run_all,
        symbols=["BTCUSDT", "ETHUSDT"],
        pairs=list(kraken.KRAKEN_NAMES),
        zip=None,
        markets=["BTC-EUR", "ETH-EUR"],
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
