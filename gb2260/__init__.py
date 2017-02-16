"""The entire database is contained in the dictionary :data:`codes`.

>>> from gb2260 import *
>>> codes.get(542621) == {
...   'alpha': None,
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
from itertools import chain

from .database import COLUMNS, load_csv, open_sqlite

__all__ = [
    'all_at',
    'alpha',
    'codes',
    'level',
    'lookup',
    'parent',
    'split',
    'within',
    ]

__version__ = '0.1'


class InvalidCodeError(ValueError):
    """Exception for an invalid code."""
    pass


def all_at(adm_level):
    """Return a sorted list of codes at the given administrative *adm_level*.

    >>> all_at(3)
    [110101, 110102, 110105, 110106, 110107, 110108, 110109, 110111, ...
    >>> len(all_at(3))
    3136
    """
    return _query('SELECT code FROM codes WHERE level=? ORDER BY code',
                  (adm_level,), list)


def alpha(code, prefix='CN-'):
    """Return an 'ISO 3166-2-like' alpha code for *code*.

    `ISO 3166-2:CN <https://en.wikipedia.org/wiki/ISO_3166-2:CN>`_ defines
    codes like "CN-11" for Beijing, where "11" are the first two digits of the
    GB/T 2260 code, 110000. An 'ISO 3166-2-like' alpha code uses the official
    GB/T 2260 two-letter alpha codes for province-level divisions (e.g. 'BJ'),
    and three-letter alpha codes for lower divisions, separated by hyphens:

    >>> alpha(130100)
    'CN-HE-SJW'

    For divisions below level 2, no official alpha codes are provided, so
    :meth:`alpha` raises :py:class:`ValueError`.
    """
    query = 'SELECT alpha FROM codes WHERE code in (?, ?, ?) ORDER BY code'
    parts = _query(query, _parents(code), list)

    if None in parts:
        raise ValueError('no alpha code for %d', code)

    return prefix + '-'.join(parts)


def _join(levels):
    return levels[0] * 10000 + levels[1] * 100 + levels[2]


def level(code):
    """Return the administrative level of *code*.

    >>> level(110108)
    3

    For codes not in the database, raises :class:`InvalidCodeError`.
    """
    try:
        return _query('SELECT level FROM codes WHERE code = ?', (code,))
    except LookupError:
        raise InvalidCodeError(code)


def _level(code):
    """Return the administrative level of *code*.

    Unlike :meth:`level`, does *not* raise an exception if *code* does not
    describe an entry in the database.
    """
    return 3 - sum([1 if c == 0 else 0 for c in split(code)])


def lookup(fields='code', **kwargs):
    """Lookup information from the database.

    *fields* is either a :py:class:`str` specifying a single field, or an
    iterable of field names.

    Aside from optional *kwargs* (below), only one other keyword argument must
    be given. Its name is a database field; the value is the value to look up:

    >>> lookup(name_zh='海淀区')
    110108

    Lookup on (a) nonexistent field(s) raises :py:class:`ValueError`. Optional *kwargs* are:

    - *within*: a code. If specified, only entries that are within this
      division are returned. This is useful for lookups that would return more
      than one entry, normally a :py:class:`LookupError`:

        >>> lookup('code', name_zh='市辖区')
        Traceback (most recent call last):
          ...
        LookupError: 285 results, expected 1
        >>> lookup('code', name_zh='市辖区', within=110000)
        110100

    Further examples:

    >>> lookup(['name_zh', 'name_en'], code=110108)
    ('海淀区', 'Beijing: Haidian qu')
    """
    if isinstance(fields, str):
        fields = (fields,)
    bad_fields = list(filter(lambda s: s not in COLUMNS, fields))
    if len(bad_fields):
        raise ValueError('invalid field name%s: %s' %
                         ('s' if len(bad_fields) > 1 else '', bad_fields))

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
        raise ValueError('unexpected arguments: %s' % kwargs.keys())
    elif key not in COLUMNS:
        raise ValueError('invalid field name: %s' % key)

    # Assemble the query string
    query = 'SELECT %s FROM codes WHERE %s = ? %s' % \
            (', '.join(fields), key, conditions)

    # Return exactly one result
    result = _query(query, (value,), columns=len(fields), results=1)
    # commented: debugging
    # print(result)
    return result


def parent(code, parent_level=None):
    """Return a valid code that is the parent of *code*.

    >>> parent(110108)
    110100
    >>> parent(110100)
    110000

    If *parent_level* is supplied, the parent at the desired level is returned:

    >>> parent(110108, 1)
    110000

    """
    l = _level(code)
    parents_guess = _parents(code)

    query = 'SELECT code FROM codes WHERE code IN (?, ?, ?) ORDER BY code'
    try:
        parents_db = _query(query, parents_guess, list)
    except LookupError:
        raise InvalidCodeError('%d and its parents %s' %
                               (code, parents_guess[:2]))

    if code not in parents_db:
        raise InvalidCodeError(code)

    if parent_level is None:
        parent_level = l - 1

    if parent_level not in (1, 2, 3):
        raise ValueError('level = %d' % parent_level)

    guess = parents_guess[parent_level - 1]
    if guess not in parents_db:
        raise ValueError('code %d is at level %d, no parent at level %d' %
                         (code, l, parent_level))
    else:
        return guess


def _parents(code):
    """Return a tuple of parents of *code* at levels 1, 2 and 3."""
    return (code - code % 10000, code - code % 100, code)


def _query(sql, args, type=None, columns=1, results=-1):
    cur = _db_conn.execute(sql, args)
    rows = cur.fetchall()

    if len(rows) == 0 or (results > 0 and len(rows) != results):
        expected = '1 or more' if results < -1 else results
        raise LookupError('%d results; expected %d' % (len(rows), expected))

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


def split(code):
    """Return a tuple containing the three parts of *code*.

    >>> split(331024)
    (33, 10, 24)
    """
    return (code // 10000, (code % 10000) // 100, code % 100)


def within(a, b):
    """Return True if division *a* is within (or the same as) division *b*.

    >>> within(331024, 330000)
    True
    >>> within(331024, 110000)
    False
    >>> within(331024, 331024)
    True

    :meth:`within` does *not* check that *a* or *b* are valid codes that exist
    in the database.

    >>> within(331024, 990000)
    False
    >>> within(990101, 990000)
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


codes = load_csv('unified')
_db_conn = open_sqlite('unified')
