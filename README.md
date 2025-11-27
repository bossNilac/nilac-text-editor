# Text Editor Project

A fully custom terminal-based text editor implemented in Python.\
This project started as a minimal buffer experiment and evolved into a
functional editor with real navigation, undo/redo, search, replace, and
multi-line editing. The goal was not to recreate Vim or Nano, but to
build a complete editing pipeline from first principles, without relying
on curses, GUI frameworks, or prebuilt widgets.

The result is a compact yet expressive demonstration of state
management, input handling, rendering logic, and algorithmic thinking.

## Features

### Editing Core

The editor maintains a two-dimensional buffer:

``` python
buffer = [list_of_chars_per_line]
```

All text operations are expressed in terms of this structure. The cursor
is tracked by `(row, col)` indices, and vertical/horizontal scrolling is
handled via `top_line` and `left_col`.

Supported editing features include:

-   Inserting characters
-   Backspace and deletion logic
-   Multi-line editing
-   Proper handling of line splits (Enter) and joins (Backspace at
    column zero)

### Undo and Redo

Every change to the buffer is recorded as an operation object, such as:

``` python
{"kind": "insert_char", "row": r, "col": c, "ch": "a"}
{"kind": "split_line", "row": r, "col": c, "right": [...]}
```

Undo is implemented by applying the inverse of the last operation, and
redo re-applies the original.\
This system works reliably for character edits, line splits/joins, and
replace operations.

### Search and Highlight

Search uses a straightforward multi-line substring scan.\
Search results are stored as `(row, start, end)` tuples.

Rendering highlights is done using ANSI escape sequences. The buffer
itself is untouched; highlighting is purely a view-layer concern.

### Replace All

The editor supports bulk replace operations. For undo correctness, each
replace is recorded as a sequence of delete/insert operations, grouped
so the entire replace action can be reversed consistently.

### Smart Navigation

Supported navigation keys:

-   Home / End
-   Ctrl+Left and Ctrl+Right (word-based movement)
-   Page Up / Page Down
-   Arrow keys

------------------------------------------------------------------------

## Rendering System

Rendering is done manually using ANSI cursor codes.\
The renderer slices each logical line using:

``` python
visible = full_line[from_col:to_col]
```

For search mode, a separate renderer walks through the visible segment
and inserts highlight sequences where appropriate.

------------------------------------------------------------------------

## Input Handling

The editor uses the `keyboard` module to read events in real time.\
Every key press passes through:

``` python
buffer_op.record_key(key)
```

Key events include cursor motion, editing, navigation (Home, End,
Ctrl+Arrows), and hotkeys (Ctrl+O, Ctrl+S, Ctrl+Q, Ctrl+Z, Ctrl+Y,
Ctrl+/).

------------------------------------------------------------------------

## File I/O

Loading and saving are implemented with simple line transformations:

``` python
buffer = [list(line.rstrip("\n")) for line in f]
```

Configuration persists the last opened file path using `editor.ini`.

------------------------------------------------------------------------

## Challenges and Learnings

Building a terminal text editor from scratch required solving problems
usually hidden behind higher-level libraries:

-   Terminal state resets
-   Cursor and scroll management
-   Insert/delete mechanics
-   Rendering with no flicker
-   Maintaining undoable operations for multi-line changes

Undo/redo in particular required designing reversible operations for
every edit type, including line splits and joins.

Search highlighting required a layered rendering approach that overlays
highlight spans onto the visible buffer region without modifying the
underlying text.

------------------------------------------------------------------------

## Final Words

This project demonstrates that a functional text editor can be built
from first principles without relying on terminal frameworks or pre-made
UI components. Every aspect of the editor---from input handling and
rendering to text storage, navigation, undo/redo, and search---was
implemented manually and deliberately.

The result is a compact, educational, and technically honest example of
how text editors operate internally. It touches on buffer architecture,
incremental state changes, terminal control sequences, and efficient
user interaction. Despite its minimalist scope, the editor is
feature-complete enough to showcase meaningful engineering decisions and
a solid understanding of system-level program behavior.

This codebase stands as a clear reference for anyone seeking to
understand the mechanics behind text editors or low-level text
manipulation in terminal environments.
