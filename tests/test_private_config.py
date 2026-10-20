import json
from pathlib import Path

from aitradingbot.ops import private_config as pc
from aitradingbot.ops.watchdog import Settings


def test_creates_a_localhost_config_with_fresh_secrets(tmp_path: Path) -> None:
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert pc.create(first) and pc.create(second)
    a, b = (json.loads(p.read_text(encoding="utf-8"))["api_server"] for p in (first, second))
    assert a["listen_ip_address"] == "127.0.0.1"
    assert len(a["jwt_secret_key"]) >= 32 and len(a["password"]) >= 32
    assert a["password"] != b["password"] and a["jwt_secret_key"] != b["jwt_secret_key"]


def test_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "config.private.json"
    path.write_text('{"mine": true}', encoding="utf-8")
    assert not pc.create(path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"mine": True}


def test_docker_config_is_reached_on_localhost(tmp_path: Path) -> None:
    path = tmp_path / "config.private.json"
    pc.create(path, listen="0.0.0.0")
    assert Settings.from_private_config(path).api_url == "http://127.0.0.1:8080"
