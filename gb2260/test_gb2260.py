import pytest

from gb2260 import \
    codes, all_at, alpha, level, lookup, parent, split, within, \
    InvalidCodeError


def test_import():
    import gb2260  # noqa: F401


def test_all_at():
    assert len(all_at(1)) == 34
    assert len(all_at(2)) == 345
    assert len(all_at(3)) == 3136

    # Invalid levels
    with pytest.raises(LookupError):
        all_at(4)
    with pytest.raises(LookupError):
        all_at(0)


def test_alpha():
    assert alpha(130100) == 'CN-HE-SJW'
    assert alpha(130000) == 'CN-HE'
    with pytest.raises(ValueError):
        alpha(542621)


def test_level():
    assert level(110108) == 3
    with pytest.raises(InvalidCodeError):
        level(990000)


def test_lookup():
    # Default field
    assert lookup(name_zh='海淀区') == 110108

    # Single fields
    assert lookup('name_en', code=110108) == 'Beijing: Haidian qu'
    assert lookup('name_zh', code=110108) == '海淀区'

    # Example of a division whose name_en & name_pinyin differ
    assert lookup('name_pinyin', code=654326) == 'Jimunai'

    # A shortcut function is provided for level
    assert lookup('level', code=659001) == level(659001)

    # Different return types
    assert lookup('latitude', code=110000) == 39.9081726

    # Multiple fields
    assert lookup(['name_zh', 'name_en'], code=110108) == \
        ('海淀区', 'Beijing: Haidian qu')

    # Ambiguous
    with pytest.raises(LookupError):
        assert lookup('code', name_zh='市辖区') == 110100

    # Using the within parameter
    assert lookup('code', name_zh='市辖区', within=110000) == 110100

    # A nonexistent field
    with pytest.raises(ValueError):
        lookup('name_zh', foo=110108)

    # Multiple nonexistent fields:
    with pytest.raises(ValueError):
        lookup(['name_zh', None], code=110000)

    # Looking up the same field
    assert lookup('name_zh', name_zh='海淀区') == '海淀区'


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
