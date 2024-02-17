# https://gist.github.com/bryanhelmig/2cc72b92e5d3c6afd71ed86c8247a4f8
import itertools
import math
import re
from operator import itemgetter


def tokenize_keyboard(board):
    return [list(row.strip()) for row in board]


def invert_grid(grid):
    out = {}
    for row_i, row in enumerate(grid):
        for col_i, cell in enumerate(row):
            if cell:
                out[cell] = (float(row_i), float(col_i))
    return out


KEYBOARD = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/'],
    ['', '', '', '', ' ', '', '', '', '', ''],
]
KEYBOARD_GRID = invert_grid(KEYBOARD)

SHIFTED_KEYBOARD = [
    ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+'],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '|'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?'],
    ['', '', '', '', ' ', '', '', '', '', ''],
]
SHIFTED_KEYBOARD_GRID = invert_grid(SHIFTED_KEYBOARD)


def get_distance(a, b):
    a_pos = KEYBOARD_GRID.get(a) or SHIFTED_KEYBOARD_GRID.get(a)
    b_pos = KEYBOARD_GRID.get(b) or SHIFTED_KEYBOARD_GRID.get(b)
    if a_pos and b_pos:
        return math.hypot(a_pos[0] - b_pos[0], a_pos[1] - b_pos[1])
    return 0.0


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def find_longest_word(word_list):
    longest_word = max(word_list, key=len)
    return longest_word


def get_letters(string):
    all_freq = {}

    for i in string:
        if i in all_freq:
            all_freq[i] += 1
        else:
            all_freq[i] = 1
    return all_freq


def score_not_mashing(text):
    "Returns a float - higher score is less likely to be mashing."
    distance = 0.0
    for a, b in pairwise(text):
        distance += (get_distance(a, b) - 1)

    return distance / len(text)


def is_mashing(text: str, cutoff=1.75):
    return score_not_mashing(text) < cutoff


ignorefilter = ['mississippi', 'triggering', 'interesting', "relatable", "disengage"]


def is_keysmash(text):
    # print(text)
    if len(find_longest_word(text)) <= 9 and not (len(text) >= 9 and text.count(' ') == 0):
        # print('no for length')
        return False
    if any(word in text for word in ignorefilter):
        # print('no for ignorefilter')
        return False
    if text.count(' ') > 2:
        # print('no for spaces')
        return False
    # if not (text.upper() == text or text.lower() == text):
    #     return False
    punc = set('/\\\'";:.,><?|()*&^%$#@!')
    if any((c in text) for c in punc):
        return False
    letters = get_letters(text)
    top_letters = dict(sorted(letters.items(), key=itemgetter(1), reverse=True)[:5])
    a = 0

    if list(top_letters.values())[-1] > 3:

        for value in letters.values():
            if value >= list(top_letters.values())[-1]:
                a += value
    else:
        a = sum([value for value in top_letters.values()])

    topkey = list(top_letters.keys())[0]
    if max(len(x) for x in re.findall(r'[%s]+' % topkey, text)) > top_letters[topkey] * (2 / 3):
        return False
    # print(a / len(text))
    # print(top_letters)
    # return len(text)/len(get_letters(text)) > 2.5
    return a / len(text) > 0.68
    # if a/len(text) > 0.7:
    #     return True
    # if sum(top_letters.values()) > len(text) / 2:
    #     return True
    # return False


if __name__ == '__main__':
    print(is_keysmash('Bahsjrjdsnbsbdkdjdlehhb'))
    print(is_keysmash('Qvdjhankqkdhabdk'))
    print(is_keysmash("ndndjejdndnrnendn"))
    print(is_keysmash("wdahiaulhlifwahiowfhioawhfil"))
    print(is_keysmash('Cnjdjdjdjjdjdjsjskss'))
    print(is_keysmash('ioawdioawjioawdjawdjiodioaw'))
    print(is_keysmash('Jdjdjsjsjsskkdkd'))
    print(is_keysmash('Jdjsjsjdjsj'))
    print(is_keysmash('spspspsp'))
    print(is_keysmash("hey im ava"))
    print(is_keysmash("antidisestablishmentarianism"))
