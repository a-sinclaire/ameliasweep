# Amelia Sinclaire 2024
import argparse
import curses
from curses import wrapper
from enum import Enum
import itertools
import os
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
    def __init__(self, width: int, height: int, mine_ratio: float, stdscr: curses.window) -> None:
        self.width = width
        self.height = height
        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)

        self.stdscr = stdscr

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

    def display(self):
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
                            self.stdscr.addstr('[', selector_format)
                            self.stdscr.addstr(f'{str(cell)}')  # TODO color numbers
                            self.stdscr.addstr(']', selector_format)
                        else:
                            self.stdscr.addstr(f'[{str(cell)}]')  # TODO color numbers
                    self.stdscr.addstr('\n')
                self.stdscr.addstr('Use arrow keys to move\n')
                self.stdscr.addstr('Press "F" to flag and "Space" to reveal')
            case GameState.LOST:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.death[0] == cid and self.death[1] == rid:
                            self.stdscr.addstr('[', death_format)
                            self.stdscr.addstr(f'{str(cell)}')  # TODO color numbers
                            self.stdscr.addstr(']', death_format)
                        else:
                            self.stdscr.addstr(f'[{str(cell)}]')  # TODO color numbers
                    self.stdscr.addstr('\n')
                self.stdscr.addstr('You Lose!\n')
                self.stdscr.addstr('Press "R" to restart')
            case GameState.WON:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if cell == Cell.FLAG:
                            self.stdscr.addstr(f'[{str(cell)}]', win_format)  # TODO: winflag format
                        else:
                            self.stdscr.addstr(f'[{str(cell)}]')  # TODO color numbers
                    self.stdscr.addstr('\n')
                self.stdscr.addstr('You Win!\n')
                self.stdscr.addstr('Press "R" to restart')

    def __str__(self) -> str:
        # selector_format = f'{Format.BRIGHT_YELLOW}{Format.BOLD}{Format.BLINKING}'
        # death_format = f'{Format.BRIGHT_RED}{Format.BOLD}{Format.BLINKING}'
        # win_flag_format = f'{Format.BRIGHT_GREEN}{Format.BOLD}{Format.BLINKING}'
        output = ''
        match self.state:
            case GameState.PLAYING:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.cursor[0] == cid and self.cursor[1] == rid:
                            output += f'[{str(cell)}]'  # TODO: selector format
                        else:
                            output += f'[{str(cell)}]'
                    output += '\n'
                output += 'Use arrow keys to move\n'
                output += 'Press "F" to flag and "Space" to reveal'
            case GameState.LOST:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.death[0] == cid and self.death[1] == rid:
                            output += f'[{str(cell)}]'  # TODO: death format
                        else:
                            output += f'[{str(cell)}]'
                    output += '\n'
                output += 'You Lose!\n'
                output += 'Press "R" to restart'
            case GameState.WON:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if cell == Cell.FLAG:
                            output += f'[{str(cell)}]'  # TODO: winflag format
                        else:
                            output += f'[{str(cell)}]'
                    output += '\n'
                output += 'You Win!\n'
                output += 'Press "R" to restart'
        return output


def main() -> None:
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

    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)

    board = Board(args.width, args.height, 0.15, stdscr)
    stdscr.clear()
    board.display()

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
        board.display()
        stdscr.refresh()
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    curses.endwin()
    exit()

if __name__=='__main__':
    wrapper(main())