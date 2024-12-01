# Amelia Sinclaire 2024
import argparse
import curses
import time
from enum import Enum
import itertools
import math
import random

import numpy as np

# TODO:
# timer
# record num wins and losses
# look up correct mine ratio
# add title screen that sets map difficulty
# fix color system
# de-couple numpy
# add help menu to show controls
# add config file to change controls
# add home/end pageup/down func to move around board easier
# add mouse support
# high score system (keep in config?) (w/ names)


class GameState(Enum):
    PLAYING = 0
    WON = 1
    LOST = 2


class Cell(Enum):
    BLANK = 0
    ONE = 1  # BLUE
    TWO = 2  # GREEN
    THREE = 3  # RED
    FOUR = 4  # NAVY
    FIVE = 5  # MAROON
    SIX = 6  # CYAN
    SEVEN = 7  # BLACK
    EIGHT = 8  # GRAY
    MINE = 9
    FLAG = 10
    QUESTION = 11
    UNOPENED = 12
    OPENED = 13

    def display(self, stdscr, display_format=None):
        match self:
            case self.BLANK:
                stdscr.addstr(' ')
            case self.MINE:
                stdscr.addstr('¤')
            case self.FLAG:
                if display_format:
                    stdscr.addstr('¶', display_format)
                else:
                    stdscr.addstr('¶')
            case self.QUESTION:
                stdscr.addstr('?')
            case self.UNOPENED:
                stdscr.addstr('■')
            case _:
                stdscr.addstr(f'{self.value}', curses.color_pair(int(self.value)))


class Board:
    neighbors = [x for x in itertools.product(range(-1, 2), range(-1, 2)) if x != (0, 0)]

    def __init__(self, width: int, height: int, mine_ratio: float) -> None:
        self.width = width
        self.height = height
        self.locations = list(itertools.product(range(self.height), range(self.width)))
        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)

        # self.real_board = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
        #               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
        #               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (self.height//2, self.width//2)
        self.death = (-1, -1)
        self.mines = []
        self.is_first_click = True
        self.state = GameState.PLAYING

    def reset(self) -> None:
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (self.height//2, self.width//2)
        self.death = (-1, -1)
        self.mines = []
        self.is_first_click = True
        self.state = GameState.PLAYING

    def populate(self) -> None:
        choices = [x for x in self.locations if x != self.cursor]
        self.mines = random.sample(choices, k=self.n_mines)
        for m in self.mines:
            self.real_board[m[0]][m[1]] = Cell.MINE

        for loc in self.locations:
            cell = self.real_board[loc]
            if cell == Cell.BLANK:
                self.real_board[loc] = Cell(self.count_mines(*loc))

    def in_bounds(self, coord: (int, int)) -> bool:
        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def count_mines(self, row: int, col: int) -> int:
        total = 0
        for n in Board.neighbors:
            loc = (row + n[0], col + n[1])
            if self.in_bounds(loc):
                total += 1 if self.real_board[loc[0], loc[1]] == Cell.MINE else 0
        return total

    def move_cursor(self, x: int, y: int) -> None:
        new_row = self.cursor[0] + y
        new_col = self.cursor[1] + x
        loc = (new_row, new_col)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
            self.cursor = loc

    def reveal_all(self) -> None:
        self.my_board = np.full((self.width, self.height), Cell.OPENED)

    def reveal(self) -> None:
        if self.is_first_click:
            self.populate()
            self.is_first_click = False

        row, col = self.cursor

        if not self.in_bounds(self.cursor) or self.state != GameState.PLAYING:
            return

        if self.my_board[row, col] == Cell.OPENED:
            return

        if self.real_board[row, col] == Cell.MINE:
            self.reveal_all()
            self.death = self.cursor
            self.state = GameState.LOST
            return

        if self.real_board[row, col] == Cell.BLANK:
            self.my_board[row, col] = Cell.OPENED
            # recursively reveal 8 surrounding cells
            temp = self.cursor
            for n in Board.neighbors:
                self.cursor = [sum(x) for x in zip((row, col), n)]
                self.reveal()
            self.cursor = temp
            return

        self.my_board[row, col] = Cell.OPENED
        self.check_win()
        return

    def check_win(self) -> None:
        won = sum(list(x).count(Cell.UNOPENED) + list(x).count(Cell.FLAG) for x in self.my_board) == self.n_mines
        if won:
            self.state = GameState.WON
            for m in self.mines:
                self.my_board[m[0], m[1]] = Cell.FLAG

    def flag(self) -> None:
        row, col = self.cursor
        if not self.in_bounds(self.cursor):
            return
        if self.my_board[row, col] == Cell.UNOPENED:
            self.my_board[row, col] = Cell.FLAG
            return
        if self.my_board[row, col] == Cell.FLAG:
            self.my_board[row, col] = Cell.UNOPENED
            return

    def display(self, stdscr: curses.window) -> None:
        selector_format = curses.A_BLINK | curses.color_pair(9) | curses.A_BOLD
        death_format = curses.A_BLINK | curses.color_pair(10) | curses.A_BOLD
        win_format = curses.A_BLINK | curses.color_pair(11) | curses.A_BOLD

        for rid, row in enumerate(self.my_board):
            for cid, cell in enumerate(row):
                if cell == Cell.OPENED:
                    cell = self.real_board[rid, cid]
                if self.cursor == (rid, cid) and self.state == GameState.PLAYING:
                    stdscr.addstr('[', selector_format)
                    cell.display(stdscr)
                    stdscr.addstr(']', selector_format)
                    continue
                if self.death == (rid, cid) and self.state == GameState.LOST:
                    stdscr.addstr('[', death_format)
                    cell.display(stdscr)
                    stdscr.addstr(']', death_format)
                    continue
                if cell == Cell.FLAG and self.state == GameState.WON:
                    stdscr.addstr('[', win_format)
                    cell.display(stdscr, win_format)
                    stdscr.addstr(']', win_format)
                    continue
                stdscr.addstr('[')
                cell.display(stdscr)
                stdscr.addstr(']')
            stdscr.addstr('\n')
        match self.state:
            case GameState.PLAYING:
                stdscr.addstr('Use arrow keys to move\n')
                stdscr.addstr('Press "F" to flag and "Space" to reveal')
            case GameState.LOST:
                stdscr.addstr('You Lose!\n')
                stdscr.addstr('Press "R" to restart')
            case GameState.WON:
                stdscr.addstr('You Win!\n')
                stdscr.addstr('Press "R" to restart')


def main(stdscr) -> None:
    min_width = 1
    min_height = 1
    default_width = 9
    default_height = 9
    parser = argparse.ArgumentParser()
    parser.add_argument('-W', '--width', default=default_width, type=int)
    parser.add_argument('-H', '--height', default=default_height, type=int)
    parser.add_argument('-r', '--ratio', default=None, type=float)
    args, _ = parser.parse_known_args()

    if args.width < min_width:
        raise Exception(f'Invalid width: {args.width}. Must be >= {min_width}')
    if args.height < min_height:
        raise Exception(f'Invalid height: {args.height}. Must be >= {min_height}')
    if args.ratio is not None and (args.ratio < 0 or args.ratio > 1):
        raise Exception(f'Invalid mine ratio: {args.ratio:.2f}. Must be between 0 and 1')

    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        if curses.can_change_color():
            curses.init_color(21, 0, 0, 1000)
            curses.init_pair(1, 21, -1)
            curses.init_color(76, 0, 500, 0)
            curses.init_pair(2, 76, -1)
            curses.init_color(196, 1000, 0, 0)
            curses.init_pair(3, 196, -1)
            curses.init_color(17, 0, 0, 500)
            curses.init_pair(4, 17, -1)
            curses.init_color(88, 500, 0, 0)
            curses.init_pair(5, 88, -1)
            curses.init_color(32, 0, 500, 500)
            curses.init_pair(6, 32, -1)
            curses.init_color(0, 0, 0, 0)
            curses.init_pair(7, 0, -1)
            curses.init_color(249, 500, 500, 500)
            curses.init_pair(8, 249, -1)
            curses.init_color(226, 1000, 1000, 0)  # selector
            curses.init_pair(9, 226, -1)
            curses.init_color(196, 1000, 0, 0)  # lose
            curses.init_pair(10, 196, -1)
            curses.init_color(46, 0, 1000, 0)  # win
            curses.init_pair(11, 46, -1)
        else:
            curses.init_pair(1, curses.COLOR_BLUE, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_YELLOW, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            curses.init_pair(6, curses.COLOR_CYAN, -1)
            curses.init_pair(7, curses.COLOR_BLACK, -1)
            curses.init_pair(8, curses.COLOR_WHITE, -1)
            curses.init_pair(9, curses.COLOR_YELLOW, -1)  # selector
            curses.init_pair(10, curses.COLOR_RED, -1)  # lose
            curses.init_pair(11, curses.COLOR_GREEN, -1)  # win

    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)

    if args.ratio is None:
        args.ratio = math.sqrt(args.width * args.height) / (args.width * args.height)
    board = Board(args.width, args.height, args.ratio)
    stdscr.clear()
    board.display(stdscr)

    while True:
        key = stdscr.getkey(0, 0)
        match key:
            case 'q':
                break
            case 'KEY_RIGHT':
                board.move_cursor(1, 0)
            case 'KEY_LEFT':
                board.move_cursor(-1, 0)
            case 'KEY_UP':
                board.move_cursor(0, -1)
            case 'KEY_DOWN':
                board.move_cursor(0, 1)
            case ' ':
                board.reveal()
            case 'f':
                board.flag()
            case 'r':
                if board.state != GameState.PLAYING:
                    board.reset()
        stdscr.clear()
        board.display(stdscr)
        stdscr.refresh()
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    curses.endwin()
    exit()


if __name__ == '__main__':
    curses.wrapper(main)
