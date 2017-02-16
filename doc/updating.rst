Updating the database
=====================

When invoked as a module::

  $ python -m gb2260
  usage: __main__.py [-h]
                     [--version {2012-10-31,2013-08-31,2014-10-31,2015-09-30}]
                     [--cached] [--verbose]
                     ACTION

  positional arguments:
    ACTION                action to perform: either update or refresh-cache

  optional arguments:
    -h, --help            show this help message and exit
    --version {2012-10-31,2013-08-31,2014-10-31,2015-09-30}
                          version to update the database with
    --cached              read the data from cached HTML, instead of the NBS
                          website
    --verbose             give verbose output

…either of :meth:`update` or :meth:`refresh_cache`, below, can be invoked.

.. py:currentmodule:: gb2260.database

.. autofunction:: update
.. autofunction:: refresh_cache
.. autofunction:: parse_html
