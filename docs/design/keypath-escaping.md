# Key Escaping in Keypaths Design Note

## Problem

YAML allows keys to contain any characters, including the characters that
OmegaConf uses as keypath delimiters: `.` and `[`/`]`. This creates an
ambiguity: given a keypath string like `"a.b"`, it is impossible to tell
whether the user means the key `"a.b"` (a single key with a literal dot) or
the path `a` → `b` (two nested keys).

Today there is no way to express a keypath that targets a key containing a
literal `.` or `[`/`]`. The following operations are all affected, since they
all converge on `split_key()`:

- `OmegaConf.update(cfg, key, value)`
- `OmegaConf.select(cfg, key)`
- `OmegaConf.from_dotlist(dotlist)`
- `OmegaConf.from_cli(args)`

Note: `${...}` interpolation expressions do **not** benefit from this fix — the
ANTLR grammar parses interpolation key paths structurally and forbids backslash
entirely. See the Follow-up section below.

Note: the bracket notation `a[b.c]` happens to protect dots and other
characters inside the brackets as a side effect of the `.*?` regex — but this
is coincidental and undocumented. It still cannot protect a `]` character
since the bracket itself is the quoting mechanism.

## Proposed solution: backslash escaping in `split_key`

Add backslash escaping to `split_key` so that special characters can be
expressed literally in a keypath string.

### Escape rules

| Input | Result |
|---|---|
| `\.` | literal `.` in key |
| `\[` | literal `[` in key |
| `\]` | literal `]` in key |
| `\=` | literal `=` in key |
| `\x` (anything else incl. `\`) | literal `\x` in key (passthrough) |
| `\\.` | literal `\.` in key |
| `\\[` | literal `\[` in key |
| `\\]` | literal `\]` in key |

The key insight in the passthrough rule is that `\` is only special when
immediately followed by `.`, `[`, `]`, or `=`. A backslash before any other
character (including another backslash) passes through unchanged. This means:

- There are no illegal escape sequences — every input has a defined meaning.
- Existing keypaths with backslash characters continue to work unchanged
  (backwards compatible).
- To produce a literal `\.` in a key, write `\\.`: the first `\` is a bare
  passthrough producing `\`, the second `\` escapes the `.` producing `.`.

### Examples

```python
cfg = OmegaConf.create({"a.b": 42})
assert OmegaConf.select(cfg, r"a\.b") == 42
OmegaConf.update(cfg, r"a\.b", 1)
assert cfg["a.b"] == 1

cfg = OmegaConf.create({"a[0]": 42})
assert OmegaConf.select(cfg, r"a\[0\]") == 42

cfg = OmegaConf.create({"x": {"a.b": 0}})
OmegaConf.update(cfg, r"x.a\.b", 99)
assert cfg["x"]["a.b"] == 99

cfg = OmegaConf.create({r"a\.b": 42})
assert OmegaConf.select(cfg, r"a\\.b") == 42

cfg = OmegaConf.from_dotlist([r"a\.b\=c=42"])
assert cfg["a.b=c"] == 42
```

### Implementation

Replace the two-regex approach in `split_key` with a character-by-character
parser that applies the escape rules above. The parser has two modes: dot mode
(normal key segment) and bracket mode (inside `[...]`). Escape rules apply in
both modes.

Additionally, update `OmegaConf.from_dotlist` to separate keys from values by splitting on the first *unescaped* `=`, rather than performing a hard split on the first `=`.

### Scope

`split_key` and the key-value separator logic in `from_dotlist` need to change. All callers (`update`, `select`,
`_select_impl`, `from_cli`) benefit automatically. The ANTLR interpolation grammar is a
separate parser and is not affected.

*Note on CLI usage:* Because `from_cli` passes arguments through the shell, the shell will consume single backslashes. Documentation must instruct users to quote or double-escape their strings (e.g., `'a\.b=1'` or `a\\.b=1`) when targeting keys with special characters via the command line.

## Follow-up: interpolation support

Backslash escaping is **not** supported in `${...}` interpolation expressions.
The ANTLR lexer rule for interpolation keys (`INTER_KEY: ~[\\{}()[\]:. \t'"]+`)
explicitly excludes backslash, so `${a\.b}` is a grammar error. There is
therefore no way to write an interpolation that targets a key containing a
literal dot, bracket, or equals sign.

The full fix would require changes at three levels:

1. **Grammar**: extend `INTER_KEY` (or add a new token) to allow backslash
   escape sequences inside interpolation key segments.
2. **Visitor**: instead of reassembling the parsed tokens back into a dotted
   string (which `split_key` then re-parses), pass the already-split segments
   directly to `_select_impl`, eliminating the redundant round-trip entirely.
3. **Hydra command-line grammar**: Hydra has its own grammar for parsing
   overrides on the command line, which is separate from OmegaConf's ANTLR
   grammar. Supporting escaped keys in Hydra overrides (e.g.
   `key."a\.b"=value`) would require a corresponding change there.

Until this is done, users with keys containing special characters can work
around the limitation by using `oc.select` with the escaped key path as an
argument, since `oc.select` goes through `OmegaConf.select` → `split_key`
rather than through the grammar's interpolation key parser.
