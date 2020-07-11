UniEmoji for ibus
==================

This simple input method for [ibus](https://github.com/ibus/ibus) allows you to enter unicode emoji and other symbols by name.

![Example usage](/example.gif?raw=true)

Since this is such a small project, there's no mailing list or website or anything. If you want automatic notification of new releases, you can use the Github releases feature; it even has a [feed](https://github.com/salty-horse/ibus-uniemoji/releases.atom).

Dependencies
-------------

Obviously:

- ibus
- python

Less obviously:

- the ibus gobject introspection information (on debian/ubuntu: gir1.2-ibus-1.0)

Optional:

- python-Levenshtein (`pip install python-Levenshtein`, also available as debian/ubuntu package python-levenshtein) makes fuzzy search faster

Installing
-----------

To install, type `make install`. If your ibus isn't on /usr/share/ibus, or you want to install to /usr/local, you can pass any of `PREFIX`, `DATADIR`, and `SYSCONFDIR` to `make`. You can also pass `DESTDIR` to aid in packaging, or `PYTHON` to use a different Python executable.

Running
--------

Restart (or start) your ibus. This can be done with the command `ibus restart`.

If you have customized your active input methods, you'll need to enable UniEmoji: open preferences (use the indicator if you have it, otherwise open “Keyboard Input Methods” on Ubuntu's dash, or run “ibus-setup”), go to the “Input Method” tab, click the “Select an input method” drop-down, UniEmoji will be in the “Other” category.

Then activate ibus using whatever key combination you have configured, and change input method until you have UniEmoji on (or use the drop-down you get by clicking the input method name on the input method toolbar).

Type some text you believe to be part of the name of an emoji or symbol. Select the one you want the usual ways (type more, use the cursor, numbers, mouse, touch...), and press Enter to insert.

Then you probably want to turn it off so you can type normal text.

Defining custom symbols
------------------------

UniEmoji automatically loads custom symbols from the following files:

* `/etc/xdg/uniemoji/custom.json` (overridden by `make install`!)
* `~/.config/uniemoji/custom.json`

The file format is a simple JSON object. See [custom.json](custom.json) for an example.

How the search is done and results are formatted
-------------------------------------------------

UniEmoji uses several data sources, and allows you to search all of them in a mostly-intelligent manner, with results given priority based on their source.

The search is fuzzy, so searching for 'tco' will find 'taco'. However, it will not correct typos that include extra letters.

The list of candidates that appears in the drop-down includes several bits of information:

* If the character has an "emoji shortname" (provided by JoyPixels), the shortname will appear first in the result, surrounded by colons.
A shortname is also a good indication that the candidate has an graphical representation, which will be replaced by an actual image on some clients (such as Twitter.com).
* If your search query matches an alias, the alias will be shown in square brackets.

For example, here is a result that appears when you search for 'eggplant' or 'aubergine':
>🍆: :​eggplant: aubergine

Here is a result that appears when you search for 'dog', which is one of the aliases for 'paw prints':
>🐾: :​feet: paw prints [dog]

Credits
--------

* Original author: Lalo Martins
* Current maintainer: Ori Avtalion

UniEmoji is dedicated to @MsAmberPRiley who AFAIK isn't even a GNU/Linux user and therefore might never hear of it, but who caused me to detour a Sunday to writing it ;-)

License
--------

UniEmoji is licensed under the GNU General Public License v3.0, except for the following files:

* UnicodeData.txt and emoji-zwj-sequences.txt are provided by the [Unicode Consortium](http://unicode.org/) under a specific license. See COPYING.unicode for details.
* emojione.json is provided by [JoyPixels](https://www.joypixels.com/) under their "[Free License](https://www.joypixels.com/licenses/free)".
