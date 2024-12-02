# AmeliaSweep
*A terminal based minesweeper application*

## How to run:
To run:\
`python main.py`

You can also specify the width and height of the board using the `-W` and `-H` options:\
`python main.py -W 15 -H 10`

You can also specify the ratio of mines in the board as a float between 0 and 1:\
`python main.py -r 0.15`

If no ratio is given the default number of mines will be equal to the square root of the board area.

The game has some flash effects. If that is something you may be sensitive to please run with the `no-flash` option:\
`python main.py --no-flash`


## How to play:
### Game Selection:
If no custom arguments were passed in on the command line, the game will open to a main menu which will allow you to select your difficulty level, or set a custom game.

If you are just starting out, simply press `1` on the main menu to start a `Beginner` game (9x9 board).

Games with larger boards may immediately crash. This is due to your terminal not having enough room. Try resizing it or reducing your font size.

### Controls:
- Use the `arrow keys` to move the cursor around the board.
- Use the `space bar` to open a cell.
- Use the `f` key to place a flag.
- Press `r` to reset the game.

### Rules:
- If you open a mined cell (represented by a `¤`), the game ends.
- Otherwise, the opened cell displays either a number, indicating the number of mines diagonally and/or adjacent to it, or a blank cell.
- If the opened cell is a blank cell, all adjacent non-mined cells will automatically be opened.
- You can also flag a cell (represented by a `¶`), to denote you believe there is a mine in that spot.\
Flagged cells are still considered unopened, and you can still open them.
- In order to win you must open all non-mined cells.

If any of your controls are not working it could be due to your terminal. You can change the default controls in the configuration file. (More on this later).

*Hint: you can use `Home`, `End`, `PageUp`, and `PageDown` to traverse faster*

## Game Customization:
Highscores can only be distinguished for the preset difficulties. Custom games all have the label `CUSTOM`. You can modify what your own presets look like by modifying the values in the `config.yaml` file under `SETUP`. This allows you to define the board height, width, and ratio of mines. The ratio should be a value between 0 and 1.

Note: If you modify these values the highscores will persist for the old settings. You may want to clear out the highscore file.

## Highscore Customization
By default, saved names will be shortened to 6 characters. And only the top 10 in each category will be saved. If there are less then 10 highscores in a category then any score will count as a highscore.

The name length and highscore list length can be modified in the `config.yaml` under the section labeled `HIGHSCORES`.

## Control Customization:
### Keyboard:
In the configuration file there is a section labeled `KEYBOARD` under `CONTROLS` which allows you to change the default key bindings for each action.

The notation used is `curses` KeyCodes.\
A list of available `curses` Keycodes can be found at the bottom of this `README.md`.

On some terminals keys may not produce the KeyCodes you expect.\
For example the left arrow may produce an `A` instead of a `KEY_LEFT`.

If you would like to check to see what KeyCodes your keyboard and terminal is producing, run the following script:
```python
import curses


def main(stdscr):
    while True:
        key = stdscr.getkey()
        stdscr.clear()
        stdscr.addstr(key)
        stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
```
You can use `CTRL+C` to exit this script.

### Mouse:
In the configuration file there is a section labeled `MOUSE` under `CONTROLS` which allows you to change the default mouse bindings for each action.

By default, the only actions enabled on the mouse are opening and flagging cells. A value of `NULL` indicates it is not set. 

A list of available `curses` MouseCodes can be found at the bottom of this `README.md`.

*Warning: The mouse controls can be a bit janky at times. Use with caution.*

## Look Customization:
### Symbols:
In the configuration file there is a section labeled `SYMBOLS` under `LOOK` which allows you to change the default symbols used in the program. This will allow you a high level of customization.

### Colors:
In the configuration file there is a section labeled `COLORS` under `LOOK` which allows you to change the default colors used in the program.

If your terminal does not support color then these values do not matter.

Some terminals support changing color values, which allows us to set custom RGB values.
You will see a subsection labeled `RGB` which allows you to change these values. The values are in `[Red, Green, Blue]` notation, and each color ranges from 0-1000 **(not 255)**.

If your terminal does not support rgb colors then it will fall back on the default colors, which can be seen in the subsection labeled `DEFAULT`. These are color codes.

The following are the 8 basic colors:\
`0:black, 1:red, 2:green, 3:yellow, 4:blue, 5:magenta, 6:cyan, and 7:white`

Your terminal may support even more colors, even if it does not support rgb. You can change these values to the color codes of your choice.

If you would like to see what default colors your terminal is capable of producing, run the following script:\
[Source](https://stackoverflow.com/a/22166613)
```python
import curses


def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    
    for i in range(1, curses.COLORS):
        stdscr.addstr(str(i-1) + ' ', curses.color_pair(i))

    stdscr.getch()


if __name__ == '__main__':
    curses.wrapper(main)
```

This should display all available color codes shown in their color.

---

## Curses KeyCodes
### Keyboard
[Source](https://www.gnu.org/software/guile-ncurses/manual/html_node/Getting-characters-from-the-keyboard.html)

For any normal key you can just use that key, such as 'h' for the letter 'h'.

For any sort of special function key you will want to refer to the below table.

Note that almost all of these function keys do not exist on modern keyboards.\
The standard PC keyboard cannot be depended upon to have more than (key-f 1) through (key-f 12), `KEY_PPAGE` (Page Up), `KEY_NPAGE` (Page Down), `KEY_HOME`, `KEY_END`, `KEY_IC` (Insert), `KEY_DC` (Delete), `KEY_BACKSPACE`, `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, and `KEY_RIGHT`.
<pre>
KEY_BREAK       Break key
KEY_DOWN        Arrow down
KEY_UP          Arrow up
KEY_LEFT        Arrow left
KEY_RIGHT       Arrow right
KEY_HOME        Home key
KEY_BACKSPACE   Backspace
KEY_F0          Function key zero **(through F63)**
KEY_DL          Delete line
KEY_IL          Insert line
KEY_DC          Delete character
KEY_IC          Insert char or enter insert mode
KEY_EIC         Exit insert char mode
KEY_CLEAR       Clear screen
KEY_EOS         Clear to end of screen
KEY_EOL         Clear to end of line
KEY_SF          Scroll 1 line forward
KEY_SR          Scroll 1 line backward (reverse)
KEY_NPAGE       Next page
KEY_PPAGE       Previous page
KEY_STAB        Set tab
KEY_CTAB        Clear tab
KEY_CATAB       Clear all tabs
KEY_ENTER       Enter or send
KEY_SRESET      Soft (partial) reset
KEY_RESET       Reset or hard reset
KEY_PRINT       Print or copy
KEY_LL          Home down or bottom (lower left)
KEY_A1          Upper left of keypad
KEY_A3          Upper right of keypad
KEY_B2          Center of keypad
KEY_C1          Lower left of keypad
KEY_C3          Lower right of keypad
KEY_BTAB        Back tab key
KEY_BEG         Beg(inning) key
KEY_CANCEL      Cancel key
KEY_CLOSE       Close key
KEY_COMMAND     Cmd (command) key
KEY_COPY        Copy key
KEY_CREATE      Create key
KEY_END         End key
KEY_EXIT        Exit key
KEY_FIND        Find key
KEY_HELP        Help key
KEY_MARK        Mark key
KEY_MESSAGE     Message key
KEY_MOUSE       Mouse event read
KEY_MOVE        Move key
KEY_NEXT        Next object key
KEY_OPEN        Open key
KEY_OPTIONS     Options key
KEY_PREVIOUS    Previous object key
KEY_REDO        Redo key
KEY_REFERENCE   Ref(erence) key
KEY_REFRESH     Refresh key
KEY_REPLACE     Replace key
KEY_RESIZE      Screen resized
KEY_RESTART     Restart key
KEY_RESUME      Resume key
KEY_SAVE        Save key
KEY_SBEG        Shifted beginning key
KEY_SCANCEL     Shifted cancel key
KEY_SCOMMAND    Shifted command key
KEY_SCOPY       Shifted copy key
KEY_SCREATE     Shifted create key
KEY_SDC         Shifted delete char key
KEY_SDL         Shifted delete line key
KEY_SELECT      Select key
KEY_SEND        Shifted end key
KEY_SEOL        Shifted clear line key
KEY_SEXIT       Shifted exit key
KEY_SFIND       Shifted find key
KEY_SHELP       Shifted help key
KEY_SHOME       Shifted home key
KEY_SIC         Shifted input key
KEY_SLEFT       Shifted left arrow key
KEY_SMESSAGE    Shifted message key
KEY_SMOVE       Shifted move key
KEY_SNEXT       Shifted next key
KEY_SOPTIONS    Shifted options key
KEY_SPREVIOUS   Shifted prev key
KEY_SPRINT      Shifted print key
KEY_SREDO       Shifted redo key
KEY_SREPLACE    Shifted replace key
KEY_SRIGHT      Shifted right arrow
KEY_SRESUME     Shifted resume key
KEY_SSAVE       Shifted save key
KEY_SSUSPEND    Shifted suspend key
KEY_SUNDO       Shifted undo key
KEY_SUSPEND     Suspend key
KEY_UNDO        Undo key
</pre>

### Mouse
[Source](https://tldp.org/HOWTO/NCURSES-Programming-HOWTO/mouse.html)
<pre>
BUTTON1_PRESSED          mouse button 1 down
BUTTON1_RELEASED         mouse button 1 up
BUTTON1_CLICKED          mouse button 1 clicked
BUTTON1_DOUBLE_CLICKED   mouse button 1 double clicked
BUTTON1_TRIPLE_CLICKED   mouse button 1 triple clicked
BUTTON2_PRESSED          mouse button 2 down
BUTTON2_RELEASED         mouse button 2 up
BUTTON2_CLICKED          mouse button 2 clicked
BUTTON2_DOUBLE_CLICKED   mouse button 2 double clicked
BUTTON2_TRIPLE_CLICKED   mouse button 2 triple clicked
BUTTON3_PRESSED          mouse button 3 down
BUTTON3_RELEASED         mouse button 3 up
BUTTON3_CLICKED          mouse button 3 clicked
BUTTON3_DOUBLE_CLICKED   mouse button 3 double clicked
BUTTON3_TRIPLE_CLICKED   mouse button 3 triple clicked
BUTTON4_PRESSED          mouse button 4 down
BUTTON4_RELEASED         mouse button 4 up
BUTTON4_CLICKED          mouse button 4 clicked
BUTTON4_DOUBLE_CLICKED   mouse button 4 double clicked
BUTTON4_TRIPLE_CLICKED   mouse button 4 triple clicked
BUTTON_SHIFT             shift was down during button state change
BUTTON_CTRL              control was down during button state change
BUTTON_ALT               alt was down during button state change
ALL_MOUSE_EVENTS         report all button state changes
REPORT_MOUSE_POSITION    report mouse movement
</pre>