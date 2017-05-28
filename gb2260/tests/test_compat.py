"""Imitate other packages."""
import sys

import gb2260
import pytest


# pycountry

def test_country_list():
    assert len(gb2260.divisions) == 3515
    assert isinstance(list(gb2260.divisions)[0], gb2260.database.Division)


def test_guangzhou_has_all_attributes():
    can = gb2260.divisions.get(code=440100)
    print(can)
    assert can.code == 440100
    assert can.name_zh == '广州市'
    assert can.name_en == 'Guangzhou'
    assert can.name_pinyin == 'Guangzhou shi'
    assert can.alpha == 'CAN'
    assert can.level == 2
    assert can.latitude == 23.1270407
    assert can.longitude == 113.341527


def test_dir():
    can = gb2260.divisions.get(code=440100)
    for n in ('code', 'name_zh', 'name_en', 'name_pinyin', 'alpha', 'level',
              'latitude', 'longitude'):
        assert n in dir(can)


def test_get():
    d = gb2260.divisions
    with pytest.raises(TypeError):
        d.get(code=440100, name_en='Guangzhou')
    assert d.get(code=440100) == d.get(name_en='Guangzhou')


def test_lookup():
    d = gb2260.divisions
    g = d.get(alpha='CAN')
    assert g == d.lookup('Guangzhou')  # name_en
    assert g == d.lookup('Guangzhou shi')  # name_pinyin
    assert g == d.lookup('广州市')  # name_zh
    assert g == d.lookup(440100)  # code
    assert g == d.lookup(23.1270407)  # latitude
    assert g == d.lookup(113.341527)  # longitude
    # Won't work on these fields, ambiguous
    assert g != d.lookup(2)  # level
    with pytest.raises(LookupError):
        gb2260.divisions.lookup('bogus country')
    with pytest.raises(LookupError):
        gb2260.divisions.lookup(12345)


# https://github.com/cn/GB2260.py

@pytest.mark.parametrize(
    'code,stack_name,is_province,is_prefecture,is_county',
    [('110101', u'北京市/市辖区/东城区', False, False, True),
     ('110100', u'北京市/市辖区', False, True, False),
     ('110000', u'北京市', True, False, False),
     ])
def test_division(code, stack_name, is_province, is_prefecture, is_county):
    div = gb2260.divisions.get(code)
    assert div.code == int(code)
    assert div.is_province == is_province
    assert div.is_prefecture == is_prefecture
    assert div.is_county == is_county
    # TODO alias name_zh to name
    assert ('/'.join(x.name_zh for x in gb2260.divisions.stack(code)) ==
            stack_name)


# to silence flake8:
unicode, Division, make_year_key = None, None, None


@pytest.mark.skipif(sys.version_info[0] != 2, reason='requires python 2.x')
@pytest.mark.parametrize('code,year,repr_result,unicode_result', [
    ('110101', None,
     "gb2260.get(u'110101')", u'<GB2260 110101 北京市/市辖区/东城区>'),
    ('110100', None,
     "gb2260.get(u'110100')", u'<GB2260 110100 北京市/市辖区>'),
    ('110000', None,
     "gb2260.get(u'110000')", u'<GB2260 110000 北京市>'),
    ('110000', 2006,
     "gb2260.get(u'110000', 2006)", u'<GB2260-2006 110000 北京市>'),
])
def test_representation_python2(code, year, repr_result, unicode_result):
    division = gb2260.divisions.get(code, year)
    assert repr(division) == repr_result
    assert str(division) == unicode_result.encode('utf-8')
    assert unicode(division) == unicode_result
    assert isinstance(repr(division), str)
    assert isinstance(str(division), str)
    assert isinstance(unicode(division), unicode)


@pytest.mark.xfail(reason='awaiting database year versions')
@pytest.mark.skipif(sys.version_info[0] != 3, reason='requires python 3.x')
@pytest.mark.parametrize('code,year,repr_result,unicode_result', [
    ('110101', None,
     u"gb2260.get('110101')", u'<GB2260 110101 北京市/市辖区/东城区>'),
    ('110100', None,
     u"gb2260.get('110100')", u'<GB2260 110100 北京市/市辖区>'),
    ('110000', None,
     u"gb2260.get('110000')", u'<GB2260 110000 北京市>'),
    ('110000', 2006,
     u"gb2260.get('110000', 2006)", u'<GB2260-2006 110000 北京市>'),
])
def test_representation_python3(code, year, repr_result, unicode_result):
    division = gb2260.divisions.get(code, year)
    assert repr(division) == repr_result
    assert str(division) == unicode_result
    assert isinstance(repr(division), str)
    assert isinstance(str(division), str)


@pytest.mark.xfail(reason='awaiting database year versions')
def test_comparable():
    assert gb2260.divisions.get(110101) == Division(110101, u'东城区')
    assert gb2260.divisions.get(110101) != Division(110000, u'北京市')
    assert (gb2260.divisions.get(110101, year=2006) !=
            Division(110101, u'东城区'))


@pytest.mark.xfail(reason='awaiting database year versions')
def test_hashable():
    division_set = set([
        Division(110101, u'东城区'),
        Division(110000, u'北京市'),
        Division(110101, u'东城区'),
        Division(110101, u'东城区', 2006),
    ])
    assert division_set == set([
        Division(110101, u'东城区'),
        Division(110000, u'北京市'),
        Division(110101, u'东城区', 2006),
    ])


@pytest.mark.xfail(reason='awaiting database year versions')
def test_history_data():
    assert (gb2260.divisions.get(522401, year=2010) ==
            Division(522401, u'毕节市', 2010))

    with pytest.raises(ValueError) as error:
        gb2260.divisions.get(522401)
    assert error.value.args[0] == '522401 is not valid division code'

    with pytest.raises(ValueError) as error:
        gb2260.divisions.get(110101, 2000)
    assert error.value.args[0].startswith('year must be in')


@pytest.mark.xfail(reason='awaiting database year versions')
@pytest.mark.parametrize('code,name,year', [
    (522401, u'毕节市', 2010),
    (419000, u'省直辖县级行政区划', None),
])
def test_searching(code, name, year):
    division = Division.search(code)
    assert division.name == name
    assert division.year == year


@pytest.mark.xfail(reason='awaiting database year versions')
@pytest.mark.parametrize('year,result', [
    (2013, (2013, 12)),
    (201304, (2013, 4)),
    ('2013', (2013, 12)),
    ('201304', (2013, 4)),
    (None, (2014, 12)),
])
def test_make_year_key(year, result):
    assert make_year_key(year) == result


@pytest.mark.xfail(reason='awaiting database year versions')
def test_make_invalid_year_key():
    pytest.raises(ValueError, make_year_key, 20)
    pytest.raises(ValueError, make_year_key, '20')
    pytest.raises(ValueError, make_year_key, 20122222)
    pytest.raises(ValueError, make_year_key, '20122222')
