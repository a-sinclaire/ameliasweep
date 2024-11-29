# Amelia Sinclaire 2024
import argparse
import itertools
import os
import random
from enum import Enum, StrEnum
from itertools import combinations
from typing import Self

import numpy as np
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

# TODO:
# Win condition
# timer
# record num wins and losses
# look up correct mine ratio
# add title screen that sets map difficulty
# move formating into seperate file(?)

class Format:
    RESET = '\033[0m'

    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINKING = '\033[5m'
    INVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'

    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    DEFAULT = '\033[39m'

    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    MAROON = '\033[38;5;124m'
    NAVY ='\033[38;5;21m'
    GRAY = '\033[38;5;237m'


class GameState(Enum):
    PLAYING = 0
    WON = 1
    LOST = 2

class Cell(Enum):
    BLANK = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    MINE = 9
    FLAG = 10
    QUESTION = 11
    UNOPENED = 12
    OPENED = 13

    def __str__(self):
        match self:
            case self.BLANK:
                return ' '
            case self.MINE:
                return f'{Format.BOLD}¤{Format.RESET}'
            case self.FLAG:
                return '¶'
            case self.QUESTION:
                return '?'
            case self.ONE:
                return f'{Format.BOLD}{Format.BRIGHT_BLUE}{self.value}{Format.RESET}'
            case self.TWO:
                return f'{Format.BOLD}{Format.BRIGHT_GREEN}{self.value}{Format.RESET}'
            case self.THREE:
                return f'{Format.BOLD}{Format.BRIGHT_RED}{self.value}{Format.RESET}'
            case self.FOUR:
                return f'{Format.BOLD}{Format.NAVY}{self.value}{Format.RESET}'
            case self.FIVE:
                return f'{Format.BOLD}{Format.MAROON}{self.value}{Format.RESET}'
            case self.SIX:
                return f'{Format.BOLD}{Format.BRIGHT_CYAN}{self.value}{Format.RESET}'
            case self.SEVEN:
                return f'{Format.BOLD}{Format.BLACK}{self.value}{Format.RESET}'
            case self.EIGHT:
                return f'{Format.BOLD}{Format.GRAY}{self.value}{Format.RESET}'
            case self.UNOPENED:
                return f'■'
            case _:
                return f'[{self.value}]'


class Board:
    def __init__(self, width: int, height: int, mine_ratio: float) -> None:
        self.width = width
        self.height = height
        self.mine_ratio = mine_ratio

        # self.real_board = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
        #               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
        #               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (0, 0)
        self.death = (-1, -1)
        self.state = GameState.PLAYING
        self.is_first_click = True

    def reset(self):
        self.real_board = np.full((self.width, self.height), Cell.BLANK)
        self.my_board = np.full((self.width, self.height), Cell.UNOPENED)
        self.cursor = (0, 0)
        self.death = (-1, -1)
        self.state = GameState.PLAYING
        self.is_first_click = True

    def populate(self):
        x = self.cursor[0]
        y = self.cursor[1]
        if y < 0 or y >= self.height or x < 0 or x >= self.width:
            raise Exception(f'Click at ({x}, {y}) is out of bounds.')

        n_mines = round(self.width * self.height * self.mine_ratio)
        locations = list(itertools.product(range(0, self.width), range(0, self.height)))
        locations.remove(self.cursor)
        mines = random.choices(locations, k=n_mines)
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
        return

    def flag(self) -> None:
        if self.my_board[self.cursor[1]][self.cursor[0]] == Cell.UNOPENED:
            self.my_board[self.cursor[1]][self.cursor[0]] = Cell.FLAG
            return
        if self.my_board[self.cursor[1]][self.cursor[0]] == Cell.FLAG:
            self.my_board[self.cursor[1]][self.cursor[0]] = Cell.UNOPENED
            return

    def __str__(self):
        selector_format = f'{Format.BRIGHT_YELLOW}{Format.BOLD}{Format.BLINKING}'
        death_format = f'{Format.BRIGHT_RED}{Format.BOLD}{Format.BLINKING}'
        output = '\033[0;0H'  # draw at 0, 0
        match self.state:
            case GameState.PLAYING:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.cursor[0] == cid and self.cursor[1] == rid:
                            output += f'{selector_format}[{Format.RESET}{str(cell)}{selector_format}]{Format.RESET}'
                        else:
                            output += f'[{str(cell)}]'
                    output += '\n'
            case GameState.LOST:
                for rid, row in enumerate(self.my_board):
                    for cid, cell in enumerate(row):
                        if cell == Cell.OPENED:
                            cell = self.real_board[rid][cid]
                        if self.death[0] == cid and self.death[1] == rid:
                            output += f'{death_format}[{Format.RESET}{str(cell)}{death_format}]{Format.RESET}'
                        else:
                            output += f'[{str(cell)}]'
                    output += '\n'
                output += 'Press "R" to restart'
        return output


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
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

    board = Board(args.width, args.height, 0.15)
    cls()
    print(board)

    with keyboard.Events() as events:
        for event in events:
            if event.key == Key.esc:
                exit()
            if event.key == Key.right and isinstance(event, keyboard.Events.Release):
                cls()
                board.move_cursor(1, 0)
                print(board)
            elif event.key == Key.left and isinstance(event, keyboard.Events.Release):
                cls()
                board.move_cursor(-1, 0)
                print(board)
            elif event.key == Key.up and isinstance(event, keyboard.Events.Release):
                cls()
                board.move_cursor(0, -1)
                print(board)
            elif event.key == Key.down and isinstance(event, keyboard.Events.Release):
                cls()
                board.move_cursor(0, +1)
                print(board)
            elif event.key == Key.space and isinstance(event, keyboard.Events.Release):
                cls()
                board.reveal()
                print(board)
            elif event.key == KeyCode.from_char('f') and isinstance(event, keyboard.Events.Release):
                cls()
                board.flag()
                print(board)
            elif event.key == KeyCode.from_char('r') and isinstance(event, keyboard.Events.Release) and board.state == GameState.LOST:
                cls()
                board.reset()
                print(board)


if __name__=='__main__':
    main()