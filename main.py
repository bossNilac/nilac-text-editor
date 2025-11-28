# This file contains the high-level control flow of the editor.
# It manages rendering, hotkeys, file I/O, and interaction with buffer_op,
# which handles the actual text buffer and cursor state.

import configparser
import time

import keyboard

import buffer_op
from buffer_op import clear_screen, move_cursor

# Keys that produce characters vs keys that move the cursor.
# These sets help the editor decide whether a key inserts text or navigates.
functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right", "home", "end", "page up", "page down"}

# Path of the currently opened file (None when unsaved).
file_name = None
status = None

# Editor reads/writes the most recently opened file to editor.ini.
config_parser = configparser.ConfigParser()

# ANSI escape sequences used to highlight matches during search mode.
HIGHLIGHT_START = "\033[43m"   # yellow background
HIGHLIGHT_END   = "\033[0m"

# When True, render() shows highlighted search results.
search_mode = False


def print_buffer():
    """
    Draw the portion of the buffer currently visible in the viewport.
    This editor only renders what fits on screen to keep things fast
    and avoid flickering.
    """
    start = buffer_op.get_top_line()
    end = min(start + buffer_op.get_max_line(), len(buffer_op.buffer))

    from_col = buffer_op.get_left_col()
    to_col = from_col + buffer_op.get_max_col()

    # Render each visible line, cropped horizontally
    for i in range(start, end):
        full_line = "".join(buffer_op.buffer[i])
        visible = full_line[from_col:to_col]
        print(visible)

    # Print blank lines to fill the screen if buffer is shorter
    for _ in range(end, start + buffer_op.get_max_line()):
        print("")


def render():
    """
    Clear the screen and redraw the entire editor UI.
    This includes the text viewport, status bar, and moving
    the cursor to its correct terminal position.
    """
    global file_name, status, search_mode
    clear_screen()

    if search_mode:
        print_search_buffer()
    else:
        print_buffer()

    display_name = file_name if file_name else "No Name"

    print(
        "-- FILE EDITOR -- STATUS:[%s] -- [%s] Ln %d, Col %d "
        "Ctrl+O Open Ctrl+S Save Ctrl+Q Quit" %
        (status, display_name, buffer_op.row, buffer_op.col)
    )

    # Restore terminal cursor to logical editor cursor.
    move_cursor()


def render_line(row_index, chars, from_col):
    """
    Helper used only when the editor is in search mode.
    Draws a single line with highlighted matches.

    row_index: index in the real buffer
    chars: visible portion of that row
    from_col: starting column of the viewport (to adjust highlighting)
    """
    line_matches = [(s, e) for (row, s, e) in buffer_op.matches if row == row_index]

    if not line_matches:
        print("".join(chars))
        return

    line = ""
    i = 0

    # Apply highlighting around matched segments
    for (start, end) in sorted(line_matches):
        local_start = start - from_col
        local_end   = end   - from_col

        if local_end <= 0 or local_start >= len(chars):
            continue  # totally outside the viewport

        local_start = max(0, local_start)
        local_end   = min(len(chars), local_end)

        line += "".join(chars[i:local_start])
        line += HIGHLIGHT_START + "".join(chars[local_start:local_end]) + HIGHLIGHT_END
        i = local_end

    line += "".join(chars[i:])
    print(line)


def print_search_buffer():
    """
    Like print_buffer(), but uses render_line() so that
    matched search results appear highlighted.
    """
    start = buffer_op.get_top_line()
    end = min(start + buffer_op.get_max_line(), len(buffer_op.buffer))

    from_col = buffer_op.get_left_col()
    to_col = from_col + buffer_op.get_max_col()

    for row in range(start, end):
        visible = buffer_op.buffer[row][from_col:to_col]
        render_line(row, visible, from_col)


def render_search():
    """
    Separate rendering path specifically used during replace-all
    operations or search mode. Keeps UI consistent.
    """
    global file_name, status
    clear_screen()
    print_search_buffer()

    display_name = file_name if file_name else "No Name"

    print(
        """-- FILE EDITOR -- STATUS:[%s] -- [%s] Ln %d, Col %d 
        Ctrl+O Open Ctrl+S Save Ctrl+Q Quit
        Ctrl+Z Undo Ctrl+Y Redo Ctrl+/ Search Ctrl+R Replace Ctrl+Left/Right word jump""" %
        (status, display_name, buffer_op.row, buffer_op.col)
    )
    move_cursor()


def load_config():
    """
    On startup, try to restore the last opened file.
    If the ini file doesn’t exist or is corrupt, just start empty.
    """
    global file_name, config_parser, status
    try:
        config_parser.read("editor.ini")
        path = config_parser.get("editor", "path")
    except Exception:
        path = None

    if path:
        file_name = buffer_op.load_file(path)
        status = "SAVED"
    else:
        status = "UNSAVED"


def save_config():
    """
    Writes the currently opened file path to editor.ini.
    Nothing fancy, just a single key.
    """
    global file_name, config_parser
    if file_name is None:
        return

    config_parser["editor"] = {"path": file_name}

    with open("editor.ini", "w") as configfile:
        config_parser.write(configfile)


def open_file():
    """
    Prompt user for a path and attempt to load it.
    This intentionally loops until a valid file is entered.
    """
    global file_name, status
    while True:
        path = input("Enter file path: ")
        try:
            with open(path, "r"):
                pass
            break
        except OSError:
            print("File not found or cannot be opened. Try again.")

    file_name = path
    buffer_op.load_file(file_name)
    status = "SAVED"
    save_config()


def save_file():
    """
    Save the current buffer back to disk.
    If the user hasn't chosen a name yet, prompt for one.
    """
    global file_name, status

    if file_name is None:
        clear_screen()
        file_name = input("Enter filename: ")

    lines = ["".join(l) + "\n" for l in buffer_op.buffer]
    with open(file_name, "w") as f:
        f.writelines(lines)

    status = "SAVED"


def fix_ui():
    """
    Small hack: after reading a key event, the terminal can
    get out of sync visually. Sending ESC cleans up the state.
    """
    time.sleep(1)
    keyboard.send("esc")


def search_dialogue():
    """
    Ask user for a search string, switch into search mode, and highlight
    all matches immediately.
    """
    global search_mode
    search_string = input("Enter search criteria: ")
    search_mode = True
    buffer_op.search_all(search_string)


def replace_all_dialogue():
    """
    Full replace-all flow: prompt for search and replace terms,
    apply the operation (with undo support), and refresh highlights.
    """
    global search_mode

    search_string = input("Find: ")
    replace_string = input("Replace with: ")

    op = {
        "kind": "replace",
        "search": search_string,
        "replace": replace_string,
    }
    buffer_op.apply_op(op, record_history=True)

    # Optionally highlight the new text
    buffer_op.search_all(replace_string)
    search_mode = True


def main():
    """
    Core event loop of the editor.
    Reads keyboard events, handles hotkeys, and delegates
    all buffer modifications to buffer_op.
    """
    load_config()
    render()

    global status, search_mode

    while True:
        try:
            render()
            key = keyboard.read_event()

            # Ignore key releases for cleaner input handling
            if key.event_type == keyboard.KEY_UP:
                continue

            # Exit search mode with ESC
            if key.name == "esc" and search_mode:
                buffer_op.matches.clear()
                search_mode = False
                render()
                continue

            # Handle Ctrl hotkeys
            if keyboard.is_pressed("ctrl"):
                if key.name == "o":
                    clear_screen()
                    fix_ui()
                    open_file()
                    continue

                elif key.name == "s":
                    save_file()
                    fix_ui()
                    continue

                elif key.name == "q":
                    clear_screen()
                    fix_ui()
                    save_file()
                    save_config()
                    return

                elif key.name == "z":
                    buffer_op.undo()
                    continue

                elif key.name == "y":
                    buffer_op.redo()
                    continue

                elif key.name == "/":
                    clear_screen()
                    fix_ui()
                    search_dialogue()
                    continue

                elif key.name == "r":
                    clear_screen()
                    fix_ui()
                    replace_all_dialogue()
                    continue
                elif key.name == "n":
                    global file_name
                    clear_screen()
                    file_name = None
                    fix_ui()
                    buffer_op.clear_buffer()
                    save_file()
                    save_config()
                    load_config()
                    continue

            if key.name in {"ctrl", "shift"}:
                continue

            # Normal typing → send to buffer_op
            buffer_op.record_key(key)
            status = "UNSAVED"

        except KeyboardInterrupt:
            print("history", buffer_op.history)
            print("buffer", buffer_op.buffer)
            break


if __name__ == "__main__":
    clear_screen()
    main()
