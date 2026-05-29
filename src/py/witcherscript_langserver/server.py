"""Language server entrypoint."""

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from witcherscript_langserver import __version__
from witcherscript_langserver.diagnostics import collect_diagnostics


class WitcherScriptLanguageServer(LanguageServer):
    """Minimal WitcherScript language server state.

    Attributes:
        documents: In-memory document cache keyed by document URI.
        workspace_root_uri: Root URI received during LSP initialization.
        initialized: Whether the client has sent the initialized notification.
    """

    def __init__(self) -> None:
        super().__init__(
            "witcherscript-langserver",
            __version__,
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )

        self.documents: dict[str, str] = {}
        self.workspace_root_uri: str | None = None
        self.initialized = False

    def cache_document(self, uri: str, text: str) -> None:
        """Store the latest text for a document URI.

        Args:
            uri: LSP document URI.
            text: Full document text to cache.
        """
        self.documents[uri] = text

    def document_text(self, uri: str) -> str:
        """Return cached text for a document URI.

        Args:
            uri: LSP document URI.

        Returns:
            Cached document text, or an empty string when the document is unknown.
        """
        return self.documents.get(uri, "")


def create_server() -> WitcherScriptLanguageServer:
    """Create and configure a WitcherScript language server instance.

    Returns:
        A language server with the minimal LSP feature set registered.
    """
    server = WitcherScriptLanguageServer()
    register_features(server)
    return server


def register_features(server: WitcherScriptLanguageServer) -> None:
    """Register the minimal LSP feature set.

    Args:
        server: Language server instance that should receive the feature handlers.
    """

    @server.feature(types.INITIALIZE)
    def initialize(ls: WitcherScriptLanguageServer, params: types.InitializeParams) -> None:
        """Handle LSP initialization.

        Args:
            ls: Active WitcherScript language server instance.
            params: Client initialization parameters.
        """
        ls.workspace_root_uri = params.root_uri

    @server.feature(types.INITIALIZED)
    def initialized(ls: WitcherScriptLanguageServer, params: types.InitializedParams) -> None:
        """Handle the LSP initialized notification.

        Args:
            ls: Active WitcherScript language server instance.
            params: Initialized notification parameters.
        """
        _ = params
        ls.initialized = True

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: WitcherScriptLanguageServer, params: types.DidOpenTextDocumentParams) -> None:
        """Cache an opened document and publish diagnostics.

        Args:
            ls: Active WitcherScript language server instance.
            params: Opened document notification parameters.
        """
        document = params.text_document
        ls.cache_document(document.uri, document.text)
        publish_diagnostics(ls, document.uri, document.text)

    @server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
    def did_change(
        ls: WitcherScriptLanguageServer,
        params: types.DidChangeTextDocumentParams,
    ) -> None:
        """Cache a changed document and publish diagnostics.

        Args:
            ls: Active WitcherScript language server instance.
            params: Changed document notification parameters.
        """
        uri = params.text_document.uri
        text = _text_from_change(params)
        ls.cache_document(uri, text)
        publish_diagnostics(ls, uri, text)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE, types.SaveOptions(include_text=True))
    def did_save(ls: WitcherScriptLanguageServer, params: types.DidSaveTextDocumentParams) -> None:
        """Analyze a saved document and publish diagnostics.

        Args:
            ls: Active WitcherScript language server instance.
            params: Saved document notification parameters.
        """
        uri = params.text_document.uri
        text = params.text if params.text is not None else ls.document_text(uri)
        ls.cache_document(uri, text)
        publish_diagnostics(ls, uri, text)


def publish_diagnostics(ls: WitcherScriptLanguageServer, uri: str, text: str) -> None:
    """Publish diagnostics for a document.

    Args:
        ls: Active WitcherScript language server instance.
        uri: LSP document URI.
        text: Full document text to analyze.
    """
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=uri,
            diagnostics=collect_diagnostics(text),
        )
    )


def _text_from_change(params: types.DidChangeTextDocumentParams) -> str:
    """Extract full document text from a change notification.

    Args:
        params: Changed document notification parameters.

    Returns:
        Text from the latest content change, or an empty string when the
        notification has no changes.
    """
    if not params.content_changes:
        return ""

    return params.content_changes[-1].text


def main() -> None:
    """Start the language server over standard input and output."""
    create_server().start_io()
