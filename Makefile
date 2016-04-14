# Only really known to work on Ubuntu and Debian 9 (stretch). If you're using
# anything else, hopefully it should at least give you a clue how to install it
# by hand.
#
# TODO: ensure "make uninstall" does not clobber a customized custom.json
# TODO: make "install" better at detecting whether IBUS_COMPONENT_PATH is correct
# TODO: package properly for various systems

ifdef user
INSTALL_DIR=$(HOME)/usr/share/ibus-uniemoji
COMPONENT_DIR=$(HOME)/.config/ibus/component
CONFIG_DIR=$(HOME)/.config/uniemoji
else
INSTALL_DIR=/usr/share/ibus-uniemoji
COMPONENT_DIR=/usr/share/ibus/component
CONFIG_DIR=/etc/xdg/uniemoji
endif

default:
	# This software has no compilation step. Just run either:
	#
	# 	sudo make install
	#
	# to install it system-wide, or
	#
	# 	make install user=1
	#
	# to install it for the current user only (which does not require root
	# permission).
	#
	# Likewise, 'make uninstall' or 'make uninstall user=1' respectively will
	# undo the changes.

install:
	mkdir -p $(INSTALL_DIR) $(CONFIG_DIR) $(COMPONENT_DIR)
	cp uniemoji.py uniemoji.svg UnicodeData.txt $(INSTALL_DIR)/
	chmod a+x $(INSTALL_DIR)/uniemoji.py
	sed -e 's%INSTALL_DIR%$(INSTALL_DIR)%' uniemoji.xml > $(COMPONENT_DIR)/uniemoji.xml
	cp custom.json $(CONFIG_DIR)/custom.json
	@if [ "$(COMPONENT_DIR)" != "/usr/share/ibus/component" ]; then\
		echo;\
		echo "NOTE: you must set IBUS_COMPONENT_PATH; for example in ~/.xprofile:";\
		echo;\
		echo "export IBUS_COMPONENT_PATH=$(COMPONENT_DIR):/usr/share/ibus/component";\
		echo;\
		fi

uninstall:
	rm -rf $(INSTALL_DIR)
	rm -rf $(CONFIG_DIR)
	rm -f $(COMPONENT_DIR)/uniemoji.xml
