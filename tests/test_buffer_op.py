import os
import sys
import tempfile

import buffer_op


def reset_state():
    """Reset global editor state on buffer_op before each test."""
    buffer_op.buffer = [[]]
    buffer_op.row = 0
    buffer_op.col = 0
    buffer_op.top_line = 0
    buffer_op.left_col = 0
    buffer_op.undo_stack.clear()
    buffer_op.redo_stack.clear()
    buffer_op.matches.clear()
    buffer_op.history.clear()


def test_insert_char_and_undo_redo():
    reset_state()

    op = {"kind": "insert_char", "row": 0, "col": 0, "ch": "a"}
    buffer_op.apply_op(op, record_history=True)

    assert buffer_op.buffer == [["a"]]
    assert buffer_op.row == 0
    assert buffer_op.col == 1
    assert buffer_op.undo_stack  # operation recorded

    # undo should remove the char
    buffer_op.undo()
    assert buffer_op.buffer == [[]]
    assert buffer_op.row == 0
    assert buffer_op.col == 0

    # redo should reinsert the char
    buffer_op.redo()
    assert buffer_op.buffer == [["a"]]
    assert buffer_op.row == 0
    assert buffer_op.col == 1


def test_delete_char_and_undo():
    reset_state()

    buffer_op.buffer = [list("ab")]
    buffer_op.row = 0
    buffer_op.col = 2

    op = {"kind": "delete_char", "row": 0, "col": 1, "ch": "b"}
    buffer_op.apply_op(op, record_history=True)

    assert buffer_op.buffer == [list("a")]
    assert buffer_op.row == 0
    assert buffer_op.col == 1

    buffer_op.undo()
    assert buffer_op.buffer == [list("ab")]
    # after undo, cursor is restored to the delete position
    assert buffer_op.row == 0
    assert buffer_op.col == 1


def test_split_line_and_undo_join_line():
    reset_state()

    buffer_op.buffer = [list("hello world")]
    buffer_op.row = 0
    buffer_op.col = 5  # after 'hello'

    right = buffer_op.buffer[0][buffer_op.col:][:]
    op = {"kind": "split_line", "row": 0, "col": 5, "right": right}

    buffer_op.apply_op(op, record_history=True)

    assert buffer_op.buffer == [list("hello"), list(" world")]
    assert buffer_op.row == 1
    assert buffer_op.col == 0

    # undo should join the lines back
    buffer_op.undo()
    assert buffer_op.buffer == [list("hello world")]
    assert buffer_op.row == 0
    # undo places cursor back at the split point
    assert buffer_op.col == 5


def test_join_line_and_undo_split():
    reset_state()

    buffer_op.buffer = [list("abc"), list("def")]
    buffer_op.row = 1
    buffer_op.col = 0

    prev_len = len(buffer_op.buffer[0])
    curr_line = buffer_op.buffer[1][:]

    op = {
        "kind": "join_line",
        "row": 0,
        "col": prev_len,
        "prev_len": prev_len,
        "curr": curr_line,
    }

    buffer_op.apply_op(op, record_history=True)

    assert buffer_op.buffer == [list("abcdef")]
    assert buffer_op.row == 0
    assert buffer_op.col == prev_len

    buffer_op.undo()
    assert buffer_op.buffer == [list("abc"), list("def")]
    assert buffer_op.row == 0
    # after undo of join, cursor sits at end of first line
    assert buffer_op.col == prev_len


def test_search_all_finds_all_matches():
    reset_state()

    buffer_op.buffer = [list("hello world"), list("world hello")]
    buffer_op.search_all("world")

    # matches are (row, start, end)
    assert len(buffer_op.matches) == 2

    rows = {m[0] for m in buffer_op.matches}
    assert rows == {0, 1}

    # check concrete positions
    assert (0, 6, 11) in buffer_op.matches  # "world" in "hello world"
    assert (1, 0, 5) in buffer_op.matches   # "world" in "world hello"


def test_replace_all_replaces_pattern_everywhere():
    reset_state()

    buffer_op.buffer = [list("foo bar foo"), list("foo")]
    buffer_op.replace_all("foo", "x")

    assert buffer_op.buffer[0] == list("x bar x")
    assert buffer_op.buffer[1] == list("x")


def test_go_line_home_and_end():
    reset_state()

    buffer_op.buffer = [list("abcdef")]
    buffer_op.row = 0
    buffer_op.col = 3

    buffer_op.go_line_home()
    assert buffer_op.col == 0

    buffer_op.go_line_end()
    assert buffer_op.col == len(buffer_op.buffer[0])


def test_move_word_left_basic():
    reset_state()

    buffer_op.buffer = [list("hello  world")]
    buffer_op.row = 0
    # position cursor at end of line (after 'd')
    buffer_op.col = len(buffer_op.buffer[0])

    buffer_op.move_word_left()

    # should jump to beginning of 'world' (index 7 in "hello  world")
    assert buffer_op.col == 7
    assert buffer_op.row == 0


def test_move_word_right_basic():
    reset_state()

    buffer_op.buffer = [list("hello  world")]
    buffer_op.row = 0
    buffer_op.col = 0  # start at beginning of "hello"

    buffer_op.move_word_right()

    # from start of "hello", jump to after the word, at first space
    assert buffer_op.col == len("hello")


def test_page_up_and_down():
    reset_state()

    # create more lines than a single page
    buffer_op.buffer = [list(str(i)) for i in range(50)]
    buffer_op.row = 30

    # page up should move up by MAX_LINE rows
    buffer_op.page_up()
    assert buffer_op.row == max(0, 30 - buffer_op.MAX_LINE)

    # page down should move down by MAX_LINE rows but not past last line
    buffer_op.page_down()
    expected_row = min(len(buffer_op.buffer) - 1, buffer_op.row + buffer_op.MAX_LINE)
    assert buffer_op.row == expected_row


def test_clear_buffer_resets_state():
    reset_state()

    buffer_op.buffer = [list("abc"), list("def")]
    buffer_op.row = 1
    buffer_op.col = 2
    buffer_op.undo_stack.append({"kind": "insert_char"})
    buffer_op.redo_stack.append({"kind": "delete_char"})

    buffer_op.clear_buffer()

    assert buffer_op.buffer == []
    assert buffer_op.row == 0
    assert buffer_op.col == 0
    assert buffer_op.undo_stack == []
    assert buffer_op.redo_stack == []


def test_load_file_populates_buffer_and_resets_cursors():
    reset_state()

    fd, path = tempfile.mkstemp()
    os.close(fd)

    try:
        with open(path, "w") as f:
            f.write("line1\nline2\n")

        returned_path = buffer_op.load_file(path)

        assert returned_path == path
        assert buffer_op.buffer == [list("line1"), list("line2")]
        assert buffer_op.row == 0
        assert buffer_op.col == 0
        assert buffer_op.top_line == 0
        assert buffer_op.left_col == 0
        assert buffer_op.undo_stack == []
        assert buffer_op.redo_stack == []
    finally:
        os.remove(path)
