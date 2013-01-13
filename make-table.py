#!/usr/bin/env python3

"""
Creates the ibus table from uniemoji.tmpl using python's unicodedata module
(so we don't have to parse UCD ourselves)

Corollary: the table will be as up-to-date as your python3. Python 3.3 uses UCD 6.1.0.
"""

import unicodedata

ranges = [range(0x1f300, 0x1f6ff+1), range(0x2600, 0x2bff+1)]
symbols = []

for r in ranges:
    for code in r:
        the_chr = chr(code)
        if unicodedata.category(the_chr) == 'So':
            name = unicodedata.name(the_chr).lower().replace(' ', '-')
            symbols.append((name, the_chr))

if len(symbols) != len(dict(symbols)):
    print("WARNING: duplicate names found, things might not work properly")

template = open('uniemoji.tmpl').read()
with open('uniemoji.txt', 'w') as table_file:
    table_file.write(template.format(
        max_length = max(len(name) for name, symbol in symbols),
        table = '\n'.join('{}\t{}\t1'.format(*entry) for entry in sorted(symbols)),
        ))
