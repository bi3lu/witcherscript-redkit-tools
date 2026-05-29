"""Language server entrypoint wrapper."""

from .lsp.server import WitcherScriptLanguageServer, create_server

__all__ = ["WitcherScriptLanguageServer", "create_server"]
