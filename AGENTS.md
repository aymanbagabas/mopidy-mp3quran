# AGENTS.md

## Project Overview

Mopidy extension for streaming Quran recitations and radio stations from [mp3quran.net](https://www.mp3quran.net/). It's a Python 3 Mopidy backend plugin that registers custom URI scheme `mp3quran:` for browsing and playback.

## Build & Install

```bash
# Install from source (development)
pip install .

# Install editable for development
pip install -e .
```

Build is handled by `pyproject.toml` using setuptools. No Makefile, tox, or CI pipeline exists. Requires Python >= 3.13.

## Testing

```bash
pytest tests/
```

## Architecture

```
src/mopidy_mp3quran/
├── __init__.py     # Extension class — registers backend, defines config schema, version
├── backend.py      # Mopidy backend + providers (Library, Playback, Search)
├── client.py       # API client for mp3quran.net with in-memory caching
└── ext.conf        # Default Mopidy configuration snippet
```

### Control Flow

1. **Extension entry point** (`__init__.py`): Mopidy discovers the extension via the `mopidy.ext` entry point defined in `pyproject.toml`. `Extension.setup()` registers `Mp3QuranBackend`.

2. **Backend** (`backend.py`): `Mp3QuranBackend` is a Pykka `ThreadingActor` that instantiates the API client and three providers:
   - `Mp3QuranLibraryProvider` — browse/lookup URIs
   - `Mp3QuranPlaybackProvider` — translates `mp3quran:` URIs to streaming URLs
   - `Mp3QuranSearchProvider` — searches reciters and radios by name

3. **Client** (`client.py`): `Mp3Quran` class fetches data from mp3quran.net APIs on init, with time-based cache invalidation (`cache_ttl`). All API calls use `requests.Session` with proxy/user-agent from Mopidy config.

### URI Scheme

URIs follow the pattern `mp3quran:<locale>:<variant>[:<identifier>[:<sub_identifier>]]`:

| URI | Meaning |
|-----|---------|
| `mp3quran:root` | Root browse directory |
| `mp3quran:languages` | List all available languages |
| `mp3quran:<locale>:language` | Browse categories for a language |
| `mp3quran:<locale>:reciters` | List all reciters |
| `mp3quran:<locale>:reciter:<id>` | List moshafs for reciter `<id>` |
| `mp3quran:<locale>:moshaf:<reciter_id>:<moshaf_id>` | List surahs in moshaf |
| `mp3quran:<locale>:reciter:<reciter_id>:<moshaf_id>:<sura_no>` | Play surah (track) |
| `mp3quran:<locale>:riwayat` | List all riwayat |
| `mp3quran:<locale>:riwaya:<id>` | List moshafs for riwaya `<id>` |
| `mp3quran:<locale>:moshaf` | List all moshaf types |
| `mp3quran:<locale>:moshaf_type:<catalog_id>` | List moshafs of a type across reciters |
| `mp3quran:<locale>:suwar` | List all surahs |
| `mp3quran:<locale>:sura:<sura_no>` | List moshafs containing this surah |
| `mp3quran:<locale>:radios` | List all radio stations |
| `mp3quran:<locale>:radio:<id>` | Play radio (track) |
| `mp3quran:<locale>:tafasir` | List all tafasir |
| `mp3quran:<locale>:tafsir:<id>` | List tafsir audio entries |
| `mp3quran:<locale>:tafsir_audio:<tafsir_id>:<audio_id>` | Play tafsir audio (track) |

Note: All identifiers are **API IDs** (dict keys from the API responses). The shared `moshaf:<reciter_id>:<moshaf_id>` node is reused across riwayat, moshaf_type, and sura browse paths.

### Browse URI → Client Method Mapping

| URI pattern | `browse()` route | Client method |
|-------------|-------------------|---------------|
| `mp3quran:root` | `len==2 and parsed[1]=='root'` | `get_language_content(locale)` + Languages ref |
| `mp3quran:languages` | `len==2 and parsed[1]=='languages'` | `get_languages()` |
| `mp3quran:<locale>:language` | `variant=='language'` | `get_language_content(locale)` |
| `mp3quran:<locale>:reciters` | `variant=='reciters'` | `get_reciters(locale)` |
| `mp3quran:<locale>:reciter:<id>` | `variant=='reciter' and identifier` | `reciter_moshaf(locale, id)` |
| `mp3quran:<locale>:moshaf:<rid>:<mid>` | `variant=='moshaf' and identifier and extra` | `moshaf_suras(locale, rid, mid)` |
| `mp3quran:<locale>:riwayat` | `variant=='riwayat'` | `get_riwayat(locale)` |
| `mp3quran:<locale>:riwaya:<id>` | `variant=='riwaya' and identifier` | `riwaya_moshafs(locale, id)` |
| `mp3quran:<locale>:moshaf` | `variant=='moshaf' and not identifier` | `get_moshaf(locale)` |
| `mp3quran:<locale>:moshaf_type:<id>` | `variant=='moshaf_type' and identifier` | `moshaf_reciters(locale, id)` |
| `mp3quran:<locale>:suwar` | `variant=='suwar'` | `get_suwar(locale)` |
| `mp3quran:<locale>:sura:<no>` | `variant=='sura' and identifier` | `sura_moshafs(locale, no)` |
| `mp3quran:<locale>:radios` | `variant=='radios'` | `get_radios(locale)` |
| `mp3quran:<locale>:tafasir` | `variant=='tafasir'` | `get_tafasir(locale)` |
| `mp3quran:<locale>:tafsir:<id>` | `variant=='tafsir' and identifier` | `tafsir_audio(locale, id)` |

### Track URI → Lookup/Translate Mapping

| Track URI pattern | `lookup()` handling | `translate_uri()` handling |
|-------------------|---------------------|---------------------------|
| `mp3quran:<locale>:reciter:<rid>:<mid>:<sura>` | Build `Track` with reciter artist, moshaf album, sura name | `server + /{sura:03d}.mp3` |
| `mp3quran:<locale>:radio:<id>` | Build `Track` with radio name | `radios[id]['url']` |
| `mp3quran:<locale>:tafsir_audio:<tid>:<aid>` | Build `Track` with tafsir name via `translate_tafsir_uri()` | `tafsir_audio[tid][aid]['url']` (cached) |

### Client Method → API Endpoint Mapping

| Client method | API endpoint | Response key | `_LocaleData` field |
|---------------|-------------|--------------|---------------------|
| `_init_languages()` | `GET /api/v3/languages` | `language[]` | `self.languages` |
| `_init_suras(locale)` | `GET /api/v3/suwar?language={locale}` | `suwar[]` | `data.suras_name` |
| `_init_riwayat(locale)` | `GET /api/v3/riwayat?language={locale}` | `riwayat[]` | `data.riwayat` |
| `_init_moshaf(locale)` | `GET /api/v3/moshaf?language={locale}` | `riwayat[]` | `data.moshaf` |
| `_init_reciters(locale)` | `GET /api/v3/reciters?language={locale}` | `reciters[].moshaf[]` | `data.reciters` |
| `_init_radios(locale)` | `GET /api/v3/radios?language={locale}` | `radios[]` | `data.radios` |
| `_init_tafasir(locale)` | `GET /api/v3/tafasir?language={locale}` | `tafasir[]` | `data.tafasir` |
| `_init_tafsir_audio(locale, tafsir_id)` | `GET /api/v3/tafsir?tafsir={id}&language={locale}` | `tafasir.soar[]` | `data.tafsir_audio[id]` |

Note: The `/api/v3/moshaf` endpoint returns its array under the key `riwayat` (not `moshaf`) — this is an API quirk. The `/api/v3/reciters` endpoint also supports filtering via `reciter`, `rewaya`, and `sura` query parameters, but the client fetches all reciters and filters client-side.

### DistinctField Mapping

`Mp3QuranLibraryProvider.get_distinct()` maps Mopidy `DistinctField` values to mp3quran domain concepts:

| DistinctField | Domain concept | Source data | Description |
|---------------|---------------|-------------|-------------|
| `artist` | Reciters | `data.reciters[].name` | Distinct reciter names |
| `albumartist` | Reciters | `data.reciters[].name` | Same as `artist` — reciters are both artist and albumartist |
| `album` | Moshafs | `data.reciters[].moshaf[].name` | Distinct moshaf names (e.g. "Rewayat Hafs A'n Assem - Murattal") |
| `track_name` | Suwar | `data.suras_name[]` | Distinct surah names |
| All other fields | — | — | Returns empty `set()` |

Query filtering is supported for cross-field lookups:

| Query field | Applies to | Filter logic |
|-------------|-----------|--------------|
| `query={'album': '...'}` | `artist`, `albumartist`, `track_name` | Filter reciters to those with a matching moshaf name |
| `query={'artist': '...'}` | `album`, `track_name` | Filter moshafs/suwar to those by a matching reciter name |

Filter matching is case-insensitive substring matching (e.g. `query={'artist': 'sudais'}` matches "Abdul Rahman Al-Sudais").

### SearchField Mapping

`Mp3QuranLibraryProvider.search()` accepts a `Query[SearchField]` dict and uses fuzzy matching via `rapidfuzz` (threshold: 60.0 on `partial_ratio` scorer). When `exact=True`, falls back to case-insensitive exact match.

| SearchField | What is searched | Fuzzy match against | Returns in SearchResult |
|-------------|-----------------|---------------------|------------------------|
| `any` | All fields | Reciter names, moshaf names, surah names, radio names | Artists + Albums + Tracks |
| `artist` | Reciters | `data.reciters[].name` | Artists |
| `albumartist` | Reciters | `data.reciters[].name` | Artists (same as `artist`) |
| `album` | Moshafs | `data.reciters[].moshaf[].name` | Albums |
| `track_name` | Suwar | `data.suras_name[]` | Tracks (per-reciter-moshaf surah refs) |

When a surah matches via `track_name` or `any`, a track ref is generated for every reciter-moshaf combination that contains that surah (not just one).

The `uris` parameter scopes results to matching `mp3quran:` URI prefixes. For example, `uris=['mp3quran:eng:radios']` limits search to radios only.

The `exact` parameter switches from fuzzy matching to case-insensitive exact equality.

## Key Patterns & Gotchas

- **Language parameter mangling**: The `language` config value (e.g., `"English"`) is resolved to a locale code via the `/api/v3/languages` endpoint. The client's `resolve_language()` method accepts both full names and locale codes (e.g., `"English"` → `"eng"`, `"ar"` → `"ar"`).

- **Caching is time-based, not event-based**: `Mp3Quran` stores timestamps per data type and re-fetches when `cache_ttl` expires. Setting `cache_ttl=0` effectively disables caching (every call re-fetches). Cache is in-memory only — no disk persistence. Tafsir audio details are also cached per-tafsir in `_LocaleData.tafsir_audio`.

- **Pykka actor model**: The backend extends `pykka.ThreadingActor`. Provider methods run in the actor's thread. Access to `self.backend.mp3quran` from providers goes through Pykka proxy — but since all providers and the backend share the same actor, direct attribute access works within the actor's thread.

- **Version from package metadata**: `__version__` is read from `importlib.metadata` using the `Mopidy-Mp3Quran` dist name, not from a hardcoded string or regex.

- **No proxy config key**: `get_requests_session()` receives the full Mopidy config dict as `proxy_config`, but `httpclient.format_proxy()` expects specific proxy keys under the Mopidy config, not under `mp3quran`. This is standard Mopidy behavior but can be confusing.

## Configuration

Defined in `__init__.py:get_config_schema()` and defaults in `ext.conf`:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `language` | String | `English` | API language for reciter/surah names |
| `cache_ttl` | Integer | `3600` | Cache TTL in seconds (0 = disabled) |
| `timeout` | Integer | `10` | HTTP request timeout in seconds |

## Docker

The Docker image bundles Mopidy + Snapcast server in a single container. Snapcast reads from a named pipe (`/audio/snapfifo`) that Mopidy writes to.

- **Dockerfile** — installs Mopidy deps, snapserver, copies configs and entrypoint
- **docker/entrypoint.sh** — starts snapserver as a daemon, then execs the main process (mopidy)
- **docker/snapserver.conf** — snapcast stream source config (pipe at `/audio/snapfifo`)
- **docker/mopidy.conf** — mopidy config (audio output to `/audio/snapfifo`)
- **docker-compose.yml** — single-service compose with all ports exposed

### Ports

| Port | Service |
|------|---------|
| 6600 | Mopidy MPD |
| 6680 | Mopidy HTTP |
| 1704 | Snapcast stream |
| 1705 | Snapcast control |
| 1780 | Snapcast HTTP/Web UI |

## Dependencies

- `Mopidy >= 4.0`
- `Pykka >= 4.0`
- `requests`
- `rapidfuzz`

Mopidy and Pykka are not pip-installed independently — they come with a Mopidy installation.
