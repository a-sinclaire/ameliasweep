# Amelia Sinclaire 2024
import argparse
import curses
from enum import Enum
import itertools
import random

import numpy as np

# TODO:
# timer
# record num wins and losses
# look up correct mine ratio
# add title screen that sets map difficulty


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

    def display(self, stdscr, format=None):
        match self:
            case self.BLANK:
                stdscr.addstr(' ')
            case self.MINE:
                stdscr.addstr('¤')
            case self.FLAG:
                if format is None:
                    stdscr.addstr('¶')
                else:
                    stdscr.addstr('¶', format)
            case self.QUESTION:
                stdscr.addstr('?')
            case self.UNOPENED:
                stdscr.addstr('■')
            case _:
                stdscr.addstr(f'{self.value}', curses.color_pair(int(self.value)))
            # case _:
            #     stdscr.addstr(f'{self.value}')

    def __str__(self) -> str:
        match self:
            case self.BLANK:
                return ' '
            case self.MINE:
                return f'¤'
            case self.FLAG:
                return '¶'
            case self.QUESTION:
                return '?'
            case self.UNOPENED:
                return f'■'
            case _:
                return f'{self.value}'


class Board:
    def __init__(self, width: int, height: int, mine_ratio: float) -> None:
        self.width = width
        self.height = height
        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)

        # self.real_board = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
        #               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
        #               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (0, 0)
        self.death = (-1, -1)
        self.state = GameState.PLAYING
        self.is_first_click = True

    def reset(self) -> None:
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (0, 0)
        self.death = (-1, -1)
        self.state = GameState.PLAYING
        self.is_first_click = True

    def populate(self) -> None:
        locations = list(itertools.product(range(0, self.width), range(0, self.height)))
        locations.remove(self.cursor)
        mines = random.choices(locations, k=self.n_mines)
        for m in mines:
            self.real_board[m[1]][m[0]] = Cell.MINE

        for rid, row in enumerate(self.real_board):
            for cid, cell in enumerate(row):
                if cell == Cell.BLANK:
                    self.real_board[rid][cid] = Cell(self.count_mines(rid, cid))

    def count_mines(self, row: int, col: int) -> int:
        total = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                if 0 <= (row + i) < self.height and 0 <= (col + j) < self.width and not (i == 0 and j == 0):
                    total += 1 if self.real_board[row + i][col + j] == Cell.MINE else 0
        return total

    def move_cursor(self, x: int, y: int) -> None:
        new_x = self.cursor[0] + x
        new_y = self.cursor[1] + y
        if 0 <= new_x < self.width and 0 <= new_y < self.height:
            self.cursor = (new_x, new_y)

    def reveal_all(self) -> None:
        self.my_board = np.full((self.width, self.height), Cell.OPENED)

    def reveal(self, x: int = None, y: int = None) -> None:
        if self.is_first_click:
            self.populate()
            self.is_first_click = False
        x = self.cursor[0] if x is None else x
        y = self.cursor[1] if y is None else y
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            return

        if self.my_board[y][x] == Cell.OPENED:
            return
        if self.real_board[y][x] == Cell.BLANK:
            self.my_board[y][x] = Cell.OPENED
            # recursively reveal 8 surrounding cells
            self.reveal(x - 1, y - 1)
            self.reveal(x - 1, y + 0)
            self.reveal(x - 1, y + 1)
            self.reveal(x + 0, y - 1)
            self.reveal(x + 0, y + 1)
            self.reveal(x + 1, y - 1)
            self.reveal(x + 1, y + 0)
            self.reveal(x + 1, y + 1)
            return
        if self.real_board[y][x] == Cell.MINE:
            self.reveal_all()
            self.death = (x, y)
            self.state = GameState.LOST
            return
        self.my_board[y][x] = Cell.OPENED
        self.check_win()
        return

    def check_win(self) -> None:
        won = sum(list(x).count(Cell.UNOPENED) + list(x).count(Cell.FLAG) for x in self.my_board) == self.n_mines
        if won:
            self.state = GameState.WON
            for rid, row in enumerate(self.my_board):
                for cid, cell in enumerate(row):
                    if cell == Cell.UNOPENED:
                        self.my_board[rid][cid] = Cell.FLAG

    def flag(self) -> None:
        if self.my_board[self.cursor[1]][self.cursor[0]] == Cell.UNOPENED:
            self.my_board[self.cursor[1]][self.cursor[0]] = Cell.FLAG
            return
        if self.my_board[self.cursor[1]][self.cursor[0]] == Cell.FLAG:
            self.my_board[self.cursor[1]][self.cursor[0]] = Cell.UNOPENED
            return

    def display(self, stdscr: curses.window) -> None:
        selector_format = curses.A_BLINK | curses.color_pair(227) | curses.A_BOLD
        death_format = curses.A_BLINK | curses.color_pair(10) | curses.A_BOLD
        win_format = curses.A_BLINK | curses.color_pair(11) | curses.A_BOLD
        match self.state:
            case GameState.PLAYING:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.cursor[0] == cid and self.cursor[1] == rid:
                            stdscr.addstr('[', selector_format)
                            cell.display(stdscr)
                            stdscr.addstr(']', selector_format)
                        else:
                            stdscr.addstr('[')
                            cell.display(stdscr)
                            stdscr.addstr(']')
                    stdscr.addstr('\n')
                stdscr.addstr('Use arrow keys to move\n')
                stdscr.addstr('Press "F" to flag and "Space" to reveal')
            case GameState.LOST:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.death[0] == cid and self.death[1] == rid:
                            stdscr.addstr('[', death_format)
                            cell.display(stdscr)
                            stdscr.addstr(']', death_format)
                        else:
                            stdscr.addstr('[')
                            cell.display(stdscr)
                            stdscr.addstr(']')
                    stdscr.addstr('\n')
                stdscr.addstr('You Lose!\n')
                stdscr.addstr('Press "R" to restart')
            case GameState.WON:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if cell == Cell.FLAG:
                            stdscr.addstr('[', win_format)
                            cell.display(stdscr, win_format)
                            stdscr.addstr(']', win_format)
                        else:
                            stdscr.addstr('[')
                            cell.display(stdscr)
                            stdscr.addstr(']')
                    stdscr.addstr('\n')
                stdscr.addstr('You Win!\n')
                stdscr.addstr('Press "R" to restart')


def main(stdscr) -> None:
    min_width = 1
    min_height = 1
    default_width = 5
    default_height = 5
    parser = argparse.ArgumentParser()
    parser.add_argument('-W', '--width', default=default_width, type=int)
    parser.add_argument('-H', '--height', default=default_height, type=int)
    args, _ = parser.parse_known_args()

    if args.width <= 0:
        raise Exception(f'Invalid width: {args.width}. Must be >= {min_width}')
    if args.height <= 0:
        raise Exception(f'Invalid height: {args.height}. Must be >= {min_height}')

    # stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    if curses.can_change_color():
        # curses.init_color(1, 0, 0, 1000)
        curses.init_pair(1, curses.COLOR_BLUE, -1)
        # curses.init_color(2, 0, 1000, 0)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        # curses.init_color(3, 1000, 0, 0)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_BLACK, -1)
        curses.init_pair(8, curses.COLOR_WHITE, -1)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)

    board = Board(args.width, args.height, 0.15)
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
