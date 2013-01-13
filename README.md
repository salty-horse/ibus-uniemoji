UniEmoji for ibus
==================

This simple input method for [ibus](http://code.google.com/p/ibus/) allows you to enter unicode emoji and other symbols by name.

To install, type `make install`. If your ibus isn't on /usr/share/ibus, you might need to edit the Makefile. If you want to install to /usr/local, you need to edit both the Makefile and the xml file. Sorry, for now you have to do that by hand. (Just don't be difficult and install it in the normal location!)

Then restart (or start) your ibus.

If you have customized your active input methods, you'll need to enable UniEmoji: open preferences (use the indicator if you have it, otherwise open “Keyboard Input Methods” on Ubuntu's dash, or run “ibus-setup”), go to the “Input Method” tab, click the “Select an input method” drop-down, UniEmoji will be in the “Other” category.

Then activate ibus using whatever key combination you have configured, and change input method until you have UniEmoji on (or use the drop-down you get by clicking the input method name on the input method toolbar).

Type some text you believe to be part of the name of an emoji or symbol. Select the one you want the usual ways (type more, use the cursor, numbers, mouse, touch...), and press Enter to insert.

Then you probably want to turn it off so you can type normal text.
