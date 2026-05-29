"""Language server entrypoint."""

from pygls.lsp.server import LanguageServer

from witcherscript_langserver import __version__


def create_server() -> LanguageServer:
    """Create the WitcherScript language server instance."""
    return LanguageServer("witcherscript-langserver", __version__)


def main() -> None:
    """Start the language server over stdio."""
    create_server().start_io()
