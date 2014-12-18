# only really known to work on ubuntu, if you're using anything else, hopefully
# it should at least give you a clue how to install it by hand
# TODO: parameterize this and the xml file (maybe scons?)
install:
	mkdir -p /usr/share/ibus-uniemoji
	cp uniemoji.py uniemoji.svg UnicodeData.txt /usr/share/ibus-uniemoji
	chmod a+x /usr/share/ibus-uniemoji/uniemoji.py
	cp uniemoji.xml /usr/share/ibus/component
uninstall:
	rm -rf /usr/share/ibus-uniemoji
	rm -f /usr/share/ibus/component/uniemoji.xml
