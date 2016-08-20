#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UniEmoji: ibus engine for unicode emoji and symbols by name
#
# Copyright (c) 2013, 2015 Lalo Martins <lalo.martins@gmail.com>
#
# based on https://github.com/ibus/ibus-tmpl/
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

from gi.repository import IBus
from gi.repository import GLib
from gi.repository import GObject

import os
import re
import sys
import json
import getopt
import locale
import codecs
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

debug_on = True
def debug(*a, **kw):
    if debug_on:
        print(*a, **kw)

# gee thank you IBus :-)
num_keys = []
for n in range(10):
    num_keys.append(getattr(IBus, str(n)))
del n

__base_dir__ = os.path.dirname(__file__)

VALID_CATEGORIES = (
    'Sm', # Symbol, math
    'So', # Symbol, other
    'Pd', # Punctuation, dash
    'Po', # Punctuation, other
)

VALID_RANGES = (
    (0x2000, 0x206f), # General Punctuation, Layout Controls, Invisible Operators
    (0x2070, 0x209f), # Superscripts and Subscripts
    (0x20a0, 0x20cf), # Currency Symbols
    (0x20ac, 0x20ac), # Euro Sign
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
    (0x1f300, 0x1f5ff), # Miscellaneous Symbols and Pictographs
    (0x1f600, 0x1f64f), # Emoticons
    (0x1f650, 0x1f67f), # Ornamental Dingbats
    (0x1f680, 0x1f6ff), # Transport and Map Symbols
    (0x1f900, 0x1f9ff), # Supplemental Symbols and Pictographs
)

def in_range(code):
    return any(x <= code <= y for x,y in VALID_RANGES)

MATCH_LIMIT = 100

if xdg:
    SETTINGS_DIRS = list(xdg.BaseDirectory.load_config_paths('uniemoji'))
else:
    SETTINGS_DIRS = [d for d in [os.path.expanduser('~/.config/uniemoji'), '/etc/xdg/uniemoji']
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


# the engine
class UniEmoji(IBus.Engine):
    __gtype_name__ = 'UniEmoji'

    def __init__(self):
        super(UniEmoji, self).__init__()
        self.is_invalidate = False
        self.preedit_string = ''
        self.lookup_table = IBus.LookupTable.new(10, 0, True, True)
        self.prop_list = IBus.PropList()
        self.table = defaultdict(UniEmojiChar)
        self.unicode_chars_to_names = {}
        self.unicode_chars_to_shortnames = {}
        self.ascii_table = {}
        self.reverse_ascii_table = {}
        self.alias_table = {}
        with codecs.open(os.path.join(__base_dir__, 'UnicodeData.txt'), encoding='utf-8') as unicodedata:
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

        emojione = json.load(codecs.open(os.path.join(__base_dir__, 'emojione.json'), encoding='utf-8'))
        for emoji_shortname, info in emojione.items():

            # ZWJ emojis such as 'family', 'couple', and 'kiss' appear in an
            # alternate field
            alternate_form = info.get('unicode_alternates')
            if alternate_form and '200d' in alternate_form:
                chars = alternate_form
            else:
                chars = info['unicode']

            unicode_str = ''.join(chr(int(codepoint, 16)) for codepoint in chars.split('-'))
            self.unicode_chars_to_shortnames[unicode_str] = emoji_shortname

            emoji_shortname = emoji_shortname.replace('_', ' ')

            if emoji_shortname in self.table:
                # Check for clashes between emojione's names and the existing unicode name.
                # Clashes turn into aliases.
                if unicode_str != self.table[emoji_shortname].unicode_str:
                    self.table[emoji_shortname].aliasing.append(unicode_str)
            elif info['category'] == 'flags':
                flag_name = 'flag of ' + info['name']
                self.table[flag_name] = UniEmojiChar(unicode_str, is_emojione=True)
                self.unicode_chars_to_names[unicode_str] = flag_name
            else:
                self.table[emoji_shortname] = UniEmojiChar(unicode_str, is_emojione=True)

            # When the string defined by emojione isn't in Unicode
            # (because it's a combination of characters), use emojione's
            # descriptive name, and set the shortname as an alias
            if unicode_str not in self.unicode_chars_to_names:
                long_name = info['name']
                self.unicode_chars_to_names[unicode_str] = long_name
                if long_name not in self.table:
                    self.table[long_name] = UniEmojiChar(unicode_str)

            # EmojiOne has duplicate entries in the keywords array
            keywords = set(info.get('keywords', []))
            for alias in keywords:
                alias_counter[alias] += 1
                temp_alias_table[alias].add(unicode_str)

            for ascii_aliases in info.get('aliases_ascii', []):
                self.ascii_table[ascii_aliases] = unicode_str
                self.reverse_ascii_table[unicode_str] = info['name']

        # Load less-frequent aliases from emojione file
        for alias, n in alias_counter.most_common():
            if n >= 20:
                continue
            self.table[alias].aliasing.extend(temp_alias_table[alias])

        # Load custom file(s)
        for d in reversed(SETTINGS_DIRS):
            custom_filename = os.path.join(d, 'custom.json')
            debug('Loading custom emoji from {}'.format(custom_filename))
            if os.path.isfile(custom_filename):
                custom_table = None
                try:
                    with codecs.open(custom_filename, encoding='utf-8') as f:
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

        debug("Create UniEmoji engine OK")

    def set_lookup_table_cursor_pos_in_current_page(self, index):
        '''Sets the cursor in the lookup table to index in the current page

        Returns True if successful, False if not.
        '''
        page_size = self.lookup_table.get_page_size()
        if index > page_size:
            return False
        page, pos_in_page = divmod(self.lookup_table.get_cursor_pos(),
                                   page_size)
        new_pos = page * page_size + index
        if new_pos > self.lookup_table.get_number_of_candidates():
            return False
        self.lookup_table.set_cursor_pos(new_pos)
        return True

    def do_candidate_clicked(self, index, dummy_button, dummy_state):
        if self.set_lookup_table_cursor_pos_in_current_page(index):
            self.commit_candidate()

    def do_process_key_event(self, keyval, keycode, state):
        debug("process_key_event(%04x, %04x, %04x)" % (keyval, keycode, state))

        # ignore key release events
        is_press = ((state & IBus.ModifierType.RELEASE_MASK) == 0)
        if not is_press:
            return False

        if self.preedit_string:
            if keyval == IBus.Return:
                if self.lookup_table.get_number_of_candidates() > 0:
                    self.commit_candidate()
                else:
                    self.commit_string(self.preedit_string)
                return True
            elif keyval == IBus.Escape:
                self.preedit_string = ''
                self.update_candidates()
                return True
            elif keyval == IBus.BackSpace:
                self.preedit_string = self.preedit_string[:-1]
                self.invalidate()
                return True
            elif keyval in num_keys[1:]:
                index = num_keys.index(keyval) - 1
                if self.set_lookup_table_cursor_pos_in_current_page(index):
                    self.commit_candidate()
                    return True
                return False
            elif keyval == IBus.Page_Up or keyval == IBus.KP_Page_Up:
                self.page_up()
                return True
            elif keyval == IBus.Page_Down or keyval == IBus.KP_Page_Down:
                self.page_down()
                return True
            elif keyval == IBus.Up:
                self.cursor_up()
                return True
            elif keyval == IBus.Down:
                self.cursor_down()
                return True
            elif keyval == IBus.Left or keyval == IBus.Right:
                return True

        if keyval == IBus.space and len(self.preedit_string) == 0:
            # Insert space if that's all you typed (so you can more easily
            # type a bunch of emoji separated by spaces)
            return False

        # Allow typing all ASCII letters and punctuation, except digits
        if ord(' ') <= keyval < ord('0') or \
           ord('9') < keyval <= ord('~'):
            if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) == 0:
                self.preedit_string += chr(keyval)
                self.invalidate()
                return True
        else:
            if keyval < 128 and self.preedit_string:
                self.commit_string(self.preedit_string)

        return False

    def invalidate(self):
        if self.is_invalidate:
            return
        self.is_invalidate = True
        GLib.idle_add(self.update_candidates)


    def page_up(self):
        if self.lookup_table.page_up():
            self._update_lookup_table()
            return True
        return False

    def page_down(self):
        if self.lookup_table.page_down():
            self._update_lookup_table()
            return True
        return False

    def cursor_up(self):
        if self.lookup_table.cursor_up():
            self._update_lookup_table()
            return True
        return False

    def cursor_down(self):
        if self.lookup_table.cursor_down():
            self._update_lookup_table()
            return True
        return False

    def commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.preedit_string = ''
        self.update_candidates()

    def commit_candidate(self):
        self.commit_string(self.candidates[self.lookup_table.get_cursor_pos()])

    def filter(self, query, candidates = None):
        if len(self.table) <= 10:
            # this only happens if something went wrong; it's our cheap way of displaying errors
            return [[0, 0, message] for message in self.table]

        if candidates is None: candidates = self.table

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

            if query == candidate:
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
                    ix = candidate.find(w)
                    if ix == -1:
                        word_ixs.append(100)
                    else:
                        substring_found = True
                        word_ixs.append(ix)

                        # Check if an exact word match or a prefix match
                        if exact_regex.search(candidate):
                            exact_word_match += 1
                        elif prefix_regex.search(candidate):
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
                        opcodes = SequenceMatcher(None, query, candidate,
                            autojunk=False).get_opcodes()
                    else:
                        opcodes = Levenshtein.opcodes(query, candidate)
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
        return matched[:MATCH_LIMIT]

    def update_candidates(self):
        preedit_len = len(self.preedit_string)
        attrs = IBus.AttrList()
        self.lookup_table.clear()
        self.candidates = []
        candidate_strings = set()

        if preedit_len > 0:
            # Look for an ASCII alias that matches exactly
            ascii_match = self.ascii_table.get(self.preedit_string)
            if ascii_match:
                unicode_name = self.reverse_ascii_table[ascii_match]
                display_str = '{}: {} [{}]'.format(ascii_match, unicode_name, self.preedit_string)
                candidate = IBus.Text.new_from_string(display_str)
                self.candidates.append(ascii_match)
                self.lookup_table.append_candidate(candidate)

            # Look for a fuzzy match against a description
            for level, score, name, candidate_type in self.filter(self.preedit_string.lower()):
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

                    candidate = IBus.Text.new_from_string(display_str)
                    self.candidates.append(uniemoji_char.unicode_str)
                    self.lookup_table.append_candidate(candidate)

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
                    candidate = IBus.Text.new_from_string(display_str)
                    self.candidates.append(unicode_str)
                    self.lookup_table.append_candidate(candidate)

        text = IBus.Text.new_from_string(self.preedit_string)
        text.set_attributes(attrs)
        self.update_auxiliary_text(text, preedit_len > 0)

        attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE,
                IBus.AttrUnderline.SINGLE, 0, preedit_len))
        text = IBus.Text.new_from_string(self.preedit_string)
        text.set_attributes(attrs)
        self.update_preedit_text(text, preedit_len, preedit_len > 0)
        self._update_lookup_table()
        self.is_invalidate = False

    def _update_lookup_table(self):
        visible = self.lookup_table.get_number_of_candidates() > 0
        self.update_lookup_table(self.lookup_table, visible)


    def do_focus_in(self):
        debug("focus_in")
        self.register_properties(self.prop_list)

    def do_focus_out(self):
        debug("focus_out")
        self.do_reset()

    def do_reset(self):
        debug("reset")
        self.preedit_string = ''

    def do_property_activate(self, prop_name):
        debug("PropertyActivate(%s)" % prop_name)

    def do_page_up(self):
        return self.page_up()

    def do_page_down(self):
        return self.page_down()

###########################################################################
# the app (main interface to ibus)
class IMApp:
    def __init__(self, exec_by_ibus):
        if not exec_by_ibus:
            global debug_on
            debug_on = True
        self.mainloop = GLib.MainLoop()
        self.bus = IBus.Bus()
        self.bus.connect("disconnected", self.bus_disconnected_cb)
        self.factory = IBus.Factory.new(self.bus.get_connection())
        self.factory.add_engine("uniemoji", GObject.type_from_name("UniEmoji"))
        if exec_by_ibus:
            self.bus.request_name("org.freedesktop.IBus.UniEmoji", 0)
        else:
            xml_path = os.path.join(__base_dir__, 'uniemoji.xml')
            if os.path.exists(xml_path):
                component = IBus.Component.new_from_file(xml_path)
            else:
                xml_path = os.path.join(os.path.dirname(__base_dir__),
                                        'ibus', 'component', 'uniemoji.xml')
                component = IBus.Component.new_from_file(xml_path)
            self.bus.register_component(component)

    def run(self):
        self.mainloop.run()

    def bus_disconnected_cb(self, bus):
        self.mainloop.quit()


def launch_engine(exec_by_ibus):
    IBus.init()
    IMApp(exec_by_ibus).run()

def print_help(out, v = 0):
    print("-i, --ibus             executed by IBus.", file=out)
    print("-h, --help             show this message.", file=out)
    print("-d, --daemonize        daemonize ibus", file=out)
    sys.exit(v)

def main():
    try:
        locale.setlocale(locale.LC_ALL, "")
    except:
        pass

    exec_by_ibus = False
    daemonize = False

    shortopt = "ihd"
    longopt = ["ibus", "help", "daemonize"]

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortopt, longopt)
    except getopt.GetoptError:
        print_help(sys.stderr, 1)

    for o, a in opts:
        if o in ("-h", "--help"):
            print_help(sys.stdout)
        elif o in ("-d", "--daemonize"):
            daemonize = True
        elif o in ("-i", "--ibus"):
            exec_by_ibus = True
        else:
            print("Unknown argument: %s" % o, file=sys.stderr)
            print_help(sys.stderr, 1)

    if daemonize:
        if os.fork():
            sys.exit()

    launch_engine(exec_by_ibus)

if __name__ == "__main__":
    main()
