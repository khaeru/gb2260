.. GB/T 2260-2007 documentation master file, created by
   sphinx-quickstart on Mon Feb 13 20:36:22 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

中华人民共和国行政区划代码** — Codes for the administrative divisions of the People's Republic of China
==========================================================================================================

Contents:

.. toctree::
   :maxdepth: 2

   license

About
-----

The GB/T 2260 standard defines six-digit numerical codes for the administrative divisions of China, at the county level and above. For instance, the Haidian district of Beijing has the code **110108**.

The most recent version of the official standard, designated "GB/T 2260-2007", was published in 2008. However, codes are routinely revised, and the National Bureau of Statistics (NBS) `publishes an updated list online annually <http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/>`_.

This repository contains a Python script (``gb2260/__init__.py``) that attempts to produce an up-to-date list of the GB/T 2260 codes, with extra information including English names, Pinyin transcriptions, administrative levels, etc. The script relies on three sources:

1. `The latest list of codes from the NBS website <http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html>`_, published 2014-01-17
   with changes up to 2013-08-31. The variable ``URL`` in the script points to
   this page; if it moves, or another version is published, update the URL!
2. The information in ``gbt_2260-2007.csv`` (provided by Github user @qiaolun)
   and ``gbt_2260-2007_sup.csv`` (supplement, by @khaeru) transcribed from the
   published GB/T 2260-2007 standard.
3. The data set `GuoBiao (GB) Codes for the Administrative Divisions of the
   People's Republic of China, v1 (1982 – 1992) <http://sedac.ciesin.columbia.edu/data/set/cddc-china-guobiao-codes-admin-divisions>`_ (``citas.csv``), produced by
   the NASA Socioeconomic Data and Applications Center (SEDAC), the University
   of Washington Chinese Academy of Surveying and Mapping (CASM), the Columbia
   University Center for International Earth Science Information Network
   (CIESIN) as part of the China in Time and Space (*CITAS*) project. This data
   set contains Pinyin transcriptions.

The script produces two outputs:

1. ``latest.csv`` contains only information from source #1: the codes, Chinese
   names (column ```name_zh``), and a ``level`` extracted by parsing the indentation on the NBS website.
2. ``unified.csv`` includes information from sources #2 and #3.


API
---

.. automodule:: gb2260
   :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
