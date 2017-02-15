Updating the database
=====================

When invoked as a module::

$ python3 -m gb2260

…the package attempts to produce an up-to-date list of the GB/T 2260 codes, with extra information including English names, Pinyin transcriptions, administrative levels, etc. The update script relies on three sources:

1. `The latest list of codes from the NBS website <http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html>`_, published 2014-01-17 with changes up to 2013-08-31. The variable ``URL`` in the script points to this page; if it moves, or another version is published, update the URL!
2. The information in ``gbt_2260-2007.csv`` (provided by `@qiaolun <https://github.com/qiaolun>`_) and ``gbt_2260-2007_sup.csv`` (supplement) transcribed from the published GB/T 2260-2007 standard.
3. The data set `GuoBiao (GB) Codes for the Administrative Divisions of the People's Republic of China, v1 (1982 – 1992) <http://sedac.ciesin.columbia.edu/data/set/cddc-china-guobiao-codes-admin-divisions>`_ (``citas.csv``), produced by the NASA Socioeconomic Data and Applications Center (SEDAC), the University of Washington Chinese Academy of Surveying and Mapping (CASM), the Columbia University Center for International Earth Science Information Network (CIESIN) as part of the China in Time and Space (*CITAS*) project. This data set contains Pinyin transcriptions.

The script produces two outputs:

1. ``latest.csv`` contains only information from source #1: the codes, Chinese
   names (column ``name_zh``), and a ``level`` extracted by parsing the indentation on the NBS website.
2. ``unified.csv`` includes information from sources #2 and #3.


.. py:currentmodule:: gb2260.database

.. autofunction:: update
.. autofunction:: parse_html
.. autofunction:: data_fn
.. autofunction:: load_csv
.. autofunction:: match_names
.. autofunction:: dict_update
