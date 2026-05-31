"""Corpus analysis helpers for WitcherScript source trees."""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from witcherscript_langserver.analysis.diagnostics_rules import collect_semantic_diagnostics
from witcherscript_langserver.analysis.symbol_table import SymbolTable
from witcherscript_langserver.indexing.file_index import FileIndex, build_file_index
from witcherscript_langserver.parser.errors import SyntaxDiagnostic


@dataclass(frozen=True)
class CorpusDiagnostic:
    """Serializable diagnostic entry for corpus reports.

    Attributes:
        code: Diagnostic code.
        message: Human-readable diagnostic message.
        line: One-based source line.
        character: One-based source character.
        source: Diagnostic origin, either ``parser`` or ``semantic``.
    """

    code: str
    message: str
    line: int
    character: int
    source: str


@dataclass(frozen=True)
class CorpusFileReport:
    """Corpus diagnostics for one source file.

    Attributes:
        path: File path included in the corpus run.
        parser_diagnostics: Parser and lexer diagnostics for the file.
        semantic_diagnostics: Semantic diagnostics for the file.
    """

    path: str
    parser_diagnostics: tuple[CorpusDiagnostic, ...]
    semantic_diagnostics: tuple[CorpusDiagnostic, ...]


@dataclass(frozen=True)
class CorpusReport:
    """Aggregate report for a WitcherScript corpus run.

    Attributes:
        roots: Corpus roots that were scanned.
        total_files: Number of ``.ws`` files discovered.
        parser_clean_files: Number of files without lexer/parser diagnostics.
        parser_coverage_percent: Percent of files without lexer/parser diagnostics.
        clean_analysis_percent: Percent of files without any diagnostics.
        files_with_diagnostics: Number of files that produced diagnostics.
        parser_diagnostic_count: Number of lexer/parser diagnostics.
        semantic_diagnostic_count: Number of semantic diagnostics.
        diagnostics_by_code: Diagnostic counts grouped by code.
        top_diagnostics: Most common diagnostic code/message pairs.
        elapsed_seconds: Corpus analysis time in seconds.
        files: Per-file reports containing only files with diagnostics.
    """

    roots: tuple[str, ...]
    total_files: int
    parser_clean_files: int
    parser_coverage_percent: float
    clean_analysis_percent: float
    files_with_diagnostics: int
    parser_diagnostic_count: int
    semantic_diagnostic_count: int
    diagnostics_by_code: dict[str, int]
    top_diagnostics: tuple[tuple[str, str, int], ...]
    elapsed_seconds: float
    files: tuple[CorpusFileReport, ...]


def run_corpus(
    roots: tuple[Path, ...],
    *,
    include_semantic: bool = True,
) -> CorpusReport:
    """Analyze a collection of WitcherScript files.

    Args:
        roots: Files or directories to scan for ``.ws`` files.
        include_semantic: Whether to run semantic diagnostics after parsing.

    Returns:
        Aggregate corpus report.
    """
    started = time.perf_counter()
    paths = _script_paths(roots)
    file_indexes = tuple(_build_file_index(path) for path in paths)
    symbol_table = _symbol_table(file_indexes)
    semantic_diagnostics = (
        collect_semantic_diagnostics(file_indexes, symbol_table) if include_semantic else None
    )
    file_reports: list[CorpusFileReport] = []
    all_diagnostics: list[CorpusDiagnostic] = []
    parser_count = 0
    semantic_count = 0

    for file_index in file_indexes:
        parser_diagnostics = tuple(
            _corpus_diagnostic(diagnostic, source="parser") for diagnostic in file_index.diagnostics
        )
        semantic_entries = (
            semantic_diagnostics.for_file(file_index.uri)
            if semantic_diagnostics is not None
            else ()
        )
        semantic_file_diagnostics = tuple(
            _corpus_diagnostic(diagnostic, source="semantic") for diagnostic in semantic_entries
        )
        parser_count += len(parser_diagnostics)
        semantic_count += len(semantic_file_diagnostics)
        all_diagnostics.extend((*parser_diagnostics, *semantic_file_diagnostics))

        if parser_diagnostics or semantic_file_diagnostics:
            file_reports.append(
                CorpusFileReport(
                    path=str(file_index.path),
                    parser_diagnostics=parser_diagnostics,
                    semantic_diagnostics=semantic_file_diagnostics,
                )
            )

    elapsed = time.perf_counter() - started
    parser_clean_files = len(file_indexes) - sum(
        1 for file_index in file_indexes if file_index.diagnostics
    )
    return CorpusReport(
        roots=tuple(str(root.expanduser().resolve()) for root in roots),
        total_files=len(file_indexes),
        parser_clean_files=parser_clean_files,
        parser_coverage_percent=_percent(parser_clean_files, len(file_indexes)),
        clean_analysis_percent=_percent(len(file_indexes) - len(file_reports), len(file_indexes)),
        files_with_diagnostics=len(file_reports),
        parser_diagnostic_count=parser_count,
        semantic_diagnostic_count=semantic_count,
        diagnostics_by_code=dict(sorted(_counts_by_code(all_diagnostics).items())),
        top_diagnostics=_top_diagnostics(all_diagnostics),
        elapsed_seconds=round(elapsed, 6),
        files=tuple(file_reports),
    )


def _percent(part: int, total: int) -> float:
    if total == 0:
        return 100.0

    return round((part / total) * 100, 2)


def _script_paths(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    paths: set[Path] = set()

    for root in roots:
        resolved = root.expanduser().resolve()

        if resolved.is_file() and resolved.suffix.lower() == ".ws":
            paths.add(resolved)
            continue

        if resolved.is_dir():
            paths.update(path.resolve() for path in resolved.rglob("*.ws"))

    return tuple(sorted(paths))


def _build_file_index(path: Path) -> FileIndex:
    return build_file_index(
        path,
        path.as_uri(),
        path.read_text(encoding="utf-8"),
    )


def _symbol_table(files: tuple[FileIndex, ...]) -> SymbolTable:
    return SymbolTable.build(
        (symbol for file_index in files for symbol in file_index.symbols),
        (scope for file_index in files for scope in file_index.scopes),
        (reference for file_index in files for reference in file_index.type_references),
        (signature for file_index in files for signature in file_index.callable_signatures),
    )


def _corpus_diagnostic(
    diagnostic: SyntaxDiagnostic,
    *,
    source: str,
) -> CorpusDiagnostic:
    return CorpusDiagnostic(
        code=diagnostic.code,
        message=diagnostic.message,
        line=diagnostic.range.start.line + 1,
        character=diagnostic.range.start.character + 1,
        source=source,
    )


def _counts_by_code(diagnostics: list[CorpusDiagnostic]) -> Counter[str]:
    return Counter(diagnostic.code for diagnostic in diagnostics)


def _top_diagnostics(
    diagnostics: list[CorpusDiagnostic],
) -> tuple[tuple[str, str, int], ...]:
    counter = Counter((diagnostic.code, diagnostic.message) for diagnostic in diagnostics)
    return tuple((code, message, count) for (code, message), count in counter.most_common(20))
