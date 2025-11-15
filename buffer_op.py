import keyboard
import os
import sys


functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right"}

x_limit = 51

buffer = []
mouse_position = [1, 1]


def move_cursor():
    row = mouse_position[1]
    col = mouse_position[0]
    sys.stdout.write("\033[%d;%dH" % (row, col))
    sys.stdout.flush()

def handle_end_line(key):
    increase_y()
    mouse_position[0] = 2
    buffer.append("\n")
    if key.name == "space":
        buffer.append(" ")
    else:
        append_key(key)

def handle_arrow_keys(key):
    if key.name == "up":
        decrease_y()
    elif key.name == "down":
        increase_y()
    elif key.name == "left":
        if mouse_position[0] < 1:
            mouse_position[0] = x_limit -1
            decrease_y()
        else:
            decrease_x()
    else:
        if mouse_position[0] >= x_limit:
            mouse_position[0] =1
            increase_y()
        else:
            increase_x()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def append_key(key):
    buffer.append(key.name)

def increase_x():
    mouse_position[0] = mouse_position[0] + 1

def decrease_x():
    mouse_position[0] = mouse_position[0] + -1

def increase_y():
    mouse_position[1] = mouse_position[1] + 1

def decrease_y():
    mouse_position[1] = mouse_position[1] - 1


def record_key():
    global mouse_position, buffer
    key = keyboard.read_event()
    if key.event_type == keyboard.KEY_UP:
        clear_screen()
        return
    if key.name in functional_keys_cursor:
        handle_arrow_keys(key)
        clear_screen()
        return
    if key.event_type == keyboard.KEY_DOWN and key.name not in functional_keys_text:
        if mouse_position[0] >= x_limit:
            handle_end_line(key)
        else:
            append_key(key)
            increase_x()
    elif key.name.lower() == 'space' :
        if mouse_position[0] >= x_limit:
            handle_end_line(key)
        else:
            buffer.append(" ")
            increase_x()
    elif key.name.lower() == 'backspace' :
        if len(buffer) > 0:
            pop = buffer.pop()
            if pop == "\n":
                mouse_position[0] = x_limit
                decrease_y()
            elif mouse_position[0] > 1:
                decrease_x()
    elif key.name.lower() == 'enter' :
        buffer.append("\n")
        increase_y()
    clear_screen()
