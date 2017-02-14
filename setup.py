#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(name='gb2260',
      version='0.1-dev',
      author='Paul Natsuo Kishimoto',
      author_email='mail@paul.kishimoto.name',
      description='GB/T 2260-2007 codes',
      install_requires=[
        'beautifulsoup4',
        ],
      tests_require=['pytest'],
      url='https://github.com/khaeru/gb2260',
      packages=find_packages(),
      )
