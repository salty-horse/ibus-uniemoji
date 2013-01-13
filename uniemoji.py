#! /usr/bin/env python
# UniEmoji: ibus engine for unicode emoji and symbols by name
#
# Copyright (c) 2013 Lalo Martins <lalo.martins@gmail.com>
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
from gi.repository import Pango

import os
import sys
import getopt
import locale

# gee thank you IBus :-)
num_keys = []
for n in range(10):
    num_keys.append(getattr(IBus, str(n)))
del n


###########################################################################
# the engine
class UniEmoji(IBus.Engine):
    __gtype_name__ = 'UniEmoji'

    def __init__(self):
        super(UniEmoji, self).__init__()
        self.__is_invalidate = False
        self.__preedit_string = u""
        self.__lookup_table = IBus.LookupTable.new(10, 0, True, True)
        self.__prop_list = IBus.PropList()
        self.__table = {'foo': '23', 'bar': '42', 'foo bar': '5'}
        #self.__prop_list.append(IBus.Property(key="test", icon="ibus-local"))
        print "Create UniEmoji engine OK"

    def do_process_key_event(self, keyval, keycode, state):
        print "process_key_event(%04x, %04x, %04x)" % (keyval, keycode, state)
        # ignore key release events
        is_press = ((state & IBus.ModifierType.RELEASE_MASK) == 0)
        if not is_press:
            return False

        if self.__preedit_string:
            if keyval == IBus.Return:
                if self.__lookup_table.get_number_of_candidates() > 0:
                    self.__commit_candidate()
                else:
                    self.__commit_string(self.__preedit_string)
                return True
            elif keyval == IBus.Escape:
                self.__preedit_string = u""
                self.__update()
                return True
            elif keyval == IBus.BackSpace:
                self.__preedit_string = self.__preedit_string[:-1]
                self.__invalidate()
                return True
            elif keyval in num_keys[1:]:
                index = num_keys.index(keyval) - 1
                page_size = self.__lookup_table.get_page_size()
                if index > page_size:
                    return False
                page, pos_in_page = divmod(self.__lookup_table.get_cursor_pos(),
                                           page_size)
                new_pos = page * page_size + index
                if new_pos > self.__lookup_table.get_number_of_candidates():
                    return False
                self.__lookup_table.set_cursor_pos(new_pos)
                self.__commit_candidate()
                return True
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
        if (keyval in xrange(IBus.a, IBus.z + 1) or
            keyval in xrange(IBus.A, IBus.Z + 1) or
            keyval == IBus.space):
            if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK) == 0:
                self.__preedit_string += unichr(keyval)
                self.__invalidate()
                return True
        else:
            if keyval < 128 and self.__preedit_string:
                self.__commit_string(self.__preedit_string)

        return False

    def __invalidate(self):
        if self.__is_invalidate:
            return
        self.__is_invalidate = True
        GLib.idle_add(self.__update)


    def page_up(self):
        if self.__lookup_table.page_up():
            self.__update_lookup_table()
            return True
        return False

    def page_down(self):
        if self.__lookup_table.page_down():
            self.__update_lookup_table()
            return True
        return False

    def cursor_up(self):
        if self.__lookup_table.cursor_up():
            self.__update_lookup_table()
            return True
        return False

    def cursor_down(self):
        if self.__lookup_table.cursor_down():
            self.__update_lookup_table()
            return True
        return False

    def __commit_string(self, text):
        self.commit_text(IBus.Text.new_from_string(text))
        self.__preedit_string = u""
        self.__update()

    def __commit_candidate(self):
        self.__commit_string(self.__table[
            self.__lookup_table.get_candidate(
                self.__lookup_table.get_cursor_pos()).text])

    def __update(self):
        preedit_len = len(self.__preedit_string)
        attrs = IBus.AttrList()
        self.__lookup_table.clear()
        #import sys, ipdb; sys.stdout = sys.__stdout__; ipdb.set_trace()
        if preedit_len > 0:
            check = self.__preedit_string.lower()
            for name in self.__table:
                if check in name:
                    self.__lookup_table.append_candidate(IBus.Text.new_from_string(name))
        text = IBus.Text.new_from_string(self.__preedit_string)
        text.set_attributes(attrs)
        self.update_auxiliary_text(text, preedit_len > 0)

        attrs.append(IBus.Attribute.new(IBus.AttrType.UNDERLINE,
                IBus.AttrUnderline.SINGLE, 0, preedit_len))
        text = IBus.Text.new_from_string(self.__preedit_string)
        text.set_attributes(attrs)
        self.update_preedit_text(text, preedit_len, preedit_len > 0)
        self.__update_lookup_table()
        self.__is_invalidate = False

    def __update_lookup_table(self):
        visible = self.__lookup_table.get_number_of_candidates() > 0
        self.update_lookup_table(self.__lookup_table, visible)


    def do_focus_in(self):
        print "focus_in"
        self.register_properties(self.__prop_list)

    def do_focus_out(self):
        print "focus_out"

    def do_reset(self):
        print "reset"

    def do_property_activate(self, prop_name):
        print "PropertyActivate(%s)" % prop_name


###########################################################################
# the app (main interface to ibus)
class IMApp:
    def __init__(self, exec_by_ibus):
        engine_name = "uniemoji" if exec_by_ibus else "uniemoji (debug)"
        self.__component = \
                IBus.Component.new("org.freedesktop.IBus.UniEmoji",
                                   "Unicode emoji and symbols by name",
                                   "0.1.0",
                                   "GPL",
                                   "Lalo Martins <lalo.martins@gmail.com>",
                                   "https://github.com/lalomartins/uniemoji",
                                   "/usr/bin/exec",
                                   "uniemoji")
        engine = IBus.EngineDesc.new("uniemoji",
                                     engine_name,
                                     "Unicode emoji and symbols by name",
                                     "en",
                                     "GPL",
                                     "Lalo Martins <lalo.martins@gmail.com>",
                                     "",
                                     "us")
        self.__component.add_engine(engine)
        self.__mainloop = GLib.MainLoop()
        self.__bus = IBus.Bus()
        self.__bus.connect("disconnected", self.__bus_disconnected_cb)
        self.__factory = IBus.Factory.new(self.__bus.get_connection())
        self.__factory.add_engine("uniemoji",
                GObject.type_from_name("UniEmoji"))
        if exec_by_ibus:
            self.__bus.request_name("org.freedesktop.IBus.UniEmoji", 0)
        else:
            self.__bus.register_component(self.__component)
            self.__bus.set_global_engine_async(
                    "uniemoji", -1, None, None, None)

    def run(self):
        self.__mainloop.run()

    def __bus_disconnected_cb(self, bus):
        self.__mainloop.quit()


def launch_engine(exec_by_ibus):
    IBus.init()
    IMApp(exec_by_ibus).run()

def print_help(out, v = 0):
    print >> out, "-i, --ibus             executed by IBus."
    print >> out, "-h, --help             show this message."
    print >> out, "-d, --daemonize        daemonize ibus"
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
    except getopt.GetoptError, err:
        print_help(sys.stderr, 1)

    for o, a in opts:
        if o in ("-h", "--help"):
            print_help(sys.stdout)
        elif o in ("-d", "--daemonize"):
            daemonize = True
        elif o in ("-i", "--ibus"):
            exec_by_ibus = True
        else:
            print >> sys.stderr, "Unknown argument: %s" % o
            print_help(sys.stderr, 1)

    if daemonize:
        if os.fork():
            sys.exit()

    launch_engine(exec_by_ibus)

if __name__ == "__main__":
    main()
