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

from .database import (
    AmbiguousRegionError,
    Database,
    InvalidCodeError,
    _parents,
    )

__all__ = [
    'AmbiguousRegionError',
    'isolike',
    'level',
    'parent',
    'split',
    'within',
    ]

__version__ = '0.2-dev'


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
