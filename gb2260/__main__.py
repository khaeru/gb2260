"""Valid actions are:

- update: update the database
"""
import argparse

from . import parse_raw, update, URL


parser = argparse.ArgumentParser(epilog=__doc__)
parser.add_argument('action', choices=['update'],
                    help='action to perform')

args = parser.parse_args()

if args.action == 'update':
    from urllib.request import urlopen
    # Read the NBS website
    update(parse_raw(urlopen(URL)))
    # commented: Use a cached copy of the website
    # update(open(data_fn('cached', 'html'), 'r'), verbose=True)
