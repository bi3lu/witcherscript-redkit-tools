"""Diagnostics provider wrapper."""

from .lsp.diagnostics import _deduplicate, collect_diagnostics, to_lsp_range

__all__ = ["_deduplicate", "collect_diagnostics", "to_lsp_range"]
