"""Developer CLI entrypoint."""

import click


@click.group()
def main() -> None:
    """WitcherScript developer tools."""


@main.command()
def version() -> None:
    """Print the CLI version."""
    click.echo("witcherscript 0.1.0")
