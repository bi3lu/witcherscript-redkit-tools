from click.testing import CliRunner

from witcherscript_cli.main import main
from witcherscript_langserver import __version__
from witcherscript_langserver.server import create_server


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_version_command() -> None:
    result = CliRunner().invoke(main, ["version"])

    assert result.exit_code == 0
    assert result.output == "witcherscript 0.1.0\n"


def test_language_server_can_be_created() -> None:
    server = create_server()

    assert server.name == "witcherscript-langserver"
