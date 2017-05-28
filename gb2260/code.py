def _coerce(code, error='raise'):
    try:
        return int(code)
    except ValueError:
        if error == 'raise':
            raise
        else:
            return None


def _join(levels):
    return levels[0] * 10000 + levels[1] * 100 + levels[2]


def _level(code):
    """Return the administrative level of *code*.

    Unlike :meth:`level`, does *not* raise an exception if *code* does not
    describe an entry in the database.
    """
    return 3 - sum([1 if c == 0 else 0 for c in split(code)])


def _parents(code):
    """Return a tuple of parents of *code* at levels 1, 2 and 3."""
    return (code - code % 10000, code - code % 100, code)


def split(code):
    """Return a tuple containing the three parts of *code*.

    >>> split(331024)
    (33, 10, 24)
    """
    return (code // 10000, (code % 10000) // 100, code % 100)
