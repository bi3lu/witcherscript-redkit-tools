"""Developer CLI entrypoint."""

import json
from dataclasses import asdict
from pathlib import Path

import click

from witcherscript_langserver import __version__
from witcherscript_langserver.corpus import run_corpus
from witcherscript_langserver.doctor import DoctorReport, run_doctor
from witcherscript_langserver.parser.parser import parse as parse_source


@click.group()
def main() -> None:
    """WitcherScript developer tools."""


@main.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def parse(path: Path) -> None:
    """Parse a WitcherScript file and print its AST as JSON.

    Args:
        path: Path to the WitcherScript source file.
    """
    result = parse_source(path.read_text(encoding="utf-8"))
    click.echo(
        json.dumps(
            {
                "module": _json_ready(asdict(result.module)),
                "diagnostics": [
                    _json_ready(asdict(diagnostic)) for diagnostic in result.diagnostics
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


@main.command()
@click.argument(
    "paths",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--no-semantic",
    is_flag=True,
    help="Only run lexer and parser diagnostics.",
)
def corpus(paths: tuple[Path, ...], no_semantic: bool) -> None:
    """Analyze a WitcherScript corpus and print a diagnostics report.

    Args:
        paths: Files or directories to scan for WitcherScript sources.
        no_semantic: Whether semantic diagnostics should be skipped.
    """
    report = run_corpus(paths, include_semantic=not no_semantic)
    click.echo(json.dumps(_json_ready(asdict(report)), indent=2, sort_keys=True))


@main.command()
@click.option(
    "--workspace",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    help="Workspace root to inspect.",
)
@click.option("--json", "json_output", is_flag=True, help="Print the report as JSON.")
def doctor(workspace: Path, json_output: bool) -> None:
    """Check the health of a WitcherScript workspace.

    Args:
        workspace: Workspace root to inspect.
        json_output: Whether the report should be printed as JSON.
    """
    report = run_doctor(workspace)

    if json_output:
        click.echo(json.dumps(_json_ready(asdict(report)), indent=2, sort_keys=True))
        raise SystemExit(1 if report.has_errors else 0)

    _print_doctor_report(report)
    raise SystemExit(1 if report.has_errors else 0)


@main.command()
def version() -> None:
    """Print the CLI version."""
    click.echo(f"witcherscript {__version__}")


def _print_doctor_report(report: DoctorReport) -> None:
    click.echo(f"WitcherScript doctor: {report.workspace}")
    click.echo(f"Indexed files: {report.indexed_files}")
    click.echo(f"Diagnostics: {report.diagnostics}")
    click.echo()

    for check in report.checks:
        detail = "" if check.detail is None else f" ({check.detail})"
        click.echo(f"[{check.status.upper()}] {check.name}: {check.message}{detail}")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_ready(item) for item in value]

    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]

    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value

    return value
