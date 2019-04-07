#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UniEmoji: ibus engine for unicode emoji and symbols by name
#
# Copyright (c) 2013, 2015 Lalo Martins <lalo.martins@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
import re
import sys
import json
from collections import Counter, defaultdict

from difflib import SequenceMatcher

try:
    import Levenshtein
except ImportError:
    Levenshtein = None

try:
    import xdg
except ImportError:
    xdg = None
else:
    import xdg.BaseDirectory

# Get SYS_CONF_DIR here
try:
    from config import SYS_CONF_DIR
except ImportError:
    SYS_CONF_DIR = '/etc'

debug_on = True
def debug(*a, **kw):
    if debug_on:
        print(*a, **kw)

__base_dir__ = os.path.dirname(__file__)

VALID_CATEGORIES = (
    'Sc', # Symbol, currency
    'Sm', # Symbol, math
    'So', # Symbol, other
    'Pd', # Punctuation, dash
    'Po', # Punctuation, other
)

VALID_RANGES = (
    (0x0024, 0x0024), # DOLLAR SIGN
    (0x00a2, 0x00a5), # CENT SIGN, POUND SIGN, CURRENCY SIGN, YEN SIGN
    (0x00b0, 0x00b0), # DEGREE SIGN
    (0x058f, 0x058f), # ARMENIAN DRAM SIGN
    (0x060b, 0x060b), # AFGHANI SIGN
    (0x09f2, 0x09f3), # BENGALI RUPEE MARK, BENGALI RUPEE SIGN
    (0x09fb, 0x09fb), # BENGALI GANDA MARK
    (0x0af1, 0x0af1), # GUJARATI RUPEE SIGN
    (0x0bf9, 0x0bf9), # TAMIL RUPEE SIGN
    (0x0e3f, 0x0e3f), # THAI CURRENCY SYMBOL BAHT
    (0x17db, 0x17db), # KHMER CURRENCY SYMBOL RIEL
    (0x2000, 0x206f), # General Punctuation, Layout Controls, Invisible Operators
    (0x2070, 0x209f), # Superscripts and Subscripts
    (0x20a0, 0x20cf), # Currency Symbols
    (0x20d0, 0x20ff), # Combining Diacritical Marks for Symbols
    (0x2100, 0x214f), # Additional Squared Symbols, Letterlike Symbols
    (0x2150, 0x218f), # Number Forms
    (0x2190, 0x21ff), # Arrows
    (0x2200, 0x22ff), # Mathematical Operators
    (0x2300, 0x23ff), # Miscellaneous Technical, Floors and Ceilings
    (0x2336, 0x237a), # APL symbols
    (0x2400, 0x243f), # Control Pictures
    (0x2440, 0x245f), # Optical Character Recognition (OCR)
    (0x2460, 0x24ff), # Enclosed Alphanumerics
    (0x2500, 0x257f), # Box Drawing
    (0x2580, 0x259f), # Block Elements
    (0x25a0, 0x25ff), # Geometric Shapes
    (0x2600, 0x26ff), # Miscellaneous Symbols
    (0x2616, 0x2617), # Japanese Chess
    (0x2654, 0x265f), # Chess
    (0x2660, 0x2667), # Card suits
    (0x2630, 0x2637), # Yijing Trigrams
    (0x268a, 0x268f), # Yijing Monograms and Digrams
    (0x26c0, 0x26c3), # Checkers/Draughts
    (0x2700, 0x27bf), # Dingbats
    (0x27c0, 0x27ef), # Miscellaneous Mathematical Symbols-A
    (0x27f0, 0x27ff), # Supplemental Arrows-A
    (0x2800, 0x28ff), # Braille Patterns
    (0x2900, 0x297f), # Supplemental Arrows-B
    (0x2980, 0x29ff), # Miscellaneous Mathematical Symbols-B
    (0x2a00, 0x2aff), # Supplemental Mathematical Operators
    (0x2b00, 0x2bff), # Additional Shapes, Miscellaneous Symbols and Arrows
    (0xa838, 0xa838), # NORTH INDIC RUPEE MARK
    (0xfdfc, 0xfdfc), # RIAL SIGN
    (0xfe69, 0xfe69), # SMALL DOLLAR SIGN
    (0xff01, 0xff60), # Fullwidth symbols and currency signs
    (0x1f300, 0x1f5ff), # Miscellaneous Symbols and Pictographs
    (0x1f600, 0x1f64f), # Emoticons
    (0x1f650, 0x1f67f), # Ornamental Dingbats
    (0x1f680, 0x1f6ff), # Transport and Map Symbols
    (0x1f900, 0x1f9ff), # Supplemental Symbols and Pictographs
)

def in_range(code):
    return any(x <= code <= y for x,y in VALID_RANGES)

if xdg:
    SETTINGS_DIRS = list(xdg.BaseDirectory.load_config_paths('uniemoji'))
else:
    SETTINGS_DIRS = [d for d in [os.path.expanduser('~/.config/uniemoji'), '{}/xdg/uniemoji'.format(SYS_CONF_DIR)]
                     if os.path.isdir(d)]

###########################################################################
CANDIDATE_UNICODE = 0
CANDIDATE_ALIAS = 1

class UniEmojiChar(object):
    def __init__(self, unicode_str=None, is_emojione=False, is_custom=False):
        self.unicode_str = unicode_str
        self.aliasing = []
        self.is_emojione = is_emojione
        self.is_custom = is_custom

    def __repr__(self):
        return 'UniEmojiChar(unicode_str={}, is_emojione={}, is_custom={}, aliasing={})'.format(
            self.unicode_str,
            self.is_emojione,
            self.is_custom,
            self.aliasing)


class UniEmoji():
    def __init__(self):
        super(UniEmoji, self).__init__()
        self.table = defaultdict(UniEmojiChar)
        self.unicode_chars_to_names = {}
        self.unicode_chars_to_shortnames = {}
        self.ascii_table = {}
        self.reverse_ascii_table = {}
        self.alias_table = {}
        with open(os.path.join(__base_dir__, 'UnicodeData.txt'), encoding='utf-8') as unicodedata:
            for line in unicodedata.readlines():
                if not line.strip(): continue
                code, name, category, _ = line.split(';', 3)
                code = int(code, 16)
                if category not in VALID_CATEGORIES:
                    continue
                if not in_range(code):
                    continue
                name = name.lower()
                unicode_char = chr(code)
                self.table[name] = UniEmojiChar(unicode_char)
                self.unicode_chars_to_names[unicode_char] = name

        # Load emojione file
        alias_counter = Counter()
        temp_alias_table = defaultdict(set)

        emojione_data = json.load(open(os.path.join(__base_dir__, 'emojione.json'), encoding='utf-8'))
        for emoji_info in emojione_data.values():

            codepoints = emoji_info['code_points']['output']

            unicode_str = ''.join(chr(int(codepoint, 16)) for codepoint in codepoints.split('-'))
            emoji_shortname = emoji_info['shortname'][1:-1]
            self.unicode_chars_to_shortnames[unicode_str] = emoji_shortname

            emoji_shortname = emoji_shortname.replace('_', ' ')

            if emoji_shortname in self.table:
                # Check for clashes between emojione's names and the existing unicode name.
                # Clashes turn into aliases.
                if unicode_str != self.table[emoji_shortname].unicode_str:
                    self.table[emoji_shortname].aliasing.append(unicode_str)
            elif emoji_info['category'] == 'flags' and ' flag' not in emoji_info['name']:
                flag_name = 'flag of ' + emoji_info['name']
                self.table[flag_name] = UniEmojiChar(unicode_str, is_emojione=True)
                self.unicode_chars_to_names[unicode_str] = flag_name
            else:
                self.table[emoji_shortname] = UniEmojiChar(unicode_str, is_emojione=True)

            # When the string defined by emojione isn't in Unicode
            # (because it's a combination of characters), use emojione's
            # descriptive name, and set the shortname as an alias
            if unicode_str not in self.unicode_chars_to_names:
                long_name = emoji_info['name']
                self.unicode_chars_to_names[unicode_str] = long_name
                if long_name not in self.table:
                    self.table[long_name] = UniEmojiChar(unicode_str)

            for alias in emoji_info.get('keywords', []):
                alias_counter[alias] += 1
                temp_alias_table[alias].add(unicode_str)

            for ascii_aliases in emoji_info.get('ascii', []):
                self.ascii_table[ascii_aliases] = unicode_str
                self.reverse_ascii_table[unicode_str] = emoji_info['name']

        # Load less-frequent aliases from emojione file
        for alias, n in alias_counter.most_common():
            if n >= 25:
                continue
            self.table[alias].aliasing.extend(temp_alias_table[alias])

        # Load custom file(s)
        for d in reversed(SETTINGS_DIRS):
            custom_filename = os.path.join(d, 'custom.json')
            debug('Loading custom emoji from {}'.format(custom_filename))
            if os.path.isfile(custom_filename):
                custom_table = None
                try:
                    with open(custom_filename, encoding='utf-8') as f:
                        custom_table = json.loads(f.read())
                except:
                    error = sys.exc_info()[1]
                    debug(error)
                    self.table = {
                        'Failed to load custom file {}: {}'.format(custom_filename, error): 'ERROR'
                    }
                    break
                else:
                    debug(custom_table)
                    for k, v in custom_table.items():
                        self.table[k] = UniEmojiChar(v, is_custom=True)

    def _filter(self, query, limit=100):
        if len(self.table) <= 10:
            # this only happens if something went wrong; it's our cheap way of displaying errors
            return [[0, 0, message] for message in self.table]

        candidates = self.table

        # Replace '_' in query with ' ' since that's how emojione names are stored
        query = query.replace('_', ' ')

        query_words = []
        for w in query.split():
            escaped_w = re.escape(w)
            query_words.append((
                w,
                re.compile(r'\b' + escaped_w + r'\b'),
                re.compile(r'\b' + escaped_w),
            ))

        # Matches are tuples of the form:
        # (match_type, score, name)
        # Match types are:
        # * 20 - exact
        # * 10 - substring
        # * 5 - substring of alias
        # * 0 - levenshtein distance
        matched = []

        for candidate, candidate_info in candidates.items():
            if len(query) > len(candidate): continue

            candidate_lowercase = candidate.lower()

            if query == candidate_lowercase:
                # Exact match
                if candidate_info.unicode_str:
                    matched.append((20, 0, candidate, CANDIDATE_UNICODE))
                if candidate_info.aliasing:
                    matched.append((5, 0, candidate, CANDIDATE_ALIAS))
            else:
                # Substring match
                word_ixs = []
                substring_found = False
                exact_word_match = 0
                prefix_match = 0
                for w, exact_regex, prefix_regex in query_words:
                    ix = candidate_lowercase.find(w)
                    if ix == -1:
                        word_ixs.append(100)
                    else:
                        substring_found = True
                        word_ixs.append(ix)

                        # Check if an exact word match or a prefix match
                        if exact_regex.search(candidate_lowercase):
                            exact_word_match += 1
                        elif prefix_regex.search(candidate_lowercase):
                            prefix_match += 1

                if substring_found and all(ix >= 0 for ix in word_ixs):
                    # For substrings, the closer to the origin, the better
                    score = -(float(sum(word_ixs)) / len(word_ixs))

                    # Receive a boost if the substring matches a word or a prefix
                    score += 20 * exact_word_match + 10 * prefix_match

                    if candidate_info.unicode_str:
                        matched.append((10, score, candidate, CANDIDATE_UNICODE))
                    if candidate_info.aliasing:
                        matched.append((5, score, candidate, CANDIDATE_ALIAS))
                else:
                    # Levenshtein distance
                    score = 0
                    if Levenshtein is None:
                        opcodes = SequenceMatcher(None, query, candidate_lowercase,
                            autojunk=False).get_opcodes()
                    else:
                        opcodes = Levenshtein.opcodes(query, candidate_lowercase)
                    for (tag, i1, i2, j1, j2) in opcodes:
                        if tag in ('replace', 'delete'):
                            score = 0
                            break
                        if tag == 'insert':
                            score -= 1
                        if tag == 'equal':
                            score += i2 - i1
                            # favor word boundaries
                            if j1 == 0:
                                score += 2
                            elif candidate[j1 - 1] == ' ':
                                score += 1
                            if j2 == len(candidate):
                                score += 2
                            elif [j2] == ' ':
                                score += 1
                    if score > 0:
                        if candidate_info.unicode_str:
                            matched.append((0, score, candidate, CANDIDATE_UNICODE))
                        if candidate_info.aliasing:
                            matched.append((0, score, candidate, CANDIDATE_ALIAS))

        # The first two fields are sorted in reverse.
        # The third text field is sorted by the length of the string, then alphabetically.
        matched.sort(key=lambda x: (len(x[2]), x[2]))
        matched.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return matched[:limit]

    def find_characters(self, query_string):
        results = []
        candidate_strings = set()

        if not query_string:
            return results

        # Look for an ASCII alias that matches exactly
        ascii_match = self.ascii_table.get(query_string)
        if ascii_match:
            unicode_name = self.reverse_ascii_table[ascii_match]
            display_str = '{}: {} [{}]'.format(ascii_match, unicode_name, query_string)
            results.append((ascii_match, display_str))

        # Look for a fuzzy match against a description
        for level, score, name, candidate_type in self._filter(query_string.lower()):
            uniemoji_char = self.table[name]

            # Since we have several source (UnicodeData.txt, EmojiOne),
            # make sure we don't output multiple identical candidates
            if candidate_type == CANDIDATE_UNICODE:
                if uniemoji_char.unicode_str in candidate_strings:
                    continue
                candidate_strings.add(uniemoji_char.unicode_str)

                display_str = None
                if uniemoji_char.is_emojione:
                    unicode_name = self.unicode_chars_to_names.get(uniemoji_char.unicode_str)
                    if unicode_name and unicode_name != name:
                        display_str = '{}: :{}: {}'.format(
                            uniemoji_char.unicode_str,
                            name.replace(' ', '_'),
                            unicode_name)
                if display_str is None:
                    shortname = self.unicode_chars_to_shortnames.get(uniemoji_char.unicode_str, '')
                    if shortname:
                        shortname = ':' + shortname + ': '
                    display_str = '{}: {}{}'.format(
                        uniemoji_char.unicode_str,
                        shortname,
                        name)

                results.append((uniemoji_char.unicode_str, display_str))

            # Aliases expand into several candidates
            for unicode_str in uniemoji_char.aliasing:
                if unicode_str in candidate_strings:
                    continue
                candidate_strings.add(unicode_str)
                unicode_name = self.unicode_chars_to_names.get(unicode_str)
                shortname = self.unicode_chars_to_shortnames.get(unicode_str, '')
                if shortname:
                    shortname = ':' + shortname + ': '
                display_str = '{}: {}{} [{}]'.format(
                    unicode_str,
                    shortname,
                    unicode_name,
                    name)
                results.append((unicode_str, display_str))

        return results

if __name__ == '__main__':
    query_string = ' '.join(sys.argv[1:])
    ue = UniEmoji()
    results = ue.find_characters(query_string)
    for _, display_str in results:
        print(display_str)
