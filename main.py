import configparser  # your module
import sys
import time

import keyboard

import buffer_op
from buffer_op import clear_screen, move_cursor  # (optional; or just use buffer_op.clear_screen)


functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right"}

file_name = None
status = None
config_parser = configparser.ConfigParser()


def print_buffer():
    start = buffer_op.get_top_line()
    end = min(start + buffer_op.get_max_line(), len(buffer_op.buffer))

    from_col = buffer_op.get_left_col()          # first visible column
    to_col = buffer_op.get_left_col() + buffer_op.get_max_col()  # one past last visible column

    # print only visible lines
    for i in range(start, end):
        # join the whole logical line
        full_line = ""
        for ch in buffer_op.buffer[i]:
            full_line += ch

        # take only the visible slice
        visible = full_line[from_col:to_col]
        print(visible)

    # fill remaining screen lines with blanks
    for _ in range(end, start + buffer_op.get_max_line()):
        print("")


def render():
    global file_name,status
    clear_screen()
    print_buffer()
    if file_name is None:
        display_name = "No Name"
    else:
        display_name = file_name
    print(
        "-- FILE EDITOR -- STATUS:[%s] -- [%s] Ln %d, Col %d Ctrl+O Open Ctrl+S Save Ctrl+Q Quit"
        % (status, display_name, buffer_op.row, buffer_op.col)
    )
    move_cursor()


def load_config():
    """Load last opened file path from editor.ini and open it."""
    global file_name, config_parser,status
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
    """Save current file path into editor.ini."""
    global file_name, config_parser
    if file_name is None:
        return

    # keep it simple: single [editor] section with path
    config_parser['editor'] = {"path": file_name}

    with open("editor.ini", "w") as configfile:
        config_parser.write(configfile)


def open_file():
    """Prompt for a file path and load it into the buffer."""
    global file_name, status
    while True:
        path = input("Enter file path: ")
        try:
            # just try to open and close to verify
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
    global file_name,status

    if file_name is None:
        clear_screen()
        file_name = input("Enter filename: ")

    lines = ["".join(l) + "\n" for l in buffer_op.buffer]
    with open(file_name, "w") as f:
        f.writelines(lines)

    status = "SAVED"

def fix_ui():
    time.sleep(0.5)
    keyboard.send('esc')

def main():
    load_config()
    render()
    global status
    while True:
        try:
            render()
            key = keyboard.read_event()

            # ignore key releases for hotkeys as well
            if key.event_type == keyboard.KEY_UP:
                continue

            # detect Ctrl hotkeys
            if keyboard.is_pressed('ctrl'):
                if key.name == 'o':
                    clear_screen()
                    fix_ui()
                    open_file()
                    render()
                    continue
                elif key.name == 's':
                    save_file()
                    fix_ui()
                    render()
                    continue
                elif key.name == 'q':
                    clear_screen()
                    fix_ui()
                    save_file()
                    save_config()
                    return

            if key.name == 'ctrl' or key.name == 'shift':
                continue

            # otherwise, normal editor keys:
            buffer_op.record_key(key)
            status = "UNSAVED"
            render()

        except KeyboardInterrupt:
            print("history", buffer_op.history)
            print("buffer", buffer_op.buffer)
            break

if __name__ == "__main__":
    clear_screen()
    main()
