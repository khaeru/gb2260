import pytest

from gb2260 import (
    divisions,
    isolike,
    level,
    parent,
    split,
    within,
    AmbiguousRegionError,
    InvalidCodeError
    )


def test_import():
    import gb2260  # noqa: F401


def test_all_at():
    assert len(divisions.all_at_level(1)) == 34
    assert len(divisions.all_at_level(2)) == 346
    assert len(divisions.all_at_level(3)) == 3134

    # Invalid levels
    with pytest.raises(ValueError):
        divisions.all_at_level(4)
    with pytest.raises(ValueError):
        divisions.all_at_level(0)


def test_isolike():
    assert isolike(130100) == 'CN-HE-SJW'
    assert isolike(130000) == 'CN-HE'
    with pytest.raises(InvalidCodeError):
        isolike(542621)


def test_level():
    assert level(110108) == 3
    with pytest.raises(InvalidCodeError):
        level(990000)


def test_search():
    d = divisions
    # Default field
    # TODO as a separate test
    assert d.search(name_zh='海淀区') == 110108

    # Single fields
    result = d.search(code=110108)
    assert result.name_en == 'Haidian'
    assert result.name_pinyin == 'Beijing: Haidian qu'
    assert result.name_zh == '海淀区'

    # Example of a division whose name_en & name_pinyin differ
    assert d.search(code=654326).name_pinyin == 'Jimunai'

    # A shortcut function is provided for level
    assert d.search(code=659001).level == level(659001)

    # Different return types
    assert d.search(code=110000).latitude == 39.9081726

    # Multiple fields
    result = d.search(code=110108)
    assert tuple(result[n] for n in ['name_zh', 'name_en']) == \
        ('海淀区', 'Haidian')

    # Ambiguous
    with pytest.raises(AmbiguousRegionError):
        d.search(name_zh='市辖区')

    # Disambiguate using the within parameter
    assert d.search(name_zh='市辖区', within=110000) == 110100

    # Ambiguous
    with pytest.raises(AmbiguousRegionError):
        d.search(name_en='Hainan')

    # Disambiguate using the level parameter
    assert d.search(name_en='Hainan', level=1) == 460000
    # a district in Wuhai, NM
    assert d.search(name_en='Hainan', level=3) == 150303
    assert d.search(name_en='Hainan', level='highest') == 460000
    assert d.search(name_en='Hainan', level='lowest') == 150303

    # A nonexistent field
    with pytest.raises(ValueError):
        d.search(foo=110108)

    # Looking up the same field
    assert d.search(name_zh='海淀区').name_zh == '海淀区'


def test_parent():
    assert parent(110108) == 110100
    assert parent(110100) == 110000
    assert parent(110108, 1) == 110000
    with pytest.raises(ValueError):
        parent(110000)
    with pytest.raises(ValueError):
        parent(110108, 0)
    with pytest.raises(InvalidCodeError):
        parent(990101)


def test_split():
    assert split(331024) == (33, 10, 24)


def test_within():
    assert within(331024, 330000)
    assert not within(331024, 110000)
    assert within(331024, 331024)
    assert not within(331024, 990000)
    assert within(990101, 990000)
