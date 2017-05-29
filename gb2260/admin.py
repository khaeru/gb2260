import csv
import logging
from os import linesep
import os.path
import re
import sqlite3

import jianfan
from xpinyin import Pinyin

from .code import _parents
from .database import COLUMNS, SUFFIXES, data_fn

log = logging.getLogger(__name__)

URLS = {
    '2015-09-30': '201608/t20160809_1386477.html',
    '2014-10-31': '201504/t20150415_712722.html',
    '2013-08-31': '201401/t20140116_501070.html',
    '2012-10-31': '201301/t20130118_38316.html',
    }

for k in URLS.keys():
    # Common prefix for all URLs
    URLS[k] = 'http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/' + URLS[k]


def _configure_log(verbose=False):
    """Return a logger, at the :py:data:`logging.DEBUG` level if *verbose*."""
    logging.basicConfig(format='%(name)s: %(message)s',
                        level=logging.DEBUG if verbose else logging.INFO)


def _dict_update(a, b, conflict='raise'):
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
                raise ValueError('Value %s for key %s would conflict with '
                                 'existing value %s ', v, k, a[k])
            elif conflict == 'squash':
                pass
            elif conflict == 'discard':
                continue
            elif callable(conflict):
                if not conflict(a[k], v, k):
                    continue
            else:
                raise ValueError('Cannot handle conflict with %s', conflict)
        a[k] = v


def _match_names(official, other):
    """Return a string describing the match between *official* and *other*."""
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


def load_csv(db, key='code', keep_key=False, filter=None):
    """Load database from a CSV file data/*db*.csv.

    A :py:class:`dict` is returned with keys from an index on column *code*,
    and values that are :py:class:`dict`s of database entries.

    If *keep_key* is :py:data:`True`, then the entries include *key*.

    If *filter* is a callable function, only CSV rows for which
    ``filter(row) == True`` are returned.
    """
    fn = data_fn(db)
    result = {}

    for row in csv.DictReader(open(fn)):
        if callable(filter) and not filter(row):
            continue

        code = int(row.pop(key))

        if keep_key:
            row[key] = code

        try:
            alpha = row.pop('alpha')
            row['alpha'] = None if alpha == '' else alpha
        except KeyError:
            pass

        for field, type in [('level', int),
                            ('latitude', float),
                            ('longitude', float)]:
            try:
                value = row.pop(field)
                row[field] = type(value)
            except KeyError:
                pass
            except ValueError as e:
                assert value == ''
                row[field] = None

        result[code] = row

    return result


def parse_html(f, year, method=2):
    """Parse the HTML code list for *year* from *f*.

    *f* can be any file-like object supported by BeautifulSoup(). Returns a
    dict where keys are codes, and entries are collections.defaultdict(None),
    with the keys code, level and name_zh populated.

    *year* is a hint to help different methods of extracting the data. In some
    years, the indentation level indicates the administrative level of a
    division. In other years, the level is inferred.
    """
    from collections import OrderedDict, defaultdict
    import bs4

    year = int(year)

    result = OrderedDict()

    # Same as gb2260._level and gb2260.split
    def _level(code):
        code_parts = (code // 10000, (code % 10000) // 100, code % 100)
        return 3 - sum([1 if c == 0 else 0 for c in code_parts])

    def _from_bare_text(text):
        # Split on whitespace
        splits = text.split()

        # Code at the beginning, name at the end
        code = int(splits[0])
        name_zh = splits[-1]

        # Same as gb2260._level()
        level = _level(code)

        return code, name_zh, level

    if year == 2012:
        # 2012 entries are in table rows
        top_selector = 'div.TRS_Editor table.MsoNormalTable tr'
    else:
        # Other years are in paragraphs
        top_selector = 'div.TRS_Editor p.MsoNormal'

    log.info(year)

    # Iterate over matching HTML elements
    for elem in bs4.BeautifulSoup(f, 'lxml').select(top_selector):
        if len(elem.text.strip()) == 0:
            continue

        if year == 2012:
            # Split on strings
            code, name_zh, level = _from_bare_text(elem.text)
        elif year == 2013:
            # The entries contain 3, 5 or 7 &nbsp; (\xa0) characters

            # Remove stray spaces and split on &nbsp;, so *parts* will
            # have 4, 6, or 8 entries
            parts = elem.text.replace(' ', '').split('\xa0')

            # Administrative level indicated by the indent
            assert len(parts) in (4, 6, 8)
            level = (len(parts) - 2) // 2

            # First part is the code, last part is the name
            code = int(parts[0])
            name_zh = parts[-1]
        else:
            # 2014, 2015
            try:
                # First <span> contains the code, last contains the name
                spans = elem.select('span')
                code = int(spans[0].text)
                name_zh = spans[-1].text.strip()

                # Name is preceded by 1–3 '\u3000' characters
                level = spans[-1].text.count('\u3000')

                if level not in (1, 2, 3):
                    old_level = level
                    level = _level(code)
                    log.debug(('Infer level %d for %d (wrong number %d of '
                               'spaces)') % (level, code, old_level))
            except ValueError:
                # int() didn't like the contents, maybe something else, e.g. a
                # 2014 line like:
                #
                # <p>
                #   <span>130111&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                #   &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
                #   <span>栾城区</span>
                # </p>
                log.debug('Fallback to plain text "%s"', elem.text)
                code, name_zh, level = _from_bare_text(elem.text)

        result[code] = defaultdict(
            lambda: None,
            code=code,
            name_zh=name_zh,
            level=level,
            )
    return result


def update(version='2015-09-30', use_cache=False, verbose=False,
           target=None):
    """Update the database.

    :meth:`update` relies on four sources, in the following order of authority:

    1. Error corrections from ``extra.csv``.
    2. The latest list of codes from the NBS website indicated by *version*
       (see :meth:`parse_html`). For instance, *version* ‘2013-08-31’ was
       published on 2014-01-17. If *use_cache* is :py:data:`True`, then a
       cached HTML list is used from the the directory ``data/cache/`` (see
       :meth:`refresh_cache`). Otherwise, or if the cache is missing, the file
       is downloaded from the website.
    3. The data set `GuoBiao (GB) Codes for the Administrative Divisions of the
       People's Republic of China, v1 (1982 – 1992)
       <http://sedac.ciesin.columbia.edu/data/set/
       cddc-china-guobiao-codes-admin-divisions>`_ (``citas.csv``), produced by
       the NASA Socioeconomic Data and Applications Center (SEDAC), the
       University of Washington Chinese Academy of Surveying and Mapping
       (CASM), the Columbia University Center for International Earth Science
       Information Network (CIESIN) as part of the China in Time and Space
       (*CITAS*) project. This data set contains Pinyin transcriptions.
    4. The information in ``gbt_2260-2007.csv`` (provided by `@qiaolun
       <https://github.com/qiaolun>`_) and ``gbt_2260-2007_sup.csv``
       (supplement) transcribed from the published GB/T 2260-2007 standard.

    If *verbose* is :py:data:`True`, verbose output is given.

    The following files are updated:

    - ``latest.csv`` with information from source #1 only: codes, Chinese names
      (``name_zh``), and ``level``.
    - ``unified.csv`` with all database fields and information from sources #2,
      #3 and #4.
    - ``unified.db``, the same information in a :py:mod:`sqlite3` database.
    """
    _configure_log(verbose)

    if use_cache:
        try:
            fn = data_fn(os.path.join('cache', version), 'html')
            log.info('reading from cached %s', fn)
            f = open(fn, 'r')
        except FileNotFoundError:
            log.info('  missing.')
            use_cache = False

    if not use_cache:
        from urllib.request import urlopen
        log.info('retrieving codes from %s', URLS[version])
        f = urlopen(URLS[version])

    # Parse the codes from HTML
    log.info('  parsing...')
    codes = parse_html(f, version.split('-')[0])
    assert sorted(codes.keys()) == list(codes.keys())
    log.info('  done.')

    # Save the latest table
    fn = data_fn('latest', path=target)
    with open(fn, 'w') as f1:
        w = csv.writer(f1, lineterminator=linesep)
        w.writerow(['code', 'name_zh', 'level'])
        for code in sorted(codes.keys()):
            w.writerow([code, codes[code]['name_zh'], codes[code]['level']])
    log.info('wrote %s', fn)

    # Load the CITAS table
    d1 = load_csv('citas', 'C-gbcode',
                  filter=lambda row: row['todate'] == '19941231')
    log.info('read CITAS data')

    # Load the GB/T 2260-2007 tables, from two files
    d2 = load_csv('gbt_2260-2007')
    d3 = load_csv('gbt_2260-2007_sup')
    log.info('loaded GB/T 2260-2007 entries')

    # Merge the two GB/T 2260-2007 files
    for code, d in d3.items():
        if code in d2:
            # Code appears in both files. Don't overwrite name_zh in
            # gbt_2260-2007.csv with an empty name_zh from
            # gbt_2260-2007_sup.csv.
            _dict_update(d2[code], d, conflict=lambda a, b, k: not(k ==
                         'name_zh' or b is None))
        else:
            # Code only appears in gbt_2260-2007_sup.csv
            d2[code] = d

    # Load extra data pertaining to the latest table
    d4 = load_csv('extra')
    log.info('loaded extra data')

    # Regular expression for English names from the CITAS database:
    # In a name like 'Beijing: Dongcheng qu' the prefix 'Beijing: ' is a
    # repetition of the name of the parent division, and the suffix ' qu' is
    # the type, not the name, of the area.
    name_re = re.compile('(?:[^:]*: )?(.*?)(?: (%s))?$' % '|'.join(SUFFIXES))

    pinyin = Pinyin()

    # Merge using codes
    log.info('merging codes')
    for code, entry in codes.items():
        # Store debug information to be printed (or not) later
        message = ['%s\t%s' % (code, entry['name_zh'])]

        if code in d1:
            # Merge CITAS entry for this code
            # Make a copy
            d = dict(d1[code])
            name_zh = d.pop('N-hanzi')
            if not _match_names(entry['name_zh'], name_zh):
                message.append('  CITAS name %s (%s) does not match' %
                               (name_zh, jianfan.ftoj(name_zh)))
            else:
                d['name_en'] = d.pop('N-local').replace("`", "'")
                d['name_pinyin'] = d.pop('N-pinyin').replace("`", "'")
                _dict_update(entry, d)
        else:
            message.append('  does not appear in CITAS data set')

        if code in d2:
            # Merge GB/T 2260-2007 entry for this code
            d = dict(d2[code])
            if len(d['name_zh']) and entry['name_zh'] != d['name_zh']:
                message.append('  GB/T 2260-2007 name %s does not match' %
                               d['name_zh'])
            else:
                # Don't overwrite name_en from CITAS with empty name_en from
                # GB/T 2260-2007
                _dict_update(entry, d, conflict=lambda a, b, k: not(
                             'name_' in k and b is ''))
        else:
            message.append('  does not appear in GB/T 2260-2007')

        # Merge extra data
        if code in d4:
            _dict_update(entry, d4[code], conflict='squash')

        # Clean up English names (in most cases, the CITAS romanized name)
        if entry['name_en'] is not None:
            # Replace ' shixiaqu' with ' city area', but do not discard
            name_en = entry['name_en'].replace(' shixiaqu', ' city area')
            # Use regex to discard prefixes and suffixes on names
            entry['name_en'] = name_re.match(name_en).group(1)
        elif entry['name_zh'] == '市辖区':
            # Fill in blank with 'CITYNAME city area', where possible
            pname = codes[_parents(code)[1]]['name_en']
            entry['name_en'] = None if pname is None else pname + ' city area'

        # Fill in pinyin names
        if entry['name_pinyin'] is None:
            entry['name_pinyin'] = pinyin.get_pinyin(entry['name_zh'],
                                                     '').title()

        if len(message) > 1 and 'does not appear in CITAS' not in message[1]:
            log.info('\n'.join(message))
        else:
            log.debug('\n'.join(message))
    log.info('merge complete')

    # Write the unified data set to CSV
    fn = data_fn('unified', path=target)
    with open(fn, 'w') as f:
        w = csv.DictWriter(f, ('code', 'name_zh', 'name_en', 'name_pinyin',
                               'alpha', 'level', 'latitude', 'longitude'),
                           extrasaction='ignore', lineterminator=linesep)
        w.writeheader()
        for k in sorted(codes.keys()):
            w.writerow(codes[k])
    log.info('wrote %s', fn)

    write_sqlite('unified', codes, target=target)
    log.info('wrote sqlite3 database')


def write_sqlite(db, data, target=None):
    """Write *data* to a table codes in data/*db*.db."""

    # Connect to database
    conn = sqlite3.connect(data_fn(db, 'db', path=target))
    cur = conn.cursor()

    # Create the table
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

    # Query string
    insert_query = 'INSERT INTO codes (' + ', '.join(COLUMNS) + ') VALUES (:'
    insert_query += ', :'.join(COLUMNS) + ')'

    # Insert data
    cur.executemany(insert_query, data.values())

    # Commit & close
    cur.close()
    conn.commit()
    conn.close()


def refresh_cache(target=None):
    """Refresh the cache.

    For each URL in the :data:`URLS` variable, download the indicated HTML file
    and save it in the directory ``data/``.
    """
    from urllib.request import urlopen

    _configure_log()

    for date, url in URLS.items():
        with urlopen(url) as f_in:
            log.info('saving %s', url)

            cache_fn = data_fn(os.path.join('cache', date), 'html',
                               path=target)

            with open(cache_fn, 'wb') as f_out:
                log.info('  to %s', cache_fn)
                f_out.write(f_in.read())

        log.info('  done')
