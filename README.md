# GB/T 2260-2007
**中华人民共和国行政区划代码** —
**Codes for the administrative divisions of the People's Republic of China**

[![Documentation Status](https://readthedocs.org/projects/gb2260/badge/?version=latest)](http://gb2260.readthedocs.io/en/latest/?badge=latest)

The GB/T 2260 standard defines six-digit numerical codes for the administrative
divisions of China, at the county level and above. For instance, the Haidian
district of Beijing has the code **110108**.

The most recent version of the official standard, designated "GB/T 2260-2007",
was published in 2008. However, codes are routinely revised, and the National
Bureau of Statistics (NBS) [publishes an updated list online annually][1].

This repository contains a Python script (`gb2260.py`) that attempts to produce
an up-to-date list of the GB/T 2260 codes, with extra information including
English names, Pinyin transcriptions, administrative levels, etc. The script
relies on three sources:

1. [The latest list of codes from the NBS website][2], published 2014-01-17
   with changes up to 2013-08-31. The variable `URL` in the script points to
   this page; if it moves, or another version is published, update the URL!
1. The information in `gbt_2260-2007.csv` (provided by Github user @qiaolun)
   and `gbt_2260-2007_sup.csv` (supplement, by @khaeru) transcribed from the
   published GB/T 2260-2007 standard.
1. The data set [GuoBiao (GB) Codes for the Administrative Divisions of the
   People's Republic of China, v1 (1982 – 1992)][1] (`citas.csv`), produced by
   the NASA Socioeconomic Data and Applications Center (SEDAC), the University
   of Washington Chinese Academy of Surveying and Mapping (CASM), the Columbia
   University Center for International Earth Science Information Network
   (CIESIN) as part of the China in Time and Space (*CITAS*) project. This data
   set contains Pinyin transcriptions.

The script produces two outputs:

1. `latest.csv` contains only information from source #1: the codes, Chinese
   names (column `name_zh`), and a `level` extracted by parsing the indentation
   on the NBS website.
1. `unified.csv` includes information from sources #2 and #3.

Dependencies
============

- [BeautifulSoup 4](http://www.crummy.com/software/BeautifulSoup/)
- [python-jianfan](https://code.google.com/p/python-jianfan/)

Copyright and License
=====================

`gb2260.py` are © 2014–2017 Paul Natsuo Kishimoto <<mail@paul.kishimoto.name>>
and distributed under the [GNU GPLv3][4].

The NBS website, which is scraped as the main and authoritative source of data,
provides [this copyright statement][5].

`gbt_2260-2007.csv` and `gbt_2260-2007_sup.csv` contain transcribed information
from GB/T 2260-2007, the copyright of which is unknown.

`citas.csv` is under the following ["use constraints"][6] (with emphasis
added):

>The University of Washington China in Time and Space (CITAS), Chinese Academy
of Surveying and Mapping (CASM), and Trustees of Columbia University in the
City of New York hold the copyright of this data set. **Users are prohibited
from any commercial, non-free resale, or redistribution without explicit
written permission** from CITAS, CASM, and CIESIN. Users should acknowledge
CITAS, CASM, and CIESIN as the source used in the creation of any reports,
publications, new data sets, derived products, or services resulting from the
use of this data set. CITAS, CASM, and CIESIN also request reprints of any
publications and notification of any redistributing efforts

[1]: http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/
[2]: http://www.stats.gov.cn/tjsj/tjbz/xzqhdm/201401/t20140116_501070.html
[3]: http://sedac.ciesin.columbia.edu/data/set/cddc-china-guobiao-codes-admin-divisions
[4]: http://www.gnu.org/licenses/gpl.html
[5]: http://www.stats.gov.cn/english/nbs/200701/t20070104_59236.html
[6]: http://sedac.ciesin.columbia.edu/data/set/cddc-china-guobiao-codes-admin-divisions/metadata
