import glob
import os
from os.path import basename, join

import pytest

from gb2260.database import DATA_DIR
from gb2260.admin import URLS, load_csv, parse_html, update, refresh_cache

num_entries = {
    '2012': 3507,
    '2013': 3515,
    '2014': 3512,
    '2015': 3514,
    }


# If nothing has been cached (e.g. on Travis), this loop never executes
@pytest.mark.parametrize('fn', glob.glob(join(DATA_DIR, 'cache', '*.html')))
def test_parse_html(fn):
    with open(fn, 'rt') as f:
        year = basename(fn).split('-')[0]
        assert len(parse_html(f, year)) == num_entries[year]


@pytest.mark.parametrize('fn', glob.glob(join(DATA_DIR, '*.csv')))
def test_load_csv(fn):
    base = basename(fn).split('.')[0]
    if base == 'citas':
        kwargs = dict(
            key='C-gbcode',
            filter=lambda row: row['todate'] == '19941231',
            )
    else:
        kwargs = {}

    load_csv(base, **kwargs)


@pytest.mark.skipif(os.environ.get('TRAVIS', '') == 'true',
                    reason="Don't spam the government's servers")
def test_refresh_cache(tmpdir):
    refresh_cache(target=str(tmpdir))


@pytest.mark.skipif(os.environ.get('TRAVIS', '') == 'true',
                    reason="Don't spam the government's servers")
@pytest.mark.parametrize('version', URLS.keys())
def test_update(version, tmpdir):
    update(version=version, use_cache=True, verbose=True, target=str(tmpdir))
