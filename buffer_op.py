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


# in buffer_op.py
def record_key(key):
    global row, col, buffer

    # ignore key releases for normal behavior
    if key.event_type == keyboard.KEY_UP:
        return

    if key.event_type == keyboard.KEY_DOWN:
        history.append(key.name)

    if key.name in functional_keys_cursor:
        handle_arrow_keys(key)
        return

    if key.event_type == keyboard.KEY_DOWN and key.name not in functional_keys_text:
        append_key(key)
        increase_x()
        ensure_cursor_in_bounds()
        adjust_top_line()
        adjust_left_col()
        return

    if key.name.lower() == 'space':
        buffer[row].insert(col, " ")
        increase_x()
        ensure_cursor_in_bounds()
        adjust_top_line()
        adjust_left_col()
        return

    if key.name.lower() == 'backspace':
        if len(buffer[row]) > 0 and col > 0:
            col -= 1
            remove_char_from_buffer(row, col)
        elif col == 0 and row > 0:
            prev_len = len(buffer[row - 1])
            buffer[row - 1].extend(buffer[row])
            buffer.pop(row)
            row -= 1
            col = prev_len

        ensure_cursor_in_bounds()
        adjust_top_line()
        adjust_left_col()
        return

    if key.name.lower() == 'enter':
        line = buffer[row]
        if col == len(line):
            buffer.insert(row + 1, [])
        else:
            before = line[:col]
            after = line[col:]
            buffer[row] = before
            buffer.insert(row + 1, after)

        row += 1
        col = 0
        ensure_cursor_in_bounds()
        adjust_top_line()
        adjust_left_col()
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
