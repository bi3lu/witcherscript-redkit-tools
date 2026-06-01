"""Language server entrypoint."""

from pathlib import Path

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from witcherscript_langserver import __version__
from witcherscript_langserver.indexing.file_index import FileIndex
from witcherscript_langserver.workspace import WorkspaceState, normalize_file_uri, path_from_uri

from .code_actions import code_actions
from .completion import completions
from .definition import definition
from .diagnostics import collect_diagnostics
from .hover import hover
from .implementation import implementations, inheritance_tree
from .references import references
from .rename import prepare_rename, rename_symbol
from .signature_help import signature_help
from .symbols import document_symbols, workspace_symbols

REFRESH_INDEX_COMMAND = "witcherscript.refreshIndex"
INHERITANCE_TREE_COMMAND = "witcherscript.inheritanceTree"


class WitcherScriptLanguageServer(LanguageServer):
    """Minimal WitcherScript language server state.

    Attributes:
        documents: In-memory document cache keyed by document URI.
        workspace_state: Workspace configuration and project index state.
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
        self.workspace_state = WorkspaceState()
        self.workspace_root_uri: str | None = None
        self.initialized = False

    def cache_document(self, uri: str, text: str) -> None:
        """Store the latest text for a document URI.

        Args:
            uri: LSP document URI.
            text: Full document text to cache.
        """
        self.documents[uri] = text
        normalized_uri = normalize_file_uri(uri)
        if normalized_uri != uri:
            self.documents[normalized_uri] = text

    def document_text(self, uri: str) -> str:
        """Return cached text for a document URI.

        Args:
            uri: LSP document URI.

        Returns:
            Cached document text, or an empty string when the document is unknown.
        """
        return self.documents.get(uri, self.documents.get(normalize_file_uri(uri), ""))


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
        root_uri = _root_uri_from_initialize(params)
        ls.workspace_root_uri = root_uri
        ls.workspace_state.initialize(root_uri)

    @server.feature(types.INITIALIZED)
    def initialized(ls: WitcherScriptLanguageServer, params: types.InitializedParams) -> None:
        """Handle the LSP initialized notification.

        Args:
            ls: Active WitcherScript language server instance.
            params: Initialized notification parameters.
        """
        _ = params
        ls.initialized = True
        publish_config_diagnostics(ls)

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    def did_open(ls: WitcherScriptLanguageServer, params: types.DidOpenTextDocumentParams) -> None:
        """Cache an opened document and publish diagnostics.

        Args:
            ls: Active WitcherScript language server instance.
            params: Opened document notification parameters.
        """
        document = params.text_document
        ls.cache_document(document.uri, document.text)
        ls.workspace_state.update_file(document.uri, document.text)
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
        ls.workspace_state.update_file(uri, text)
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
        ls.workspace_state.update_file(uri, text)
        publish_diagnostics(ls, uri, text)

    @server.feature(types.WORKSPACE_DID_CHANGE_WATCHED_FILES)
    def did_change_watched_files(
        ls: WitcherScriptLanguageServer,
        params: types.DidChangeWatchedFilesParams,
    ) -> None:
        """Refresh project index entries changed outside the editor.

        Args:
            ls: Active WitcherScript language server instance.
            params: Watched file change notification parameters.
        """
        for change in params.changes:
            path = path_from_uri(change.uri)
            if path is not None and path.name == "witcherscript.toml":
                refresh_workspace_index(ls)
                continue

            if change.type == types.FileChangeType.Deleted:
                ls.workspace_state.remove_file(change.uri)

            else:
                ls.workspace_state.refresh_file(change.uri)

    @server.feature(
        types.WORKSPACE_EXECUTE_COMMAND,
        types.ExecuteCommandOptions(commands=[REFRESH_INDEX_COMMAND, INHERITANCE_TREE_COMMAND]),
    )
    def execute_command(
        ls: WitcherScriptLanguageServer,
        params: types.ExecuteCommandParams,
    ) -> object | None:
        """Run a workspace command requested by the LSP client.

        Args:
            ls: Active WitcherScript language server instance.
            params: Execute command request parameters.

        Returns:
            Command result payload for known commands, or ``None`` for unknown
            commands.
        """
        if params.command == INHERITANCE_TREE_COMMAND:
            class_name = (
                str(params.arguments[0])
                if params.arguments is not None and len(params.arguments) > 0
                else ""
            )
            return inheritance_tree(ls.workspace_state.index, class_name)

        if params.command != REFRESH_INDEX_COMMAND:
            return None

        return refresh_workspace_index(ls)

    @server.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(
        ls: WitcherScriptLanguageServer,
        params: types.DocumentSymbolParams,
    ) -> list[types.DocumentSymbol]:
        """Return outline symbols for a document.

        Args:
            ls: Active WitcherScript language server instance.
            params: Document symbol request parameters.

        Returns:
            Hierarchical document symbols.
        """
        file_index = _indexed_file(ls, params.text_document.uri)
        if file_index is None:
            return []

        return document_symbols(file_index)

    @server.feature(types.WORKSPACE_SYMBOL)
    def workspace_symbol(
        ls: WitcherScriptLanguageServer,
        params: types.WorkspaceSymbolParams,
    ) -> list[types.WorkspaceSymbol]:
        """Return project-wide symbols matching a query.

        Args:
            ls: Active WitcherScript language server instance.
            params: Workspace symbol request parameters.

        Returns:
            Matching workspace symbols.
        """
        return workspace_symbols(ls.workspace_state.index, params.query)

    @server.feature(types.TEXT_DOCUMENT_DEFINITION)
    def goto_definition(
        ls: WitcherScriptLanguageServer,
        params: types.DefinitionParams,
    ) -> types.Location | None:
        """Return the definition for the symbol under the cursor.

        Args:
            ls: Active WitcherScript language server instance.
            params: Definition request parameters.

        Returns:
            Definition location, when resolved.
        """
        uri = params.text_document.uri
        normalized_uri = normalize_file_uri(uri)
        return definition(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalized_uri,
            params.position,
        )

    @server.feature(types.TEXT_DOCUMENT_IMPLEMENTATION)
    def implementation(
        ls: WitcherScriptLanguageServer,
        params: types.ImplementationParams,
    ) -> list[types.Location]:
        """Return derived classes or override-like member implementations.

        Args:
            ls: Active WitcherScript language server instance.
            params: Implementation request parameters.

        Returns:
            Implementation locations.
        """
        uri = params.text_document.uri
        normalized_uri = normalize_file_uri(uri)
        return implementations(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalized_uri,
            params.position,
        )

    @server.feature(types.TEXT_DOCUMENT_COMPLETION)
    def completion(
        ls: WitcherScriptLanguageServer,
        params: types.CompletionParams,
    ) -> types.CompletionList:
        """Return keyword and project symbol completions.

        Args:
            ls: Active WitcherScript language server instance.
            params: Completion request parameters.

        Returns:
            Completion list.
        """
        uri = params.text_document.uri
        return completions(
            ls.workspace_state.index,
            normalize_file_uri(uri),
            ls.document_text(uri),
            params.position,
        )

    @server.feature(
        types.TEXT_DOCUMENT_CODE_ACTION,
        types.CodeActionOptions(code_action_kinds=[types.CodeActionKind.QuickFix]),
    )
    def code_action(
        ls: WitcherScriptLanguageServer,
        params: types.CodeActionParams,
    ) -> list[types.CodeAction]:
        """Return safe quick fixes for syntax, semantic, and config diagnostics.

        Args:
            ls: Active WitcherScript language server instance.
            params: Code action request parameters.

        Returns:
            Available code actions.
        """
        uri = params.text_document.uri
        config = ls.workspace_state.config
        config_uri = (
            config.config_path.as_uri()
            if config is not None and config.config_path is not None
            else None
        )
        return code_actions(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalize_file_uri(uri),
            params,
            config_uri,
        )

    @server.feature(types.TEXT_DOCUMENT_PREPARE_RENAME)
    def prepare_rename_symbol(
        ls: WitcherScriptLanguageServer,
        params: types.PrepareRenameParams,
    ) -> types.Range | None:
        """Return the local symbol range that can be renamed.

        Args:
            ls: Active WitcherScript language server instance.
            params: Prepare rename request parameters.

        Returns:
            Rename range when the symbol is supported.
        """
        uri = params.text_document.uri
        return prepare_rename(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalize_file_uri(uri),
            params.position,
        )

    @server.feature(types.TEXT_DOCUMENT_RENAME, types.RenameOptions(prepare_provider=True))
    def rename(
        ls: WitcherScriptLanguageServer,
        params: types.RenameParams,
    ) -> types.WorkspaceEdit | None:
        """Rename a local variable or parameter within its function scope.

        Args:
            ls: Active WitcherScript language server instance.
            params: Rename request parameters.

        Returns:
            Workspace edit for supported local renames.
        """
        uri = params.text_document.uri
        return rename_symbol(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalize_file_uri(uri),
            params.position,
            params.new_name,
        )

    @server.feature(
        types.TEXT_DOCUMENT_SIGNATURE_HELP,
        types.SignatureHelpOptions(trigger_characters=["(", ","], retrigger_characters=[","]),
    )
    def signature_help_info(
        ls: WitcherScriptLanguageServer,
        params: types.SignatureHelpParams,
    ) -> types.SignatureHelp | None:
        """Return signature help for the active call expression.

        Args:
            ls: Active WitcherScript language server instance.
            params: Signature help request parameters.

        Returns:
            Signature help, when the cursor is inside a known call.
        """
        uri = params.text_document.uri
        return signature_help(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalize_file_uri(uri),
            params.position,
        )

    @server.feature(types.TEXT_DOCUMENT_HOVER)
    def hover_info(
        ls: WitcherScriptLanguageServer,
        params: types.HoverParams,
    ) -> types.Hover | None:
        """Return hover information for the symbol under the cursor.

        Args:
            ls: Active WitcherScript language server instance.
            params: Hover request parameters.

        Returns:
            Hover information, when resolved.
        """
        uri = params.text_document.uri
        normalized_uri = normalize_file_uri(uri)
        return hover(
            ls.workspace_state.index,
            ls.document_text(uri),
            normalized_uri,
            params.position,
        )

    @server.feature(types.TEXT_DOCUMENT_REFERENCES)
    def find_references(
        ls: WitcherScriptLanguageServer,
        params: types.ReferenceParams,
    ) -> list[types.Location]:
        """Return simple references for the symbol under the cursor.

        Args:
            ls: Active WitcherScript language server instance.
            params: Reference request parameters.

        Returns:
            Reference locations.
        """
        uri = params.text_document.uri
        normalized_uri = normalize_file_uri(uri)
        return references(
            ls.workspace_state.index,
            ls.documents,
            ls.document_text(uri),
            normalized_uri,
            params.position,
            params.context.include_declaration,
        )


def publish_diagnostics(ls: WitcherScriptLanguageServer, uri: str, text: str) -> None:
    """Publish diagnostics for a document.

    Args:
        ls: Active WitcherScript language server instance.
        uri: LSP document URI.
        text: Full document text to analyze.
    """
    normalized_uri = normalize_file_uri(uri)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=uri,
            diagnostics=collect_diagnostics(
                text,
                ls.workspace_state.index.semantic_diagnostics.for_file(normalized_uri),
            ),
        )
    )


def refresh_workspace_index(ls: WitcherScriptLanguageServer) -> dict[str, int]:
    """Reload workspace configuration and rebuild the project index.

    Args:
        ls: Active WitcherScript language server instance.

    Returns:
        Summary of the refreshed index.
    """
    ls.workspace_state.reload()
    publish_config_diagnostics(ls)

    for uri, text in _unique_cached_documents(ls).items():
        ls.workspace_state.update_file(uri, text)
        publish_diagnostics(ls, uri, text)

    return {
        "indexedFiles": len(ls.workspace_state.index.files),
        "indexedSymbols": len(ls.workspace_state.index.symbols),
    }


def publish_config_diagnostics(ls: WitcherScriptLanguageServer) -> None:
    """Publish diagnostics associated with ``witcherscript.toml``.

    Args:
        ls: Active WitcherScript language server instance.
    """
    for uri, diagnostics in ls.workspace_state.config_diagnostics.items():
        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                diagnostics=collect_diagnostics("", diagnostics),
            )
        )


def _unique_cached_documents(ls: WitcherScriptLanguageServer) -> dict[str, str]:
    documents: dict[str, str] = {}

    for uri, text in ls.documents.items():
        documents[normalize_file_uri(uri)] = text

    return documents


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


def _root_uri_from_initialize(params: types.InitializeParams) -> str | None:
    """Extract the best workspace root URI from initialization parameters.

    Args:
        params: Client initialization parameters.

    Returns:
        Root URI from modern or legacy initialize parameters, when available.
    """
    if params.root_uri is not None:
        return str(params.root_uri)

    if params.workspace_folders:
        return str(params.workspace_folders[0].uri)

    if params.root_path:
        return Path(params.root_path).expanduser().resolve().as_uri()

    return None


def _indexed_file(ls: WitcherScriptLanguageServer, uri: str) -> FileIndex | None:
    normalized_uri = normalize_file_uri(uri)
    for file_index in ls.workspace_state.index.files.values():
        if file_index.uri == normalized_uri:
            return file_index

    text = ls.document_text(uri)
    if not text:
        return None

    return ls.workspace_state.update_file(uri, text)


def main() -> None:
    """Start the language server over standard input and output."""
    create_server().start_io()
