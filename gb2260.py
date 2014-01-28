#!/usr/bin/env python3
# Generate an up-to-date list of China administrative divisons
#
# TODO lots of documentation
import csv
from os import linesep
import re
import urllib.request

from bs4 import BeautifulSoup

import jianfan  # https://code.google.com/p/python-jianfan/

URL = "http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html"


def match_names(official, other):
    if official == other:
        return 'exact'
    elif official in other or other in official:
        return 'substring'
    tr = jianfan.ftoj(other)  # Avoid repeated calls
    if official == tr:
        return 'translated'
    elif official in tr or tr in official:
        return 'translated substring'
    else:
        return False


def load_file(f, key):
    result = {}
    for row in csv.DictReader(f):
        code = int(row[key])
        del row[key]
        result[code] = row
    return result


def parse_raw(f):
    """Parse the webpage with the code list, from *f*.

    *f* can be any file-like object supported by BeautifulSoup(). Returns a
    dict where keys are .

    In the 2014 edition, the entries look like:

        <p align="justify" class="MsoNormal">110101&nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp; &nbsp;&nbsp;东城区</p>

    Spaces after the code and before the name are not always present; sometimes
    there are stray spaces. There a either 3, 5 or 7 &nbsp; characters,
    indicating the administrative level.
    """
    soup = BeautifulSoup(f)
    exp = re.compile('(?P<code>\d{6})(?P<level>(\xa0){1,7})(?P<name_zh>.*)')
    result = {}
    for p in soup.select('div.TRS_Editor p.MsoNormal'):
        match = exp.match(p.text.replace(' ', ''))  # Remove stray spaces
        if match is None:
            continue
        d = match.groupdict()
        assert len(d['level']) % 2 == 1  # 3, 5 or 6 &nbsp; characters
        result[int(d['code'])] = {
            'code': int(d['code']),
            'name_zh': d['name_zh'],
            'level': int(len(d['level']) / 2)
            }
    return result


def update(a, b, conflict='raise'):
    """Like dict.update(), but with conflict checking."""
    for k, v in b.items():
        if k in a and a[k] != v:  # Conflict
            if conflict == 'raise':
                raise ValueError(('Value {} for key {} would conflict with '
                                  'existing value {}').format(v, k, a[k]))
            elif conflict == 'squash':
                pass
            elif conflict == 'discard':
                continue
            elif callable(conflict):
                if not conflict(a, b, k):
                    continue
            else:
                raise ValueError("'Cannot handle conflict with '{}'".format(
                    conflict))
        a[k] = v


if __name__ == '__main__':
    # Read the NBS website
    d0 = parse_raw(urllib.request.urlopen(URL))
#    # commented: Use a cached copy of the website
#    d0 = parse_raw(open('cached.html', 'r'))

    # Write out the latest data to file
    with open('latest.csv', 'w') as f:
        w = csv.writer(f, lineterminator=linesep)
        w.writerow(['code', 'name_zh', 'level'])
        for k in sorted(d0.keys()):
            w.writerow([k, d0[k]['name_zh'], d0[k]['level']])

    # Load the CITAS table
    d1 = load_file(open('citas.csv', 'r'), 'C-gbcode')
    # Load the GB/T 2260-2007 tables
    d2 = load_file(open('gbt_2260-2007.csv', 'r'), 'code')
    d3 = load_file(open('gbt_2260-2007_sup.csv', 'r'), 'code')
    for code, d in d3.items():  # Merge the two GB/T 2260-2007 tables
        if code in d2:  # Code appears in both files
            # Don't overwrite name_zh in gbt_2260-2007.csv with an empty
            # name_zh from gbt_2260-2007_sup.csv
            update(d2[code], d, conflict=lambda a, b, k: not(k == 'name_zh' and
                   b[k] == ''))
        else:  # Code only appears in gbt_2260-2007_sup.csv
            d2[code] = d

    # Merge usings codes
    for code in sorted(d0.keys()):
        message = '{}\t{}\n'.format(code, d0[code]['name_zh'])  # Diagnostics
        # Merge CITAS entry for this code
        if code not in d1:
            message += '  does not appear in CITAS data set\n'
        else:
            d = dict(d1[code])
            name_zh = d.pop('N-hanzi')
            if not match_names(d0[code]['name_zh'], name_zh):
                message += '  CITAS name {} ({}) does not match\n'.format(
                    name_zh, jianfan.ftoj(name_zh))
            else:
                d['name_en'] = d.pop('N-local').replace("`", "'")
                d['name_pinyin'] = d.pop('N-pinyin').replace("`", "'")
                update(d0[code], d)
        # Merge GB/T 2260-2007 entry for this code
        if code not in d2:
            message += '  does not appear in GB/T 2260-2007\n'
        else:
            d = dict(d2[code])
            if not d0[code]['name_zh'] == d['name_zh']:
                message += '  GB/T 2260-2007 name {} does not match\n'.format(
                    d['name_zh'])
            else:
                # Don't overwrite name_en from CITAS with empty name_en from
                # GB/T 2260-2007
                update(d0[code], d, conflict=lambda a, b, k: not (k ==
                       'name_en' and b[k] is None))
        if message.count('\n') > 1:
            print(message, end='')

    # Write the unified data set to file
    with open('unified.csv', 'w') as f:
        w = csv.DictWriter(f, ('code', 'name_zh', 'name_en', 'name_pinyin',
                               'level', 'latitude', 'longitude'),
                           extrasaction='ignore', lineterminator=linesep)
        w.writeheader()
        for k in sorted(d0.keys()):
            w.writerow(d0[k])
