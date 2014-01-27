#!/usr/bin/env python3
# Generate an up-to-date list of China administrative divisons
#
# TODO lots of documentation
import csv
from os import linesep
import re
import urllib.request

from bs4 import BeautifulSoup

import jianfan  # https://code.google.com/p/python-jianfan/

URL = "http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html"

exp = re.compile('(?P<code>\d{6})(?P<level>(\xa0){1,7})(?P<name_zh>.*)')


def match_names(official, citas):
    if official == citas:
        return 'identical'
    elif official in citas or citas in official:
        return 'substring'
    tr = jianfan.ftoj(citas)  # Avoid double call in next line
    if official in tr or tr in official:
        return 'translated substring'
    return False


def load_file(f, key):
    result = {}
    for row in csv.DictReader(f):
        code = int(row[key])
        del row[key]
        result[code] = row
    return result


def lookup(data, name, lang='en'):
    for k, v in data.items():
        if (lang == 'en' and name in v.get('name_en', '')) or (
            lang == 'zh' and name in v.get('name_zh', '')):
            return k
    raise KeyError(name)


if __name__ == '__main__':
    soup = BeautifulSoup(urllib.request.urlopen(URL))
    # commented: use this with a cached copy of the website
    #soup = BeautifulSoup(open('cached.html', 'r'))
    d0 = {}
    for div in soup('div', {'class': 'TRS_Editor'}):
        for p in div('p', {'align': 'justify', 'class': 'MsoNormal'}):
            match = exp.match(p.text.replace(' ', ''))
            if match is None:
                print('Not parsing:', p.prettify().replace('\n',''))
            else:
                d = match.groupdict()
                assert len(d['level']) % 2 == 1
                d0[int(d['code'])] = {
                    'code':int(d['code']),
                    'name_zh': d['name_zh'],
                    'level': int(len(d['level']) / 2)
                    }
    # Write out the latest data to file
    with open('latest.csv', 'w') as f:
        w = csv.writer(f, lineterminator=linesep)
        w.writerow(['code', 'name', 'level'])
        for k in sorted(d0.keys()):
            w.writerow([k, d0[k]['name_zh'], d0[k]['level']])
    # Load the CITAS data set
    d1 = load_file(open('citas.csv', 'r'), 'C-gbcode')
    # Load the GB/T 2260-2007 data
    d2 = load_file(open('gbt_2260-2007.csv', encoding='utf-8-sig'), 'code')
    d3 = load_file(open('gbt_2260-2007_sup.csv'), 'code')
    assert not any([k in d2 for k in d3.keys()])
    d2.update(d3)
    # Merge data
    for code in sorted(d0.keys()):
        message = '{}\t{}\n'.format(code, d0[code]['name_zh'])
        if code not in d1:
            message += '  does not appear in CITAS data set\n'
        else:
            d = dict(d1[code])
            d['name_zh'] = d.pop('N-hanzi')
            if not match_names(d0[code]['name_zh'], d['name_zh']):
                message += '  CITAS name {} ({}) does not match\n'.format(
                    d['name_zh'], jianfan.ftoj(d['name_zh']))
            else:
                d['name_en'] = d.pop('N-local').replace("`","'")
                d['name_pinyin'] = d.pop('N-pinyin').replace("`","'")
                d0[code].update(d)
        if code not in d2:
            message += '  does not appear in GB/T 2260-2007\n'
        else:
            d = dict(d2[code])
            d['name_zh'] = d.pop('name')
            if d0[code]['name_zh'] == d['name_zh']:
                d.pop('code', None)
                d.pop('id', None)
                if 'name_en' in d and d['name_en'] is None:
                    del d['name_en']
                d0[code].update(d)
            else:
                message += '  GB/T 2260-2007 name {} does not match\n'.format(
                    d['name_zh'])
        if message.count('\n') > 1:
            print(message, end='')
    # Write the unified data set to file
    with open('unified.csv', 'w') as f:
        w = csv.DictWriter(f, ('code', 'name_zh', 'name_en', 'name_pinyin',
            'level', 'latitude', 'longitude'), extrasaction='ignore',
            lineterminator=linesep)
        for k in sorted(d0.keys()):
            w.writerow(d0[k])
