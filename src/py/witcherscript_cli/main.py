"""Developer CLI entrypoint."""

import json
from dataclasses import asdict
from pathlib import Path

import click

from witcherscript_langserver.corpus import run_corpus
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
def version() -> None:
    """Print the CLI version."""
    click.echo("witcherscript 0.1.0")


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
