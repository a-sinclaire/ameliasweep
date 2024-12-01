# Amelia Sinclaire 2024
import argparse
import curses
import datetime
from enum import Enum
import itertools
import math
import random
import yaml


# TODO:
# remove match statements to improve accessibility
# look up correct mine ratio
# add title screen that sets map difficulty
# add help menu to show controls
# high score system (keep in config?) (w/ names)
# better win lose screen
# update readme with any new changes


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
    UNOPENED = 11
    OPENED = 12

    def display(self, stdscr: curses.window, symbols: {str: str}, display_format=None):
        if self == self.FLAG and display_format:
            stdscr.addstr(symbols[self.name], display_format)
        elif self.ONE.value <= self.value <= self.EIGHT.value:
            stdscr.addstr(symbols[self.name], curses.color_pair(int(self.value)))
        else:
            stdscr.addstr(symbols[self.name])


class Board:
    neighbors = [x for x in itertools.product(range(-1, 2), range(-1, 2)) if x != (0, 0)]
    zero_time = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    def __init__(self, width: int, height: int, mine_ratio: float) -> None:
        self.start_time = None
        self.end_time = None
        self.n_wins = 0
        self.n_games = 0
        self.width = width
        self.height = height
        self.locations = list(itertools.product(range(self.height), range(self.width)))
        self.mine_ratio = mine_ratio
        self.n_mines = round(self.width * self.height * self.mine_ratio)

        # self.real_board = [[Cell.UNOPENED, Cell.FLAG, Cell.MINE, Cell.BLANK],
        #               [Cell.ONE, Cell.TWO, Cell.THREE, Cell.FOUR],
        #               [Cell.FIVE, Cell.SIX, Cell.SEVEN, Cell.EIGHT]]
        self.real_board = [[Cell.BLANK for x in range(self.width)] for y in range(self.height)]
        self.my_board = [[Cell.UNOPENED for x in range(self.width)] for y in range(self.height)]
        self.cursor = (self.height//2, self.width//2)
        self.death = (-1, -1)
        self.mines = []
        self.is_first_click = True
        self.state = GameState.PLAYING

    def reset(self) -> None:
        self.start_time = None
        self.end_time = None
        self.real_board = [[Cell.BLANK for x in range(self.width)] for y in range(self.height)]
        self.my_board = [[Cell.UNOPENED for x in range(self.width)] for y in range(self.height)]
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

    def set_cursor(self, x: int, y: int) -> None:
        # x and y are screen coordinates
        new_row = y - 2  # two for timer and win/loss counts
        new_col = (x // 3)  # to account for [ ] style
        loc = (new_row, new_col)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
            self.cursor = loc

    def move_cursor(self, x: int, y: int) -> None:
        new_row = self.cursor[0] + y
        new_col = self.cursor[1] + x
        loc = (new_row % self.height, new_col % self.width)
        if self.in_bounds(loc) and self.state == GameState.PLAYING:
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
        self.cursor = (self.cursor[0], self.width-1)

    def floor(self) -> None:
        self.cursor = (self.height-1, self.cursor[1])

    def ceiling(self) -> None:
        self.cursor = (0, self.cursor[1])

    def reveal_all(self) -> None:
        self.my_board = [[Cell.OPENED for x in range(self.width)] for y in range(self.height)]

    def reveal(self) -> None:
        curses.beep()
        if self.is_first_click:
            self.populate()
            self.is_first_click = False

        row, col = self.cursor

        if not self.in_bounds(self.cursor) or self.state != GameState.PLAYING:
            return

        if self.my_board[row][col] == Cell.OPENED:
            return

        if self.real_board[row][col] == Cell.MINE:
            self.reveal_all()
            self.death = self.cursor
            self.state = GameState.LOST
            self.end_time = datetime.datetime.now()
            self.n_games += 1
            curses.flash()
            return

        if self.real_board[row][col] == Cell.BLANK:
            self.my_board[row][col] = Cell.OPENED
            # recursively reveal 8 surrounding cells
            temp = self.cursor
            for n in Board.neighbors:
                self.cursor = [sum(x) for x in zip((row, col), n)]
                self.reveal()
                self.check_win()
            self.cursor = temp
            return

        self.my_board[row][col] = Cell.OPENED
        self.check_win()
        return

    def check_win(self) -> None:
        won = sum(x.count(Cell.UNOPENED) + x.count(Cell.FLAG) for x in self.my_board) == self.n_mines
        if won:
            self.state = GameState.WON
            self.end_time = datetime.datetime.now()
            self.n_wins += 1
            self.n_games += 1
            for m in self.mines:
                self.my_board[m[0]][m[1]] = Cell.FLAG

    def flag(self) -> None:
        row, col = self.cursor
        if not self.in_bounds(self.cursor):
            return
        if self.my_board[row][col] == Cell.UNOPENED:
            self.my_board[row][col] = Cell.FLAG
            return
        if self.my_board[row][col] == Cell.FLAG:
            self.my_board[row][col] = Cell.UNOPENED
            return

    def display(self, stdscr: curses.window, symbols: {str: str}) -> None:
        if curses.has_colors():
            selector_format = curses.A_BLINK | curses.color_pair(9) | curses.A_BOLD
            death_format = curses.A_BLINK | curses.color_pair(10) | curses.A_BOLD
            win_format = curses.A_BLINK | curses.color_pair(11) | curses.A_BOLD
        else:
            selector_format = curses.A_REVERSE | curses.color_pair(9) | curses.A_BOLD
            death_format = curses.A_REVERSE | curses.color_pair(10) | curses.A_BOLD
            win_format = curses.A_REVERSE | curses.color_pair(11) | curses.A_BOLD

        stdscr.addstr(f'{ "WINS: " + str(self.n_wins):^{(self.width * 3)//2}}')
        stdscr.addstr(f'{"LOSSES: " + str(self.n_games - self.n_wins):^{(self.width * 3) // 2}}\n')
        if self.start_time is not None and self.state == GameState.PLAYING:
            time = Board.zero_time + (datetime.datetime.now() - self.start_time)
        elif self.state != GameState.PLAYING:
            time = Board.zero_time + (self.end_time - self.start_time)
        else:
            time = Board.zero_time
        time_str = f'{time:%H:%M:%S.%f}'[:-4]
        stdscr.addstr(f'{time_str:^{self.width * 3}}\n')
        for rid, row in enumerate(self.my_board):
            for cid, cell in enumerate(row):
                if cell == Cell.OPENED:
                    cell = self.real_board[rid][cid]
                if self.cursor == (rid, cid) and self.state == GameState.PLAYING:
                    stdscr.addstr('[', selector_format)
                    cell.display(stdscr, symbols)
                    stdscr.addstr(']', selector_format)
                    continue
                if self.death == (rid, cid) and self.state == GameState.LOST:
                    stdscr.addstr('[', death_format)
                    cell.display(stdscr, symbols)
                    stdscr.addstr(']', death_format)
                    continue
                if cell == Cell.FLAG and self.state == GameState.WON:
                    stdscr.addstr('[', win_format)
                    cell.display(stdscr, symbols, win_format)
                    stdscr.addstr(']', win_format)
                    continue
                stdscr.addstr('[')
                cell.display(stdscr, symbols)
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


def init_colors(colors: {str: dict}) -> None:
    defaults: {str, int} = colors['default']
    rgbs: {str: [int]} = colors['rgb']
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        if curses.can_change_color():
            for idx, c in enumerate(rgbs.values()):
                curses.init_color(list(defaults.values())[idx], *c)
                curses.init_pair(idx+1, list(defaults.values())[idx], -1)
        else:
            for idx, c in enumerate(defaults.values()):
                curses.init_pair(idx+1, c, -1)


def setup(stdscr: curses.window) -> None:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    min_width = config['setup']['min_width']
    min_height = config['setup']['min_height']
    default_width = config['setup']['default_width']
    default_height = config['setup']['default_height']
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

    init_colors(config['look']['colors'])
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(True)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    try:
        curses.curs_set(0)
    except:
        pass

    if args.ratio is None:
        args.ratio = math.sqrt(args.width * args.height) / (args.width * args.height)
    board = Board(args.width, args.height, args.ratio)

    main_loop(stdscr, board, config)


def main_loop(stdscr: curses.window, board: Board, config: dict) -> None:
    symbols = config['look']['symbols']
    stdscr.clear()
    board.display(stdscr, symbols)
    stdscr.refresh()

    while True:
        try:
            key = stdscr.getkey(0, 0)
        except Exception as e:
            key = curses.ERR
        if key == config['controls']['exit']:
            break
        elif key == config['controls']['right']:
            board.right()
        elif key == config['controls']['left']:
            board.left()
        elif key == config['controls']['up']:
            board.up()
        elif key == config['controls']['down']:
            board.down()
        elif key == config['controls']['reveal']:
            board.reveal()
        elif key == config['controls']['flag']:
            board.flag()
        elif key == config['controls']['reset']:
            board.reset()
        elif key == config['controls']['home']:
            board.home()
        elif key == config['controls']['end']:
            board.end()
        elif key == config['controls']['floor']:
            board.floor()
        elif key == config['controls']['ceiling']:
            board.ceiling()
        elif key == 'KEY_MOUSE':
            try:
                _, mx, my, _, bstate = curses.getmouse()
                board.set_cursor(mx, my)
                if bstate & getattr(curses, config['controls']['mouse_reveal']):
                    board.reveal()
                elif bstate & getattr(curses, config['controls']['mouse_flag']):
                    board.flag()
            except:
                pass
        elif key == curses.ERR:
            board.display(stdscr, symbols)
            stdscr.noutrefresh()
            stdscr.refresh()
            continue
        stdscr.clear()
        board.display(stdscr, symbols)
        stdscr.refresh()

    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.curs_set(1)
    curses.endwin()
    exit()


if __name__ == '__main__':
    curses.wrapper(setup)
