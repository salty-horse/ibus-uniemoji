# only really known to work on ubuntu, if you're using anything else, hopefully
# it should at least give you a clue how to install it by hand

PREFIX ?= /usr
SYSCONFDIR ?= /etc
DATADIR ?= $(PREFIX)/share
DESTDIR ?=

PYTHON ?= /usr/bin/python3

all: uniemoji.xml

uniemoji.xml: uniemoji.xml.in
	sed -e "s:@PYTHON@:$(PYTHON):g; s:@DATADIR@:$(DATADIR):g" $< > $@

install: all
	install -m 0755 -d $(DESTDIR)$(DATADIR)/ibus-uniemoji $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji $(DESTDIR)$(DATADIR)/ibus/component
	install -m 0644 uniemoji.svg UnicodeData.txt $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0755 uniemoji.py $(DESTDIR)$(DATADIR)/ibus-uniemoji
	install -m 0644 uniemoji.xml $(DESTDIR)$(DATADIR)/ibus/component
	install -m 0644 custom.json $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji

uninstall:
	rm -rf $(DESTDIR)$(DATADIR)/ibus-uniemoji
	rm -rf $(DESTDIR)$(SYSCONFDIR)/xdg/uniemoji
	rm -f $(DESTDIR)$(DATADIR)/ibus/component/uniemoji.xml

clean:
	rm -f uniemoji.xml
