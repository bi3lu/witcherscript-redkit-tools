"""Tests for the ``witcherscript doctor`` command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from witcherscript_cli.main import main
from witcherscript_langserver.doctor import run_doctor


def test_doctor_reports_workspace_health(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    vanilla = tmp_path / "vanilla" / "scripts"
    scripts.mkdir(parents=True)
    vanilla.mkdir(parents=True)
    (scripts / "player.ws").write_text("class Player {}\n", encoding="utf-8")
    (vanilla / "base.ws").write_text("class Base {}\n", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        """
[project]
name = "DoctorFixture"

[scripts]
source_roots = ["scripts"]
vanilla_roots = ["vanilla/scripts"]
""".lstrip(),
        encoding="utf-8",
    )

    report = run_doctor(tmp_path)

    assert not report.has_errors
    assert report.indexed_files == 2
    assert report.diagnostics == 0
    assert ("config.exists", "ok") in {(check.name, check.status) for check in report.checks}


def test_doctor_cli_json_output(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "player.ws").write_text("class Player {}\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["doctor", "--workspace", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["indexed_files"] == 1
    assert any(check["name"] == "config.exists" for check in payload["checks"])


def test_doctor_exits_nonzero_for_invalid_toml(tmp_path: Path) -> None:
    (tmp_path / "witcherscript.toml").write_text("[project\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["doctor", "--workspace", str(tmp_path)])

    assert result.exit_code == 1
    assert "Invalid TOML" in result.output
