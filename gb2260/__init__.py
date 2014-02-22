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
    'alpha',
    'AmbiguousKeyError',
    'codes',
    'level',
    'lookup',
    'parent',
    'split',
    'within',
    ]

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..',
                        'data')
URL = "http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html"

codes = {}


class AmbiguousKeyError(IndexError):
    """Exception for lookup()"""
    pass


def data_fn(base, ext='csv'):
    """Construct the path to a filename in the package's data directory."""
    return os.path.join(DATA_DIR, '{}.{}'.format(base, ext))


def alpha(code, prefix='CN-'):
    """Return an 'ISO 3166-2-like' alpha code for *code*.

    ISO 3166-2:CN defines codes like "CN-11" for Beijing, where "11" are the
    first two digits of the GB/T 2260 code, 110000. An 'ISO 3166-2-like' alpha
    code uses the official GB/T 2260 two-letter alpha codes for province-level
    divisions (e.g. 'BJ'), and three-letter alpha codes for lower divisions,
    separated by hyphens.
    """
    result = prefix
    for parent_level in range(1, level(code)):
        parent_code = codes[parent(code, parent_level)]['alpha']
        if len(parent_code) == 0:
            raise ValueError('No alpha code for parent division {}.'.format(
                             parent(code)))
        result += parent_code + '-'
    alpha_ = codes[code]['alpha']
    if len(alpha_) == 0:
        raise ValueError('No alpha code for {}.'.format(code))
    return result + alpha_


def dict_update(a, b, conflict='raise'):
    """Like dict.update(), but with conflict checking.

    dict *a* is updated with the items of *b*. Where the same key exists in
    both dicts, but the corresponding values differ, the result is defined by
    the value of *conflict*:

    - 'raise' (default): a ValueError is raised.
    - 'squash': the entry in *a* is replaced with the entry in *b*.
    - 'discard': the entry in *a* is retained.
    - any callable object: *conflict* is called with arguments (a[k], b[k], k),
      where k is the conflicting key. Then, depending on the returned value:
      - True: the entry in *a* is replaced with the entry in *b* (squash)
      - False: the entry in *a* is retained (discard)

    On any other value for *conflict*, a ValueError is raised.
    """
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
                if not conflict(a[k], v, k):
                    continue
            else:
                raise ValueError("'Cannot handle conflict with '{}'".format(
                    conflict))
        a[k] = v


def load_file(f, key, filter=None):
    result = {}
    for row in csv.DictReader(f):
        if callable(filter) and not filter(row):
            continue
        code = int(row[key])
        del row[key]
        result[code] = row
    return result


def level(code):
    """Return the administrative level of *code*."""
    return 3 - sum([1 if c == 0 else 0 for c in split(code)])


def lookup(name, lang='en', parent=None, highest=True):
    """Lookup a code for the given *name*.

    The *name* is given in language *lang* (either 'en' or 'zh').

    The *parent* and *highest* arguments determine how to resolve ambiguities
    (cases where more than one name_en or name_zh match *name*). If a GB/T 2260
    code *parent* is given, only codes for children of the parent region will
    be returned. For instance, with parent=350000, only codes from 350000 to
    360000 (exclusive) will be returned. If *highest* is True (the default),
    then of two regions with matching names, the one at a higher administrative
    level will be returned.
    """
    name_key = 'name_{}'.format(lang)
    if parent is not None:
        min_ = parent
        max_ = parent + 10 ** (6 - 2 * level(parent))
        parent = lambda x: x > min_ and x < max_
    matches = set()
    for code in filter(parent, sorted(codes.keys())):
        if name in codes[code].get(name_key, ''):
            matches.add(code)
    if len(matches) == 1:
        return matches.pop()
    elif len(matches) > 1:
        if highest:
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
        raise AmbiguousKeyError('\n'.join(message), name)
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


def parent(code, parent_level=None):
    """Return a valid GB/T 2260 code that is the parent of *code*."""
    l = level(code)
    if parent_level is not None:
        assert l - parent_level > 0, ("Code {} is at level {}, no parent at "
                                      "level {}").format(code, l, parent_level)
        l = parent_level
    else:
        l = level(code) - 1
        assert l > 0, "No parent of top-level code {}.".format(code)
    result = code - (code % 10 ** (6 - 2 * l))
    assert code in codes
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


split = lambda code: (int(code / 1e4), int(code % 1e4 / 100), code % 100)


def update(f, verbose=False):
    global data
#    # Read the NBS website
#    d0 = parse_raw(urllib.request.urlopen(URL))
    # commented: Use a cached copy of the website
    codes = parse_raw(f)

    # Save the latest table
    with open(data_fn('latest'), 'w') as f1:
        w = csv.writer(f1, lineterminator=linesep)
        w.writerow(['code', 'name_zh', 'level'])
        for code in sorted(codes.keys()):
            w.writerow([code, codes[code]['name_zh'], codes[code]['level']])

    # Load the CITAS table
    d1 = load_file(open(data_fn('citas'), 'r'), 'C-gbcode', lambda row:
                   row['todate'] == '19941231')

    # Load the GB/T 2260-2007 tables, from two files
    d2 = load_file(open(data_fn('gbt_2260-2007'), 'r'), 'code')
    d3 = load_file(open(data_fn('gbt_2260-2007_sup'), 'r'), 'code')
    for code, d in d3.items():  # Merge the two GB/T 2260-2007 files
        if code in d2:  # Code appears in both files
            # Don't overwrite name_zh in gbt_2260-2007.csv with an empty
            # name_zh from gbt_2260-2007_sup.csv
            dict_update(d2[code], d, conflict=lambda a, b, k: not(k ==
                        'name_zh' or b is None))
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
            if (len(d['name_zh']) and not codes[code]['name_zh'] ==
                    d['name_zh']):
                message += '  GB/T 2260-2007 name {} does not match\n'.format(
                    d['name_zh'])
            else:
                # Don't overwrite name_en from CITAS with empty name_en from
                # GB/T 2260-2007
                dict_update(codes[code], d, conflict=lambda a, b, k: not(
                            'name_' in k and b is ''))
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
    """Return True if division *a* is within (or the same as) division *b*."""
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
#    update(open(data_fn('cached', 'html'), 'r'), verbose=True)
else:
    codes = load_file(open(data_fn('unified'), 'r'), 'code')
