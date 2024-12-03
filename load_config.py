import math
import os.path
import shutil

import yaml

from main import Difficulty

# TODO: maybe handle loading of highscores in here too?
config_path = 'config.yaml'


def load_config() -> dict:
    # TODO: figure out canonical location for config file
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = generate_new_config()

    if config is None:
        config = {}

    return fill_uninitialized_values(config)


def generate_new_config() -> dict:
    if os.path.isfile('config_template.yaml'):
        shutil.copy('config_template.yaml', config_path)
    else:
        raise NotImplementedError

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def fill_uninitialized_values(config: dict) -> dict:
    # adding hardcoded values for controls if none are specified
    hard_coded_keyboard = {'LEFT': 'KEY_LEFT',
                           'RIGHT': 'KEY_RIGHT',
                           'UP': 'KEY_UP',
                           'DOWN': 'KEY_DOWN',
                           'REVEAL': ' ',
                           'FLAG': 'f',
                           'RESET': 'r',
                           'HOME': 'KEY_HOME',
                           'END': 'KEY_END',
                           'CEILING': 'KEY_PPAGE',
                           'FLOOR': 'KEY_NPAGE',
                           'HELP': 'h',
                           'HIGHSCORES': 'p',
                           'EXIT': 'q'}
    if not config.get('CONTROLS'):
        config['CONTROLS'] = {}
    if not config['CONTROLS'].get('KEYBOARD'):
        config['CONTROLS']['KEYBOARD'] = {}
    if not config['CONTROLS'].get('MOUSE'):
        config['CONTROLS']['MOUSE'] = {}
    for k_n, k_v in hard_coded_keyboard.items():
        if config['CONTROLS']['KEYBOARD'].get(k_n) is None:
            config['CONTROLS']['KEYBOARD'][k_n] = None
    always_set = ['LEFT', 'RIGHT', 'UP', 'DOWN', 'REVEAL', 'FLAG', 'RESET',
                  'HELP', 'EXIT']
    for k in always_set:
        if config['CONTROLS']['KEYBOARD'].get(k) is None \
                and config['CONTROLS']['MOUSE'].get(k) is None:
            config['CONTROLS']['KEYBOARD'][k] = hard_coded_keyboard[k]

    # adding hardcoded values for setup if none are specified
    hard_code_setup = {'NO_FLASH': False,
                       'MIN_WIDTH': 2,
                       'MIN_HEIGHT': 2,
                       'MAX_WIDTH': None,
                       'MAX_HEIGHT': None,
                       'BEGINNER': {'WIDTH': '09',
                                    'HEIGHT': '09',
                                    'RATIO': 0.123},
                       'INTERMEDIATE': {'WIDTH': 16,
                                        'HEIGHT': 16,
                                        'RATIO': 0.156},
                       'EXPERT': {'WIDTH': 30,
                                  'HEIGHT': 16,
                                  'RATIO': 0.206},
                       }
    if not config.get('SETUP'):
        config['SETUP'] = {}
    if config['SETUP'].get('NO_FLASH') is None:
        config['SETUP']['NO_FLASH'] = hard_code_setup['NO_FLASH']
    if config['SETUP'].get('MIN_WIDTH') is None:
        config['SETUP']['MIN_WIDTH'] = hard_code_setup['MIN_WIDTH']
    if config['SETUP'] and config['SETUP'].get('MIN_HEIGHT') is None:
        config['SETUP']['MIN_HEIGHT'] = hard_code_setup['MIN_HEIGHT']
    if config['SETUP'] and config['SETUP'].get('MAX_WIDTH') is None:
        config['SETUP']['MAX_WIDTH'] = hard_code_setup['MAX_WIDTH']
    if config['SETUP'] and config['SETUP'].get('MAX_HEIGHT') is None:
        config['SETUP']['MAX_HEIGHT'] = hard_code_setup['MAX_HEIGHT']
    for d in Difficulty:
        for b_n, b_v in hard_code_setup.get(d.name, {}).items():
            if not config['SETUP'].get(d.name):
                config['SETUP'][d.name] = {}
            if config['SETUP'][d.name].get(b_n) is None:
                config['SETUP'][d.name][b_n] = b_v

    # adding hardcoded values for highscores if none are specified
    hard_code_highscore = {'MAX_NAME_LENGTH': math.inf,
                           'BEGINNER_MAX': math.inf,
                           'INTERMEDIATE_MAX': math.inf,
                           'CUSTOM_MAX': math.inf}
    if not config.get('HIGHSCORES'):
        config['HIGHSCORES'] = {}
    for hs_n, hs_v in hard_code_highscore.items():
        if config['HIGHSCORES'].get(hs_n) is None:
            config['HIGHSCORES'][hs_n] = hs_v

    # adding hardcoded values for symbols if none are specified
    hard_coded_symbols = {'BLANK': ' ',
                          'ONE': '1',
                          'TWO': '2',
                          'THREE': '3',
                          'FOUR': '4',
                          'FIVE': '5',
                          'SIX': '6',
                          'SEVEN': '7',
                          'EIGHT': '8',
                          'MINE': '¤',
                          'FLAG': '¶',
                          'UNOPENED': '■'}
    if not config.get('LOOK'):
        config['LOOK'] = {}
    if not config['LOOK'].get('SYMBOLS'):
        config['LOOK']['SYMBOLS'] = {}
    for b_n, b_v in hard_coded_symbols.items():
        if config['LOOK']['SYMBOLS'].get(b_n) is None:
            config['LOOK']['SYMBOLS'][b_n] = b_v

    # adding hardcoded values for colors if none are specified
    hard_coded_colors = {'ONE': 4,
                         'TWO': 2,
                         'THREE': 1,
                         'FOUR': 3,
                         'FIVE': 5,
                         'SIX': 6,
                         'SEVEN': 0,
                         'EIGHT': 7,
                         'SELECTOR': 3,
                         'LOSE': 1,
                         'WIN': 2}
    if not config['LOOK'].get('COLORS'):
        config['LOOK']['COLORS'] = {}
    if not config['LOOK']['COLORS'].get('DEFAULT'):
        config['LOOK']['COLORS']['DEFAULT'] = {}
    if not config['LOOK']['COLORS'].get('RGB'):
        config['LOOK']['COLORS']['RGB'] = {}
    for c_n, c_v in hard_coded_colors.items():
        if config['LOOK']['COLORS']['DEFAULT'].get(c_n) is None:
            config['LOOK']['COLORS']['DEFAULT'][c_n] = c_v
    for c_n, c_v in hard_coded_colors.items():
        if config['LOOK']['COLORS']['RGB'].get(c_n) is None:
            config['LOOK']['COLORS']['RGB'][c_n] = None

    return config
