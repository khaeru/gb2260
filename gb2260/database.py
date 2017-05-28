import logging
import os.path
import sqlite3

from pkg_resources import resource_filename

from .code import _coerce, _join, _level, _parents, split

log = logging.getLogger(__name__)

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

DATA_DIR = resource_filename(__name__, 'data')

SUFFIXES = [
    'kuangqu',    # 矿区, mining area
    'qi',         # 旗, banner
    'qu',         # 区, area
    'shi',        # 市, city
    'xian',       # 县, county
    'zizhixian',  # 自治县, autonomous county
    'zizhizhou',  # 自治州, autonomous state
    ]


class AmbiguousRegionError(LookupError):
    """Exception for a lookup that returns multiple results."""
    pass


class InvalidCodeError(LookupError):
    """Exception for an invalid code."""
    pass


class RegionKeyError(KeyError):
    """Exception for a lookup that returns nothing."""
    pass


def lazy_load(f):
    def load_if_needed(self, *args, **kw):
        if not self._is_loaded:
            self._load()
        return f(self, *args, **kw)
    return load_if_needed


class Division:
    _getattr_levels = ['is_province', 'is_prefecture', 'is_county']

    def __init__(self, cur=None, row=None, **fields):
        if cur:
            row = sqlite3.Row(cur, row)
            self._row = row
        else:
            self._fields = fields

    def __getattr__(self, key):
        if key in self._row.keys():
            return self._row[key]
        elif key in self._getattr_levels:
            return self._row['level'] == self._getattr_levels.index(key) + 1
        else:
            raise AttributeError

    def __getitem__(self, key):
        return self._row[key]

    def __eq__(self, other):
        if isinstance(other, Division):
            return self._row == other._row
        else:
            other = _coerce(other)
            if other is None:
                raise TypeError
            else:
                return self._row['code'] == other

    def __hash__(self):
        return self._row['code']

    def __repr__(self):
        cls_name = self.__class__.__name__
        fields = ', '.join('%s=%r' % (k, self._row[k]) for k in
                           sorted(self._row.keys()))
        return '%s(%s)' % (cls_name, fields)

    def __dir__(self):
        return dir(self.__class__) + self._row.keys()


class Database:
    def __init__(self, name):
        self.name = name
        self._index = {}
        self._is_loaded = False

    def _load(self):
        self._objects = set()
        self._conn = open_sqlite(self.name)
        self._is_loaded = True

    def _get_by_code(self, code):
        try:
            return self._index[code]
        except KeyError:
            result = self._select('code = ?', (code,))
            if len(result) == 0:
                raise InvalidCodeError(code)

    @lazy_load
    def _select(self, condition='', args=()):
        sql = 'SELECT * FROM codes' + (' WHERE %s' % condition if
                                       len(condition) else '')
        result = self._conn.execute(sql, args).fetchall()
        for div in result:
            self._objects.add(div)
            self._index[div.code] = div
        return result

    def all_at_level(self, level):
        if level not in (1, 2, 3):
            raise ValueError('level must be in 1, 2, 3')
        return self._select('level = ?', (level,))

    def get(self, code=None, **kwarg):
        if len(kwarg) > 1 or (len(kwarg) and code is not None):
            raise TypeError('Only one criterion may be given')
        elif len(kwarg) == 0:
            if code is None:
                raise TypeError('Must give a criterion')
            else:
                k = 'code'
                v = code
        else:
            k, v = kwarg.popitem()

        if k == 'code':
            div = self._get_by_code(int(v))
        else:
            result = self._select('%s = ?' % k, (v,))
            assert len(result) == 1
            div = result[0]

        return div

    def lookup(self, value):
        """Return first value matching the *kwargs."""
        types = {
            'code': int,
            'name_zh': str,
            'level': int,
            'name_pinyin': str,
            'name_en': str,
            'alpha': str,
            'latitude': float,
            'longitude': float,
            }
        conditions = []
        args = []
        for field, ftype in types.items():
            try:
                # Convert the argument to the field's type
                args.append(ftype(value))
                conditions.append('%s %s ?' % (
                    field,
                    'LIKE' if ftype == str else '=',
                    ))
            except ValueError:
                continue
        condition = ' OR '.join(conditions) + 'LIMIT 1'
        result = self._select(condition, args)
        if len(args) == 0:
            raise LookupError('Could not find a record for %r' % value)
        return result[0]

    def search(self, **kwargs):
        """Lookup information from the database.

        *fields* is either a :py:class:`str` specifying a single field, or an
        iterable of field names.

        Aside from optional *kwargs* (below), only one other keyword argument
        must be given. Its name is a database field; the value is the value to
        look up:

        >>> lookup(name_zh='海淀区')
        110108

        Lookup on (a) nonexistent field(s) raises :py:class:`ValueError`.
        Optional *kwargs* are:

        - *within*: a code. If specified, only entries that are within this
          division are returned. This is useful for lookups that would return
          more than one entry, normally a :py:class:`LookupError`:

            >>> lookup('code', name_zh='市辖区')
            Traceback (most recent call last):
              ...
            LookupError: 285 results, expected 1
            >>> lookup('code', name_zh='市辖区', within=110000)
            110100

        - *level*: an administrative level. If an integer (1, 2 or 3), only
           entries at this level are returned.

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
          strings like name_zh and name_en, instead of matching the entire
          string. The match is case sensitive.

        Further examples:

        >>> lookup(['name_zh', 'name_en'], code=110108)
        ('海淀区', 'Haidian')
        """
        # Query condition
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

        # The only remaining argument's name is the column to query on; its
        # value is the value to look up.
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
        result = self._select(condition, (value,))
        if len(result) != 1:
            error_str = '%s = %s with conditions %s' % (key, value, conditions)
            ErrorCls = AmbiguousRegionError if len(result) else RegionKeyError
            raise ErrorCls(error_str)

        return result[0]

    def stack(self, code):
        return tuple(map(self._get_by_code,
                         sorted(set(_parents(_coerce(code))))))

    def __iter__(self):
        self._select()  # Load all
        return iter(self._objects)

    @lazy_load
    def __len__(self):
        sql = 'SELECT count(*) FROM codes;'
        return self._conn.execute(sql).fetchone()._row[0]


def data_fn(base, ext='csv', path=None):
    """Construct the path to a filename in the package's ``data`` directory.

    Use *base* (may contain path separators) as the file basename, and *ext* as
    the extension.
    """
    if path is None:
        path = DATA_DIR
    return os.path.normpath(os.path.join(path, '%s.%s' % (base, ext)))


def open_sqlite(db):
    """Connect to the sqlite3 database in data/*db*.db."""
    db_fn = data_fn(db, 'db')

    if not os.path.exists(db_fn):
        from .admin import write_sqlite, load_csv

        write_sqlite(db, load_csv(db, keep_key=True))

    conn = sqlite3.connect(db_fn)
    conn.row_factory = Division

    return conn
