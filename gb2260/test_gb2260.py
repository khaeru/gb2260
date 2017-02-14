import pytest

from gb2260 import codes, all_at, alpha, level, lookup, within


def test_import():
    import gb2260  # noqa: F401


def test_all_at():
    assert len(all_at(1)) == 34


def test_alpha():
    assert alpha(130100) == 'CN-HE-SJW'
    with pytest.raises(ValueError):
        alpha(542621)


def test_level():
    assert level(110108) == 3
    assert level(990000) == 1
    with pytest.raises(KeyError):
        codes[990000]['level']


def test_lookup():
    assert lookup(code=110108) == 'Beijing: Haidian qu'
    assert lookup(code=110108, field='name_zh') == '海淀区'


def test_within():
    assert within(331024, 330000)
    assert not within(331024, 110000)
    assert within(331024, 331024)
