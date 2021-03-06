import argparse

from .admin import URLS, refresh_cache, update

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', metavar='ACTION',
                    choices=['update', 'refresh-cache'],
                    help='action to perform: either update or refresh-cache')
parser.add_argument('--version', choices=sorted(URLS.keys()),
                    help='version to update the database with')
parser.add_argument('--cached', action='store_true',
                    help='read the data from cached HTML, instead of the NBS '
                         'website')
parser.add_argument('--verbose', action='store_true',
                    help='give verbose output')

args = parser.parse_args()


if args.action == 'update':
    update(args.version, use_cache=args.cached, verbose=args.verbose)
elif args.action == 'refresh-cache':
    refresh_cache()
