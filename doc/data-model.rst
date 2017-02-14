Data model
==========

The database includes the following fields, and is *sparse*: not every field is populated for every entry. In particular, only ``code``, ``name_zh`` and ``level`` exist for all entries.

``code``
  The six-digit GB/T 2260-2007 code (:py:class:`int`).

``name_zh``
  Name of the region in simplified Chinese (:py:class:`str`).

``level``
  Administrative level of the region (:py:class:`int`, one of 1, 2, or 3).

  See `this table <https://en.wikipedia.org/wiki/Administrative_divisions_of_China#Table>`_ for an explanation of the various names for these levels.

``name_pinyin``
  Name of the region rendered in pinyin (:py:class:`str`).

``name_en``
  Name of the region in English (:py:class:`str`).

``alpha``
  2- or 3-digit uppercase alphabetical code for the region (:py:class:`str`).

``latitude``, ``longitude``
  Latitude and longitude of a point within the region (:py:class:`float`).
