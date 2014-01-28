#!/usr/bin/env python3
# Generate an up-to-date list of China administrative divisons
#
# TODO lots of documentation
import csv
from math import ceil, log10
from os import linesep
import os.path
import re
import urllib.request

from bs4 import BeautifulSoup

# https://code.google.com/p/python-jianfan/ or
# https://code.google.com/r/stryderjzw-python-jianfan/source/browse
import jianfan


__all__ = [
    'codes',
    'lookup',
    'parent',
    'partial',
    'split',
    'within',
    ]

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..',
                        'data')
URL = "http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html"

codes = {}


data_fn = lambda base: os.path.join(DATA_DIR, '{}.csv'.format(base))


def dict_update(a, b, conflict='raise'):
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


def load_file(f, key):
    result = {}
    for row in csv.DictReader(f):
        code = int(row[key])
        del row[key]
        result[code] = row
    return result


def lookup(name, lang='en', fragment=None, top=True):
    name_key = 'name_{}'.format(lang)
    if fragment is not None:
        digits = ceil(log10(fragment))
        min_ = fragment * 10 ** (6 - digits)
        max_ = (fragment + 1) * 10 ** (6 - digits)
        fragment = lambda x: x >= min_ and x < max_
    matches = set()
    for code in filter(fragment, sorted(codes.keys())):
        if name in codes[code].get(name_key, ''):
            matches.add(code)
    if len(matches) == 1:
        return matches.pop()
    elif len(matches) > 1:
        if top:
            best = codes[min(matches, key=lambda x:
                         codes[x]['level'])]['level']
            matches = list(filter(lambda x: codes[x]['level'] == best,
                           matches))
            if len(matches) == 1:
                return matches[0]
        # No luck…
        message = ["{} name '{}' is ambiguous:".format(lang.upper(), name)]
        for code in matches:
            message.append('  {} {}'.format(code, codes[code][name_key]))
        raise KeyError('\n'.join(message))
    else:
        raise KeyError("name '{}' not found".format(name))


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


parent = lambda code, digits: code - (code % 10 ** (6 - digits))


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


def partial(code, digits=2):
    return int(code / 10 ** (6 - digits))


split = lambda code: (int(code / 1e4), int(code % 1e4 / 100), code % 100)


def update(f, verbose=False):
    global data
#    # Read the NBS website
#    d0 = parse_raw(urllib.request.urlopen(URL))
    # commented: Use a cached copy of the website
    codes = parse_raw(f)

    # Save the latest table
    with open(data_fn('latest.csv'), 'w') as f1:
        w = csv.writer(f1, lineterminator=linesep)
        w.writerow(['code', 'name_zh', 'level'])
        for code in sorted(codes.keys()):
            w.writerow([code, codes[code]['name_zh'], codes[code]['level']])

    # Load the CITAS table
    d1 = load_file(open(data_fn('citas'), 'r'), 'C-gbcode')

    # Load the GB/T 2260-2007 tables, from two files
    d2 = load_file(open(data_fn('gbt_2260-2007'), 'r'), 'code')
    d3 = load_file(open(data_fn('gbt_2260-2007'), 'r'), 'code')
    for code, d in d3.items():  # Merge the two GB/T 2260-2007 files
        if code in d2:  # Code appears in both files
            # Don't overwrite name_zh in gbt_2260-2007.csv with an empty
            # name_zh from gbt_2260-2007_sup.csv
            dict_update(d2[code], d, conflict=lambda a, b, k: not(k ==
                        'name_zh' and b[k] == ''))
        else:  # Code only appears in gbt_2260-2007_sup.csv
            d2[code] = d

    # Load extra data pertaining to the latest table
    d4 = load_file(open(data_fn('extra'), 'r'), 'code')

    # Merge using codes
    for code in sorted(codes.keys()):
        # Store debug information to be printed (or not) later
        message = '{}\t{}\n'.format(code, codes[code]['name_zh'])
        # Merge CITAS entry for this code
        if code not in d1:
            message += '  does not appear in CITAS data set\n'
        else:
            d = dict(d1[code])  # Make a copy
            name_zh = d.pop('N-hanzi')
            if not match_names(codes[code]['name_zh'], name_zh):
                message += '  CITAS name {} ({}) does not match\n'.format(
                    name_zh, jianfan.ftoj(name_zh))
            else:
                d['name_en'] = d.pop('N-local').replace("`", "'")
                d['name_pinyin'] = d.pop('N-pinyin').replace("`", "'")
                dict_update(codes[code], d)
        # Merge GB/T 2260-2007 entry for this code
        if code not in d2:
            message += '  does not appear in GB/T 2260-2007\n'
        else:
            d = dict(d2[code])
            if not codes[code]['name_zh'] == d['name_zh']:
                message += '  GB/T 2260-2007 name {} does not match\n'.format(
                    d['name_zh'])
            else:
                # Don't overwrite name_en from CITAS with empty name_en from
                # GB/T 2260-2007
                dict_update(codes[code], d, conflict=lambda a, b, k: not (k ==
                            'name_en' and b[k] is None))
        # Merge extra data
        if code in d4:
            dict_update(codes[code], d4[code], conflict='squash')
        if verbose and message.count('\n') > 1:
            print(message, end='')

    # TODO merge on names

    # Write the unified data set to file
    with open(data_fn('unified'), 'w') as f:
        w = csv.DictWriter(f, ('code', 'name_zh', 'name_en', 'name_pinyin',
                               'alpha', 'level', 'latitude', 'longitude'),
                           extrasaction='ignore', lineterminator=linesep)
        w.writeheader()
        for k in sorted(codes.keys()):
            w.writerow(codes[k])


def within(a, b):
    a_ = split(a)
    b_ = split(b)
    if b_[2] == 0:
        if b_[1] == 0:
            return a_[0] == b_[0]
        return a_[:2] == b_[:2]
    else:
        return False


if __name__ == '__main__':
    # Read the NBS website
    update(parse_raw(urllib.request.urlopen(URL)))
#    # commented: Use a cached copy of the website
#    update(open('cached.html', 'r'))
else:
    codes = load_file(open(data_fn('unified'), 'r'), 'code')
