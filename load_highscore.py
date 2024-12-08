import csv
import datetime
import math
import operator
from typing import Any

# type Any used instead of Difficulty
# not correct, but I wanted to avoid circular import here

highscore_filepath = 'highscores.csv'


def load_raw_highscores() -> [[str, str, str]]:
    raw_highscore_data: [[str, str, str]] = []

    # read in data
    with open('highscores.csv', 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ')
        for row in reader:
            # ignore blank lines
            if ''.join(row).strip() == '':
                continue
            raw_highscore_data.append(row)

    return raw_highscore_data


def load_real_highscores() -> [[Any, str, datetime.timedelta]]:
    raw_highscore_data = load_raw_highscores()
    return convert_raw_to_real(raw_highscore_data)


def convert_raw_to_real(
        raw_highscore_data: [[str, str, str]]) \
        -> [[Any, str, datetime.timedelta]]:
    # turn the score strings into timedelta objects
    # and turn the difficulty strings into Difficulty objects
    from meeleymine import Difficulty
    highscore_data: [[str, str, float]] = []
    for idx, hs in enumerate(raw_highscore_data):
        t = datetime.datetime.strptime(hs[2], '%H:%M:%S.%f')
        this_difficulty = Difficulty[hs[0]]
        this_name = hs[1]
        this_score = datetime.timedelta(hours=t.hour, minutes=t.minute,
                                        seconds=t.second,
                                        microseconds=t.microsecond)
        highscore_data.append([this_difficulty, this_name, this_score])

    return highscore_data


def convert_real_to_raw(
        real_highscore_date: [[Any, str, datetime.timedelta]]) \
        -> [[str, str, str]]:
    zero_time = datetime.datetime.today().replace(hour=0,
                                                  minute=0,
                                                  second=0,
                                                  microsecond=0)
    # convert to strings
    raw_highscore_data: [[str, str, str]]
    raw_highscore_data = [[hs[0].name,
                           hs[1],
                           f'{zero_time + hs[2]:%H:%M:%S.%f}']
                          for hs in real_highscore_date]
    return raw_highscore_data


def get_scores_for_difficulty(highscore_data: [[Any, str,
                                                datetime.timedelta]],
                              difficulty: Any) -> [datetime.timedelta]:
    # get only scores for the selected Difficulty level
    scores: [datetime.timedelta] = [x[2] for x in highscore_data
                                    if x[0] == difficulty.name]

    return scores


def load_highscores_for_difficulty(difficulty: Any) \
        -> [Any, str, datetime.timedelta]:
    return\
        [x for x in load_real_highscores() if x[0].value == difficulty.value]


def add_and_save_scores(
        highscore_data: [[Any, str, datetime.timedelta]],
        difficulty: Any,
        name: str,
        score: datetime.timedelta,
        max_scores: int) -> None:

    # add in the new score
    highscore_data.append([difficulty, name, score])
    # sort the scores
    highscore_data = sorted(highscore_data, key=operator.itemgetter(2))
    # convert to strings for output
    raw_highscore_data = convert_real_to_raw(highscore_data)

    from meeleymine import Difficulty
    # split into separate arrays per difficulty level
    total_list: [[[str, str, str]]] = []
    for difficulty in Difficulty:
        total_list.append([x for x in raw_highscore_data
                           if x[0] == difficulty.name])

    # save the newly adjusted highscores
    with open('highscores.csv', 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ')
        for idx, cat in enumerate(total_list):
            if not cat:
                continue
            if max_scores == math.inf:
                max_scores = len(cat)
            if idx == difficulty.value:
                for hs in cat[:]:
                    writer.writerow(hs)
            else:
                for hs in cat[:max_scores]:
                    writer.writerow(hs)
            # add a gap between each difficulty level
            writer.writerow('')


def generate_dummy() -> None:
    dummy = """BEGINNER AMELIA 00:01:47.776417
BEGINNER PLACID 00:03:00.000000
BEGINNER CENTUM 00:03:15.000000
BEGINNER AFRAID 00:03:30.000000
BEGINNER DEPUTY 00:03:45.000000
BEGINNER DOCTOR 00:04:00.000000
BEGINNER CACTUS 00:04:15.000000
BEGINNER ANIMAL 00:04:30.000000
BEGINNER BISHOP 00:04:45.000000
BEGINNER DRIVER 00:05:00.000000

INTERMEDIATE DRIVER 00:05:00.000000
INTERMEDIATE AMELIA 00:05:05.829190
INTERMEDIATE AMELIA 00:06:23.520259
INTERMEDIATE DOCTOR 00:09:00.000000
INTERMEDIATE ANIMAL 00:09:30.000000
INTERMEDIATE BISHOP 00:09:45.000000
INTERMEDIATE CACTUS 00:11:15.000000
INTERMEDIATE PLACID 00:12:00.000000
INTERMEDIATE AFRAID 00:12:30.000000
INTERMEDIATE DEPUTY 00:12:45.000000

EXPERT DRIVER 00:05:00.000000
EXPERT AFRAID 00:09:30.000000
EXPERT DEPUTY 00:10:45.000000
EXPERT DOCTOR 00:13:00.000000
EXPERT CACTUS 00:15:15.000000
EXPERT ANIMAL 00:18:30.000000
EXPERT CENTUM 00:24:15.000000
EXPERT BISHOP 00:24:45.000000
EXPERT DRIVER 00:25:00.000000
EXPERT PLACID 00:35:00.000000
"""
    with open(highscore_filepath, 'w+') as f:
        f.write(dummy)


def generate_dummy_if_needed() -> None:
    try:
        with open(highscore_filepath, 'r'):
            pass
    except FileNotFoundError:
        generate_dummy()


if __name__ == '__main__':
    generate_dummy()
