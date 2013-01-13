uniemoji.db: uniemoji.txt
	ibus-table-createdb -s uniemoji.txt

uniemoji.txt: uniemoji.tmpl make-table.py
	./make-table.py

# only really known to work on ubuntu, if you're using anything else, hopefully
# it should at least give you a clue how to install it by hand
install:
	cp uniemoji.svg /usr/share/ibus-table/icons
	cp uniemoji.db /usr/share/ibus-table/tables
