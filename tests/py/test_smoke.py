"""Smoke tests for package metadata, CLI commands, and server creation."""

import json
from pathlib import Path

from click.testing import CliRunner

from witcherscript_cli.main import main
from witcherscript_langserver import __version__
from witcherscript_langserver.server import create_server

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_package_version() -> None:
    assert __version__ == _expected_version()


def test_cli_version_command() -> None:
    result = CliRunner().invoke(main, ["version"])

    assert result.exit_code == 0
    assert result.output == f"witcherscript {_expected_version()}\n"


def test_cli_parse_command_outputs_ast() -> None:
    result = CliRunner().invoke(main, ["parse", "samples/scripts/valid/minimal_class.ws"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["module"]["declarations"][0]["name"] == "MinimalClass"
    assert payload["diagnostics"] == []


def test_language_server_can_be_created() -> None:
    server = create_server()

    assert server.name == "witcherscript-langserver"


def _expected_version() -> str:
    return (PROJECT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
