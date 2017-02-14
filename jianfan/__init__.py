# -*- coding: utf-8 -*-
# author: Leon Dong <Leon.Dong@gmail.com> 老董

"""
    Jianfan is a library for translation between traditional and simplified chinese.
        two functions are provided by the library:
        jtof: translate simplified chinese to traditional chinese
        jtoj: translate traditional chinese to simplified chinese
        the two functions accept one parameter that is unicode or string
        the type of return value is unicode

    Jianfan是一个简体中文和繁体中文转换的库。提供了两个函数：
        jtof: 简体转换为繁体
        ftoj: 繁体转换为简体
        函数接受unicode和string类型作为参数，返回值统一为unicode
"""

from .charsets import gbk, big5, gbk_big5, big5_gbk

def _t(unistr, charset_from, charset_to):
    """
        This is a unexposed function, is responsibility for translation internal.
    """
    if type(unistr) is str:
        try:
            unistr = unistr.decode('utf-8')
        except:
            pass
    if type(unistr) is not bytes:
        return unistr
    chars = []
    for c in unistr:
        idx = charset_from.find(c)
        chars.append(charset_to[idx] if idx!=-1 else c)
    return u''.join(chars)


def jtof(unicode_string):
    """
        Translate simplified chinese to traditional chinese.
        >>> s = u'中华'
        >>> print jtof(s)
        中華
    """
    #return _t(unicode_string, gbk, big5)
    return(str.translate(unicode_string, gbk_big5))

def ftoj(unicode_string):
    """
        Translate traditional chinese to simplified chinese.
        >>> t = u'中華'
        >>> print ftoj(t)
        中华
    """
    #return _t(unicode_string, big5, gbk)
    return(str.translate(unicode_string, big5_gbk))
