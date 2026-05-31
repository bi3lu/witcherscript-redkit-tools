"""Tests for WitcherScript corpus analysis reports."""

import json
from dataclasses import asdict
from pathlib import Path

from click.testing import CliRunner

from witcherscript_cli.main import main
from witcherscript_langserver.corpus import run_corpus

ROOT = Path(__file__).resolve().parents[2]
CORPUS_FIXTURE = ROOT / "samples" / "fixtures" / "corpus_project" / "scripts"


def test_corpus_fixture_reports_clean_analysis() -> None:
    report = run_corpus((CORPUS_FIXTURE,))

    assert report.total_files == 3
    assert report.parser_clean_files == 3
    assert report.parser_coverage_percent == 100.0
    assert report.clean_analysis_percent == 100.0
    assert report.files_with_diagnostics == 0
    assert report.parser_diagnostic_count == 0
    assert report.semantic_diagnostic_count == 0
    assert report.diagnostics_by_code == {}
    assert report.top_diagnostics == ()
    assert report.elapsed_seconds >= 0


def test_corpus_report_summarizes_diagnostics(tmp_path: Path) -> None:
    good = tmp_path / "good.ws"
    broken = tmp_path / "broken.ws"
    good.write_text("class Known {}\n", encoding="utf-8")
    broken.write_text(
        """
class Broken
{
    var item : MissingType;

    function run()
    {
        missing;
    }
}
""".lstrip(),
        encoding="utf-8",
    )

    report = run_corpus((tmp_path,))

    assert report.total_files == 2
    assert report.parser_clean_files == 2
    assert report.parser_coverage_percent == 100.0
    assert report.clean_analysis_percent == 50.0
    assert report.files_with_diagnostics == 1
    assert report.diagnostics_by_code == {"WS3002": 1, "WS3004": 1}
    assert report.files[0].path == str(broken.resolve())
    assert [diagnostic.code for diagnostic in report.files[0].semantic_diagnostics] == [
        "WS3002",
        "WS3004",
    ]


def test_cli_corpus_command_outputs_json_report() -> None:
    result = CliRunner().invoke(main, ["corpus", str(CORPUS_FIXTURE)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_files"] == 3
    assert payload["parser_coverage_percent"] == 100.0
    assert payload["clean_analysis_percent"] == 100.0
    assert payload["files_with_diagnostics"] == 0
    assert payload["diagnostics_by_code"] == {}


def test_corpus_report_is_json_serializable() -> None:
    report = run_corpus((CORPUS_FIXTURE,))

    payload = json.dumps(asdict(report), sort_keys=True)

    assert "total_files" in payload
