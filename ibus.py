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

import gi
gi.require_version('IBus', '1.0')
from gi.repository import IBus
from gi.repository import GLib
from gi.repository import GObject

import os
import sys
import getopt
import locale

from uniemoji import UniEmoji

__base_dir__ = os.path.dirname(__file__)

debug_on = True
def debug(*a, **kw):
    if debug_on:
        print(*a, **kw)

# gee thank you IBus :-)
num_keys = []
for n in range(1, 10):
    num_keys.append(getattr(IBus, str(n)))
num_keys.append(getattr(IBus, '0'))
del n

numpad_keys = []
for n in range(1, 10):
    numpad_keys.append(getattr(IBus, 'KP_' + str(n)))
numpad_keys.append(getattr(IBus, 'KP_0'))
del n

###########################################################################
# the engine
class UniEmojiIBusEngine(IBus.Engine):
    __gtype_name__ = 'UniEmojiIBusEngine'

    def __init__(self):
        super(UniEmojiIBusEngine, self).__init__()
        self.uniemoji = UniEmoji()
        self.is_invalidate = False
        self.preedit_string = ''
        self.lookup_table = IBus.LookupTable.new(10, 0, True, True)
        self.prop_list = IBus.PropList()

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
            if keyval in (IBus.Return, IBus.KP_Enter):
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
            elif keyval in num_keys:
                index = num_keys.index(keyval)
                if self.set_lookup_table_cursor_pos_in_current_page(index):
                    self.commit_candidate()
                    return True
                return False
            elif keyval in numpad_keys:
                index = numpad_keys.index(keyval)
                if self.set_lookup_table_cursor_pos_in_current_page(index):
                    self.commit_candidate()
                    return True
                return False
            elif keyval in (IBus.Page_Up, IBus.KP_Page_Up, IBus.Left, IBus.KP_Left):
                self.page_up()
                return True
            elif keyval in (IBus.Page_Down, IBus.KP_Page_Down, IBus.Right, IBus.KP_Right):
                self.page_down()
                return True
            elif keyval in (IBus.Up, IBus.KP_Up):
                self.cursor_up()
                return True
            elif keyval in (IBus.Down, IBus.KP_Down):
                self.cursor_down()
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

    def update_candidates(self):
        preedit_len = len(self.preedit_string)
        attrs = IBus.AttrList()
        self.lookup_table.clear()
        self.candidates = []

        if preedit_len > 0:
            uniemoji_results = self.uniemoji.find_characters(self.preedit_string)
            for char_sequence, display_str in uniemoji_results:
                candidate = IBus.Text.new_from_string(display_str)
                self.candidates.append(char_sequence)
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

    def do_cursor_up(self):
        return self.cursor_up()

    def do_cursor_down(self):
        return self.cursor_down()

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
        self.factory.add_engine("uniemoji", GObject.type_from_name("UniEmojiIBusEngine"))
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
