"""Workspace document and project index state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

from witcherscript_langserver.config import WorkspaceConfig, load_workspace_config
from witcherscript_langserver.indexing.file_index import FileIndex
from witcherscript_langserver.indexing.project_index import ProjectIndex


@dataclass
class WorkspaceState:
    """Mutable language-server view of the current workspace.

    Attributes:
        root_uri: LSP root URI received from the client.
        root_path: Local workspace root path.
        config: Loaded workspace configuration.
        index: Project-wide file index.
    """

    root_uri: str | None = None
    root_path: Path | None = None
    config: WorkspaceConfig | None = None
    index: ProjectIndex = field(default_factory=ProjectIndex)

    def initialize(self, root_uri: str | None) -> None:
        """Initialize workspace state from an LSP root URI.

        Args:
            root_uri: Workspace root URI received during LSP initialization.
        """
        self.root_uri = root_uri
        root_path = path_from_uri(root_uri) if root_uri is not None else None

        if root_path is None:
            return

        self.root_path = root_path
        self.config = load_workspace_config(root_path)
        self.reindex()

    def reindex(self) -> None:
        """Rebuild the project index from the loaded workspace configuration."""
        if self.config is None:
            self.index = ProjectIndex()
            return

        self.index = ProjectIndex.build(self.config)

    def update_file(self, uri: str, text: str) -> FileIndex | None:
        """Index an opened or changed WitcherScript file.

        Args:
            uri: LSP document URI.
            text: Full document text.

        Returns:
            Updated per-file index, or ``None`` when the URI is not a local
            WitcherScript file.
        """
        path = path_from_uri(uri)

        if path is None or path.suffix.lower() != ".ws":
            return None

        return self.index.index_path(path, source=text)

    def remove_file(self, uri: str) -> None:
        """Remove a local file URI from the project index.

        Args:
            uri: LSP document URI.
        """
        path = path_from_uri(uri)

        if path is not None:
            self.index.remove_path(path)

    def refresh_file(self, uri: str) -> FileIndex | None:
        """Reindex a local file URI from disk.

        Args:
            uri: LSP document URI.

        Returns:
            Updated per-file index, or ``None`` when the URI cannot be indexed.
        """
        path = path_from_uri(uri)

        if path is None or path.suffix.lower() != ".ws":
            return None

        if not path.exists():
            self.index.remove_path(path)
            return None

        return self.index.index_path(path)


def path_from_uri(uri: str) -> Path | None:
    """Convert a local LSP file URI to a path.

    Args:
        uri: LSP document or workspace URI.

    Returns:
        Local path, or ``None`` for non-file URIs.
    """
    parsed = urlparse(uri)

    if parsed.scheme != "file":
        return None

    path = unquote(parsed.path)

    if parsed.netloc and parsed.netloc not in {"localhost", ""}:
        path = f"//{parsed.netloc}{path}"

    if len(path) >= 3 and path[0] == "/" and path[2] == ":":
        path = path[1:]

    return Path(path).expanduser().resolve()
