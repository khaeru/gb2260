#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(name='gb2260',
      version='1',
      description=('GB/T 2260-2007 codes'),
      url='https://github.com/khaeru/gb2260',
      packages=find_packages(),
      long_description=("GB/T 2260-2007 中华人民共和国行政区划代码 Codes for"
                        "the administrative divisions of the People's Republic"
                        " of China"),
      license='GPLv3',
      platforms=['any'],
      )
