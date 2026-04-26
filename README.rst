****************
Mopidy-Mp3Quran
****************

`Mopidy <http://www.mopidy.com/>`_ extension for streaming Quran recitations and radio stations from `Mp3Quran <http://www.mp3quran.net/>`_.

Features
========

- Browse and stream Quran recitations from 100+ reciters
- Listen to Quran radio stations
- Search reciters by name or recitation style (Riwaya)
- Configurable language, cache TTL, and request timeout
- Caching to reduce API calls


Installation
============

From PyPI::

    pip install Mopidy-Mp3Quran

From source::

    git clone https://github.com/aymanbagabas/mopidy-mp3quran.git
    cd mopidy-mp3quran && pip install .


Configuration
=============

By default, this extension is enabled. Modify the Mopidy configuration file to customize::

    [mp3quran]
    enabled = true
    language = English
    cache_ttl = 3600
    timeout = 10

**Configuration options:**

- **language** - API language (default: ``English``). Controls the language of reciter and surah names.
- **cache_ttl** - Cache time-to-live in seconds (default: ``3600``). Set to ``0`` to disable caching.
- **timeout** - HTTP request timeout in seconds (default: ``10``).


Usage
=====

Browse the library tree:

1. **Mp3Quran** (root) — top-level entry
2. **Reciters** — list of all available reciters
3. **Radios** — list of all radio stations
4. Select a reciter to see their available surahs
5. Select a surah to play it

Use search to find reciters or radio stations by name.


Project resources
=================

- `Source code <https://github.com/aymanbagabas/mopidy-mp3quran>`_
- `Issue tracker <https://github.com/aymanbagabas/mopidy-mp3quran/issues>`_


Changelog
=========

v0.2.0
-------------------

- Migrate to Python 3
- Add error handling for all API calls
- Add caching with configurable TTL
- Add search functionality
- Add configuration options (language, cache_ttl, timeout)
- Add type hints and docstrings
- Improve error handling in URI parsing and lookup

v0.1.0 (2018-03-05)
-------------------

- Initial release.
