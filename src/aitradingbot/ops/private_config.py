"""Create user_data/config.private.json with a REST API login made of fresh random secrets.

Usage:
    python -m aitradingbot.ops.private_config                    # PC: API on 127.0.0.1
    python -m aitradingbot.ops.private_config --listen 0.0.0.0   # inside Docker (see below)

In Docker the API must listen on 0.0.0.0 inside the container. ops/docker-compose.yml still
publishes it on the host's 127.0.0.1 only. Never overwrites an existing file, and never prints a
secret. Add the Telegram token and the Healthchecks URL yourself afterwards (PROJECT_PLAN.md §9.1).
"""

from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path
from typing import Any


def private_config(listen: str) -> dict[str, Any]:
    return {
        "_comment": "Local secrets (gitignored). Never commit, paste into chats, or screenshot.",
        "telegram": {"enabled": False, "token": "", "chat_id": ""},
        "watchdog": {"healthchecks_url": ""},
        "api_server": {
            "enabled": True,
            "listen_ip_address": listen,
            "listen_port": 8080,
            "verbosity": "error",
            "enable_openapi": False,
            "jwt_secret_key": secrets.token_urlsafe(48),
            "ws_token": secrets.token_urlsafe(32),
            "CORS_origins": [],
            "username": "aitradingbot",
            "password": secrets.token_urlsafe(32),
        },
    }


def create(path: Path, listen: str = "127.0.0.1") -> bool:
    """Write a new private config; False (and untouched) if one already exists."""
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(private_config(listen), indent=4) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aitradingbot.ops.private_config")
    parser.add_argument("--path", type=Path, default=Path("user_data/config.private.json"))
    parser.add_argument("--listen", default="127.0.0.1", choices=["127.0.0.1", "0.0.0.0"])
    args = parser.parse_args(argv)
    if create(args.path, args.listen):
        print(f"Created {args.path} (API on {args.listen}:8080, Telegram off).")
    else:
        print(f"{args.path} already exists; left untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
