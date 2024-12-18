import curses
import math
import os.path
import shutil

import yaml

config_path = 'config.yaml'


def load_config() -> dict:
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = generate_new_config()

    if config is None:
        config = {}

    config = initialize_structure(config)
    type_check_values(config)
    value_check_values(config)
    config = replace_hex(config)
    config = replace_none_default_colors(config)
    config = put_controls_in_list(config)
    return fill_uninitialized_values(config)


def generate_new_config() -> dict:
    if os.path.isfile('config_template.yaml'):
        shutil.copy('config_template.yaml', config_path)
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    config = default_config()
    with open(config_path, 'w') as outfile:
        yaml.safe_dump(config, outfile,
                       sort_keys=False, indent=4, width=79, allow_unicode=True)

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def default_config() -> dict:
    return {'CONTROLS': {'LEFT': ['KEY_LEFT'],
                         'RIGHT': ['KEY_RIGHT'],
                         'UP': ['KEY_UP'],
                         'DOWN': ['KEY_DOWN'],
                         'REVEAL': [' ', '\n', 'BUTTON1_CLICKED'],
                         'FLAG': ['f', 'BUTTON3_CLICKED'],
                         'RESET': ['r'],
                         'HOME': ['KEY_HOME'],
                         'END': ['KEY_END'],
                         'CEILING': ['KEY_PPAGE'],
                         'FLOOR': ['KEY_NPAGE'],
                         'HELP': ['h'],
                         'HIGHSCORES': ['p'],
                         'MENU': ['m'],
                         'EXIT': ['q']
                         },
            'SETUP': {'OPEN_START': False,
                      'CHORDING': True,
                      'LOCK_FLAGS': True,
                      'NO_FLASH': False,
                      'WRAP_AROUND': True,
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
                                 'RATIO': 0.206}},
            'HIGHSCORES': {'MAX_NAME_LENGTH': 6,
                           'BEGINNER_MAX': 10,
                           'INTERMEDIATE_MAX': 10,
                           'EXPERT_MAX': 10,
                           'CUSTOM_MAX': 10},
            'LOOK': {'SYMBOLS': {'BLANK': ' ',
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
                                 'UNOPENED': '■'},
                     'COLORS': {'DEFAULT': {'BG': 0,
                                            'FG': 7,
                                            'ONE': 4,
                                            'TWO': 2,
                                            'THREE': 1,
                                            'FOUR': 3,
                                            'FIVE': 5,
                                            'SIX': 6,
                                            'SEVEN': 8,
                                            'EIGHT': 7,
                                            'MINE': 7,
                                            'FLAG': 7,
                                            'UNOPENED': 8,
                                            'SELECTOR': 3,
                                            'LOSE': 1,
                                            'WIN': 2,
                                            'BRACKETS': 8},
                                # https://lospec.com/palette-list/sweetie-16
                                'RGB': {'BG': '#1a1c2c',
                                        'FG': '#f4f4f4',
                                        'ONE': '#41a6f6 ',
                                        'TWO': '#38b764',
                                        'THREE': '#b13e53',
                                        'FOUR': '#3b5dc9',
                                        'FIVE': '#5d275d',
                                        'SIX': '#257179',
                                        'SEVEN': '#566c86',
                                        'EIGHT': '#94b0c2',
                                        'MINE': '#f4f4f4',
                                        'FLAG': '#f4f4f4',
                                        'UNOPENED': '#566c86',
                                        'SELECTOR': '#ffcd75',
                                        'LOSE': '#b13e53',
                                        'WIN': '#a7f070',
                                        'BRACKETS': '#333c57'}}}}


def initialize_structure(config: dict) -> dict:
    hard_coded = default_config()

    if not config.get('CONTROLS'):
        config['CONTROLS'] = {}
    for k_n, k_v in hard_coded['CONTROLS'].items():
        if config['CONTROLS'].get(k_n) is None:
            config['CONTROLS'][k_n] = None

    if not config.get('SETUP'):
        config['SETUP'] = {}
    for k_n, k_v in hard_coded['SETUP'].items():
        if config['SETUP'].get(k_n) is None:
            config['SETUP'][k_n] = None
    from meeleymine import Difficulty
    for d in Difficulty:
        if d == Difficulty.CUSTOM:
            continue
        if config['SETUP'].get(d.name) is None:
            config['SETUP'][d.name] = {}
    for d in Difficulty:
        if d == Difficulty.CUSTOM:
            continue
        if config['SETUP'][d.name].get('WIDTH') is None:
            config['SETUP'][d.name]['WIDTH'] = None
        if config['SETUP'][d.name].get('HEIGHT') is None:
            config['SETUP'][d.name]['HEIGHT'] = None
        if config['SETUP'][d.name].get('RATIO') is None:
            config['SETUP'][d.name]['RATIO'] = None

    if not config.get('HIGHSCORES'):
        config['HIGHSCORES'] = {}
    for k_n, k_v in hard_coded['HIGHSCORES'].items():
        if config['HIGHSCORES'].get(k_n) is None:
            config['HIGHSCORES'][k_n] = None

    if not config.get('LOOK'):
        config['LOOK'] = {}
    if not config['LOOK'].get('SYMBOLS'):
        config['LOOK']['SYMBOLS'] = {}
    for k_n, k_v in hard_coded['LOOK']['SYMBOLS'].items():
        if config['LOOK']['SYMBOLS'].get(k_n) is None:
            config['LOOK']['SYMBOLS'][k_n] = None

    if not config['LOOK'].get('COLORS'):
        config['LOOK']['COLORS'] = {}
    if not config['LOOK']['COLORS'].get('DEFAULT'):
        config['LOOK']['COLORS']['DEFAULT'] = {}
    for k_n, k_v in hard_coded['LOOK']['COLORS']['DEFAULT'].items():
        if config['LOOK']['COLORS']['DEFAULT'].get(k_n) is None:
            config['LOOK']['COLORS']['DEFAULT'][k_n] = None
    if not config['LOOK']['COLORS'].get('RGB'):
        config['LOOK']['COLORS']['RGB'] = {}
    for k_n, k_v in hard_coded['LOOK']['COLORS']['RGB'].items():
        if config['LOOK']['COLORS']['RGB'].get(k_n) is None:
            config['LOOK']['COLORS']['RGB'][k_n] = None

    return config


def fill_uninitialized_values(config: dict) -> dict:
    hard_coded = default_config()

    # adding hardcoded values for controls if none are specified

    always_set = ['LEFT', 'RIGHT', 'UP', 'DOWN', 'REVEAL', 'FLAG', 'RESET',
                  'HELP', 'MENU', 'EXIT']
    for k in always_set:
        if config['CONTROLS'].get(k) is None:
            config['CONTROLS'][k] = hard_coded['CONTROLS'][k]

    # adding hardcoded values for setup if none are specified
    hard_coded_setup = hard_coded['SETUP']
    if config['SETUP'].get('OPEN_START') is None:
        config['SETUP']['OPEN_START'] = hard_coded['SETUP']['OPEN_START']
    if config['SETUP'].get('CHORDING') is None:
        config['SETUP']['CHORDING'] = hard_coded['SETUP']['CHORDING']
    if config['SETUP'].get('LOCK_FLAGS') is None:
        config['SETUP']['LOCK_FLAGS'] = hard_coded['SETUP']['LOCK_FLAGS']
    if config['SETUP'].get('NO_FLASH') is None:
        config['SETUP']['NO_FLASH'] = hard_coded['SETUP']['NO_FLASH']
    if config['SETUP'].get('WRAP_AROUND') is None:
        config['SETUP']['WRAP_AROUND'] = hard_coded['SETUP']['WRAP_AROUND']
    if config['SETUP'].get('MIN_WIDTH') is None:
        config['SETUP']['MIN_WIDTH'] = hard_coded_setup['MIN_WIDTH']
    if config['SETUP'] and config['SETUP'].get('MIN_HEIGHT') is None:
        config['SETUP']['MIN_HEIGHT'] = hard_coded_setup['MIN_HEIGHT']
    if config['SETUP'] and config['SETUP'].get('MAX_WIDTH') is None:
        config['SETUP']['MAX_WIDTH'] = hard_coded_setup['MAX_WIDTH']
    if config['SETUP'] and config['SETUP'].get('MAX_HEIGHT') is None:
        config['SETUP']['MAX_HEIGHT'] = hard_coded_setup['MAX_HEIGHT']
    from meeleymine import Difficulty
    for d in Difficulty:
        for b_n, b_v in hard_coded_setup.get(d.name, {}).items():
            if config['SETUP'][d.name].get(b_n) is None:
                config['SETUP'][d.name][b_n] = b_v

    # adding hardcoded values for highscores if none are specified
    # hard_coded_highscore = hard_coded['HIGHSCORES']
    hard_coded_highscore = {'MAX_NAME_LENGTH': math.inf,
                            'BEGINNER_MAX': math.inf,
                            'INTERMEDIATE_MAX': math.inf,
                            'CUSTOM_MAX': math.inf}
    for hs_n, hs_v in hard_coded_highscore.items():
        if config['HIGHSCORES'].get(hs_n) is None:
            config['HIGHSCORES'][hs_n] = hs_v

    # adding hardcoded values for symbols if none are specified
    hard_coded_symbols = hard_coded['LOOK']['SYMBOLS']
    for b_n, b_v in hard_coded_symbols.items():
        if config['LOOK']['SYMBOLS'].get(b_n) is None:
            config['LOOK']['SYMBOLS'][b_n] = b_v

    # adding hardcoded values for colors if none are specified
    hard_coded_colors = hard_coded['LOOK']['COLORS']['DEFAULT']
    for c_n, c_v in hard_coded_colors.items():
        if config['LOOK']['COLORS']['DEFAULT'].get(c_n) is None:
            config['LOOK']['COLORS']['DEFAULT'][c_n] = c_v
    for c_n, c_v in hard_coded_colors.items():
        if config['LOOK']['COLORS']['RGB'].get(c_n) is None:
            config['LOOK']['COLORS']['RGB'][c_n] = None

    return config


def type_check_values(config: dict):
    # CONTROLS
    for k_n, k_v in config['CONTROLS'].items():
        if k_v is None:
            continue
        if not isinstance(k_v, list) and not isinstance(k_v, str):
            raise TypeError(f'Config for CONTROLS:{k_n}'
                            f' must be of type list or str.')
        else:
            for idx, i in enumerate(config['CONTROLS'][k_n]):
                if i is None:
                    continue
                if not isinstance(i, str):
                    raise TypeError(f'Config for CONTROLS:{k_n}[{idx}]'
                                    f' must be of type str.')

    # SETUP
    if (not isinstance(config['SETUP']['OPEN_START'], bool)
            and config['SETUP']['OPEN_START'] is not None):
        raise TypeError(f'Config for SETUP:OPEN_START must be of type bool.')
    if (not isinstance(config['SETUP']['CHORDING'], bool)
            and config['SETUP']['CHORDING'] is not None):
        raise TypeError(f'Config for SETUP:CHORDING must be of type bool.')
    if (not isinstance(config['SETUP']['LOCK_FLAGS'], bool)
            and config['SETUP']['LOCK_FLAGS'] is not None):
        raise TypeError(f'Config for SETUP:LOCK_FLAGS must be of type bool.')
    if (not isinstance(config['SETUP']['NO_FLASH'], bool)
            and config['SETUP']['NO_FLASH'] is not None):
        raise TypeError(f'Config for SETUP:NO_FLASH must be of type bool.')
    if (not isinstance(config['SETUP']['WRAP_AROUND'], bool)
            and config['SETUP']['WRAP_AROUND'] is not None):
        raise TypeError(f'Config for SETUP:WRAP_AROUND must be of type bool.')
    try:
        int(config['SETUP']['MIN_WIDTH'])
    except (ValueError, TypeError):
        if config['SETUP']['MIN_WIDTH'] is not None:
            raise TypeError(f'Config for SETUP:MIN_WIDTH must be of type int.')
    try:
        int(config['SETUP']['MIN_HEIGHT'])
    except (ValueError, TypeError):
        if config['SETUP']['MIN_HEIGHT'] is not None:
            raise TypeError(f'Config for SETUP:MIN_HEIGHT'
                            f' must be of type int.')
    try:
        int(config['SETUP']['MAX_WIDTH'])
    except (ValueError, TypeError):
        if config['SETUP']['MAX_WIDTH'] is not None:
            raise TypeError(f'Config for SETUP:MAX_WIDTH must be of type int.')
    try:
        int(config['SETUP']['MAX_HEIGHT'])
    except (ValueError, TypeError):
        if config['SETUP']['MAX_HEIGHT'] is not None:
            raise TypeError(f'Config for SETUP:MAX_HEIGHT'
                            f' must be of type int.')

    from meeleymine import Difficulty
    for d in Difficulty:
        if d == Difficulty.CUSTOM:
            continue
        try:
            int(config['SETUP'][d.name]['WIDTH'])
        except (ValueError, TypeError):
            if config['SETUP'][d.name]['WIDTH'] is not None:
                raise TypeError(
                    f'Config for SETUP:{d.name}:WIDTH must be of type int.')
        try:
            int(config['SETUP'][d.name]['HEIGHT'])
        except (ValueError, TypeError):
            if config['SETUP'][d.name]['HEIGHT'] is not None:
                raise TypeError(
                    f'Config for SETUP:{d.name}:HEIGHT must be of type int.')
        try:
            float(config['SETUP'][d.name]['RATIO'])
        except (ValueError, TypeError):
            if config['SETUP'][d.name]['RATIO'] is not None:
                raise TypeError(
                    f'Config for SETUP:{d.name}:RATIO must be of type float.')

    # HIGHSCORES
    for k_n, k_v in config['HIGHSCORES'].items():
        if k_v is None:
            continue
        try:
            int(k_v)
        except (ValueError, TypeError):
            raise TypeError(
                f'Config for HIGHSCORES:{k_n} must be of type int.')

    # LOOK: SYMBOLS
    for k_n, k_v in config['LOOK']['SYMBOLS'].items():
        if not isinstance(k_v, str) and k_v is not None:
            raise TypeError(f'Config for LOOK:SYMBOLS:{k_n}'
                            f' must be of type str.')

    # LOOK: COLORS
    for k_n, k_v in config['LOOK']['COLORS']['DEFAULT'].items():
        if k_v is None:
            continue
        try:
            int(k_v)
        except (ValueError, TypeError):
            raise TypeError(f'Config for LOOK:COLORS:DEFAULT:{k_n}'
                            f' must be of type int.')

    for k_n, k_v in config['LOOK']['COLORS']['RGB'].items():
        if k_v is None:
            continue
        if not isinstance(k_v, list) and not isinstance(k_v, str):
            raise TypeError(f'Config for LOOK:COLORS:DEFAULT:RGB:{k_n}'
                            f' must be of type list or str (hex).')
        elif isinstance(k_v, list):
            try:
                for i in config['LOOK']['COLORS']['RGB'][k_n]:
                    int(i)
            except (ValueError, TypeError):
                raise TypeError(f'Config for LOOK:COLORS:DEFAULT:RGB{k_n}'
                                f' must be a list of type int.')


def value_check_values(config: dict):
    # CONTROLS
    for k_n, k_v in config['CONTROLS'].items():
        if k_v is None:
            continue
        if isinstance(k_v, list):
            for idx, i in enumerate(config['CONTROLS'][k_n]):
                if i is None:
                    continue
                if len(i) == 1 and i in ((r' `1234567890-=qwertyuiop[]\asdfgh'
                                          r'jkl;zxcvbnm,./~!@#$%^&*()_+QWERTY'
                                          r'UI OP{}|ASDFGHJKL:"ZXCVBNM<>?')
                                         + "'\n"):
                    continue
                try:
                    getattr(curses, str(i))
                except AttributeError:
                    raise ValueError(f'{i} is not acceptable for'
                                     f' CONTROLS:{k_n}[{idx}].')

    # SETUP
    if (config['SETUP']['MIN_WIDTH'] is not None
            and int(config['SETUP']['MIN_WIDTH']) < 1):
        raise ValueError(f'Config at SETUP:MIN_WIDTH cannot be less than 1.')
    if (config['SETUP']['MIN_HEIGHT'] is not None
            and int(config['SETUP']['MIN_HEIGHT']) < 1):
        raise ValueError(f'Config at SETUP:MIN_HEIGHT cannot be less than 1.')
    if (config['SETUP']['MAX_WIDTH'] is not None
            and int(config['SETUP']['MAX_WIDTH']) < 2):
        raise ValueError(f'Config at SETUP:MAX_WIDTH cannot be less than 2.')
    if (config['SETUP']['MAX_HEIGHT'] is not None
            and int(config['SETUP']['MAX_HEIGHT']) < 2):
        raise ValueError(f'Config at SETUP:MAX_HEIGHT cannot be less than 2.')

    from meeleymine import Difficulty
    for d in Difficulty:
        if d == Difficulty.CUSTOM:
            continue
        if (config['SETUP'][d.name]['WIDTH'] is not None
                and int(config['SETUP'][d.name]['WIDTH']) < 2):
            raise ValueError(
                f'Config at SETUP:{d.name}:WIDTH cannot be less than 2.')
        if (config['SETUP'][d.name]['HEIGHT'] is not None
                and int(config['SETUP'][d.name]['HEIGHT']) < 2):
            raise ValueError(
                f'Config at SETUP:{d.name}:HEIGHT cannot be less than 2.')
        if (config['SETUP'][d.name]['RATIO'] is not None
                and float(config['SETUP'][d.name]['RATIO']) < 0):
            raise ValueError(
                f'Config at SETUP:{d.name}:RATIO cannot be less than 0.')
        if (config['SETUP'][d.name]['RATIO'] is not None and float(
                config['SETUP'][d.name]['RATIO']) > 1):
            raise ValueError(
                f'Config at SETUP:{d.name}:RATIO cannot be greater than 1.')

    # HIGHSCORES
    if config['HIGHSCORES']['MAX_NAME_LENGTH'] is not None and int(
            config['HIGHSCORES']['MAX_NAME_LENGTH']) < 1:
        raise ValueError(
            f'Config at HIGHSCORES:MAX_NAME_LENGTH cannot be less than 1.')
    for k_n, k_v in config['HIGHSCORES'].items():
        if k_n == 'MAX_NAME_LENGTH' or k_v is None:
            continue
        if k_v < 0:
            raise ValueError(
                f'Config at HIGHSCORES:{k_n} cannot be less than 0.')

    # LOOK: COLORS
    for k_n, k_v in config['LOOK']['COLORS']['DEFAULT'].items():
        if k_v is None:
            continue
        if int(k_v) < -1:
            raise ValueError(f'Config at LOOK:COLORS:DEFAULT:{k_n}'
                             f' cannot be less than -1')

    for k_n, k_v in config['LOOK']['COLORS']['RGB'].items():
        if k_v is None:
            continue
        if isinstance(k_v, list):
            if len(k_v) != 3:
                raise ValueError(f'Config at LOOK:COLORS:RGB:{k_n}'
                                 f' must be a list of length 3.')
            else:
                for i in k_v:
                    if i < 0:
                        raise ValueError(
                            f'Config at LOOK:COLORS:RGB:{k_n}[{i}]'
                            f' must be greater than 0.')
                    if i > 1000:
                        raise ValueError(
                            f'Config at LOOK:COLORS:RGB:{k_n}[{i}]'
                            f' must be less than 1000.')
        elif isinstance(k_v, str):
            if not is_hex(k_v):
                raise ValueError(f'Config at LOOK:COLORS:RGB:{k_n} is not a '
                                 f'valid hex code.')


def is_hex(hex_color: str) -> bool:
    h = hex_color.lstrip('#').strip().upper()
    if len(h) != 6:
        return False
    for c in h:
        if c not in '0123456789ABCDEF':
            return False
    return True


def replace_hex(config: dict) -> dict:
    for k_n, k_v in config['LOOK']['COLORS']['RGB'].items():
        if k_v is None:
            continue
        if isinstance(k_v, list):
            continue
        if isinstance(k_v, str):
            config['LOOK']['COLORS']['RGB'][k_n] = hex_to_list(k_v)
    return config


def replace_none_default_colors(config: dict) -> dict:
    for k_n, k_v in config['LOOK']['COLORS']['DEFAULT'].items():
        if k_v is None:
            config['LOOK']['COLORS']['DEFAULT'][k_n] = -1
    return config


def hex_to_list(hex_color: str) -> [int]:
    h = hex_color.lstrip('#').strip().upper()
    lv = len(h)
    t = [int(h[i:i + lv // 3], 16) for i in range(0, lv, lv // 3)]
    return [(1000 * i) // 255 for i in t]


def put_controls_in_list(config: dict) -> dict:
    for k_n, k_v in config['CONTROLS'].items():
        if isinstance(k_v, str):
            config['CONTROLS'][k_n] = [k_v]
    return config


if __name__ == '__main__':
    generate_new_config()
