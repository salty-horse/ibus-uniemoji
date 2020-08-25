# only really known to work on ubuntu, if you're using anything else, hopefully
# it should at least give you a clue how to install it by hand

PREFIX ?= /usr
SYSCONFDIR ?= /etc
DATADIR ?= $(PREFIX)/share
DESTDIR ?=

PYTHON ?= /usr/bin/python3

CURRENTDATE = $(shell date '+%Y%m%d')

all: uniemoji.xml config.py

uniemoji.xml: uniemoji.xml.in
	sed -e "s:@PYTHON@:$(PYTHON):g;" \
	    -e "s:@DATADIR@:$(DATADIR):g" $< > $@

config.py: config.py.in
	sed -e "s:@SYSCONFDIR@:$(SYSCONFDIR):g" $< > $@

install: all
	install -m 0755 -d $(DESTDIR)$(DATADIR)/ibus-uniemoji $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji $(DESTDIR)$(DATADIR)/ibus/component
	install -m 0644 uniemoji.svg UnicodeData.txt emojione.json emoji-sequences.txt emoji-zwj-sequences.txt $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0755 uniemoji.py $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0644 config.py $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0644 ibus.py $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0644 uniemoji.xml $(DESTDIR)$(DATADIR)/ibus/component
	install -m 0644 custom.json $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji

uninstall:
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/uniemoji.svg
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/UnicodeData.txt
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/emojione.json
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/emoji-sequences.txt
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/emoji-zwj-sequences.txt
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/uniemoji.py
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/config.py
	rm -f $(DESTDIR)$(DATADIR)/ibus-uniemoji/ibus.py
	rmdir $(DESTDIR)$(DATADIR)/ibus-uniemoji
	rm -f $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji/custom.json
	rmdir $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji
	rm -f $(DESTDIR)$(DATADIR)/ibus/component/uniemoji.xml

deb:
	make install DESTDIR=./deb-output/
	cp -r DEBIAN deb-output
	sed -i "s/<currentversion>/$(CURRENTDATE)/" deb-output/DEBIAN/control
	dpkg-deb -b deb-output ibus-uniemoji-$(CURRENTDATE).deb

clean:
	rm -f uniemoji.xml
	rm -f config.py
	rm -rf deb-output
