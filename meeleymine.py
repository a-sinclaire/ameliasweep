# Amelia Sinclaire 2024
import argparse
import curses
import datetime
from enum import Enum
import itertools
import math
import random
import time
from typing import Any, List

import load_config
import load_highscore


# TODO:
# Features:
# no 50/50s

# Bugs:
# revert back to normal terminal colors on exit (wait for bug to be reproduced)
# don't resize terminal while inputting custom settings
# figure out how to deal with terminals that fuck the color up? idk.

# Other:
# make script to test mouse buttons, like done for keyboard in readme.
# make those scripts a bit better?
# make readme nicer
# load games from game_history file
# change config NO_FLASH to FLASH

# Stretch Goals:
# make mouse work for menu selection
# in game settings / config editor
# let user define own game modes other than the 3 basics


class Difficulty(Enum):
    BEGINNER = 0
    INTERMEDIATE = 1
    EXPERT = 2
    CUSTOM = 3

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class GameState(Enum):
    PLAYING = 0
    WON = 1
    LOST = 2
    PAUSED = 3


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
    UNOPENED = 11
    OPENED = 12

    def display(self, win: curses.window, symbols: {str: str},
                display_format=None) -> None:
        if display_format:
            win.addstr(symbols[self.name], display_format)
        else:
            color = curses.color_pair(int(self.value))
            win.addstr(symbols[self.name], color)

    def print(self, symbols):
        return symbols[self.name]

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented


def full(width: int, height: int, value: Any) -> [[Any]]:
    return [[value for _ in range(width)] for _ in range(height)]


class Board:
    neighbors = [x for x in itertools.product(range(-1, 2),
                                              range(-1, 2)) if x != (0, 0)]
    zero_time = datetime.datetime.today().replace(hour=0,
                                                  minute=0,
                                                  second=0,
                                                  microsecond=0)
    str_to_id = {'ONE': 1,
                 'TWO': 2,
                 'THREE': 3,
                 'FOUR': 4,
                 'FIVE': 5,
                 'SIX': 6,
                 'SEVEN': 7,
                 'EIGHT': 8,
                 'MINE': 9,
                 'FLAG': 10,
                 'UNOPENED': 11,
                 'SELECTOR': 12,
                 'LOSE': 13,
                 'WIN': 14,
                 'BG': 15,
                 'FG': 16}

    def __init__(self, width: int, height: int, mine_ratio: float,
                 difficulty: Difficulty, config: dict,
                 win: curses.window) -> None:
        self.width = width
        self.height = height
        self.locations = list(itertools.product(range(self.height),
                                                range(self.width)))
        self.full_width = self.width * 3

        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)
        self.mines = []
        self.moves = []

        self.difficulty = difficulty
        self.config = config
        self.no_flash = config['SETUP']['NO_FLASH']
        self.hs_config = config['HIGHSCORES']
        self.symbols = config["LOOK"]["SYMBOLS"]

        self.win = win

        self.start_time = None
        self.end_time = None
        self.cum_time = datetime.timedelta(0)
        self.score = datetime.timedelta(0)

        self.real_board = full(self.width, self.height, Cell.BLANK)
        self.my_board = full(self.width, self.height, Cell.UNOPENED)
        self.cursor = (self.height // 2, self.width // 2)
        self.death = (-1, -1)
        self.is_first_click = True

        self.state = GameState.PLAYING
        self.previous_state = self.state

    def reset(self) -> None:
        self.mines = []
        self.moves = []

        self.start_time = None
        self.end_time = None
        self.cum_time = datetime.timedelta(0)
        self.score = datetime.timedelta(0)

        self.real_board = full(self.width, self.height, Cell.BLANK)
        self.my_board = full(self.width, self.height, Cell.UNOPENED)
        self.cursor = (self.height // 2, self.width // 2)
        self.death = (-1, -1)
        self.is_first_click = True

        self.state = GameState.PLAYING
        self.previous_state = self.state

        if self.config['SEED'] is not None:
            random.seed(self.config['SEED'])

        # flash on reset
        if not self.no_flash:
            curses.flash()

    def pause(self) -> None:
        if self.state == GameState.PAUSED:
            # unpause
            if not self.is_first_click:
                self.start_time = datetime.datetime.now()
            self.state = self.previous_state
        else:
            # pause
            if not self.is_first_click:
                self.cum_time += (datetime.datetime.now() - self.start_time)
            self.previous_state = self.state
            self.state = GameState.PAUSED

    def in_bounds(self, coord: (int, int)) -> bool:
        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def count_mines(self, row: int, col: int) -> int:
        total = 0
        for n in Board.neighbors:
            loc = (row + n[0], col + n[1])
            if self.in_bounds(loc):
                total += self.real_board[loc[0]][loc[1]] == Cell.MINE
        return total

    def first_empty(self, locations: [(int, int)]) -> (int, int):
        for rid, row in enumerate(self.real_board):
            for cid, cell in enumerate(row):
                if (cell == Cell.BLANK
                        and (rid, cid) not in locations):
                    return rid, cid
        raise Exception('No where to move mines to!')

    def open_opening(self) -> None:
        # move all mines in adjacent squares
        locations = []
        for n_r, n_c in Board.neighbors:
            r = n_r + self.cursor[0]
            c = n_c + self.cursor[1]
            locations.append((r, c))
        locations.append(self.cursor)
        for r, c in locations:
            if self.in_bounds((r, c)):
                if self.real_board[r][c] == Cell.MINE:
                    self.mines.remove((r, c))
                    self.real_board[r][c] = Cell.BLANK
                    ro, co = self.first_empty(locations)
                    self.real_board[ro][co] = Cell.MINE
                    self.mines.append((ro, co))

    def populate(self) -> None:
        # set mines
        choices = [x for x in self.locations if x != self.cursor]
        if self.n_mines <= len(choices):
            self.mines = random.sample(choices, k=self.n_mines)
            for m_row, m_col in self.mines:
                self.real_board[m_row][m_col] = Cell.MINE
        else:
            for m_row, m_col in self.locations:
                self.mines.append((m_row, m_col))
                self.real_board[m_row][m_col] = Cell.MINE

        if self.config['SETUP']['OPEN_START']:
            self.open_opening()

        # populate numbers
        for loc in self.locations:
            cell = self.real_board[loc[0]][loc[1]]
            if cell == Cell.BLANK:
                self.real_board[loc[0]][loc[1]] = Cell(self.count_mines(*loc))

        self.start_time = datetime.datetime.now()

    def set_cursor_from_mouse(self, screen_x: int, screen_y: int) -> bool:
        if not self.state == GameState.PLAYING:
            return False
        # x and y are screen coordinates
        new_row = screen_y - 1  # two for timer
        new_col = (screen_x // 3)  # to account for [ ] style
        loc = (new_row, new_col)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
            self.cursor = loc
            return True
        return False

    def move_cursor(self, x: int, y: int) -> None:
        if not self.state == GameState.PLAYING:
            return
        new_row = self.cursor[0] + y
        new_col = self.cursor[1] + x
        if self.config['SETUP']['WRAP_AROUND']:
            loc = (new_row % self.height, new_col % self.width)  # wrap around
        else:
            loc = (new_row, new_col)
        if self.in_bounds(loc):
            self.cursor = loc

    def move_direction(self, direction: str) -> None:
        if not self.state == GameState.PLAYING:
            return
        if direction == 'LEFT':
            self.move_cursor(-1, 0)
        elif direction == 'RIGHT':
            self.move_cursor(1, 0)
        elif direction == 'UP':
            self.move_cursor(0, -1)
        elif direction == 'DOWN':
            self.move_cursor(0, 1)
        elif direction == 'HOME':
            self.cursor = (self.cursor[0], 0)
        elif direction == 'END':
            self.cursor = (self.cursor[0], self.width - 1)
        elif direction == 'CEILING':
            self.cursor = (0, self.cursor[1])
        elif direction == 'FLOOR':
            self.cursor = (self.height - 1, self.cursor[1])

    def update_highscores(self) -> bool:
        term_width, term_height = self.win.getmaxyx()
        if term_width > self.full_width:
            w = self.full_width
        else:
            w = self.width
        new_highscore = False

        # read in data
        real_highscores = load_highscore.load_real_highscores()

        # get only scores for the selected Difficulty level
        scores = load_highscore.get_scores_for_difficulty(real_highscores,
                                                          self.difficulty)

        # check if current score is better than any score in highscore list
        max_scores = self.hs_config.get(self.difficulty.name + '_MAX')
        if (any(self.score < s for s in scores)  # higher than any value
                or scores is None  # or list is empty
                or len(scores) < max_scores):  # or list is not full
            # NEW HIGH SCORE!
            new_highscore = True

            # Get player's name
            self.display()
            self.win.addstr(f'{"NEW HIGHSCORE!!!":^{w}}',
                            curses.A_BOLD
                            | curses.A_REVERSE
                            | curses.A_BLINK)
            name = raw_input(self.win, self.height + 7, 0,
                             prompt='Enter Name:')
            # remove invalid characters (white spaces and quotes)
            name = name.translate(str.maketrans('', '', ' \n\t\r\'"'))
            # force uppercase and enforce name char limit
            max_name_length = self.hs_config.get('MAX_NAME_LENGTH')
            if max_name_length != math.inf:
                name = name.upper()[:max_name_length]
            else:
                name = name.upper()

            load_highscore.add_and_save_scores(real_highscores,
                                               self.difficulty, name,
                                               self.score, max_scores)
        return new_highscore

    def write_game(self) -> None:
        out = 'Mines:\n'
        for m in self.mines:
            out += f'{m}\n'
        out += '\n'
        out += 'Moves:\n'
        for m in self.moves:
            out += f'{m}\n'

        with open('game_history.txt', 'w+') as f:
            f.write(out)

    def won(self) -> None:
        self.state = GameState.WON
        self.end_time = datetime.datetime.now()

        self.score = self.cum_time + (self.end_time - self.start_time)
        for m in self.mines:
            self.my_board[m[0]][m[1]] = Cell.FLAG

        # Update highscores
        if self.config['SEED'] is None:
            new_highscore = self.update_highscores()
            if new_highscore:
                self.show_highscores()

        # write out game:
        self.write_game()

    def check_win(self) -> None:
        if self.state != GameState.PLAYING:
            return
        won = sum(x.count(Cell.UNOPENED) + x.count(Cell.FLAG) for x in
                  self.my_board) == self.n_mines
        if won:
            self.won()

    def reveal_all(self) -> None:
        self.my_board = full(self.width, self.height, Cell.OPENED)

    def lose(self) -> None:
        self.state = GameState.LOST
        self.end_time = datetime.datetime.now()

        self.reveal_all()
        self.death = self.cursor
        if not self.no_flash:
            curses.flash()
            time.sleep(0.1)
            curses.flash()
            curses.flash()

        # write out game:
        self.write_game()

    def surrounding_flags(self, row: int, col: int) -> int:
        count = 0
        for n_r, n_c in Board.neighbors:
            if (self.in_bounds((n_r + row, n_c + col))
                    and self.my_board[n_r + row][n_c + col] == Cell.FLAG):
                count += 1
        return count

    def reveal(self, auto: bool = False) -> None:
        if not self.state == GameState.PLAYING:
            return
        if not self.in_bounds(self.cursor):
            return

        if self.is_first_click:
            self.populate()
            self.is_first_click = False

        row, col = self.cursor

        if isinstance(self.cursor, tuple):
            self.moves.append(self.cursor)

        # chording
        if (self.config['SETUP']['CHORDING']
                and Cell.ONE.value <= self.real_board[row][col].value <=
                Cell.EIGHT.value
                and self.my_board[row][col] == Cell.OPENED
                and not auto):
            if (self.surrounding_flags(row, col)
                    == self.real_board[row][col].value):
                # chord
                # recursively reveal 8 surrounding cells
                # * that are not flags
                temp = self.cursor
                for n in Board.neighbors:
                    self.cursor = [sum(x) for x in zip((row, col), n)]
                    if (self.in_bounds(self.cursor)
                            and self.my_board[self.cursor[0]][
                                self.cursor[1]] !=
                            Cell.FLAG):
                        self.reveal(auto=True)
                self.cursor = temp

        if self.my_board[row][col] == Cell.OPENED:
            return

        if self.real_board[row][col] == Cell.MINE:
            self.lose()
            return

        if self.real_board[row][col] == Cell.BLANK:
            self.my_board[row][col] = Cell.OPENED
            # recursively reveal 8 surrounding cells
            temp = self.cursor
            for n in Board.neighbors:
                self.cursor = [sum(x) for x in zip((row, col), n)]
                self.reveal(auto=True)
            self.cursor = temp
        else:
            self.my_board[row][col] = Cell.OPENED
        self.check_win()
        return

    def show_highscores(self) -> None:
        self.pause()

        # read in data
        highscores: [Difficulty, str, datetime.timedelta] = (
            load_highscore.load_highscores_for_difficulty(self.difficulty))

        highscores = load_highscore.convert_real_to_raw(highscores)

        max_scores = self.hs_config[f'{self.difficulty.name}_MAX']
        if max_scores == math.inf:
            max_scores = len(highscores)
        title_format = curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK
        # clear the screen
        self.win.clear()

        max_name_length = len(max(highscores, key=lambda x: len(x[1]))[1])

        # title
        w = len(str(len(highscores))) + max_name_length + 22
        self.win.addstr(f'{f"{self.difficulty.name} HIGH SCORES":^{w}}\n',
                        title_format)

        # list scores
        for idx, score in enumerate(highscores[:max_scores]):
            self.win.addstr(f'[')
            # do cute color matching for numbers
            num = idx + 1
            self.win.addstr(str(num), curses.color_pair((idx % 8) + 1))
            # add closing bracket with some spacing to make everything line up
            spaces = " " * (len(str(len(highscores))) - len(str(num)) + 2)
            self.win.addstr(f']{spaces}')

            # if we are showing the highscores after someone got a new one
            # then we will do our best to highlight their new score
            if f'{Board.zero_time + self.score:%H:%M:%S.%f}' == score[2]:
                self.win.addstr(
                    f'{score[1]:<{max_name_length}} | {score[2]}\n',
                    title_format)
            else:
                self.win.addstr(f'{score[1]:<{max_name_length}} |'
                                f' {score[2]}\n')
        self.win.nodelay(False)
        self.win.refresh()
        self.win.getch()
        self.win.nodelay(True)
        self.pause()

    def count_flags(self) -> int:
        count = 0
        for r, c in self.locations:
            if self.my_board[r][c] == Cell.FLAG:
                count += 1
        return count

    def flag(self) -> None:
        if self.state != GameState.PLAYING:
            return
        if not self.in_bounds(self.cursor):
            return

        row, col = self.cursor
        if self.my_board[row][col] == Cell.UNOPENED:
            self.my_board[row][col] = Cell.FLAG
            return
        if self.my_board[row][col] == Cell.FLAG:
            self.my_board[row][col] = Cell.UNOPENED
            return

    def display(self) -> None:
        if curses.has_colors():
            selector_format = (curses.A_BLINK
                               | curses.color_pair(Board.str_to_id[
                                                       'SELECTOR'])
                               | curses.A_BOLD)
            death_format = (curses.A_BLINK
                            | curses.color_pair(Board.str_to_id[
                                                    'LOSE'])
                            | curses.A_BOLD)
            win_format = (curses.A_BLINK
                          | curses.color_pair(Board.str_to_id[
                                                  'WIN'])
                          | curses.A_BOLD)
        else:
            selector_format = (curses.A_REVERSE
                               | curses.color_pair(Board.str_to_id[
                                                       'SELECTOR'])
                               | curses.A_BOLD)
            death_format = (curses.A_REVERSE
                            | curses.color_pair(Board.str_to_id[
                                                    'LOSE'])
                            | curses.A_BOLD)
            win_format = (curses.A_REVERSE
                          | curses.color_pair(Board.str_to_id[
                                                  'WIN'])
                          | curses.A_BOLD)

        term_height, term_width = self.win.getmaxyx()
        remaining = self.n_mines - self.count_flags()
        self.win.addstr(f'Remaining: {remaining}')
        if term_width > self.full_width:
            # show timer next
            if self.start_time is not None and self.state == GameState.PLAYING:
                _time = Board.zero_time + self.cum_time + (
                        datetime.datetime.now() - self.start_time)
            elif self.state == GameState.WON or self.state == GameState.LOST:
                _time = Board.zero_time + self.cum_time + (
                        self.end_time - self.start_time)
            else:
                _time = Board.zero_time + self.cum_time

            title_format = curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK
            time_str = f'{_time:%H:%M:%S.%f}'[:-4]
            self.win.addstr(f'{time_str:^{self.full_width}}\n')

            # display board
            for rid, row in enumerate(self.my_board):
                for cid, cell in enumerate(row):
                    if cell == Cell.OPENED:
                        cell = self.real_board[rid][cid]
                    # highlight cursor position
                    if self.cursor == (
                            rid, cid) and self.state == GameState.PLAYING:
                        self.win.addstr('[', selector_format)
                        cell.display(self.win, self.symbols)
                        self.win.addstr(']', selector_format)
                        continue
                    # highlight death location
                    if self.death == (
                            rid, cid) and self.state == GameState.LOST:
                        self.win.addstr('[', death_format)
                        cell.display(self.win, self.symbols)
                        self.win.addstr(']', death_format)
                        continue
                    # flash all flags if won
                    if cell == Cell.FLAG and self.state == GameState.WON:
                        self.win.addstr('[', win_format)
                        cell.display(self.win, self.symbols, win_format)
                        self.win.addstr(']', win_format)
                        continue
                    # otherwise normal cell display
                    self.win.addstr('[')
                    cell.display(self.win, self.symbols)
                    self.win.addstr(']')
                self.win.addstr('\n')
            self.win.addstr('\n')

            reset_key = control_str(self.config["CONTROLS"]["RESET"])
            if self.state == GameState.LOST:
                self.win.addstr(f'{"YOU LOSE!":^{self.full_width}}\n',
                                title_format)
                self.win.addstr(
                    f'{f"Press {reset_key} to reset.":^{self.full_width}}\n')
            elif self.state == GameState.WON:
                self.win.addstr(f'{"YOU WIN!":^{self.full_width}}\n',
                                title_format)
                self.win.addstr(
                    f'{f"Press {reset_key} to reset.":^{self.full_width}}\n')
        else:
            # show timer next
            if self.start_time is not None and self.state == GameState.PLAYING:
                _time = Board.zero_time + self.cum_time + (
                        datetime.datetime.now() - self.start_time)
            elif self.state == GameState.WON or self.state == GameState.LOST:
                _time = Board.zero_time + self.cum_time + (
                        self.end_time - self.start_time)
            else:
                _time = Board.zero_time + self.cum_time

            title_format = curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK
            time_str = f'{_time:%H:%M:%S.%f}'[:-4]
            self.win.addstr(f'{time_str:^{self.width}}\n')

            # display board
            for rid, row in enumerate(self.my_board):
                for cid, cell in enumerate(row):
                    if cell == Cell.OPENED:
                        cell = self.real_board[rid][cid]
                    # highlight cursor position
                    if self.cursor == (
                            rid, cid) and self.state == GameState.PLAYING:
                        cell.display(self.win, self.symbols, curses.A_REVERSE)
                        continue
                    # highlight death location
                    if self.death == (
                            rid, cid) and self.state == GameState.LOST:
                        cell.display(self.win, self.symbols)
                        continue
                    # flash all flags if won
                    if cell == Cell.FLAG and self.state == GameState.WON:
                        cell.display(self.win, self.symbols, win_format)
                        continue
                    # otherwise normal cell display
                    cell.display(self.win, self.symbols)
                self.win.addstr('\n')
            self.win.addstr('\n')

            reset_key = control_str(self.config["CONTROLS"]["RESET"])
            if self.state == GameState.LOST:
                self.win.addstr(f'{"YOU LOSE!":^{self.width}}\n',
                                title_format)
                self.win.addstr(
                    f'{f"Press {reset_key} to reset.":^{self.width}}\n')
            elif self.state == GameState.WON:
                self.win.addstr(f'{"YOU WIN!":^{self.width}}\n',
                                title_format)
                self.win.addstr(
                    f'{f"Press {reset_key} to reset.":^{self.width}}\n')


def init_colors(win: curses.window, colors: {str: dict}) -> None:
    str_to_id = Board.str_to_id
    defaults: {str, int} = colors['DEFAULT']
    rgbs: {str: [int]} = colors['RGB']

    if curses.has_colors():
        # initialize some basic colors
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            try:
                curses.init_pair(i + 1, i, -1)
            except (ValueError, curses.error):
                # sometimes error on Windows? idk. let's just ignore it
                pass

        if curses.can_change_color():
            # use rgb values
            # get BG color
            bg_color = rgbs.get('BG')
            fg_color = rgbs.get('FG')
            if bg_color and fg_color:
                # noinspection PyArgumentList
                curses.init_color(str_to_id['BG'], *bg_color)
                bg = str_to_id['BG']
                # noinspection PyArgumentList
                curses.init_color(str_to_id['FG'], *fg_color)
                fg = str_to_id['FG']
            elif bg_color:
                # noinspection PyArgumentList
                curses.init_color(str_to_id['BG'], *bg_color)
                bg = str_to_id['BG']
                fg = defaults['FG']
            elif fg_color:
                bg = defaults['BG']
                # noinspection PyArgumentList
                curses.init_color(str_to_id['FG'], *fg_color)
                fg = str_to_id['FG']
            else:
                bg = defaults['BG']
                fg = defaults['FG']
            try:
                curses.init_pair(str_to_id['BG'], fg, bg)
                win.bkgd(' ', curses.color_pair(str_to_id['BG']))
            except curses.error:
                pass


            for idx, (c_n, c_v) in enumerate(rgbs.items()):
                if c_n == 'BG' or c_n == 'FG':
                    continue
                my_color = defaults.get(c_n)
                if c_v is None:
                    try:
                        curses.init_pair(str_to_id[c_n], my_color, bg)
                    except curses.error:
                        pass
                    continue

                # noinspection PyArgumentList
                curses.init_color(str_to_id[c_n], *c_v)
                try:
                    curses.init_pair(str_to_id[c_n], str_to_id[c_n], bg)
                except curses.error:
                    pass
        else:
            bg = defaults['BG']
            try:
                curses.init_pair(str_to_id['BG'], defaults['FG'],
                             defaults['BG'])
                win.bkgd(' ', curses.color_pair(str_to_id['BG']))
            except curses.error:
                pass
            for idx, (c_n, c_v) in enumerate(defaults.items()):
                if c_n == 'BG' or c_n == 'FG':
                    continue
                try:
                    curses.init_pair(str_to_id[c_n], c_v, bg)
                except curses.error:
                    pass


class _Sentinel:
    pass


def setup(win: curses.window) -> None:
    # loading config
    config = load_config.load_config()
    load_highscore.generate_dummy_if_needed()

    # defaults and arg parse
    min_width = config['SETUP']['MIN_WIDTH']
    min_height = config['SETUP']['MIN_HEIGHT']
    max_width = config['SETUP']['MAX_WIDTH']
    max_height = config['SETUP']['MAX_HEIGHT']
    default_width = config['SETUP']['BEGINNER']['WIDTH']
    default_height = config['SETUP']['BEGINNER']['HEIGHT']
    default_ratio = config['SETUP']['BEGINNER']['RATIO']
    parser = argparse.ArgumentParser()
    parser.add_argument('-W', '--width', default=default_width, type=int)
    parser.add_argument('-H', '--height', default=default_height, type=int)
    parser.add_argument('-r', '--ratio', default=default_ratio, type=float)
    parser.add_argument('--no-flash', action='store_true',
                        default=config['SETUP']['NO_FLASH'])
    parser.add_argument('--seed', default=None, type=int)
    args = parser.parse_args()

    config['SEED'] = args.seed
    if args.seed is not None:
        random.seed(args.seed)

    # this is a way to check which values were actually passed in
    # https://stackoverflow.com/questions/58594956/find-out-which-arguments-were-passed-explicitly-in-argparse
    sentinel = _Sentinel
    sentinel_ns = argparse.Namespace(**{key: sentinel for key in vars(args)})
    parser.parse_args(namespace=sentinel_ns)

    explicit = argparse.Namespace(
        **{key: (value is not sentinel) for key, value in
           vars(sentinel_ns).items()})

    # verifies the values passed in via cli are appropriate
    if min_width and args.width < min_width:
        raise ValueError(
            f'Invalid width: {args.width}. Must be >= {min_width}')
    if min_height and args.height < min_height:
        raise ValueError(
            f'Invalid height: {args.height}. Must be >= {min_height}')
    if max_width and args.width > max_width:
        raise ValueError(
            f'Invalid width: {args.width}. Must be <= {max_width}')
    if max_height and args.height > max_height:
        raise ValueError(
            f'Invalid height: {args.height}. Must be <= {max_width}')
    if args.ratio is not None and (args.ratio < 0 or args.ratio > 1):
        raise ValueError(
            f'Invalid mine ratio: {args.ratio:.2f}. Must be between 0 and 1')
    config["SETUP"]["NO_FLASH"] = args.no_flash

    init_colors(win, config["LOOK"]['COLORS'])
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    win.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    # if the width or height or ratio is set from CLI this is a CUSTOM game,
    # and we can skip the main menu
    if explicit.width or explicit.height or explicit.ratio:
        if not explicit.ratio:
            args.ratio = math.sqrt(args.width * args.height) / (
                    args.width * args.height)
        board = Board(args.width, args.height, args.ratio, Difficulty.CUSTOM,
                      config, win)
        main_loop(win, board, config)
    else:
        splash(win, config)


# use curses to prompt the user for a response
# https://stackoverflow.com/a/21785167
def raw_input(win: curses.window, r: int, c: int, prompt: str) -> str:
    curses.echo()
    win.nodelay(False)
    win.addstr(r, c, prompt)
    win.refresh()
    inp = win.getstr(r + 1, c, 20)
    win.nodelay(True)
    return inp.decode()  # ^^^^  reading input at next line


def logo(win: curses.window) -> None:
    term_height, term_width = win.getmaxyx()
    options: [str] = [
        # formatter:off
        (f'\n'
         f'  ▄▄▄▄███▄▄▄▄      ▄████████    ▄████████  ▄█          ▄████████ '
         f'▄██   ▄     ▄▄▄▄███▄▄▄▄    ▄█  ███▄▄▄▄      ▄████████\n'
         f'▄██▀▀▀███▀▀▀██▄   ███    ███   ███    ███ ███         ███    ███ '
         f'███   ██▄ ▄██▀▀▀███▀▀▀██▄ ███  ███▀▀▀██▄   ███    ███\n'
         f'███   ███   ███   ███    █▀    ███    █▀  ███         ███    █▀  '
         f'███▄▄▄███ ███   ███   ███ ███▌ ███   ███   ███    █▀\n'
         f'███   ███   ███  ▄███▄▄▄      ▄███▄▄▄     ███        ▄███▄▄▄     '
         f'▀▀▀▀▀▀███ ███   ███   ███ ███▌ ███   ███  ▄███▄▄▄\n'
         f'███   ███   ███ ▀▀███▀▀▀     ▀▀███▀▀▀     ███       ▀▀███▀▀▀     '
         f'▄██   ███ ███   ███   ███ ███▌ ███   ███ ▀▀███▀▀▀\n'
         f'███   ███   ███   ███    █▄    ███    █▄  ███         ███    █▄  '
         f'███   ███ ███   ███   ███ ███  ███   ███   ███    █▄\n'
         f'███   ███   ███   ███    ███   ███    ███ ███▌    ▄   ███    ███ '
         f'███   ███ ███   ███   ███ ███  ███   ███   ███    ███\n'
         f' ▀█   ███   █▀    ██████████   ██████████ █████▄▄██   ██████████  '
         f'▀█████▀   ▀█   ███   █▀  █▀    ▀█   █▀    ██████████\n'
         f'                                          ▀\n'
         f'\n'),
        # formatter:on
        (f'\n'
         f'▗▖  ▗▖▗▞▀▚▖▗▞▀▚▖█ ▗▞▀▚▖▄   ▄ ▗▖  ▗▖▄ ▄▄▄▄  ▗▞▀▚▖\n'
         f'▐▛▚▞▜▌▐▛▀▀▘▐▛▀▀▘█ ▐▛▀▀▘█   █ ▐▛▚▞▜▌▄ █   █ ▐▛▀▀▘\n'
         f'▐▌  ▐▌▝▚▄▄▖▝▚▄▄▖█ ▝▚▄▄▖ ▀▀▀█ ▐▌  ▐▌█ █   █ ▝▚▄▄▖\n'
         f'▐▌  ▐▌          █      ▄   █ ▐▌  ▐▌█            \n'
         f'                        ▀▀▀                     \n'
         f'\n'),
        (f'\n'  # @formatter:off
         fr"  __  __         _          __  __ _          " + '\n'
         fr" |  \/  |___ ___| |___ _  _|  \/  (_)_ _  ___ " + '\n'
         fr" | |\/| / -_) -_) / -_) || | |\/| | | ' \/ -_)" + '\n'
         fr" |_|  |_\___\___|_\___|\_, |_|  |_|_|_||_\___|" + '\n'
         fr"                       |__/                   " + '\n'
         f'\n'),  # formatter:on
        (f'\n'
         f' _____         _         _____ _         \n'
         f'|     |___ ___| |___ _ _|     |_|___ ___ \n'
         f'| | | | -_| -_| | -_| | | | | | |   | -_|\n'
         f'|_|_|_|___|___|_|___|_  |_|_|_|_|_|_|___|\n'
         f'                    |___|                \n'
         f'\n'),
        (f'\n'
         f'╔╦╗┌─┐┌─┐┬  ┌─┐┬ ┬╔╦╗┬┌┐┌┌─┐\n'
         f'║║║├┤ ├┤ │  ├┤ └┬┘║║║││││├┤ \n'
         f'╩ ╩└─┘└─┘┴─┘└─┘ ┴ ╩ ╩┴┘└┘└─┘\n'
         f'\n'),
        (f'\n'
         f'┳┳┓    ┓    ┳┳┓•    \n'
         f'┃┃┃┏┓┏┓┃┏┓┓┏┃┃┃┓┏┓┏┓\n'
         f'┛ ┗┗ ┗ ┗┗ ┗┫┛ ┗┗┛┗┗ \n'
         f'           ┛        \n'
         f'\n'),
        f'\nMeeleyMine\n\n',
        f'\nMM\n\n']

    options.sort(key=lambda x: len(max(x.split('\n'))), reverse=True)

    for op in options:
        longest_line = max(op.split('\n'), key=len)
        if term_width > len(longest_line):
            for row in op:
                win.addstr(row)
            return


# used as a helper for help screen
def control_str(configs: [str]) -> str:
    out = ''
    for c in configs:
        if c is None:
            continue
        if c == ' ':
            c = 'SPACE'
        if c == '\n':
            c = 'ENTER'
        if out == '':
            out += f'[{c.upper()}]'
        else:
            out += f' OR [{c.upper()}]'
    out = out.strip()
    if out == '':
        return '{NO KEY SET}'
    return out


def show_help(win: curses.window, config: dict) -> None:
    controls = config["CONTROLS"]
    win.clear()
    win.addstr('HELP\n\n')
    longest_cmd = max(controls.keys(), key=len)
    for command in controls.keys():
        win.addstr(
            f'{command + ":":<{1 + len(longest_cmd)}} '
            f'{control_str(controls.get(command))}\n')


def display_sample(win: curses.window, config: dict) -> None:
    term_height, term_width = win.getmaxyx()
    symbols = config["LOOK"]["SYMBOLS"]
    display = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
    out1 = ''
    for row in display:
        for cell in row:
            out1 += '['
            out1 += cell.print(symbols)
            out1 += ']'
        out1 += '\n'
    if term_width > len(max(out1.split('\n'), key=len)):
        for row in display:
            for cell in row:
                win.addstr('[')
                cell.display(win, symbols)
                win.addstr(']')
            win.addstr('\n')
        return
    out2 = ''
    for row in display:
        for cell in row:
            out2 += cell.print(symbols)
        out2 += '\n'
    if term_width > len(max(out2.split('\n'), key=len)):
        for row in display:
            for cell in row:
                cell.display(win, symbols)
            win.addstr('\n')
        return
    return


def splash(win: curses.window, config: dict) -> None:
    beginner_width = config["SETUP"]["BEGINNER"]["WIDTH"]
    beginner_height = config["SETUP"]["BEGINNER"]["HEIGHT"]
    beginner_ratio = config["SETUP"]["BEGINNER"]["RATIO"]
    intermediate_width = config["SETUP"]["INTERMEDIATE"]["WIDTH"]
    intermediate_height = config["SETUP"]["INTERMEDIATE"]["HEIGHT"]
    intermediate_ratio = config["SETUP"]["INTERMEDIATE"]["RATIO"]
    expert_width = config["SETUP"]["EXPERT"]["WIDTH"]
    expert_height = config["SETUP"]["EXPERT"]["HEIGHT"]
    expert_ratio = config["SETUP"]["EXPERT"]["RATIO"]

    # read in highscore data
    raw_highscore_data = load_highscore.load_raw_highscores()

    total_list: [[[str, str, str]]] = []
    for difficulty in Difficulty:
        total_list.append([x for x in raw_highscore_data
                           if x[0] == difficulty.name])

    win.clear()
    logo(win)

    def show_option(d: Difficulty) -> None:
        term_height, term_width = win.getmaxyx()
        longest_d = max(Difficulty, key=lambda x: len(x.name))
        spaces = len(longest_d.name)
        if len(total_list[d.value]) > 0:
            name = total_list[d.value][0][1]
            score = total_list[d.value][0][2]
        else:
            name = None
            score = None
        options: [(str, bool, bool, bool)] = []
        try:
            w = config['SETUP'][d.name]['WIDTH']
            h = config['SETUP'][d.name]['HEIGHT']
            r = config['SETUP'][d.name]['RATIO']
        except KeyError:
            w = -1
            h = -1
            r = -1

        options.append((f'{d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {name} {score}\n', True, True, True))
        options.append((f'{d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {score}\n', True, True, True))
        options.append((f'{d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {name}\n', True, True, True))
        options.append(
            (f'{d.name:<{spaces}} ({w}x{h}) | {r:.2%}\n', False, True, True))
        options.append(
            (f'{d.name:<{spaces}} ({w}x{h})\n', False, True, False))
        options.append((f'] {d.name:<{spaces}} | HS: {name} {score}\n', True,
                        False, False))
        options.append(
            (f'{d.name:<{spaces}} | HS: {score}\n', True, False, False))
        options.append(
            (f'{d.name:<{spaces}} | HS: {name}\n', True, False, False))
        options.append((f'{d.name}\n', False, False, False))
        options.append((f'{d.name[0]}\n', False, False, False))

        # options.sort(key=lambda x: len(x[0]), reverse=True)

        for (op, has_hs, has_wh, has_r) in options:
            if has_r and r == -1:
                continue
            if has_wh and w == -1 or has_hs and h == -1:
                continue
            if term_width >= len(op) + 2:
                if has_hs and len(total_list[d.value]) > 0:
                    win.addstr(op)
                    return
                elif not has_hs:
                    win.addstr(op)
                    return
                else:
                    continue

    if curses.has_colors():
        selector = (curses.A_BLINK
                    | curses.color_pair(Board.str_to_id['SELECTOR'])
                    | curses.A_BOLD)
    else:
        selector = (curses.A_REVERSE
                    | curses.color_pair(Board.str_to_id['SELECTOR'])
                    | curses.A_BOLD)

    menu_cursor = 0

    def display_options() -> [int, int]:
        # DISPLAY OPTIONS
        for diff in Difficulty:
            if diff.value == menu_cursor:
                win.addstr(f'[', selector)
            else:
                win.addstr(f'[')
            win.addstr(f'{diff.value + 1}', curses.color_pair((diff.value+1) % 8))
            if diff.value == menu_cursor:
                win.addstr(f'] ', selector)
            else:
                win.addstr(f'] ')
            show_option(diff)
        win.addstr('\n')
        if menu_cursor == 4:
            win.addstr(f'[', selector)
        else:
            win.addstr(f'[')
        exit_spot = win.getyx()
        win.addstr(f'5', curses.color_pair((len(
            Difficulty) + 1) % 8))
        if menu_cursor == 4:
            win.addstr(f'] ', selector)
        else:
            win.addstr(f'] ')
        win.addstr(f'Exit\n\n')
        return exit_spot
    exit_spot = display_options()

    # DISPLAY all symbols (useful if changing themes:)
    display_sample(win, config)

    win.refresh()

    # Handle user interaction (selecting difficulty)
    while True:
        try:
            key = win.getkey(0, 0)
        except curses.error:
            key = curses.ERR
        if key in config["CONTROLS"].get("EXIT"):
            raise SystemExit(0)
        if key in config['CONTROLS'].get('UP'):
            menu_cursor = (menu_cursor - 1) % 5
            win.clear()
            logo(win)
            exit_spot = display_options()
            # DISPLAY all symbols (useful if changing themes:)
            display_sample(win, config)
            win.refresh()
        if key in config['CONTROLS'].get('DOWN'):
            menu_cursor = (menu_cursor + 1) % 5
            win.clear()
            logo(win)
            exit_spot = display_options()
            # DISPLAY all symbols (useful if changing themes:)
            display_sample(win, config)
            win.refresh()
        if key == 'KEY_RESIZE':
            win.clear()
            logo(win)
            exit_spot = display_options()

            # DISPLAY all symbols (useful if changing themes:)
            display_sample(win, config)
            win.refresh()
        if (key == '1' or
                (menu_cursor == 0
                 and key in config['CONTROLS'].get('REVEAL'))):
            board = Board(int(beginner_width), int(beginner_height),
                          float(beginner_ratio), Difficulty.BEGINNER,
                          config, win)
            break
        elif (key == '2' or
                (menu_cursor == 1
                 and key in config['CONTROLS'].get('REVEAL'))):
            board = Board(int(intermediate_width), int(intermediate_height),
                          float(intermediate_ratio), Difficulty.INTERMEDIATE,
                          config, win)
            break
        elif (key == '3' or
                (menu_cursor == 2
                 and key in config['CONTROLS'].get('REVEAL'))):
            board = Board(int(expert_width), int(expert_height),
                          float(expert_ratio), Difficulty.EXPERT,
                          config, win)
            break
        elif (key == '4' or
                (menu_cursor == 3
                 and key in config['CONTROLS'].get('REVEAL'))):
            min_width = config["SETUP"]['MIN_WIDTH']
            min_height = config["SETUP"]['MIN_HEIGHT']
            max_width = config["SETUP"]['MAX_WIDTH']
            max_height = config["SETUP"]['MAX_HEIGHT']
            # get width from user
            custom_width = ''
            while not custom_width.isdigit():
                win.clear()
                logo(win)
                y, x = win.getyx()
                custom_width = raw_input(win, y, 0,
                                         f"width (min: {min_width}, "
                                         f"max: {max_width}): ").lower()
                if custom_width.isdigit():
                    if min_width and int(custom_width) < min_width:
                        custom_width = 'NaN'
                    if max_width and int(custom_width) > max_width:
                        custom_width = 'NaN'
                if custom_width == '':
                    custom_width = config["SETUP"]["BEGINNER"]["WIDTH"]
            # get height from user
            custom_height = ''
            while not custom_height.isdigit():
                win.clear()
                logo(win)
                win.addstr(f'width: {custom_width}')
                y, x = win.getyx()
                custom_height = raw_input(win, y+1, 0,
                                          f"height (min: {min_height}, "
                                          f"max: {max_height}): ").lower()
                if custom_height.isdigit():
                    if min_height and int(custom_height) < min_height:
                        custom_height = 'NaN'
                    if max_height and int(custom_height) > max_height:
                        custom_height = 'NaN'
                if custom_height == '':
                    custom_height = config["SETUP"]["BEGINNER"]["HEIGHT"]
            # get ratio from user
            custom_ratio = ''
            while not custom_ratio.replace('.', '', 1).isdigit():
                win.clear()
                logo(win)
                win.addstr(f'width: {custom_width}\n')
                win.addstr(f'height: {custom_height}')
                y, x = win.getyx()
                custom_ratio = raw_input(win, y+1, 0, "ratio: ").lower()
                if custom_ratio.replace('.', '', 1).isdigit():
                    if float(custom_ratio) > 1 or float(custom_ratio) < 0:
                        custom_ratio = 'NaN'
                if custom_ratio == '':
                    custom_ratio = str(config["SETUP"]["BEGINNER"]["RATIO"])
            board = Board(int(custom_width), int(custom_height),
                          float(custom_ratio), Difficulty.CUSTOM,
                          config, win)
            break
        elif (key == '5' or
                (menu_cursor == 4
                 and key in config['CONTROLS'].get('REVEAL'))):
            if not config['SETUP']['NO_FLASH']:
                win.addstr(exit_spot[0], exit_spot[1], config['LOOK'][
                    'SYMBOLS']['MINE'])
                win.refresh()
                curses.flash()
                time.sleep(0.1)
                curses.flash()
                curses.flash()
            raise SystemExit(0)

    curses.noecho()
    main_loop(win, board, config)


def main_loop(win: curses.window, board: Board, config: dict) -> None:
    term_height, term_width = win.getmaxyx()
    controls = config["CONTROLS"]
    help_str = control_str(controls.get("HELP"))
    # show board
    win.clear()
    board.display()
    win.refresh()

    # handle user input
    while True:
        try:
            key = win.getkey(0, 0)
        except curses.error:
            key = curses.ERR
        if key in controls.get("EXIT"):
            break
        elif key in controls.get("HELP"):
            board.pause()
            show_help(win, config)
        elif key in controls.get("HIGHSCORES"):
            board.show_highscores()
        elif key in controls.get("MENU"):
            splash(win, config)
            break
        elif key in controls.get("REVEAL"):
            board.reveal()
        elif key in controls.get("FLAG"):
            board.flag()
        elif key in controls.get("RESET"):
            board.reset()
        elif (key in controls.get("LEFT") or
              key in controls.get("RIGHT") or
              key in controls.get("UP") or
              key in controls.get("DOWN") or
              key in controls.get("HOME") or
              key in controls.get("END") or
              key in controls.get("FLOOR") or
              key in controls.get("CEILING")):

            for k_n, k_v in controls.items():
                if key in k_v:
                    board.move_direction(k_n)
        elif key == 'KEY_MOUSE':
            bstate = 0
            mx, my = (-1, -1)
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except curses.error:
                pass
            if mouse_helper(controls, 'EXIT', bstate):
                break
            elif mouse_helper(controls, 'HELP', bstate):
                board.pause()
                show_help(win, config)
            elif mouse_helper(controls, 'HIGHSCORES', bstate):
                board.show_highscores()
            elif mouse_helper(controls, 'MENU', bstate):
                splash(win, config)
                break
            elif mouse_helper(controls, 'REVEAL', bstate):
                if board.set_cursor_from_mouse(mx, my):
                    board.reveal()
            elif mouse_helper(controls, 'FLAG', bstate):
                if board.set_cursor_from_mouse(mx, my):
                    board.flag()
            elif (mouse_helper(controls, 'LEFT', bstate)
                  or mouse_helper(controls, 'RIGHT', bstate)
                  or mouse_helper(controls, 'UP', bstate)
                  or mouse_helper(controls, 'DOWN', bstate)
                  or mouse_helper(controls, 'HOME', bstate)
                  or mouse_helper(controls, 'END', bstate)
                  or mouse_helper(controls, 'FLOOR', bstate)
                  or mouse_helper(controls, 'CEILING', bstate)):
                for k_n, k_v in controls.items():
                    if key in k_v:
                        board.move_direction(k_n)
        elif key == curses.ERR:
            if board.state != GameState.PAUSED:
                board.display()
                if term_width > board.full_width:
                    w = board.full_width
                else:
                    w = board.width
                win.addstr(f'{f"Press {help_str} for help.":^{w}}')
                win.noutrefresh()
                win.refresh()
            continue
        if board.state != GameState.PAUSED or key == curses.KEY_RESIZE:
            term_height, term_width = win.getmaxyx()
            win.clear()
            board.display()
            if term_width > board.full_width:
                w = board.full_width
            else:
                w = board.width
            win.addstr(f'{f"Press {help_str} for help.":^{w}}')
        win.refresh()

    raise SystemExit(0)


def mouse_helper(controls: {str, List[int]}, command: str, bstate: int)\
        -> bool:
    if controls.get(command) is None:
        return False
    for o in controls.get(command):
        try:
            attr = getattr(curses, str(o))
        except (ValueError, AttributeError):
            attr = None
        if attr and bstate & attr:
            return True
    return False


if __name__ == '__main__':
    try:
        curses.wrapper(setup)
    except curses.error as e:
        raise Exception(f'Terminal too small. Increase size'
                        f'of terminal or reduce font size.') from e
