"""The entire database is contained in the dictionary :data:`codes`.

>>> from gb2260 import *
>>> codes.get(542621) == {
...   'alpha': '',
...   'latitude': 29.6365717,
...   'level': 3,
...   'longitude': 94.3610895,
...   'name_en': 'Nyingchi',
...   'name_pinyin': 'Linzhi',
...   'name_zh': '林芝县',
...   }
True
>>> codes.get(632726)['level']
3

"""
import csv
from itertools import chain
from os import linesep
import os.path
import re
import sqlite3


from bs4 import BeautifulSoup

# https://code.google.com/p/python-jianfan/ or
# https://code.google.com/r/stryderjzw-python-jianfan/source/browse
import jianfan


__all__ = [
    'all_at',
    'alpha',
    'AmbiguousKeyError',
    'codes',
    'level',
    'lookup',
    'lookup_name',
    'parent',
    'split',
    'within',
    ]

__version__ = '0.1-dev'

DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..',
                        'data')
URL = "http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html"

COLUMNS = [
    'code',
    'name_zh',
    'level',
    'name_pinyin',
    'name_en',
    'alpha',
    'latitude',
    'longitude',
    ]


class AmbiguousKeyError(IndexError):
    """Exception for :meth:`lookup()`."""
    pass


class InvalidCodeError(ValueError):
    pass


def _create_db(conn, data):
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS codes')
    cur.execute("""CREATE TABLE codes (
        code        int   PRIMARY KEY,
        name_zh     text  NOT NULL,
        level       int   NOT NULL,
        name_pinyin text,
        name_en     text,
        alpha       text,
        latitude    real,
        longitude   real)
        """)

    insert_query = 'INSERT INTO codes (' + ', '.join(COLUMNS) + ') VALUES (:'
    insert_query += ', :'.join(COLUMNS) + ')'

    cur.executemany(insert_query, data.values())
    cur.close()
    conn.commit()


def _query(sql, args, type=None, columns=1, results=-1):
    cur = _conn.execute(sql, args)
    rows = cur.fetchall()

    if results > 0 and len(rows) != results:
        raise LookupError('%d results; expected %d', len(rows), results)

    if type is None:
        if results == -1 or results == 1:
            result = rows[0]
            if columns == 1:
                result = result[0]
        return result
    elif type is list and columns == 1:
        return list(chain(*rows))
    else:
        raise ValueError


def all_at(adm_level):
    """Return a sorted list of codes at the given administrative *adm_level*.

    >>> all_at(3)
    [110101, 110102, 110105, 110106, 110107, 110108, 110109, 110111, ...

    """
    return _query('SELECT code FROM codes WHERE level=? ORDER BY code',
                  (adm_level,), list)


def data_fn(base, ext='csv'):
    """Construct the path to a filename in the package's data directory."""
    return os.path.join(DATA_DIR, '{}.{}'.format(base, ext))


def alpha(code, prefix='CN-'):
    """Return an 'ISO 3166-2-like' alpha code for *code*.

    `ISO 3166-2:CN <https://en.wikipedia.org/wiki/ISO_3166-2:CN>`_ defines
    codes like "CN-11" for Beijing, where "11" are the first two digits of the
    GB/T 2260 code, 110000. An 'ISO 3166-2-like' alpha code uses the official
    GB/T 2260 two-letter alpha codes for province-level divisions (e.g. 'BJ'),
    and three-letter alpha codes for lower divisions, separated by hyphens.

    >>> alpha(130100)
    'CN-HE-SJW'

    """

    query = 'SELECT alpha FROM codes WHERE code in (?, ?, ?) ORDER BY code'
    parts = _query(query, _parents(code), list)

    if None in parts:
        raise ValueError('no alpha code for %d', code)

    return prefix + '-'.join(parts)


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
        row['level'] = int(row['level'])
        lat = row.pop('latitude')
        row['latitude'] = lat if lat == '' else float(lat)
        lon = row.pop('longitude')
        row['longitude'] = lon if lon == '' else float(lon)
        result[code] = row
    return result


def level(code):
    return _query('SELECT level FROM codes WHERE code = ?', (code,))


def _level(code):
    """Return the administrative level of *code*.

    >>> level(110108)
    3

    :meth:`level` does *not* raise an exception if *code* does not describe an
    entry in the database. To raise an exception on an invalid code, access
    :data:`codes`:

    >>> level(990000)
    1
    >>> codes[990000]['level']
    Traceback (most recent call last):
     ...
    KeyError: 990000

    """
    return 3 - sum([1 if c == 0 else 0 for c in split(code)])


def lookup(fields='code', **kwargs):
    """Lookup information from the database.

    Returns *fields* from the database for the requested entry, which can be
    specified using a keyword argument. For instance:

    - ``lookup('name_zh', code=110108)``: lookup the Chinese name for code
      `110108`.
    - ``lookup('code', name_en='Beijing')``: lookup the code for which the
      English name is 'Beijing'.

    """
    if isinstance(fields, str):
        fields = (fields,)
    if not all([f in COLUMNS for f in fields]):
        raise ValueError('one of %s is not a database field', fields)

    # String of additional query expressions
    conditions = ''

    # Limit search to divisions under the parent *within*
    within = kwargs.pop('within', None)

    if within is not None:
        # Split the code to parts, increment the one at the relevant level,
        # and rejoin
        parts = list(split(within))
        parts[_level(within) - 1] += 1
        high = _join(parts)

        # Add to the query expressions
        conditions += 'AND code BETWEEN %d AND %d' % (within, high)

    # The only remaining argument's name is the column to query on; its value
    # is the value to look up.
    key, value = kwargs.popitem()
    if len(kwargs):
        raise ValueError('unexpected arguments: %s', kwargs.keys())
    elif key not in COLUMNS:
        raise ValueError('%s is not a database field', key)

    # Assemble the query string
    query = 'SELECT %s FROM codes WHERE %s = ? %s' % \
            (', '.join(fields), key, conditions)

    # Return exactly one result
    result = _query(query, (value,), columns=len(fields), results=1)
    # commented: debugging
    # print(result)
    return result


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


def _join(levels):
    return levels[0] * 10000 + levels[1] * 100 + levels[2]


def parent(code, parent_level=None):
    """Return a valid GB/T 2260 code that is the parent of *code*."""
    l = _level(code)
    parents_guess = _parents(code)

    query = 'SELECT code FROM codes WHERE code IN (?, ?, ?) ORDER BY code'
    try:
        parents_db = _query(query, parents_guess, list)
    except LookupError:
        raise InvalidCodeError('%d and its parents %s', code,
                               parents_guess[:2])

    if code not in parents_db:
        raise InvalidCodeError(code)

    if parent_level is None:
        parent_level = l - 1

    if parent_level not in (1, 2, 3):
        raise ValueError('level = %d', parent_level)

    guess = parents_guess[parent_level - 1]
    if guess not in parents_db:
        raise ValueError('Code %d is at level %d, no parent at level %d',
                         code, l, parent_level)
    else:
        return guess


def _parents(code):
    """Return a tuple of parents of *code* at levels 1, 2 and 3."""
    return (code - code % 10000, code - code % 100, code)


def parse_raw(f):
    """Parse the webpage with the code list, from *f*.

    *f* can be any file-like object supported by BeautifulSoup(). Returns a
    dict where keys are .

    In the 2014 edition, the entries look like:

        <p align="justify" class="MsoNormal">110101&nbsp;&nbsp;&nbsp;&nbsp;
        &nbsp; &nbsp;&nbsp;东城区</p>

    Spaces after the code and before the name are not always present; sometimes
    there are stray spaces. There are either 3, 5 or 7 &nbsp; characters,
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


def split(code):
    """Return a tuple containing the three parts of *code*."""
    return (code // 10000, (code % 10000) // 100, code % 100)


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
    """Return True if division *a* is within (or the same as) division *b*.

    Like :meth:`level`, :meth:`within` does *not* check that *a* or *b* are
    valid codes that exist in the database.

    >>> within(331024, 330000)
    True
    >>> within(331024, 990000)
    False
    >>> within(331024, 110000)
    True

    """
    a_ = split(a)
    b_ = split(b)
    if b_[2] == 0:
        if b_[1] == 0:
            return a_[0] == b_[0]
        return a_[:2] == b_[:2]
    else:
        return a == b


codes = load_file(open(data_fn('unified'), 'r'), 'code')
_conn = sqlite3.connect(data_fn('unified', 'db'))
