# buffer_op.py
# This module contains all the low-level text-editing logic:
# the cursor, viewport scrolling, undo/redo system, and operations
# like splitting lines, joining lines, and replacing text.
#
# main.py handles UI, while this file handles the "guts" of the editor.

import keyboard
import os
import sys

# Keys that insert text vs keys that move the cursor.
functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right"}

# Keeps a simple log of raw key events (mostly for debugging).
history = []

# The text buffer. Represented as a list of lines, where each line is a list of chars.
buffer = [[]]

# Logical cursor position in the buffer.
row = 0
col = 0

# Viewport scrolling offsets.
top_line = 0
MAX_LINE = 24

left_col = 0
MAX_COL = 120

# Undo/redo stacks storing operations dictionaries.
undo_stack = []
redo_stack = []

# List of (row, start, end) tuples marking search matches.
matches = []


# ---- Basic state getters used by main.py ----

def get_top_line():
    return top_line

def get_max_line():
    return MAX_LINE

def get_left_col():
    return left_col

def get_max_col():
    return MAX_COL


def remove_char_from_buffer(row_, col_):
    """
    Safely remove a character from a specific position in the buffer.
    This helper exists because many edits need the same logic,
    and manually slicing lists everywhere gets messy.
    """
    size = len(buffer[row_])
    if col_ < 0 or col_ >= size:
        return

    temp = []
    for i in range(size):
        if i != col_:
            temp.append(buffer[row_][i])

    buffer[row_] = temp


def move_cursor():
    """
    Convert logical cursor coordinates (row, col) into terminal coordinates,
    considering scroll offsets, and move the real terminal cursor there.
    """
    screen_row = row - top_line
    screen_col = col - left_col

    screen_row = max(0, min(screen_row, MAX_LINE - 1))
    screen_col = max(0, min(screen_col, MAX_COL - 1))

    sys.stdout.write("\033[%d;%dH" % (screen_row + 1, screen_col + 1))
    sys.stdout.flush()


def ensure_cursor_in_bounds():
    """
    After any edit, make sure row/col are still valid.
    Prevents cursor from drifting outside its line length.
    """
    global row, col

    row = max(0, min(row, len(buffer) - 1))
    line_len = len(buffer[row])

    if col < 0:
        col = 0
    if col > line_len:
        col = line_len


def adjust_top_line():
    """
    Scroll the viewport vertically so the cursor stays visible.
    """
    global top_line

    if len(buffer) <= MAX_LINE:
        top_line = 0
        return

    if row < top_line:
        top_line = row
    elif row > top_line + MAX_LINE - 1:
        top_line = row - (MAX_LINE - 1)

    top_line = max(0, min(top_line, len(buffer) - MAX_LINE))


def adjust_left_col():
    """
    Horizontal scrolling. Ensures that long lines are viewable
    and the cursor doesn't disappear off-screen horizontally.
    """
    global left_col

    line_len = len(buffer[row])
    if line_len <= MAX_COL:
        left_col = 0
        return

    if col < left_col:
        left_col = col
    elif col >= left_col + MAX_COL:
        left_col = col - MAX_COL + 1

    left_col = max(0, min(left_col, line_len - MAX_COL))


def handle_arrow_keys(key):
    """
    Arrow key navigation with sensible behavior across line boundaries.
    """
    global col, row

    if key.name == "up":
        if row > 0:
            row -= 1
            col = min(col, len(buffer[row]))

    elif key.name == "down":
        if row < len(buffer) - 1:
            row += 1
            col = min(col, len(buffer[row]))

    elif key.name == "left":
        if col > 0:
            col -= 1
        elif row > 0:
            row -= 1
            col = len(buffer[row])

    elif key.name == "right":
        line_len = len(buffer[row])
        if col < line_len:
            col += 1
        elif row < len(buffer) - 1:
            row += 1
            col = 0

    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()


def clear_screen():
    """Simple wrapper around system CLS/clear."""
    os.system('cls' if os.name == 'nt' else 'clear')


def append_key(key):
    """Insert a raw character at the cursor position."""
    buffer[row].insert(col, key.name)

def clear_buffer():
    """Clear buffer and reset cursor position."""
    global row, col, top_line, left_col
    buffer.clear()
    row = 0
    col = 0
    top_line = 0
    left_col = 0
    redo_stack.clear()
    undo_stack.clear()

def record_key(key):
    """
    Main entry point for all edits.
    This is where we translate a keyboard event into a mutation
    of the underlying buffer (with undo history).
    """
    global row, col

    if key.event_type == keyboard.KEY_UP:
        return

    if key.event_type == keyboard.KEY_DOWN:
        history.append(key.name)

    # Arrow keys and navigation
    if key.name in functional_keys_cursor:
        if keyboard.is_pressed('ctrl') and key.name == "left":
            move_word_left()
        elif keyboard.is_pressed('ctrl') and key.name == "right":
            move_word_right()
        elif key.name == "home":
            go_line_home()
        elif key.name == "end":
            go_line_end()
        elif key.name == "page up":
            page_up()
        elif key.name == "page down":
            page_down()
        else:
            handle_arrow_keys(key)
        return

    # Normal character input (anything not special)
    if key.event_type == keyboard.KEY_DOWN and key.name not in functional_keys_text:
        op = {"kind": "insert_char", "row": row, "col": col, "ch": key.name}
        apply_op(op, record_history=True)
        return

    # Space
    if key.name == "space":
        op = {"kind": "insert_char", "row": row, "col": col, "ch": " "}
        apply_op(op, record_history=True)
        return

    # Backspace
    if key.name == "backspace":
        if len(buffer[row]) > 0 and col > 0:
            ch = buffer[row][col - 1]
            op = {"kind": "delete_char", "row": row, "col": col - 1, "ch": ch}
            apply_op(op, record_history=True)

        elif col == 0 and row > 0:
            prev_len = len(buffer[row - 1])
            curr_line = buffer[row][:]
            op = {
                "kind": "join_line",
                "row": row - 1,
                "col": prev_len,
                "prev_len": prev_len,
                "curr": curr_line,
            }
            apply_op(op, record_history=True)
        return

    # Enter key splits the line
    if key.name == "enter":
        right = buffer[row][col:][:]
        op = {"kind": "split_line", "row": row, "col": col, "right": right}
        apply_op(op, record_history=True)
        return


def load_file(path):
    """
    Load disk file into buffer.
    Resets viewport and cursor.
    """
    global buffer, row, col, top_line, left_col

    buffer = []

    with open(path, "r") as f:
        for line in f:
            buffer.append(list(line.rstrip("\n")))

    if not buffer:
        buffer = [[]]

    row = 0
    col = 0
    top_line = 0
    left_col = 0
    redo_stack.clear()
    undo_stack.clear()

    return path


def apply_op(op, record_history=True):
    """
    General operation dispatcher.
    Every undoable action comes through here.
    """
    global row, col

    kind = op["kind"]

    if kind == "insert_char":
        buffer[op["row"]].insert(op["col"], op["ch"])
        row = op["row"]
        col = op["col"] + 1

    elif kind == "delete_char":
        r, c = op["row"], op["col"]
        if 0 <= r < len(buffer) and 0 <= c < len(buffer[r]):
            del buffer[r][c]
        row, col = r, c

    elif kind == "split_line":
        r, c = op["row"], op["col"]
        left = buffer[r][:c]
        right = op["right"][:]
        buffer[r] = left
        buffer.insert(r + 1, right)
        row, col = r + 1, 0

    elif kind == "join_line":
        r = op["row"]
        join_pos = op["col"]
        if r + 1 < len(buffer):
            buffer[r].extend(buffer[r + 1])
            del buffer[r + 1]
        row, col = r, join_pos

    elif kind == "replace":
        replace_all(op["search"], op["replace"])

    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()

    if record_history:
        undo_stack.append(op)
        redo_stack.clear()


def undo():
    """
    Reverse the last edit.
    Undo logic mirrors apply_op() but in reverse.
    """
    if not undo_stack:
        return

    op = undo_stack.pop()
    kind = op["kind"]

    if kind == "insert_char":
        r, c = op["row"], op["col"]
        del buffer[r][c]

    elif kind == "delete_char":
        buffer[op["row"]].insert(op["col"], op["ch"])

    elif kind == "split_line":
        r = op["row"]
        buffer[r].extend(buffer[r + 1])
        del buffer[r + 1]

    elif kind == "join_line":
        r = op["row"]
        prev_len = op["prev_len"]
        curr = op["curr"]
        left = buffer[r][:prev_len]
        buffer[r] = left
        buffer.insert(r + 1, curr[:])

    elif kind == "replace":
        replace_all(op["replace"], op["search"])

    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()

    # Allow redo
    redo_stack.append(op)


def redo():
    """
    Reapply the last undone operation.
    """
    if not redo_stack:
        return
    op = redo_stack.pop()
    apply_op(op, record_history=False)
    undo_stack.append(op)


def find_all_in_line(line_str, pattern):
    """Naive substring search used by search_all()."""
    out = []
    n, m = len(line_str), len(pattern)
    for i in range(n - m + 1):
        if line_str[i:i+m] == pattern:
            out.append(i)
    return out


def search_all(pattern):
    """
    Populate matches[] with all occurrences of `pattern`.
    main.py will use this to highlight search results.
    """
    global matches
    matches = []
    if not pattern:
        return

    plen = len(pattern)

    for row_, chars in enumerate(buffer):
        line_str = "".join(chars)
        for idx in find_all_in_line(line_str, pattern):
            matches.append((row_, idx, idx + plen))


def replace_all(pattern, replacement):
    """
    Simple (non-regex) global replace operation applied line-by-line.
    """
    if not pattern:
        return

    for i, line_chars in enumerate(buffer):
        line_str = "".join(line_chars)
        if pattern in line_str:
            buffer[i] = list(line_str.replace(pattern, replacement))


def go_line_home():
    global col
    col = 0
    ensure_cursor_in_bounds()
    adjust_left_col()


def go_line_end():
    global col
    col = len(buffer[row])
    ensure_cursor_in_bounds()
    adjust_left_col()


def move_word_left():
    """
    Jump left by a whole word (Ctrl+Left).
    """
    global row, col

    if col == 0 and row > 0:
        row -= 1
        col = len(buffer[row])
        ensure_cursor_in_bounds()
        adjust_top_line()
        adjust_left_col()
        return

    line = buffer[row]
    if not line or col == 0:
        return

    i = col - 1
    while i >= 0 and line[i].isspace():
        i -= 1
    while i >= 0 and not line[i].isspace():
        i -= 1

    col = i + 1
    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()


def move_word_right():
    """
    Jump right by a whole word (Ctrl+Right).
    """
    global row, col

    line = buffer[row]
    n = len(line)

    if col >= n and row < len(buffer) - 1:
        row += 1
        col = 0
        line = buffer[row]
        n = len(line)

    i = col
    while i < n and line[i].isspace():
        i += 1
    while i < n and not line[i].isspace():
        i += 1

    col = i
    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()


def page_up():
    """
    Moves up by an entire page (viewport height).
    """
    global row
    row = max(0, row - MAX_LINE)
    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()


def page_down():
    """
    Moves down by an entire page (viewport height).
    """
    global row
    row = min(len(buffer) - 1, row + MAX_LINE)
    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()
