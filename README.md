UniEmoji for ibus
==================

This simple input method for [ibus](https://github.com/ibus/ibus) allows you to enter unicode emoji and other symbols by name.

Since this is such a small project, there's no mailing list or website or anything. If you want automatic notification of new releases, you can use the Github releases feature; it even has a feed (https://github.com/lalomartins/ibus-uniemoji/releases.atom).

Dependencies
-------------

Obviously:

- ibus
- python
- the ibus python bindings (on debian/ubuntu: ibus-python)

Less obviously:

- the ibus gobject introspection information (on debian/ubuntu: gir1.2-ibus-1.0)

Optional:

- python-Levenshtein (`pip install python-Levenshtein`, also available as debian/ubuntu package python-levenshtein) makes fuzzy search faster

Installing
-----------

To install, type `make install`. If your ibus isn't on /usr/share/ibus, or you want to install to /usr/local, you can pass any of `PREFIX`, `DATADIR`, and `SYSCONFDIR` to `make`.  You can also pass `DESTDIR` to aid in packaging.

Running
--------

Restart (or start) your ibus.

If you have customized your active input methods, you'll need to enable UniEmoji: open preferences (use the indicator if you have it, otherwise open “Keyboard Input Methods” on Ubuntu's dash, or run “ibus-setup”), go to the “Input Method” tab, click the “Select an input method” drop-down, UniEmoji will be in the “Other” category.

Then activate ibus using whatever key combination you have configured, and change input method until you have UniEmoji on (or use the drop-down you get by clicking the input method name on the input method toolbar).

Type some text you believe to be part of the name of an emoji or symbol. Select the one you want the usual ways (type more, use the cursor, numbers, mouse, touch...), and press Enter to insert.

Then you probably want to turn it off so you can type normal text.

That's it
----------

This package is dedicated to @MsAmberPRiley who AFAIK isn't even a GNU/Linux user and therefore might never hear of it, but who caused me to detour a Sunday to writing it ;-)
