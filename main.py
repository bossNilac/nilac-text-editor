from operator import index

from buffer_op import buffer, record_key, clear_screen, move_cursor

functional_keys_text = {"space", "backspace", "enter"}
functional_keys_cursor = {"up", "down", "left", "right"}

x_limit = 50

def print_buffer():
    string = ""
    for i in range(len(buffer)):
        string = string + buffer[i]
    print(string)

def main():
    while True:
        try:# making a loop
            record_key()
            print_buffer()
            move_cursor()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    clear_screen()
    main()