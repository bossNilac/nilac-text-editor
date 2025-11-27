import keyboard
import os
import sys

functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right"}

history = []

buffer = [[]]
row = 0
col = 0


top_line = 0
MAX_LINE = 24

left_col = 0       # first visible column
MAX_COL = 120       # how many columns you want to show (tweak to your terminal)

undo_stack = []
redo_stack = []

matches = []




def get_top_line():
    return top_line

def get_max_line():
    return MAX_LINE

def get_left_col():
    return left_col

def get_max_col():
    return MAX_COL


def remove_char_from_buffer(row_, col_):
    # remove the character AT index col_ in line row_
    size = len(buffer[row_])
    if col_ < 0 or col_ >= size:   # <<< prevent out-of-range
        return
    temp_line = []
    for i in range(size):
        if i != col_:
            temp_line.append(buffer[row_][i])
    buffer[row_] = temp_line


def move_cursor():
    # map logical (row, col) to screen coordinates using scrolling
    screen_row = row - top_line       # 0-based
    screen_col = col - left_col       # 0-based

    # clamp vertically
    if screen_row < 0:
        screen_row = 0
    if screen_row >= MAX_LINE:
        screen_row = MAX_LINE - 1

    # clamp horizontally
    if screen_col < 0:
        screen_col = 0
    if screen_col >= MAX_COL:
        screen_col = MAX_COL - 1

    sys.stdout.write("\033[%d;%dH" % (screen_row + 1, screen_col + 1))
    sys.stdout.flush()



def handle_end_line(key):
    # this function will almost never fire with your huge x_limit,
    # but we'll keep it mostly as you had it
    increase_y()
    global col
    col = 0
    print(row, col)
    if row > len(buffer) - 1:
        buffer.append([])

    if key.name == "space":
        buffer[row].append(" ")
    else:
        append_key(key)

def ensure_cursor_in_bounds():
    """Keep (row, col) valid inside the buffer."""
    global row, col

    # clamp row
    if row < 0:
        row = 0
    if row >= len(buffer):
        row = len(buffer) - 1

    # clamp col to line length
    line_len = len(buffer[row])
    if col < 0:
        col = 0
    if col > line_len:
        col = line_len

def adjust_top_line():
    global top_line

    if len(buffer) <= MAX_LINE:
        top_line = 0
        return

    if row < top_line:
        top_line = row
    elif row > top_line + MAX_LINE - 1:
        top_line = row - (MAX_LINE - 1)

    # clamp
    max_top = len(buffer) - MAX_LINE
    if top_line < 0:
        top_line = 0
    if top_line > max_top:
        top_line = max_top

def adjust_left_col():
    global left_col

    line_len = len(buffer[row])

    # If line fits entirely in the window, always show from the start
    if line_len <= MAX_COL:
        left_col = 0
        return

    # If cursor is left of the window, scroll left
    if col < left_col:
        left_col = col

    # If cursor is right of the window, scroll right
    elif col >= left_col + MAX_COL:
        left_col = col - MAX_COL + 1

    # Don't let the window start beyond the last possible position
    max_left = max(0, line_len - MAX_COL)
    if left_col > max_left:
        left_col = max_left

    if left_col < 0:
        left_col = 0



def handle_arrow_keys(key):
    global col, row

    if key.name == "up":
        # don't let row go below 0
        if row > 0:               # <<< fixed condition
            row -= 1              # <<< use row-1
            # clamp col to line length
            if col > len(buffer[row]):   # <<< keep col valid
                col = len(buffer[row])

    elif key.name == "down":
        # don't go below last line
        if row < len(buffer) - 1:        # <<< prevent out-of-range
            row += 1
            if col > len(buffer[row]):   # <<< clamp col
                col = len(buffer[row])


    elif key.name == "left":
        if col > 0:
            col -= 1                     # <<< simple left move
        elif row > 0:
            # go to end of previous line
            row -= 1                     # <<< previous line
            col = len(buffer[row])       # <<< end of that line

    elif key.name == "right":
        line_len = len(buffer[row])      # <<< get line length
        if col < line_len:
            col += 1                     # move right in same line
        elif row < len(buffer) - 1:
            # go to start of next line
            row += 1
            col = 0
    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def append_key(key):
    # insert at the cursor column, not at the end
    buffer[row].insert(col, key.name)



def increase_x():
    global col
    col = col + 1


def decrease_x():
    global col
    col = col - 1


def increase_y():
    global row
    row = row + 1


def decrease_y():
    global row
    row = row - 1


def record_key(key):
    global row, col, buffer

    # ignore key releases
    if key.event_type == keyboard.KEY_UP:
        return

    if key.event_type == keyboard.KEY_DOWN:
        history.append(key.name)

    # cursor movement
    if key.name in functional_keys_cursor:
        handle_arrow_keys(key)
        return

    # --- normal character insert (NOT space, enter, backspace) ---
    if key.event_type == keyboard.KEY_DOWN and key.name not in functional_keys_text:
        ch = key.name
        op = {
            "kind": "insert_char",
            "row": row,
            "col": col,
            "ch": ch,
        }
        apply_op(op, record_history=True)
        return

    # --- SPACE ---
    if key.name.lower() == "space":
        op = {
            "kind": "insert_char",
            "row": row,
            "col": col,
            "ch": " ",
        }
        apply_op(op, record_history=True)
        return

    # --- BACKSPACE ---
    if key.name.lower() == "backspace":
        # delete character before cursor
        if len(buffer[row]) > 0 and col > 0:
            ch = buffer[row][col - 1]
            op = {
                "kind": "delete_char",
                "row": row,
                "col": col - 1,
                "ch": ch,
            }
            apply_op(op, record_history=True)

        # at start of line: join with previous line
        elif col == 0 and row > 0:
            prev_len = len(buffer[row - 1])
            curr_line = buffer[row][:]   # copy current line

            op = {
                "kind": "join_line",
                "row": row - 1,          # previous line index
                "col": prev_len,         # join point
                "prev_len": prev_len,
                "curr": curr_line,
            }
            apply_op(op, record_history=True)

        return

    # --- ENTER ---
    if key.name.lower() == "enter":
        line = buffer[row]
        right = line[col:][:]   # chars that move to new line

        op = {
            "kind": "split_line",
            "row": row,
            "col": col,
            "right": right,
        }
        apply_op(op, record_history=True)
        return

def load_file(path):
    global buffer, row, col, top_line, left_col

    buffer = []

    with open(path, "r") as f:
        for line in f:
            # strip newline, keep text
            line = line.rstrip("\n")
            buffer.append(list(line))

    # if file is empty, keep one empty line
    if not buffer:
        buffer = [[]]

    # reset cursor and viewport
    row = 0
    col = 0
    top_line = 0
    left_col = 0

    return path  # so main can store it in file_name

def apply_op(op, record_history=True):
    """
    op: dict with keys:
      kind: "insert_char" | "delete_char" | "split_line" | "join_line"
      row, col
      ch (for char ops)
      right (for split_line: list of chars that moved to next line)
      prev_len, curr (for join_line)
    """
    global row, col, buffer,top_line, left_col

    kind = op["kind"]

    if kind == "insert_char":
        r = op["row"]
        c = op["col"]
        ch = op["ch"]
        buffer[r].insert(c, ch)
        row = r
        col = c + 1

    elif kind == "delete_char":
        r = op["row"]
        c = op["col"]
        if 0 <= r < len(buffer) and 0 <= c < len(buffer[r]):
            del buffer[r][c]
        row = r
        col = c

    elif kind == "split_line":
        r = op["row"]
        c = op["col"]
        right = op["right"]  # list of chars

        line = buffer[r]
        left = line[:c]
        buffer[r] = left
        buffer.insert(r + 1, right[:])  # copy

        row = r + 1
        col = 0

    elif kind == "join_line":
        r = op["row"]        # index of previous line
        join_col = op["col"] # where the join happened

        if r + 1 < len(buffer):
            buffer[r].extend(buffer[r + 1])
            del buffer[r + 1]

        row = r
        col = join_col

    elif kind == "replace":
        search = op["search"]
        replacement = op["replace"]
        replace_all(search, replacement)

    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()

    if record_history:
        undo_stack.append(op)
        redo_stack.clear()

def undo():
    global row, col

    if not undo_stack:
        return

    op = undo_stack.pop()
    kind = op["kind"]

    if kind == "insert_char":
        # undo = delete the char we inserted
        r = op["row"]
        c = op["col"]
        if 0 <= r < len(buffer) and 0 <= c < len(buffer[r]):
            del buffer[r][c]
        row = r
        col = c

    elif kind == "delete_char":
        # undo = reinsert the deleted char
        r = op["row"]
        c = op["col"]
        ch = op["ch"]
        buffer[r].insert(c, ch)
        row = r
        col = c + 1

    elif kind == "split_line":
        # undo Enter = join lines back
        r = op["row"]
        if r + 1 < len(buffer):
            buffer[r].extend(buffer[r + 1])
            del buffer[r + 1]
        row = r
        col = op["col"]

    elif kind == "join_line":
        # undo backspace-at-start = split lines again
        r = op["row"]
        prev_len = op["prev_len"]
        curr = op["curr"]  # list of chars that used to be the second line

        line = buffer[r]
        left = line[:prev_len]
        buffer[r] = left
        buffer.insert(r + 1, curr[:])

        row = r + 1
        col = 0
    elif kind == "replace":
        search = op["search"]
        replacement = op["replace"]
        replace_all(replacement, search)

    ensure_cursor_in_bounds()
    adjust_top_line()
    adjust_left_col()

    # so we can redo
    redo_stack.append(op)


def redo():
    if not redo_stack:
        return
    op = redo_stack.pop()
    # re-apply the original op
    apply_op(op, record_history=False)
    undo_stack.append(op)

def find_all_in_line(line_str: str, pattern: str):
    res = []
    n = len(line_str)
    m = len(pattern)

    for i in range(n - m + 1):
        if line_str[i:i+m] == pattern:
            res.append(i)
    return res

def search_all(pattern: str):
    global matches
    matches = []
    if not pattern:
        return

    plen = len(pattern)

    for row_, line_chars in enumerate(buffer):
        line_str = "".join(line_chars)
        positions = find_all_in_line(line_str, pattern)
        for idx in positions:
            matches.append((row_, idx, idx + plen))

def replace_all(pattern: str, replacement: str):
    """
    Replace all occurrences of `pattern` with `replacement` in the whole buffer.
    Does not currently integrate with undo; it's a bulk edit.
    """
    global buffer

    if not pattern:
        return

    for i, line_chars in enumerate(buffer):
        line_str = "".join(line_chars)
        if pattern in line_str:
            new_str = line_str.replace(pattern, replacement)
            buffer[i] = list(new_str)
