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

from .database import (
    COLUMNS,
    Database,
    InvalidCodeError,
    _parents,
    AmbiguousRegionError,
    )

__all__ = [
    'all_at',
    'isolike',
    'level',
    'lookup',
    'parent',
    'split',
    'within',
    ]

__version__ = '0.2-dev'


def all_at(adm_level):
    """Return a sorted list of codes at the given administrative *adm_level*.

    >>> all_at(3)
    [110101, 110102, 110105, 110106, 110107, 110108, 110109, 110111, ...
    >>> len(all_at(3))
    3136
    """
    return _select(['code'], 'level=? ORDER BY code', (adm_level,), list)


def isolike(code, prefix='CN-'):
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
    parts = [d.alpha for d in divisions.stack(code)]

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
    return divisions.get(code=code).level


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

    Lookup on (a) nonexistent field(s) raises :py:class:`ValueError`. Optional
    *kwargs* are:

    - *within*: a code. If specified, only entries that are within this
      division are returned. This is useful for lookups that would return more
      than one entry, normally a :py:class:`LookupError`:

        >>> lookup('code', name_zh='市辖区')
        Traceback (most recent call last):
          ...
        LookupError: 285 results, expected 1
        >>> lookup('code', name_zh='市辖区', within=110000)
        110100

    - *level*: an administrative level. If an integer (1, 2 or 3), only entries
       at this level are returned.

        >>> lookup(name_en='Hainan', level=1)  # the province
        460000
        >>> lookup(name_en='Hainan', level=3)  # a district in Wuhai, NM
        150303

        If 'highest' or 'lowest', then the entry at the highest or lowest
        administrative level is returned:

        >>> lookup(name_en='Hainan', level='highest')
        460000
        >>> lookup(name_en='Hainan', level='lowest')
        150303

    - *partial*: if True, the search value is matched at the beginning of
      strings like name_zh and name_en, instead of matching the entire string.
      The match is case sensitive.

    Further examples:

    >>> lookup(['name_zh', 'name_en'], code=110108)
    ('海淀区', 'Haidian')
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
        conditions += ' AND code BETWEEN %d AND %d' % (within, high)

    # Limit search to administrative level *level*
    level = kwargs.pop('level', None)

    if level is not None:
        if level in ('highest', 'lowest'):
            conditions += ' ORDER BY level %s LIMIT 1' % (
                'ASC' if level == 'highest' else 'DESC')
        elif level in (1, 2, 3):
            conditions += ' AND level == %d' % level
        else:
            raise ValueError(("level should be in (1, 2, 3, lowest, "
                              "highest); received %s") % level)

    partial = kwargs.pop('partial', False)

    # The only remaining argument's name is the column to query on; its value
    # is the value to look up.
    key, value = kwargs.popitem()
    if len(kwargs):
        raise ValueError('unexpected arguments: %s' % kwargs.keys())
    elif key not in COLUMNS:
        raise ValueError('invalid field name: %s' % key)

    if partial:
        condition = '%s GLOB ? %s' % (key, conditions)
        value += '*'
    else:
        condition = '%s = ? %s' % (key, conditions)

    # Retrieve the results
    try:
        return _select(fields, condition, (value,), columns=len(fields),
                       results=1)
    except KeyError:
        raise RegionKeyError('%s = %s with conditions %s' % (key, value,
                                                             conditions))


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

    parents_db = divisions.stack(code)

    # try:
    #     parents_db = _select(['code'], 'code in (?, ?, ?) ORDER BY code',
    #                          parents_guess, list)
    # except LookupError:
    #     raise InvalidCodeError('%d and its parents %s' %
    #                            (code, parents_guess[:2]))

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


def _select(fields, condition='', args=(), type=None, columns=1, results=-1):
    """Query the database."""
    sql = 'SELECT %s FROM codes %s' % (
        ', '.join(fields),
        ('WHERE ' + condition) if len(condition) else '',
        )
    # print(sql, args)
    cur = _db_conn.execute(sql, args)
    rows = cur.fetchall()

    if len(rows) == 0 or (results > 0 and len(rows) != results):
        exc_class = KeyError if len(rows) == 0 else AmbiguousRegionError
        expected = '1 or more' if results < 0 else results
        raise exc_class('%d results; expected %s' % (len(rows), expected))

    if type is None:
        if results == 1:
            result = rows[0]
            if columns == 1:
                result = result[0]
        else:
            result = rows
    elif type is list and columns == 1:
        result = list(chain(*rows))
    else:
        raise ValueError('type = %s (valid: None, list)')

    return result


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


divisions = Database('unified')
