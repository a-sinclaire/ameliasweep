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
import yaml


# TODO:
# show high scores when you get a new high score.
# show highest score for each difficulty on splash
# better win lose screen
# show total time played(?)
# update readme with any new changes


class Difficulty(Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    EXPERT = 3
    CUSTOM = 4

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

    def display(self, stdscr: curses.window, symbols: {str: str}, display_format=None) -> None:
        if self == self.FLAG and display_format:
            stdscr.addstr(symbols[self.name], display_format)
        elif self.ONE.value <= self.value <= self.EIGHT.value:
            stdscr.addstr(symbols[self.name], curses.color_pair(int(self.value)))
        else:
            stdscr.addstr(symbols[self.name])


class Board:
    neighbors = [x for x in itertools.product(range(-1, 2), range(-1, 2)) if x != (0, 0)]
    zero_time = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    def __init__(self, width: int, height: int, mine_ratio: float, difficulty: Difficulty, config: dict, stdscr: curses.window, no_flash: bool = False) -> None:
        self.start_time = None
        self.end_time = None
        self.cum_time = datetime.timedelta(0)
        self.score = datetime.timedelta(0)
        self.n_wins = 0
        self.n_games = 0
        self.width = width
        self.height = height
        self.locations = list(itertools.product(range(self.height), range(self.width)))
        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)
        self.no_flash = no_flash
        self.difficulty = difficulty
        self.hs_config = config['HIGHSCORES']
        self.symbols = config["LOOK"]["SYMBOLS"]
        self.stdscr = stdscr

        self.real_board = [[Cell.BLANK for x in range(self.width)] for y in range(self.height)]
        self.my_board = [[Cell.UNOPENED for x in range(self.width)] for y in range(self.height)]
        self.cursor = (self.height // 2, self.width // 2)
        self.death = (-1, -1)
        self.mines = []
        self.is_first_click = True
        self.state = GameState.PLAYING
        self.previous_state = self.state

    def reset(self) -> None:
        self.start_time = None
        self.end_time = None
        self.cum_time = datetime.timedelta(0)
        self.score = datetime.timedelta(0)
        self.real_board = [[Cell.BLANK for x in range(self.width)] for y in range(self.height)]
        self.my_board = [[Cell.UNOPENED for x in range(self.width)] for y in range(self.height)]
        self.cursor = (self.height // 2, self.width // 2)
        self.death = (-1, -1)
        self.mines = []
        self.is_first_click = True
        self.state = GameState.PLAYING
        self.previous_state = self.state
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
                self.cum_time = self.cum_time + (datetime.datetime.now() - self.start_time)
            self.previous_state = self.state
            self.state = GameState.PAUSED

    def populate(self) -> None:
        choices = [x for x in self.locations if x != self.cursor]
        self.mines = random.sample(choices, k=self.n_mines)
        for m in self.mines:
            self.real_board[m[0]][m[1]] = Cell.MINE

        for loc in self.locations:
            cell = self.real_board[loc[0]][loc[1]]
            if cell == Cell.BLANK:
                self.real_board[loc[0]][loc[1]] = Cell(self.count_mines(*loc))

        self.start_time = datetime.datetime.now()

    def in_bounds(self, coord: (int, int)) -> bool:
        row, col = coord
        return 0 <= row < self.height and 0 <= col < self.width

    def count_mines(self, row: int, col: int) -> int:
        total = 0
        for n in Board.neighbors:
            loc = (row + n[0], col + n[1])
            if self.in_bounds(loc):
                total += 1 if self.real_board[loc[0]][loc[1]] == Cell.MINE else 0
        return total

    def set_cursor_from_mouse(self, x: int, y: int) -> None:
        if not self.state == GameState.PLAYING:
            return
        # x and y are screen coordinates
        new_row = y - 2  # two for timer and win/loss counts
        new_col = (x // 3)  # to account for [ ] style
        loc = (new_row, new_col)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
            self.cursor = loc

    def move_cursor(self, x: int, y: int) -> None:
        if not self.state == GameState.PLAYING:
            return
        new_row = self.cursor[0] + y
        new_col = self.cursor[1] + x
        loc = (new_row % self.height, new_col % self.width)
        if self.in_bounds(loc):
            self.cursor = loc

    def up(self) -> None:
        self.move_cursor(0, -1)

    def down(self) -> None:
        self.move_cursor(0, 1)

    def left(self) -> None:
        self.move_cursor(-1, 0)

    def right(self) -> None:
        self.move_cursor(1, 0)

    def home(self) -> None:
        self.cursor = (self.cursor[0], 0)

    def end(self) -> None:
        self.cursor = (self.cursor[0], self.width - 1)

    def floor(self) -> None:
        self.cursor = (self.height - 1, self.cursor[1])

    def ceiling(self) -> None:
        self.cursor = (0, self.cursor[1])

    def reveal_all(self) -> None:
        self.my_board = [[Cell.OPENED for x in range(self.width)] for y in range(self.height)]

    def reveal(self) -> None:
        if not self.state == GameState.PLAYING:
            return

        curses.beep()
        if self.is_first_click:
            self.populate()
            self.is_first_click = False

        row, col = self.cursor

        if not self.in_bounds(self.cursor):
            return

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

    def lose(self) -> None:
        self.reveal_all()
        self.death = self.cursor
        self.state = GameState.LOST
        self.end_time = datetime.datetime.now()
        self.n_games += 1
        if not self.no_flash:
            curses.flash()
            time.sleep(0.1)
            curses.flash()
            curses.flash()

    def won(self) -> None:
        self.state = GameState.WON
        self.end_time = datetime.datetime.now()
        self.score = self.cum_time + (self.end_time - self.start_time)
        self.n_wins += 1
        self.n_games += 1
        for m in self.mines:
            self.my_board[m[0]][m[1]] = Cell.FLAG

        # Update highscores
        highscore_data = []
        with open('highscores.csv', 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ')
            for row in reader:
                if ''.join(row).strip() == '':
                    continue
                highscore_data.append(row)
        for idx, hs in enumerate(highscore_data):
            t = datetime.datetime.strptime(hs[2], '%H:%M:%S.%f')
            highscore_data[idx][2] = (datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond))
            highscore_data[idx][0] = Difficulty[hs[0]]
        scores = [x for x in highscore_data if x == self.difficulty.name]
        if all(self.score < s for s in scores) or scores is None or len(scores) < self.hs_config[self.difficulty.name + '_MAX']:
            # NEW HIGH SCORE!
            self.display()
            self.stdscr.addstr('NEW HIGHSCORE!!', curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK)
            name = ''.join(raw_input(self.stdscr, self.height + 7, 0, prompt='Enter Name:').upper().split())[:self.hs_config['MAX_NAME_LENGTH']]
            highscore_data.append([self.difficulty, name, self.score])
            highscore_data = sorted(highscore_data, key=operator.itemgetter(0, 2))
            highscore_data = [[hs[0].name, hs[1], f'{Board.zero_time + hs[2]:%H:%M:%S.%f}'] for hs in highscore_data]

            total_list = []
            for difficulty in Difficulty:
                total_list.append([x for x in highscore_data if x[0] == difficulty.name])

            with open('highscores.csv', 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                for cat in total_list:
                    if not cat:
                        continue
                    for hs in cat[:self.hs_config[cat[0][0] + '_MAX']]:
                        writer.writerow(hs)
                    writer.writerow('')

    def check_win(self) -> None:
        if self.state != GameState.PLAYING:
            return
        won = sum(x.count(Cell.UNOPENED) + x.count(Cell.FLAG) for x in self.my_board) == self.n_mines
        if won:
            self.won()

    def flag(self) -> None:
        if not self.state == GameState.PLAYING:
            return
        row, col = self.cursor
        if not self.in_bounds(self.cursor):
            return
        if self.my_board[row][col] == Cell.UNOPENED:
            self.my_board[row][col] = Cell.FLAG
            return
        if self.my_board[row][col] == Cell.FLAG:
            self.my_board[row][col] = Cell.UNOPENED
            return

    def display(self) -> None:
        if curses.has_colors():
            selector_format = curses.A_BLINK | curses.color_pair(9) | curses.A_BOLD
            death_format = curses.A_BLINK | curses.color_pair(10) | curses.A_BOLD
            win_format = curses.A_BLINK | curses.color_pair(11) | curses.A_BOLD
        else:
            selector_format = curses.A_REVERSE | curses.color_pair(9) | curses.A_BOLD
            death_format = curses.A_REVERSE | curses.color_pair(10) | curses.A_BOLD
            win_format = curses.A_REVERSE | curses.color_pair(11) | curses.A_BOLD

        self.stdscr.addstr(f'{"WINS: " + str(self.n_wins):^{(self.width * 3) // 2}}')
        self.stdscr.addstr(f'{"LOSSES: " + str(self.n_games - self.n_wins):^{(self.width * 3) // 2}}\n')
        if self.start_time is not None and self.state == GameState.PLAYING:
            _time = Board.zero_time + self.cum_time + (datetime.datetime.now() - self.start_time)
        elif self.state == GameState.WON or self.state == GameState.LOST:
            _time = Board.zero_time + self.cum_time + (self.end_time - self.start_time)
        else:
            _time = Board.zero_time + self.cum_time
        time_str = f'{_time:%H:%M:%S.%f}'[:-4]
        self.stdscr.addstr(f'{time_str:^{self.width * 3}}\n')
        for rid, row in enumerate(self.my_board):
            for cid, cell in enumerate(row):
                if cell == Cell.OPENED:
                    cell = self.real_board[rid][cid]
                if self.cursor == (rid, cid) and self.state == GameState.PLAYING:
                    self.stdscr.addstr('[', selector_format)
                    cell.display(self.stdscr, self.symbols)
                    self.stdscr.addstr(']', selector_format)
                    continue
                if self.death == (rid, cid) and self.state == GameState.LOST:
                    self.stdscr.addstr('[', death_format)
                    cell.display(self.stdscr, self.symbols)
                    self.stdscr.addstr(']', death_format)
                    continue
                if cell == Cell.FLAG and self.state == GameState.WON:
                    self.stdscr.addstr('[', win_format)
                    cell.display(self.stdscr, self.symbols, win_format)
                    self.stdscr.addstr(']', win_format)
                    continue
                self.stdscr.addstr('[')
                cell.display(self.stdscr, self.symbols)
                self.stdscr.addstr(']')
            self.stdscr.addstr('\n')
        self.stdscr.addstr('\n')
        if self.state == GameState.LOST:
            self.stdscr.addstr('You Lose!\n')
            self.stdscr.addstr('Press "R" to restart\n\n')
        elif self.state == GameState.WON:
            self.stdscr.addstr('You Win!\n')
            self.stdscr.addstr('Press "R" to restart\n\n')


def init_colors(colors: {str: dict}) -> None:
    defaults: {str, int} = colors['DEFAULT']
    rgbs: {str: [int]} = colors['RGB']
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        if curses.can_change_color():
            for idx, c in enumerate(rgbs.values()):
                curses.init_color(list(defaults.values())[idx], *c)
                curses.init_pair(idx + 1, list(defaults.values())[idx], -1)
        else:
            for idx, c in enumerate(defaults.values()):
                curses.init_pair(idx + 1, c, -1)


class _Sentinel:
    pass


def setup(stdscr: curses.window) -> None:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

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
    parser.add_argument('--no-flash', action='store_true', default=False)
    args = parser.parse_args()

    # https://stackoverflow.com/questions/58594956/find-out-which-arguments-were-passed-explicitly-in-argparse
    sentinel = _Sentinel
    sentinel_ns = argparse.Namespace(**{key: sentinel for key in vars(args)})
    parser.parse_args(namespace=sentinel_ns)

    explicit = argparse.Namespace(**{key: (value is not sentinel) for key, value in vars(sentinel_ns).items()})

    if min_width and args.width < min_width:
        raise Exception(f'Invalid width: {args.width}. Must be >= {min_width}')
    if min_height and args.height < min_height:
        raise Exception(f'Invalid height: {args.height}. Must be >= {min_height}')
    if max_width and args.width > max_width:
        raise Exception(f'Invalid width: {args.width}. Must be <= {max_width}')
    if max_height and args.height > max_height:
        raise Exception(f'Invalid height: {args.height}. Must be <= {max_width}')
    if args.ratio is not None and (args.ratio < 0 or args.ratio > 1):
        raise Exception(f'Invalid mine ratio: {args.ratio:.2f}. Must be between 0 and 1')

    init_colors(config["LOOK"]['COLORS'])
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    stdscr.nodelay(True)
    try:
        curses.curs_set(0)
    except:
        pass

    if explicit.width or explicit.height or explicit.ratio:
        if not explicit.ratio:
            args.ratio = math.sqrt(args.width * args.height) / (args.width * args.height)
        board = Board(args.width, args.height, args.ratio, Difficulty.CUSTOM, config, stdscr, args.no_flash)
        main_loop(stdscr, board, config)
    else:
        splash(stdscr, config, args.no_flash)


# https://stackoverflow.com/a/21785167
def raw_input(stdscr: curses.window, r: int, c: int, prompt: str) -> str:
    curses.echo()
    stdscr.nodelay(False)
    stdscr.addstr(r, c, prompt)
    stdscr.refresh()
    inp = stdscr.getstr(r + 1, c, 20)
    stdscr.nodelay(True)
    return inp.decode()   # ^^^^  reading input at next line


def logo(stdscr: curses.window) -> None:
    stdscr.addstr(f'\n')
    stdscr.addstr(f'▗▖  ▗▖▗▞▀▚▖▗▞▀▚▖█ ▗▞▀▚▖▄   ▄ ▗▖  ▗▖▄ ▄▄▄▄  ▗▞▀▚▖\n')
    stdscr.addstr(f'▐▛▚▞▜▌▐▛▀▀▘▐▛▀▀▘█ ▐▛▀▀▘█   █ ▐▛▚▞▜▌▄ █   █ ▐▛▀▀▘\n')
    stdscr.addstr(f'▐▌  ▐▌▝▚▄▄▖▝▚▄▄▖█ ▝▚▄▄▖ ▀▀▀█ ▐▌  ▐▌█ █   █ ▝▚▄▄▖\n')
    stdscr.addstr(f'▐▌  ▐▌          █      ▄   █ ▐▌  ▐▌█            \n')
    stdscr.addstr(f'                        ▀▀▀                     \n')
    stdscr.addstr(f'\n')


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
    for command in keyboard.keys():
        stdscr.addstr(f'{command + ":":<8} {control_str(keyboard[command], mouse[command])}\n')


def splash(stdscr: curses.window, config: dict, no_flash: bool) -> None:
    beginner_width = config["SETUP"]["BEGINNER"]["WIDTH"]
    beginner_height = config["SETUP"]["BEGINNER"]["HEIGHT"]
    beginner_ratio = config["SETUP"]["BEGINNER"]["RATIO"]
    intermediate_width = config["SETUP"]["INTERMEDIATE"]["WIDTH"]
    intermediate_height = config["SETUP"]["INTERMEDIATE"]["HEIGHT"]
    intermediate_ratio = config["SETUP"]["INTERMEDIATE"]["RATIO"]
    expert_width = config["SETUP"]["EXPERT"]["WIDTH"]
    expert_height = config["SETUP"]["EXPERT"]["HEIGHT"]
    expert_ratio = config["SETUP"]["EXPERT"]["RATIO"]

    highscore_data = []
    with open('highscores.csv', 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ')
        for row in reader:
            if ''.join(row).strip() == '':
                continue
            highscore_data.append(row)
    for idx, hs in enumerate(highscore_data):
        t = datetime.datetime.strptime(hs[2], '%H:%M:%S.%f')
        highscore_data[idx][2] = (
            datetime.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond))
        highscore_data[idx][0] = Difficulty[hs[0]]
    highscore_data = sorted(highscore_data, key=operator.itemgetter(0, 2))
    highscore_data = [[hs[0].name, hs[1], f'{Board.zero_time + hs[2]:%H:%M:%S.%f}'] for hs in highscore_data]
    total_list = []
    for difficulty in Difficulty:
        total_list.append([x for x in highscore_data if x[0] == difficulty.name])

    stdscr.clear()
    logo(stdscr)
    stdscr.addstr(f'[')
    stdscr.addstr('1', curses.color_pair(1))
    if len(total_list[0]) > 0:
        stdscr.addstr(f'] Beginner     ({beginner_width}x{beginner_height}) | {beginner_ratio:.2%} | HS: {total_list[0][0][1]} {total_list[0][0][2]}\n')
    else:
        stdscr.addstr(f'] Beginner     ({beginner_width}x{beginner_height}) | {beginner_ratio:.2%}\n')
    stdscr.addstr(f'[')
    stdscr.addstr('2', curses.color_pair(2))
    if len(total_list[1]) > 0:
        stdscr.addstr(f'] Intermediate ({intermediate_width}x{intermediate_height}) | {intermediate_ratio:.2%} | HS: {total_list[1][0][1]} {total_list[1][0][2]}\n')
    else:
        stdscr.addstr(f'] Intermediate ({intermediate_width}x{intermediate_height}) | {intermediate_ratio:.2%}\n')
    stdscr.addstr(f'[')
    stdscr.addstr('3', curses.color_pair(3))
    if len(total_list[2]) > 0:
        stdscr.addstr(f'] Expert       ({expert_width}x{expert_height}) | {expert_ratio:.2%} | HS: {total_list[2][0][1]} {total_list[2][0][2]}\n')
    else:
        stdscr.addstr(f'] Expert       ({expert_width}x{expert_height}) | {expert_ratio:.2%}\n')
    stdscr.addstr(f'[')
    stdscr.addstr('4', curses.color_pair(4))
    if len(total_list[3]) > 0:
        stdscr.addstr(f'] Custom                        | HS: {total_list[3][0][1]} {total_list[3][0][2]}\n')
    else:
        stdscr.addstr(f'] Custom\n')
    stdscr.addstr('\n')

    display = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
    for row in display:
        for cell in row:
            stdscr.addstr('[')
            cell.display(stdscr, config["LOOK"]["SYMBOLS"])
            stdscr.addstr(']')
        stdscr.addstr('\n')
    stdscr.refresh()

    while True:
        try:
            key = stdscr.getkey(0, 0)
        except Exception as e:
            key = curses.ERR
        if key == config["CONTROLS"]["KEYBOARD"]["EXIT"]:
            curses.nocbreak()
            stdscr.keypad(False)
            curses.echo()
            curses.curs_set(1)
            stdscr.nodelay(False)
            curses.endwin()
            exit()
        if key == '1':
            board = Board(int(beginner_width), int(beginner_height), float(beginner_ratio), Difficulty.BEGINNER, config, stdscr, no_flash)
            break
        elif key == '2':
            board = Board(int(intermediate_width), int(intermediate_height), float(intermediate_ratio), Difficulty.INTERMEDIATE, config, stdscr, no_flash)
            break
        elif key == '3':
            board = Board(int(expert_width), int(expert_height), float(expert_ratio), Difficulty.EXPERT, config, stdscr, no_flash)
            break
        elif key == '4':
            min_width = config["SETUP"]['MIN_WIDTH']
            min_height = config["SETUP"]['MIN_HEIGHT']
            max_width = config["SETUP"]['MAX_WIDTH']
            max_height = config["SETUP"]['MAX_HEIGHT']
            custom_width = ''
            while not custom_width.isdigit():
                stdscr.clear()
                logo(stdscr)
                custom_width = raw_input(stdscr, 7, 0, f"width (min: {min_width}, max: {max_width}): ").lower()
                if custom_width.isdigit():
                    if min_width and int(custom_width) < min_width:
                        custom_width = 'NaN'
                    if max_width and int(custom_width) > max_width:
                        custom_width = 'NaN'
                if custom_width == '':
                    custom_width = config["SETUP"]["BEGINNER"]["WIDTH"]
            custom_height = ''
            while not custom_height.isdigit():
                stdscr.clear()
                logo(stdscr)
                stdscr.addstr(f'width: {custom_width}')
                custom_height = raw_input(stdscr, 8, 0, "height: ").lower()
                if custom_height.isdigit():
                    if min_height and int(custom_height) < min_height:
                        custom_height = 'NaN'
                    if max_height and int(custom_height) > max_height:
                        custom_height = 'NaN'
                if custom_height == '':
                    custom_height = config["SETUP"]["BEGINNER"]["HEIGHT"]
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
            board = Board(int(custom_width), int(custom_height), float(custom_ratio), Difficulty.CUSTOM, config, stdscr, no_flash)
            break

    curses.noecho()
    main_loop(stdscr, board, config)


def main_loop(stdscr: curses.window, board: Board, config: dict) -> None:
    keyboard = config["CONTROLS"]["KEYBOARD"]
    mouse = config["CONTROLS"]["MOUSE"]
    help_str = control_str(keyboard["HELP"], mouse["HELP"])
    stdscr.clear()
    board.display()
    stdscr.refresh()

    while True:
        try:
            key = stdscr.getkey(0, 0)
        except Exception as e:
            key = curses.ERR
        if key == keyboard["EXIT"]:
            break
        elif key == keyboard["HELP"]:
            board.pause()
            show_help(stdscr, config)
        elif key == keyboard["LEFT"]:
            board.left()
        elif key == keyboard["RIGHT"]:
            board.right()
        elif key == keyboard["UP"]:
            board.up()
        elif key == keyboard["DOWN"]:
            board.down()
        elif key == keyboard["REVEAL"]:
            board.reveal()
        elif key == keyboard["FLAG"]:
            board.flag()
        elif key == keyboard["RESET"]:
            board.reset()
        elif key == keyboard["HOME"]:
            board.home()
        elif key == keyboard["END"]:
            board.end()
        elif key == keyboard["FLOOR"]:
            board.floor()
        elif key == keyboard["CEILING"]:
            board.ceiling()
        elif key == 'KEY_MOUSE':
            try:
                _, mx, my, _, bstate = curses.getmouse()
                if mouse["EXIT"] and (bstate & getattr(curses, mouse["EXIT"])):
                    break
                elif mouse["HELP"] and (bstate & getattr(curses, mouse["HELP"])):
                    board.pause()
                    show_help(stdscr, config)
                elif mouse["LEFT"] and (bstate & getattr(curses, mouse["LEFT"])):
                    board.left()
                elif mouse["RIGHT"] and (bstate & getattr(curses, mouse["RIGHT"])):
                    board.right()
                elif mouse["UP"] and (bstate & getattr(curses, mouse["UP"])):
                    board.up()
                elif mouse["DOWN"] and (bstate & getattr(curses, mouse["DOWN"])):
                    board.down()
                elif mouse["REVEAL"] and (bstate & getattr(curses, mouse["REVEAL"])):
                    board.set_cursor_from_mouse(mx, my)
                    board.reveal()
                elif mouse["FLAG"] and (bstate & getattr(curses, mouse["FLAG"])):
                    board.set_cursor_from_mouse(mx, my)
                    board.flag()
                elif mouse["HOME"] and (bstate & getattr(curses, mouse["HOME"])):
                    board.home()
                elif mouse["END"] and (bstate & getattr(curses, mouse["END"])):
                    board.end()
                elif mouse["FLOOR"] and (bstate & getattr(curses, mouse["FLOOR"])):
                    board.floor()
                elif mouse["CEILING"] and (bstate & getattr(curses, mouse["CEILING"])):
                    board.ceiling()
            except:
                pass
        elif key == curses.ERR:
            if board.state != GameState.PAUSED:
                board.display()
                stdscr.addstr(f'Press {help_str} for help.')
                stdscr.noutrefresh()
                stdscr.refresh()
            continue
        if board.state != GameState.PAUSED:
            stdscr.clear()
            board.display()
            stdscr.addstr(f'Press {help_str} for help.')
        stdscr.refresh()

    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    stdscr.nodelay(False)
    curses.endwin()
    exit()


if __name__ == '__main__':
    curses.wrapper(setup)
