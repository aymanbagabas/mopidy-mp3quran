# Mopidy-Mp3Quran

[Mopidy](http://www.mopidy.com/) extension for streaming Quran recitations and radio stations from [Mp3Quran](http://www.mp3quran.net/).

## Features

- Browse and stream Quran recitations from 100+ reciters
- Listen to Quran radio stations
- **Fuzzy search** reciters by name — handles typos and partial matches
- **Favorites** folder for quick access to saved reciters and radios
- Configurable language, cache TTL, and request timeout
- Caching to reduce API calls

## Installation

From PyPI:

    pip install Mopidy-Mp3Quran

From source:

    git clone https://github.com/aymanbagabas/mopidy-mp3quran.git
    cd mopidy-mp3quran && pip install .

## Configuration

By default, this extension is enabled. Modify the Mopidy configuration file to customize:

```ini
[mp3quran]
enabled = true
language = english
cache_ttl = 3600
timeout = 10
favorites_path =
```

**Configuration options:**

- **language** - API language (default: `English`). Controls the language of reciter and surah names. Accepts both the full name (e.g. `English`, `arabic`) and the locale code (e.g. `eng`, `ar`), case-insensitive.

**Supported languages:**

| Locale | Language         | Native    |
| ------ | ---------------- | --------- |
| `ar`   | Arabic           | العربية   |
| `eng`  | English          | English   |
| `fr`   | French           | Français  |
| `ru`   | Russian          | Русский   |
| `de`   | German           | Deutsch   |
| `es`   | Spanish          | Español   |
| `tr`   | Turkish          | Türkçe    |
| `cn`   | Chinese          | 中文      |
| `th`   | Thai             | ไทย       |
| `ur`   | Urdu             | اردو      |
| `bn`   | Bengali          | বাংলা     |
| `bs`   | Bosnian          | Bosanski  |
| `ug`   | Uyghur           | ئۇيغۇرچە  |
| `fa`   | Persian          | فارسی     |
| `tg`   | Tajik (Cyrillic) | тоҷикӣ    |
| `ml`   | Malayalam        | മലയാളം    |
| `tl`   | Tagalog          | Tagalog   |
| `id`   | Indonesian       | Indonesia |
| `pt`   | Portuguese       | Português |
| `ha`   | Hausa            | Hausa     |
| `sw`   | Swahili          | Kiswahili |

- **cache_ttl** - Cache time-to-live in seconds (default: `3600`). Set to `0` to disable caching.
- **timeout** - HTTP request timeout in seconds (default: `10`).
- **favorites_path** - Path to JSON file storing favorites. Leave empty to use the default (`~/.local/share/mopidy-mp3quran/favorites.json`).

## Usage

Browse the library tree:

1. **Mp3Quran** (root) — top-level entry
2. **Languages** — switch to a different language
3. **Favorites** — quick access to saved reciters and radios
4. **Reciters** — list of all available reciters
5. **Radios** — list of all radio stations
6. Select a reciter to see their recitation versions (Moshaf, e.g. Hafs, Warsh)
7. Select a moshaf to see its available surahs
8. Select a surah to play it

Use search to find reciters or radio stations by name. Search uses fuzzy matching so typos and partial names work (e.g. `meshary` finds `Mishary Rashid Alafasy`).

## Development

```bash
git clone https://github.com/aymanbagabas/mopidy-mp3quran.git
cd mopidy-mp3quran
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

### Docker

Run with Docker Compose (includes Mopidy + Snapcast server):

```bash
docker compose up
```

This starts a single container with Mopidy and Snapcast server. Mopidy outputs audio to a named pipe that Snapcast reads from.

| Port | Service              |
| ---- | -------------------- |
| 6600 | Mopidy MPD           |
| 6680 | Mopidy HTTP          |
| 1704 | Snapcast stream      |
| 1705 | Snapcast control     |
| 1780 | Snapcast HTTP/Web UI |

Configuration files are in `docker/mopidy.conf` and `docker/snapserver.conf`.

## Project resources

- [Source code](https://github.com/aymanbagabas/mopidy-mp3quran)
- [Issue tracker](https://github.com/aymanbagabas/mopidy-mp3quran/issues)

## Changelog

### v0.2.0 (2026-04-26)

- Migrate to mp3quran.net v3 REST API
- Support multiple moshaf (recitation versions) per reciter
- Add riwayat (narration types) support
- **Fuzzy search** — handles typos and partial matches (e.g. `meshary` → `Mishary`)
- **Favorites** folder — save and quickly access preferred reciters and radios
- Language config now accepts both full names and locale codes (case-insensitive)
- Migrate to `pyproject.toml` with `src` layout
- Migrate to Mopidy 4.x API (search on LibraryProvider)
- Fix proxy configuration bug (config key)
- Fix search dropping reciter results
- Add unit test suite (102+ tests)
- Remove dead `parse_uri()` function
- Migrate to Python 3
- Add error handling for all API calls
- Add caching with configurable TTL
- Add search functionality
- Add configuration options (language, cache_ttl, timeout, favorites_path)
- Add type hints and docstrings
- Improve error handling in URI parsing and lookup

### v0.1.0 (2018-03-05)

- Initial release.
