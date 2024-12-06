# Amelia Sinclaire 2024
import argparse
import csv
import curses
import datetime
from enum import Enum
import itertools
import math
import operator
import random
import time
from typing import Any

import load_config


# TODO:
# allow editing all symbol colors (flag and mine and unopened)

# put config in canonical location
# type check config values
# check curses keycodes are valid
# allow hex codes OR rgb lists
# consolidate keyboard/mouse config (allow multiple options)
# in game settings / config editor

# resize entire game (if possible) based on terminal size
# revert back to normal terminal colors on exit

# let user define own game modes other than the 3 basics?


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

    def display(self, stdscr: curses.window, symbols: {str: str},
                display_format=None) -> None:
        if self == self.FLAG and display_format:
            stdscr.addstr(symbols[self.name], display_format)
        elif self.ONE <= self <= self.EIGHT:
            color = curses.color_pair(int(self.value))
            stdscr.addstr(symbols[self.name], color)
        else:
            stdscr.addstr(symbols[self.name])

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

    def __init__(self, width: int, height: int, mine_ratio: float,
                 difficulty: Difficulty, config: dict,
                 stdscr: curses.window) -> None:
        self.width = width
        self.height = height
        self.locations = list(itertools.product(range(self.height),
                                                range(self.width)))
        self.middle = self.width * 3

        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)
        self.mines = []

        self.difficulty = difficulty
        self.config = config
        self.no_flash = config['SETUP']['NO_FLASH']
        self.hs_config = config['HIGHSCORES']
        self.symbols = config["LOOK"]["SYMBOLS"]

        self.stdscr = stdscr

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

    def populate(self) -> None:
        # set mines
        choices = [x for x in self.locations if x != self.cursor]
        self.mines = random.sample(choices, k=self.n_mines)
        for m_row, m_col in self.mines:
            self.real_board[m_row][m_col] = Cell.MINE

        # populate numbers
        for loc in self.locations:
            cell = self.real_board[loc[0]][loc[1]]
            if cell == Cell.BLANK:
                self.real_board[loc[0]][loc[1]] = Cell(self.count_mines(*loc))

        self.start_time = datetime.datetime.now()

    def set_cursor_from_mouse(self, screen_x: int, screen_y: int) -> None:
        if not self.state == GameState.PLAYING:
            return
        # x and y are screen coordinates
        new_row = screen_y - 2  # two for timer and win/loss counts
        new_col = (screen_x // 3)  # to account for [ ] style
        loc = (new_row, new_col)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
            self.cursor = loc

    def move_cursor(self, x: int, y: int) -> None:
        if not self.state == GameState.PLAYING:
            return
        new_row = self.cursor[0] + y
        new_col = self.cursor[1] + x
        loc = (new_row % self.height, new_col % self.width)  # wrap around
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
        raw_highscore_data: [[str, str, str]] = []
        new_highscore = False

        # read in data
        with open('highscores.csv', 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ')
            for row in reader:
                # ignore blank lines
                if ''.join(row).strip() == '':
                    continue
                raw_highscore_data.append(row)

        # turn the score strings into timedelta objects
        # and turn the difficulty strings into Difficulty objects
        highscore_data: [[str, str, float]] = []
        for idx, hs in enumerate(raw_highscore_data):
            t = datetime.datetime.strptime(hs[2], '%H:%M:%S.%f')
            this_difficulty = Difficulty[hs[0]]
            this_name = hs[1]
            this_score = datetime.timedelta(hours=t.hour, minutes=t.minute,
                                            seconds=t.second,
                                            microseconds=t.microsecond)
            highscore_data.append([this_difficulty, this_name, this_score])

        # get only scores for the selected Difficulty level
        scores: [datetime.timedelta] = [x[2] for x in highscore_data
                                        if x[0] == self.difficulty.name]

        # check if current score is better than any score in highscore list
        max_scores = self.hs_config.get(self.difficulty.name + '_MAX')
        if (any(self.score < s for s in scores)  # higher than any value
                or scores is None  # or list is empty
                or len(scores) < max_scores):  # or list is not full
            # NEW HIGH SCORE!
            new_highscore = True

            # Get player's name
            self.display()
            self.stdscr.addstr(f'{"NEW HIGHSCORE!!!":^{self.middle}}',
                               curses.A_BOLD
                               | curses.A_REVERSE
                               | curses.A_BLINK)
            name = raw_input(self.stdscr, self.height + 7, 0,
                             prompt='Enter Name:')
            # remove invalid characters (white spaces and quotes)
            name = name.translate(str.maketrans('', '', ' \n\t\r\'"'))
            # force uppercase and enforce name char limit
            max_name_length = self.hs_config.get('MAX_NAME_LENGTH')
            if max_name_length != math.inf:
                name = name.upper()[:max_name_length]
            else:
                name = name.upper()

            # add in the new score
            highscore_data.append([self.difficulty, name, self.score])
            # sort the scores
            highscore_data = sorted(highscore_data,
                                    key=operator.itemgetter(0, 2))

            # convert back to strings
            raw_highscore_data: [[str, str, str]]
            raw_highscore_data = [[hs[0].name,
                                   hs[1],
                                   f'{Board.zero_time + hs[2]:%H:%M:%S.%f}']
                                  for hs in highscore_data]

            # split into separate arrays per difficulty level
            total_list: [[[str, str, str]]] = []
            for difficulty in Difficulty:
                total_list.append([x for x in raw_highscore_data
                                   if x[0] == difficulty.name])

            # save the newly adjusted highscores
            with open('highscores.csv', 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                for cat in total_list:
                    if not cat:
                        continue
                    max_scores = self.hs_config[cat[0][0] + '_MAX']
                    if max_scores == math.inf:
                        max_scores = len(cat)
                    for hs in cat[:max_scores]:
                        writer.writerow(hs)
                    # add a gap between each difficulty level
                    writer.writerow('')
        return new_highscore

    def won(self) -> None:
        self.state = GameState.WON
        self.end_time = datetime.datetime.now()

        self.score = self.cum_time + (self.end_time - self.start_time)
        for m in self.mines:
            self.my_board[m[0]][m[1]] = Cell.FLAG

        # Update highscores
        new_highscore = self.update_highscores()
        if new_highscore:
            self.show_highscores()

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

    def reveal(self) -> None:
        if not self.state == GameState.PLAYING:
            return
        if not self.in_bounds(self.cursor):
            return

        curses.beep()
        if self.is_first_click:
            self.populate()
            self.is_first_click = False

        row, col = self.cursor

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
                self.reveal()
            self.cursor = temp
        else:
            self.my_board[row][col] = Cell.OPENED
        self.check_win()
        return

    def show_highscores(self) -> None:
        self.pause()
        raw_highscore_data: [[str, str, str]] = []

        # read in data
        with open('highscores.csv', 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ')
            for row in reader:
                # ignore blank lines
                if ''.join(row).strip() == '':
                    continue
                raw_highscore_data.append(row)

        # get only scores for the selected Difficulty level
        scores_str: [[str, str, datetime.timedelta]] = \
            [x for x in raw_highscore_data if x[0] == self.difficulty.name]

        difficulty_n = self.difficulty.name
        max_scores = self.hs_config[f'{difficulty_n}_MAX']
        if max_scores == math.inf:
            max_scores = len(scores_str)
        title_format = curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK
        # clear the screen
        self.stdscr.clear()

        # title
        # TODO: center this text based on the width of the highscore screen
        self.stdscr.addstr(f'{f"{difficulty_n} HIGH SCORES":^{self.middle}}\n',
                           title_format)

        # list scores
        max_name_length = len(max(scores_str, key=lambda x: len(x[1]))[1])
        for idx, score in enumerate(scores_str[:max_scores]):
            self.stdscr.addstr(f'[')
            # do cute color matching for numbers
            num = idx + 1
            self.stdscr.addstr(str(num), curses.color_pair((num % 8)) + 1)
            # add closing bracket with some spacing to make everything line up
            spaces = " " * (len(str(len(scores_str))) - len(str(num)) + 2)
            self.stdscr.addstr(f']{spaces}')

            # if we are showing the highscores after someone got a new one
            # then we will do our best to highlight their new score
            if f'{Board.zero_time + self.score:%H:%M:%S.%f}' == score[2]:
                self.stdscr.addstr(
                    f'{score[1]:<{max_name_length}} | {score[2]}\n',
                    title_format)
            else:
                self.stdscr.addstr(f'{score[1]:<{max_name_length}} |'
                                   f' {score[2]}\n')
        self.stdscr.nodelay(False)
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)
        self.pause()

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
                               | curses.color_pair(9)
                               | curses.A_BOLD)
            death_format = (curses.A_BLINK
                            | curses.color_pair(10)
                            | curses.A_BOLD)
            win_format = (curses.A_BLINK
                          | curses.color_pair(11)
                          | curses.A_BOLD)
        else:
            selector_format = (curses.A_REVERSE
                               | curses.color_pair(9)
                               | curses.A_BOLD)
            death_format = (curses.A_REVERSE
                            | curses.color_pair(10)
                            | curses.A_BOLD)
            win_format = (curses.A_REVERSE
                          | curses.color_pair(11)
                          | curses.A_BOLD)

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
        self.stdscr.addstr(f'{time_str:^{self.middle}}\n')

        # display board
        for rid, row in enumerate(self.my_board):
            for cid, cell in enumerate(row):
                if cell == Cell.OPENED:
                    cell = self.real_board[rid][cid]
                # highlight cursor position
                if self.cursor == (
                        rid, cid) and self.state == GameState.PLAYING:
                    self.stdscr.addstr('[', selector_format)
                    cell.display(self.stdscr, self.symbols)
                    self.stdscr.addstr(']', selector_format)
                    continue
                # highlight death location
                if self.death == (rid, cid) and self.state == GameState.LOST:
                    self.stdscr.addstr('[', death_format)
                    cell.display(self.stdscr, self.symbols)
                    self.stdscr.addstr(']', death_format)
                    continue
                # flash all flags if won
                if cell == Cell.FLAG and self.state == GameState.WON:
                    self.stdscr.addstr('[', win_format)
                    cell.display(self.stdscr, self.symbols, win_format)
                    self.stdscr.addstr(']', win_format)
                    continue
                # otherwise normal cell display
                self.stdscr.addstr('[')
                cell.display(self.stdscr, self.symbols)
                self.stdscr.addstr(']')
            self.stdscr.addstr('\n')
        self.stdscr.addstr('\n')

        reset_key = control_str(self.config["CONTROLS"]["KEYBOARD"]["RESET"],
                                self.config["CONTROLS"]["MOUSE"]["RESET"])
        if self.state == GameState.LOST:
            self.stdscr.addstr(f'{"YOU LOSE!":^{self.middle}}\n', title_format)
            self.stdscr.addstr(f'{f"Press {reset_key} to reset.":^{self.middle}}\n')
        elif self.state == GameState.WON:
            self.stdscr.addstr(f'{"YOU WIN!":^{self.middle}}\n', title_format)
            self.stdscr.addstr(f'{f"Press {reset_key} to reset.":^{self.middle}}\n')


def init_colors(stdscr: curses.window, colors: {str: dict}) -> None:
    str_to_id = {'ONE': 1,
                 'TWO': 2,
                 'THREE': 3,
                 'FOUR': 4,
                 'FIVE': 5,
                 'SIX': 6,
                 'SEVEN': 7,
                 'EIGHT': 8,
                 'SELECTOR': 9,
                 'LOSE': 10,
                 'WIN': 11,
                 'BG': 12,
                 'FG': 13}
    defaults: {str, int} = colors['DEFAULT']
    rgbs: {str: [int]} = colors['RGB']

    if curses.has_colors():
        # initialize some basic colors
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        if curses.can_change_color():
            # use rgb values
            # get BG color
            if (bg_color := rgbs.get('BG')) and (fg_color := rgbs.get('FG')):
                # noinspection PyArgumentList
                curses.init_color(str_to_id['BG'], *bg_color)
                bg = str_to_id['BG']
                # noinspection PyArgumentList
                curses.init_color(str_to_id['FG'], *fg_color)
                fg = str_to_id['FG']
            elif bg_color := rgbs.get('BG'):
                # noinspection PyArgumentList
                curses.init_color(str_to_id['BG'], *bg_color)
                bg = str_to_id['BG']
                fg = defaults['FG']
            elif fg_color := rgbs.get('FG'):
                bg = defaults['BG']
                # noinspection PyArgumentList
                curses.init_color(str_to_id['FG'], *fg_color)
                fg = str_to_id['FG']
            else:
                bg = defaults['BG']
                fg = defaults['FG']
            curses.init_pair(str_to_id['BG'], fg, bg)
            stdscr.bkgd(' ', curses.color_pair(str_to_id['BG']))

            for idx, (c_n, c_v) in enumerate(rgbs.items()):
                if c_n == 'BG' or c_n == 'FG':
                    continue
                my_color = defaults.get(c_n)
                if c_v is None:
                    curses.init_pair(str_to_id[c_n], my_color, bg)
                    continue

                # noinspection PyArgumentList
                curses.init_color(str_to_id[c_n], *c_v)
                curses.init_pair(str_to_id[c_n], str_to_id[c_n], bg)
        else:
            bg = defaults['BG']
            curses.init_pair(str_to_id['BG'], defaults['FG'],
                             defaults['BG'])
            stdscr.bkgd(' ', curses.color_pair(str_to_id['BG']))
            for idx, (c_n, c_v) in enumerate(defaults.items()):
                if c_n == 'BG' or c_n == 'FG':
                    continue
                curses.init_pair(str_to_id[c_n], c_v, bg)


class _Sentinel:
    pass


def setup(stdscr: curses.window) -> None:
    # loading config
    config = load_config.load_config()

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
    args = parser.parse_args()

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
        raise ValueError(f'Invalid width: {args.width}. Must be >= {min_width}')
    if min_height and args.height < min_height:
        raise ValueError(
            f'Invalid height: {args.height}. Must be >= {min_height}')
    if max_width and args.width > max_width:
        raise ValueError(f'Invalid width: {args.width}. Must be <= {max_width}')
    if max_height and args.height > max_height:
        raise ValueError(
            f'Invalid height: {args.height}. Must be <= {max_width}')
    if args.ratio is not None and (args.ratio < 0 or args.ratio > 1):
        raise ValueError(
            f'Invalid mine ratio: {args.ratio:.2f}. Must be between 0 and 1')
    config["SETUP"]["NO_FLASH"] = args.no_flash

    init_colors(stdscr, config["LOOK"]['COLORS'])
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    stdscr.nodelay(True)
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
                      config, stdscr)
        main_loop(stdscr, board, config)
    else:
        splash(stdscr, config)


# use curses to prompt the user for a response
# https://stackoverflow.com/a/21785167
def raw_input(stdscr: curses.window, r: int, c: int, prompt: str) -> str:
    curses.echo()
    stdscr.nodelay(False)
    stdscr.addstr(r, c, prompt)
    stdscr.refresh()
    inp = stdscr.getstr(r + 1, c, 20)
    stdscr.nodelay(True)
    return inp.decode()  # ^^^^  reading input at next line


def logo(stdscr: curses.window) -> None:
    term_height, term_width = stdscr.getmaxyx()
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
                stdscr.addstr(row)
            return


# used as a helper for help screen
def control_str(config1: str | None, config2: str | None = None) -> str:
    if config1 == ' ':
        config1 = 'space'
    if config2 == ' ':
        config2 = 'space'

    if config1 is not None and config2 is not None:
        return f'[{config1.upper()}] OR [{config2.upper()}]'
    if config1 is not None:
        return f'[{config1.upper()}]'
    if config2 is not None:
        return f'[{config2.upper()}]'
    return '{NO KEY SET}'


def show_help(stdscr: curses.window, config: dict) -> None:
    keyboard = config["CONTROLS"]["KEYBOARD"]
    mouse = config["CONTROLS"]["MOUSE"]
    stdscr.clear()
    stdscr.addstr('HELP\n\n')
    longest_cmd = max(keyboard.keys(), key=len)
    for command in keyboard.keys():
        stdscr.addstr(
            f'{command + ":":<{1 + len(longest_cmd)}} '
            f'{control_str(keyboard.get(command), mouse.get(command))}\n')


def display_sample(stdscr: curses.window, config: dict) -> None:
    term_height, term_width = stdscr.getmaxyx()
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
                stdscr.addstr('[')
                cell.display(stdscr, symbols)
                stdscr.addstr(']')
            stdscr.addstr('\n')
        return
    out2 = ''
    for row in display:
        for cell in row:
            out2 += cell.print(symbols)
        out2 += '\n'
    if term_width > len(max(out2.split('\n'), key=len)):
        for row in display:
            for cell in row:
                cell.display(stdscr, symbols)
            stdscr.addstr('\n')
        return
    return


def splash(stdscr: curses.window, config: dict) -> None:
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
    raw_highscore_data: [[str, str, str]] = []
    with open('highscores.csv', 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ')
        for row in reader:
            # ignore blank lines
            if ''.join(row).strip() == '':
                continue
            raw_highscore_data.append(row)

    # turn the score strings into timedelta objects
    # and turn the difficulty strings into Difficulty objects
    highscore_data: [[str, str, float]] = []
    for idx, hs in enumerate(raw_highscore_data):
        t = datetime.datetime.strptime(hs[2], '%H:%M:%S.%f')
        this_difficulty = Difficulty[hs[0]]
        this_name = hs[1]
        this_score = datetime.timedelta(hours=t.hour, minutes=t.minute,
                                        seconds=t.second,
                                        microseconds=t.microsecond)
        highscore_data.append([this_difficulty, this_name, this_score])

    # sort the scores (should not be necessary)
    highscore_data = sorted(highscore_data, key=operator.itemgetter(0, 2))
    # convert back to strings
    raw_highscore_data: [[str, str, str]]
    raw_highscore_data = [[hs[0].name,
                           hs[1],
                           f'{Board.zero_time + hs[2]:%H:%M:%S.%f}']
                          for hs in highscore_data]

    total_list: [[[str, str, str]]] = []
    for difficulty in Difficulty:
        total_list.append([x for x in raw_highscore_data
                           if x[0] == difficulty.name])

    stdscr.clear()
    logo(stdscr)

    def show_option(d: Difficulty) -> None:
        term_height, term_width = stdscr.getmaxyx()
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

        options.append((f'] {d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {name} {score}\n', True, True, True))
        options.append((f'] {d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {score}\n', True, True, True))
        options.append((f'] {d.name:<{spaces}} ({w}x{h}) | {r:.2%} '
                        f'| HS: {name}\n', True, True, True))
        options.append(
            (f'] {d.name:<{spaces}} ({w}x{h}) | {r:.2%}\n', False, True, True))
        options.append(
            (f'] {d.name:<{spaces}} ({w}x{h})\n', False, True, False))
        options.append((f'] {d.name:<{spaces}} | HS: {name} {score}\n', True,
                        False, False))
        options.append(
            (f'] {d.name:<{spaces}} | HS: {score}\n', True, False, False))
        options.append(
            (f'] {d.name:<{spaces}} | HS: {name}\n', True, False, False))
        options.append((f'] {d.name}\n', False, False, False))
        options.append((f'] {d.name[0]}\n', False, False, False))

        # options.sort(key=lambda x: len(x[0]), reverse=True)

        for (op, has_hs, has_wh, has_r) in options:
            if has_r and r == -1:
                continue
            if has_wh and w == -1 or has_hs and h == -1:
                continue
            if term_width >= len(op) + 2:
                if has_hs and len(total_list[d.value]) > 0:
                    stdscr.addstr(op)
                    return
                elif not has_hs:
                    stdscr.addstr(op)
                    return
                else:
                    continue

    # DISPLAY OPTIONS
    for diff in Difficulty:
        stdscr.addstr(f'[')
        stdscr.addstr(f'{diff.value + 1}', curses.color_pair(diff.value + 1))
        show_option(diff)
    stdscr.addstr('\n')
    stdscr.addstr(f'[')
    stdscr.addstr(f'5', curses.color_pair(len(
        Difficulty) + 1))
    stdscr.addstr(f'] Exit\n\n')

    # DISPLAY all symbols (useful if changing themes:)
    display_sample(stdscr, config)

    stdscr.refresh()

    # Handle user interaction (selecting difficulty)
    # TODO: allow selection with movement keys and reveal keys
    while True:
        try:
            key = stdscr.getkey(0, 0)
        except curses.error:
            key = curses.ERR
        if key == config["CONTROLS"]["KEYBOARD"].get("EXIT"):
            raise SystemExit(0)
        if key == 'KEY_RESIZE':
            stdscr.clear()
            logo(stdscr)

            # DISPLAY OPTIONS
            for diff in Difficulty:
                stdscr.addstr(f'[')
                stdscr.addstr(f'{diff.value + 1}',
                              curses.color_pair(diff.value + 1))
                show_option(diff)
            stdscr.addstr('\n')

            # DISPLAY all symbols (useful if changing themes:)
            display_sample(stdscr, config)
            stdscr.refresh()
        if key == '1':
            board = Board(int(beginner_width), int(beginner_height),
                          float(beginner_ratio), Difficulty.BEGINNER,
                          config, stdscr)
            break
        elif key == '2':
            board = Board(int(intermediate_width), int(intermediate_height),
                          float(intermediate_ratio), Difficulty.INTERMEDIATE,
                          config, stdscr)
            break
        elif key == '3':
            board = Board(int(expert_width), int(expert_height),
                          float(expert_ratio), Difficulty.EXPERT,
                          config, stdscr)
            break
        elif key == '4':
            # TODO: these need to be moved down according to the height of the
            # logo... maybe can get current cursor position or something?
            min_width = config["SETUP"]['MIN_WIDTH']
            min_height = config["SETUP"]['MIN_HEIGHT']
            max_width = config["SETUP"]['MAX_WIDTH']
            max_height = config["SETUP"]['MAX_HEIGHT']
            # get width from user
            custom_width = ''
            while not custom_width.isdigit():
                stdscr.clear()
                logo(stdscr)
                custom_width = raw_input(stdscr, 7, 0,
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
                stdscr.clear()
                logo(stdscr)
                stdscr.addstr(f'width: {custom_width}')
                custom_height = raw_input(stdscr, 8, 0,
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
                stdscr.clear()
                logo(stdscr)
                stdscr.addstr(f'width: {custom_width}\n')
                stdscr.addstr(f'height: {custom_height}')
                custom_ratio = raw_input(stdscr, 9, 0, "ratio: ").lower()
                if custom_ratio.replace('.', '', 1).isdigit():
                    if float(custom_ratio) > 1 or float(custom_ratio) < 0:
                        custom_ratio = 'NaN'
                if custom_ratio == '':
                    custom_ratio = str(config["SETUP"]["BEGINNER"]["RATIO"])
            board = Board(int(custom_width), int(custom_height),
                          float(custom_ratio), Difficulty.CUSTOM,
                          config, stdscr)
            break
        elif key == '5':
            raise SystemExit(0)

    curses.noecho()
    main_loop(stdscr, board, config)


def main_loop(stdscr: curses.window, board: Board, config: dict) -> None:
    keyboard = config["CONTROLS"]["KEYBOARD"]
    mouse = config["CONTROLS"]["MOUSE"]
    help_str = control_str(keyboard.get("HELP"), mouse.get("HELP"))
    # show board
    stdscr.clear()
    board.display()
    stdscr.refresh()

    # handle user input
    while True:
        try:
            key = stdscr.getkey(0, 0)
        except curses.error:
            key = curses.ERR
        if key == keyboard.get("EXIT"):
            break
        elif key == keyboard.get("HELP"):
            board.pause()
            show_help(stdscr, config)
        elif key == keyboard.get("HIGHSCORES"):
            board.show_highscores()
        elif key == keyboard.get("MENU"):
            splash(stdscr, config)
            break
        elif key == keyboard.get("REVEAL"):
            board.reveal()
        elif key == keyboard.get("FLAG"):
            board.flag()
        elif key == keyboard.get("RESET"):
            board.reset()
        elif (key == keyboard.get("LEFT") or
              key == keyboard.get("RIGHT") or
              key == keyboard.get("UP") or
              key == keyboard.get("DOWN") or
              key == keyboard.get("HOME") or
              key == keyboard.get("END") or
              key == keyboard.get("FLOOR") or
              key == keyboard.get("CEILING")):
            move_str = list(keyboard.keys())[
                list(keyboard.values()).index(key)]
            board.move_direction(move_str)
        elif key == 'KEY_MOUSE':
            bstate = 0
            mx, my = (-1, -1)
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except curses.error:
                pass
            if (mouse.get("EXIT")
                    and (bstate & getattr(curses, mouse.get("EXIT")))):
                break
            elif (mouse.get("HELP")
                  and (bstate & getattr(curses, mouse.get("HELP")))):
                board.pause()
                show_help(stdscr, config)
            elif (mouse.get("HIGHSCORES")
                  and (bstate & getattr(curses, mouse.get("HIGHSCORES")))):
                board.show_highscores()
            elif (mouse.get("MENU")
                    and (bstate & getattr(curses, mouse.get("MENU")))):
                splash(stdscr, config)
                break
            elif (mouse.get("REVEAL")
                  and (bstate & getattr(curses, mouse.get("REVEAL")))):
                board.set_cursor_from_mouse(mx, my)
                board.reveal()
            elif (mouse.get("FLAG")
                  and (bstate & getattr(curses, mouse.get("FLAG")))):
                board.set_cursor_from_mouse(mx, my)
                board.flag()
            elif ((mouse.get("LEFT")
                   and (bstate & getattr(curses, mouse.get("LEFT"))))
                  or (mouse.get("RIGHT")
                      and (bstate & getattr(curses, mouse.get("RIGHT"))))
                  or (mouse.get("UP")
                      and (bstate & getattr(curses, mouse.get("UP"))))
                  or (mouse.get("DOWN")
                      and (bstate & getattr(curses, mouse.get("DOWN"))))
                  or (mouse.get("HOME")
                      and (bstate & getattr(curses, mouse.get("HOME"))))
                  or (mouse.get("END")
                      and (bstate & getattr(curses, mouse.get("END"))))
                  or (mouse.get("FLOOR")
                      and (bstate & getattr(curses, mouse.get("FLOOR"))))
                  or (mouse.get("CEILING")
                      and (bstate & getattr(curses, mouse.get("CEILING"))))):
                move_str = list(keyboard.keys())[
                    list(keyboard.values()).index(key)]
                board.move_direction(move_str)
        elif key == curses.ERR:
            if board.state != GameState.PAUSED:
                board.display()
                stdscr.addstr(f'{f"Press {help_str} for help.":^{board.middle}}')
                stdscr.noutrefresh()
                stdscr.refresh()
            continue
        if board.state != GameState.PAUSED:
            stdscr.clear()
            board.display()
            stdscr.addstr(f'{f"Press {help_str} for help.":^{board.middle}}')
        stdscr.refresh()

    raise SystemExit(0)


if __name__ == '__main__':
    try:
        curses.wrapper(setup)
    except curses.error as e:
        raise Exception(f'Terminal too small. Increase size'
                        f'of terminal or reduce font size.') from e
