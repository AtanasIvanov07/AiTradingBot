"""Repository safety checks: config stays in dry-run, holds no secrets, versions stay pinned."""

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "user_data" / "config.json"


def load_config() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CONFIG.read_text(encoding="utf-8"))
    return data


def test_config_is_dry_run_spot_eur() -> None:
    config = load_config()
    assert config["dry_run"] is True, (
        "config.json must stay in dry-run; live mode is a Phase 4 decision"
    )
    assert config["trading_mode"] == "spot"
    assert config["stake_currency"] == "EUR"


def test_config_holds_no_secrets() -> None:
    config = load_config()
    assert config["exchange"]["key"] == ""
    assert config["exchange"]["secret"] == ""
    assert config["telegram"]["token"] == ""
    assert "api_server" not in config, (
        "API server settings (incl. secrets) belong in config.private.json"
    )


def test_private_example_binds_api_to_localhost() -> None:
    example_path = ROOT / "user_data" / "config.private.example.json"
    example = json.loads(example_path.read_text(encoding="utf-8"))
    assert example["api_server"]["listen_ip_address"] == "127.0.0.1"


def test_private_config_is_gitignored() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "user_data/config.private.json" in gitignore


def test_freqtrade_version_matches_docker_image() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    compose = (ROOT / "ops" / "docker-compose.yml").read_text(encoding="utf-8")
    pip_version = re.search(r"^freqtrade==(\S+)$", requirements, re.MULTILINE)
    image_version = re.search(r"image:\s*freqtradeorg/freqtrade:(\S+)", compose)
    assert pip_version and image_version
    assert pip_version.group(1) == image_version.group(1)
