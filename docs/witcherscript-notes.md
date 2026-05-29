# WitcherScript Notes

This document records the WitcherScript language constructs represented by the lexer, parser, and symbol index.

## Source Files

WitcherScript files use the `.ws` extension. The language server scans configured script roots and parses files into a tolerant structural AST. The parser is designed for editor use: it keeps useful declarations available even when a file contains syntax errors.

## Lexical Elements

The lexer recognizes:

- identifiers
- keywords
- integer and floating-point number literals
- numeric suffixes such as `100.0f` and `10u32`
- single-quoted and double-quoted string literals
- line comments with `//`
- block comments with `/* ... */`
- punctuation and operators
- unknown characters as recoverable error tokens

Recoverable lexer diagnostics include:

- unexpected characters
- unterminated strings
- unterminated block comments

## Keywords

The keyword table includes common WitcherScript declarations, control flow, modifiers, and REDkit-oriented constructs:

```text
abstract
auto
break
case
class
cleanup
continue
default
else
entry
enum
event
exec
extends
false
final
for
function
if
import
in
latent
native
none
optional
out
parent
private
protected
public
quest
return
reward
state
statemachine
storyscene
super
switch
timer
true
var
while
NULL
```

## Parsed Declarations

The parser builds structural nodes for:

- imports
- classes
- inheritance through `extends`
- states
- state parent clauses through `in`
- functions
- events
- parameters
- fields
- local variables
- default declarations
- basic statements

The AST model is intentionally declaration-oriented. This gives the language server enough structure for diagnostics, outline, completion, hover, definition, references, and project indexing.

## Symbol Kinds

The symbol table tracks:

- `class`
- `event`
- `field`
- `function`
- `local`
- `state`

Each symbol stores:

- name
- kind
- file URI
- declaration range
- selection range
- container name
- type name, return type, base class, or parent state where applicable

## Type References

The index records type-like names from:

- class base names
- state parent names
- field declarations
- function return types
- parameters
- local variables

This supports type lookup, definition, hover, completion, and inheritance indexing.

## Error Recovery

The parser reports syntax diagnostics and then resumes at declaration or member boundaries where possible. This keeps editor features available while a file is being edited.

Examples:

- a missing `;` in a field declaration does not prevent following functions from being indexed
- a missing `}` produces a diagnostic without discarding all symbols collected before the error
- malformed strings produce lexer diagnostics while tokenization continues
