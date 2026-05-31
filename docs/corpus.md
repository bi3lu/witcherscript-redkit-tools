# WitcherScript Corpus Analysis

The corpus runner checks parser, analyzer, and indexing behavior across many `.ws` files.

It is designed for local WitcherScript sources from:

- The Witcher 3 vanilla scripts
- REDkit project scripts
- mod scripts
- repository regression fixtures

The repository does not include proprietary game scripts. Keep local vanilla, REDkit, and mod corpora outside git and pass their directories to the runner.

## Run

```bash
uv run witcherscript corpus samples/fixtures/corpus_project/scripts
```

Multiple roots can be scanned in one run:

```bash
uv run witcherscript corpus \
  "D:/Steam/steamapps/common/The Witcher 3/content/content0/scripts" \
  "D:/REDkitProjects/MyMod/content/scripts" \
  "D:/Games/The Witcher 3/Mods/modExample/content/scripts"
```

Parser-only mode is available when semantic noise from incomplete external roots is not useful:

```bash
uv run witcherscript corpus --no-semantic path/to/scripts
```

## Report

The command prints JSON with:

- scanned roots
- total `.ws` files
- parser coverage percentage
- clean analysis percentage
- files that produced diagnostics
- lexer/parser diagnostic count
- semantic diagnostic count
- diagnostic counts by code
- most common diagnostic code/message pairs
- per-file diagnostics for files that failed clean analysis
- elapsed analysis time

This makes it suitable for release checks and for comparing parser coverage before and after grammar changes.

## Regression Corpus

Committed regression fixtures live in:

```text
samples/fixtures/corpus_project/
```

They are original, compact scripts that mimic vanilla-like, REDkit-like, and mod-like code patterns without copying game content.

## Local Corpus Policy

Do not commit proprietary scripts extracted from the game or REDkit installations.

Recommended local layout:

```text
.corpus/
  vanilla/
  redkit/
  mods/
```

The `.corpus/` directory is ignored by git.
