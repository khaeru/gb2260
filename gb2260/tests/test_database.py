import glob
from os.path import basename, join

from gb2260.database import DATA_DIR, parse_html

num_entries = {
    '2012': 3507,
    '2013': 3515,
    '2014': 3512,
    '2015': 3514,
    }


def test_parse_html():
    # If nothing has been cached (e.g. on Travis), this loop never executes
    for fn in glob.glob(join(DATA_DIR, 'cache', '*.html')):
        with open(fn, 'rt') as f:
            year = basename(fn).split('-')[0]
            assert len(parse_html(f, year)) == num_entries[year]
