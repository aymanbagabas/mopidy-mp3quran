import time
import logging
from typing import Dict, Iterable, List, Optional, Any, Set

import requests
from rapidfuzz import fuzz, process
from mopidy.models import Album, Artist, Ref, SearchResult, Track
from mopidy.types import Uri

logger = logging.getLogger(__name__)

_API_BASE = 'https://mp3quran.net/api/v3/'
_DEFAULT_CACHE_TTL = 3600  # 1 hour
_DEFAULT_TIMEOUT = 10  # seconds
_DEFAULT_LOCALE = 'eng'


class _LocaleData:
    """Cached data for a single locale."""

    __slots__ = ('reciters', 'radios', 'suras_name', 'riwayat', 'moshaf', 'tafasir',
                 'tafsir_audio',
                 'reciters_ts', 'radios_ts', 'suras_ts', 'riwayat_ts', 'moshaf_ts', 'tafasir_ts',
                 'tafsir_audio_ts')

    def __init__(self):
        self.reciters: Dict[int, Dict[str, Any]] = {}
        self.radios: Dict[int, Dict[str, str]] = {}
        self.suras_name: Dict[int, str] = {}
        self.riwayat: Dict[int, str] = {}
        self.moshaf: Dict[int, Dict[str, Any]] = {}
        self.tafasir: Dict[int, Dict[str, Any]] = {}
        self.tafsir_audio: Dict[int, Dict[int, Dict[str, str]]] = {}
        self.reciters_ts: float = 0.0
        self.radios_ts: float = 0.0
        self.suras_ts: float = 0.0
        self.riwayat_ts: float = 0.0
        self.moshaf_ts: float = 0.0
        self.tafasir_ts: float = 0.0
        self.tafsir_audio_ts: float = 0.0


class Mp3Quran:
    """Client for the mp3quran.net v3 REST API with per-locale caching."""

    def __init__(
        self,
        session: requests.Session = None,
        cache_ttl: int = _DEFAULT_CACHE_TTL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.session = session or requests.Session()
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        self.languages: List[Dict[str, str]] = []
        self._languages_timestamp: float = 0.0

        self._locales: Dict[str, _LocaleData] = {}

        self._init_languages()

    def resolve_language(self, name: str) -> str:
        """Resolve a language name or locale code to a canonical locale code.

        Accepts both long form (e.g. 'English', 'arabic') and short form
        (e.g. 'eng', 'AR'). Case-insensitive. Returns the locale as-is if
        no match is found (may be a valid locale the API hasn't listed yet).
        """
        lower = name.lower().strip()
        for lang in self.languages:
            if lang['locale'].lower() == lower or lang['name'].lower() == lower:
                return lang['locale']
        return lower

    def _get_locale_data(self, locale: str) -> _LocaleData:
        """Get or create locale data, loading on first access."""
        if locale not in self._locales:
            self._locales[locale] = _LocaleData()
        return self._locales[locale]

    def _ensure_loaded(self, locale: str, data: _LocaleData = None) -> None:
        """Ensure data for a locale is loaded from the API."""
        if data is None:
            data = self._get_locale_data(locale)
        self._init_suras(locale, data)
        self._init_riwayat(locale, data)
        self._init_moshaf(locale, data)
        self._init_reciters(locale, data)
        self._init_radios(locale, data)
        self._init_tafasir(locale, data)

    def _is_cache_valid(self, timestamp: float) -> bool:
        if timestamp == 0.0:
            return False
        return (time.time() - timestamp) < self.cache_ttl

    def _fetch(self, url: str) -> Optional[dict]:
        """Fetch JSON from a URL with error handling."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error('Mp3Quran: Failed to fetch %s: %s', url, e)
            return None
        except (KeyError, ValueError) as e:
            logger.error('Mp3Quran: Invalid data from %s: %s', url, e)
            return None

    def _init_languages(self) -> None:
        if self._is_cache_valid(self._languages_timestamp):
            return
        data = self._fetch(_API_BASE + 'languages')
        if data is None:
            return
        self.languages = []
        for lang in data.get('language', []):
            try:
                self.languages.append({
                    'id': lang['id'],
                    'name': lang['language'],
                    'native': lang.get('native', ''),
                    'locale': lang['locale'],
                })
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid language entry: %s', e)
                continue
        self._languages_timestamp = time.time()

    def _init_suras(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.suras_ts):
            return
        url = _API_BASE + 'suwar?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for sura in resp.get('suwar', []):
            try:
                name = sura['name'].strip()
                data.suras_name[int(sura['id'])] = name
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid surah entry: %s', e)
                continue
        data.suras_ts = time.time()

    def _init_riwayat(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.riwayat_ts):
            return
        url = _API_BASE + 'riwayat?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for r in resp.get('riwayat', []):
            try:
                data.riwayat[int(r['id'])] = r['name']
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid riwayat entry: %s', e)
                continue
        data.riwayat_ts = time.time()

    def _init_moshaf(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.moshaf_ts):
            return
        url = _API_BASE + 'moshaf?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for m in resp.get('riwayat', []):
            try:
                data.moshaf[int(m['id'])] = {
                    'name': m['name'],
                    'moshaf_type': int(m['moshaf_type']),
                    'moshaf_id': int(m['moshaf_id']),
                }
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid moshaf catalog entry: %s', e)
                continue
        data.moshaf_ts = time.time()

    def _init_reciters(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.reciters_ts):
            return
        url = _API_BASE + 'reciters?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for reciter in resp.get('reciters', []):
            try:
                moshaf_list = []
                has_valid_moshaf = False
                for m in reciter.get('moshaf', []):
                    try:
                        sura_ids = [int(n) for n in m['surah_list'].split(',') if n.strip()]
                        moshaf_list.append({
                            'id': int(m['id']),
                            'name': m['name'],
                            'rewaya_id': int(m.get('rewaya_id', 0)),
                            'server': m['server'],
                            'surah_total': int(m.get('surah_total', 0)),
                            'moshaf_type': int(m.get('moshaf_type', 0)),
                            'surah_list': sura_ids,
                        })
                        has_valid_moshaf = True
                    except (KeyError, ValueError) as e:
                        logger.warning('Mp3Quran: Skipping invalid moshaf entry: %s', e)
                        continue
                if not has_valid_moshaf:
                    logger.warning('Mp3Quran: Skipping reciter with no valid moshaf: %s', reciter.get('name', '?'))
                    continue
                data.reciters[int(reciter['id'])] = {
                    'name': reciter['name'],
                    'letter': reciter.get('letter', ''),
                    'date': reciter.get('date', ''),
                    'moshaf': moshaf_list,
                }
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid reciter entry: %s', e)
                continue
        data.reciters_ts = time.time()

    def _init_tafasir(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.tafasir_ts):
            return
        url = _API_BASE + 'tafasir?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for t in resp.get('tafasir', []):
            try:
                data.tafasir[int(t['id'])] = {
                    'name': t['name'],
                    'url': t['url'],
                }
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid tafsir entry: %s', e)
                continue
        data.tafasir_ts = time.time()

    def _init_radios(self, locale: str, data: _LocaleData) -> None:
        if self._is_cache_valid(data.radios_ts):
            return
        url = _API_BASE + 'radios?language=' + locale
        resp = self._fetch(url)
        if resp is None:
            return
        for radio in resp.get('radios', []):
            try:
                data.radios[int(radio['id'])] = {
                    'name': radio['name'],
                    'url': radio['url'],
                }
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid radio entry: %s', e)
                continue
        data.radios_ts = time.time()

    def lookup(self, locale: str, uris: Iterable[Uri]) -> dict[Uri, list[Track]]:
        """Look up URIs, expanding directory URIs to their child entries."""
        result = {}
        for uri in uris:
            if not uri.startswith('mp3quran:'):
                continue
            result.update(self._lookup_uri(locale, uri))
        return result

    def _lookup_uri(self, locale: str, uri: str) -> dict[Uri, list[Track]]:
        """Resolve a single URI to a dict of URI → tracks."""
        parts = uri.split(':')
        if len(parts) < 3:
            return {uri: []}

        try:
            variant = parts[2]
            data = self._get_locale_data(locale)

            if variant == 'reciter' and len(parts) == 6:
                return self._lookup_track(locale, data, uri)
            elif variant == 'reciter' and len(parts) == 4:
                return {uri: self._lookup_reciter(locale, data, int(parts[3]))}
            elif variant == 'moshaf' and len(parts) == 5:
                return {uri: self._lookup_moshaf(locale, data, int(parts[3]), int(parts[4]))}
            elif variant == 'radio' and len(parts) == 4:
                return self._lookup_radio(locale, data, uri)
            elif variant == 'tafsir_audio' and len(parts) == 5:
                return self._lookup_tafsir_audio(locale, data, uri)
        except (ValueError, IndexError):
            pass
        return {uri: []}

    def _lookup_track(self, locale: str, data: _LocaleData, uri: str) -> dict[Uri, list[Track]]:
        """Look up a single reciter surah track."""
        parts = uri.split(':')
        reciter_id = int(parts[3])
        moshaf_id = int(parts[4])
        sura_no = int(parts[5])
        self._init_reciters(locale, data)
        self._init_suras(locale, data)
        if reciter_id not in data.reciters:
            return {uri: []}
        reciter = data.reciters[reciter_id]
        for moshaf in reciter['moshaf']:
            if moshaf['id'] == moshaf_id and sura_no in moshaf['surah_list']:
                sura_name = data.suras_name.get(sura_no, 'Surah %d' % sura_no)
                return {uri: [Track(
                    uri=Uri(uri), name=sura_name,
                    artists=frozenset([Artist(
                        uri=Uri('mp3quran:%s:reciter:%d' % (locale, reciter_id)),
                        name=reciter['name'],
                    )]),
                    album=Album(
                        uri=Uri('mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf_id)),
                        name=moshaf['name'],
                    ),
                    track_no=sura_no,
                )]}
        return {uri: []}

    def _lookup_reciter(self, locale: str, data: _LocaleData, reciter_id: int) -> list[Track]:
        """Expand a reciter URI to all tracks across all moshafs."""
        self._init_reciters(locale, data)
        self._init_suras(locale, data)
        if reciter_id not in data.reciters:
            return []
        reciter = data.reciters[reciter_id]
        artist = Artist(
            uri=Uri('mp3quran:%s:reciter:%d' % (locale, reciter_id)),
            name=reciter['name'],
        )
        tracks = []
        for moshaf in reciter['moshaf']:
            moshaf_uri = Uri('mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf['id']))
            album = Album(uri=moshaf_uri, name=moshaf['name'])
            for sura_no in moshaf['surah_list']:
                tracks.append(Track(
                    uri=Uri('mp3quran:%s:reciter:%d:%d:%d' % (locale, reciter_id, moshaf['id'], sura_no)),
                    name=data.suras_name.get(sura_no, 'Surah %d' % sura_no),
                    artists=frozenset([artist]),
                    album=album,
                    track_no=sura_no,
                ))
        return tracks

    def _lookup_moshaf(self, locale: str, data: _LocaleData, reciter_id: int, moshaf_id: int) -> list[Track]:
        """Expand a moshaf URI to all its tracks."""
        self._init_reciters(locale, data)
        self._init_suras(locale, data)
        if reciter_id not in data.reciters:
            return []
        reciter = data.reciters[reciter_id]
        for moshaf in reciter['moshaf']:
            if moshaf['id'] == moshaf_id:
                moshaf_uri = Uri('mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf_id))
                artist = Artist(
                    uri=Uri('mp3quran:%s:reciter:%d' % (locale, reciter_id)),
                    name=reciter['name'],
                )
                album = Album(uri=moshaf_uri, name=moshaf['name'])
                return [Track(
                    uri=Uri('mp3quran:%s:reciter:%d:%d:%d' % (locale, reciter_id, moshaf_id, sura_no)),
                    name=data.suras_name.get(sura_no, 'Surah %d' % sura_no),
                    artists=frozenset([artist]),
                    album=album,
                    track_no=sura_no,
                ) for sura_no in moshaf['surah_list']]
        return []

    def _lookup_radio(self, locale: str, data: _LocaleData, uri: str) -> dict[Uri, list[Track]]:
        """Look up a radio track."""
        radio_id = int(uri.split(':')[3])
        self._init_radios(locale, data)
        if radio_id in data.radios:
            return {uri: [Track(uri=Uri(uri), name=data.radios[radio_id]['name'])]}
        return {uri: []}

    def _lookup_tafsir_audio(self, locale: str, data: _LocaleData, uri: str) -> dict[Uri, list[Track]]:
        """Look up a tafsir audio track."""
        parts = uri.split(':')
        tafsir_id = int(parts[3])
        audio_id = int(parts[4])
        self._init_tafasir(locale, data)
        self._init_tafsir_audio(locale, data, tafsir_id)
        audio_info = data.tafsir_audio.get(tafsir_id, {}).get(audio_id)
        if audio_info:
            tafsir_name = data.tafasir.get(tafsir_id, {}).get('name', 'Tafsir')
            return {uri: [Track(uri=Uri(uri), name=audio_info['name'], album=Album(name=tafsir_name))]}
        return {uri: []}

    def translate_uri(self, uri: str) -> Optional[str]:
        """Translate a mopidy URI to a streaming URL."""
        parsed = uri.split(':')[1:]
        if not parsed:
            logger.debug('Could not translate uri: %s', uri)
            return None

        try:
            locale = parsed[0]
            variant = parsed[1]
            if variant == 'reciter' and len(parsed) == 5:
                reciter_id = int(parsed[2])
                moshaf_id = int(parsed[3])
                sura_no = int(parsed[4])
            elif variant == 'radio' and len(parsed) == 3:
                radio_id = int(parsed[2])
            elif variant == 'tafsir_audio' and len(parsed) == 4:
                tafsir_id = int(parsed[2])
                audio_id = int(parsed[3])
            else:
                logger.debug('Invalid uri format: %s', uri)
                return None
        except (ValueError, IndexError) as e:
            logger.debug('Invalid uri format %s: %s', uri, e)
            return None

        data = self._get_locale_data(locale)

        if variant == 'reciter':
            self._init_reciters(locale, data)
            if reciter_id not in data.reciters:
                logger.debug('Reciter ID %d not found', reciter_id)
                return None
            for moshaf in data.reciters[reciter_id]['moshaf']:
                if moshaf['id'] == moshaf_id and sura_no in moshaf['surah_list']:
                    return moshaf['server'].rstrip('/') + '/%03d' % sura_no + '.mp3'
            logger.debug('Moshaf %d or surah %d not found for reciter %d', moshaf_id, sura_no, reciter_id)
            return None
        elif variant == 'radio':
            self._init_radios(locale, data)
            if radio_id in data.radios:
                return data.radios[radio_id]['url']
            logger.debug('Radio ID %d not found', radio_id)
            return None
        elif variant == 'tafsir_audio':
            url = self.translate_tafsir_uri(tafsir_id, audio_id, locale=locale)
            if url:
                return url
            logger.debug('Tafsir audio %d/%d not found', tafsir_id, audio_id)
            return None

        logger.debug('Could not translate uri: %s', uri)
        return None

    def get_languages(self) -> List[Ref]:
        results = []
        for lang in self.languages:
            results.append(Ref.directory(
                uri='mp3quran:%s:language' % lang['locale'],
                name=lang['name'],
            ))
        return results

    def get_language_content(self, locale: str) -> List[Ref]:
        """Get the content category directories for a language."""
        resolved = self.resolve_language(locale)
        results = []
        results.append(Ref.directory(uri='mp3quran:%s:reciters' % resolved, name='Reciters'))
        results.append(Ref.directory(uri='mp3quran:%s:riwayat' % resolved, name='Riwayat'))
        results.append(Ref.directory(uri='mp3quran:%s:moshaf' % resolved, name='Moshaf'))
        results.append(Ref.directory(uri='mp3quran:%s:suwar' % resolved, name='Suwar'))
        results.append(Ref.directory(uri='mp3quran:%s:radios' % resolved, name='Radios'))
        results.append(Ref.directory(uri='mp3quran:%s:tafasir' % resolved, name='Tafasir'))
        return results

    def get_radios(self, locale: str) -> List[Ref]:
        data = self._get_locale_data(locale)
        self._init_radios(locale, data)
        results = []
        for radio_id, radio in data.radios.items():
            results.append(Ref.track(uri='mp3quran:%s:radio:%d' % (locale, radio_id), name=radio['name']))
        return results

    def get_reciters(self, locale: str) -> List[Ref]:
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        results = []
        for reciter_id, reciter in data.reciters.items():
            results.append(Ref.directory(uri='mp3quran:%s:reciter:%d' % (locale, reciter_id), name=reciter['name']))
        return results

    def reciter_moshaf(self, locale: str, reciter_id: int) -> List[Ref]:
        """Return moshaf (recitation versions) for a reciter."""
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        results = []
        reciter_id = int(reciter_id)
        if reciter_id not in data.reciters:
            logger.warning('Mp3Quran: Reciter ID %d not found', reciter_id)
            return results
        reciter = data.reciters[reciter_id]
        for moshaf in reciter['moshaf']:
            results.append(
                Ref.directory(
                    uri='mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf['id']),
                    name=moshaf['name'],
                )
            )
        return results

    def moshaf_suras(self, locale: str, reciter_id: int, moshaf_id: int) -> List[Ref]:
        """Return surahs for a specific moshaf of a reciter."""
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        self._init_suras(locale, data)
        results = []
        reciter_id = int(reciter_id)
        moshaf_id = int(moshaf_id)
        if reciter_id not in data.reciters:
            logger.warning('Mp3Quran: Reciter ID %d not found', reciter_id)
            return results
        reciter = data.reciters[reciter_id]
        for moshaf in reciter['moshaf']:
            if moshaf['id'] == moshaf_id:
                for sura_no in moshaf['surah_list']:
                    sura_name = data.suras_name.get(sura_no, 'Surah %d' % sura_no)
                    results.append(
                        Ref.track(
                            uri='mp3quran:%s:reciter:%d:%d:%d' % (locale, reciter_id, moshaf_id, sura_no),
                            name=sura_name,
                        )
                    )
                return results
        logger.warning('Mp3Quran: Moshaf ID %d not found for reciter %d', moshaf_id, reciter_id)
        return results

    def get_riwayat(self, locale: str) -> List[Ref]:
        data = self._get_locale_data(locale)
        self._init_riwayat(locale, data)
        self._init_reciters(locale, data)
        results = []
        for riwaya_id, name in data.riwayat.items():
            reciters_with_riwaya = [
                (rid, r) for rid, r in data.reciters.items()
                if any(m['rewaya_id'] == riwaya_id for m in r['moshaf'])
            ]
            if reciters_with_riwaya:
                results.append(Ref.directory(
                    uri='mp3quran:%s:riwaya:%d' % (locale, riwaya_id), name=name,
                ))
        return results

    def riwaya_moshafs(self, locale: str, riwaya_id: int) -> List[Ref]:
        """Return moshafs for a specific riwaya, grouped by reciter."""
        data = self._get_locale_data(locale)
        self._init_riwayat(locale, data)
        self._init_reciters(locale, data)
        results = []
        riwaya_id = int(riwaya_id)
        for reciter_id, reciter in data.reciters.items():
            for moshaf in reciter['moshaf']:
                if moshaf['rewaya_id'] == riwaya_id:
                    results.append(
                        Ref.directory(
                            uri='mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf['id']),
                            name='%s - %s' % (reciter['name'], moshaf['name']),
                        )
                    )
        return results

    def get_moshaf(self, locale: str) -> List[Ref]:
        """Return all moshaf types from the moshaf catalog API."""
        data = self._get_locale_data(locale)
        self._init_moshaf(locale, data)
        results = []
        for moshaf_id, moshaf in data.moshaf.items():
            results.append(Ref.directory(
                uri='mp3quran:%s:moshaf_type:%d' % (locale, moshaf_id), name=moshaf['name'],
            ))
        return results

    def moshaf_reciters(self, locale: str, moshaf_type: int) -> List[Ref]:
        """Return moshafs matching a specific moshaf type, across all reciters."""
        data = self._get_locale_data(locale)
        self._init_moshaf(locale, data)
        self._init_reciters(locale, data)
        results = []
        moshaf_type = int(moshaf_type)
        for reciter_id, reciter in data.reciters.items():
            for moshaf in reciter['moshaf']:
                if moshaf['moshaf_type'] == moshaf_type:
                    results.append(Ref.directory(
                        uri='mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf['id']),
                        name='%s - %s' % (reciter['name'], moshaf['name']),
                    ))
        return results

    def get_suwar(self, locale: str) -> List[Ref]:
        """Return all surahs as browseable directories."""
        data = self._get_locale_data(locale)
        self._init_suras(locale, data)
        results = []
        for sura_no, sura_name in sorted(data.suras_name.items()):
            results.append(Ref.directory(
                uri='mp3quran:%s:sura:%d' % (locale, sura_no), name=sura_name,
            ))
        return results

    def sura_moshafs(self, locale: str, sura_no: int) -> List[Ref]:
        """Return moshafs that contain a specific surah."""
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        results = []
        sura_no = int(sura_no)
        for reciter_id, reciter in data.reciters.items():
            for moshaf in reciter['moshaf']:
                if sura_no in moshaf['surah_list']:
                    results.append(Ref.directory(
                        uri='mp3quran:%s:moshaf:%d:%d' % (locale, reciter_id, moshaf['id']),
                        name='%s - %s' % (reciter['name'], moshaf['name']),
                    ))
        return results

    def get_tafasir(self, locale: str) -> List[Ref]:
        data = self._get_locale_data(locale)
        self._init_tafasir(locale, data)
        results = []
        for tafsir_id, tafsir in data.tafasir.items():
            results.append(Ref.directory(
                uri='mp3quran:%s:tafsir:%d' % (locale, tafsir_id), name=tafsir['name'],
            ))
        return results

    def _init_tafsir_audio(self, locale: str, data: _LocaleData, tafsir_id: int) -> None:
        """Fetch and cache audio entries for a specific tafsir."""
        if tafsir_id in data.tafsir_audio and self._is_cache_valid(data.tafsir_audio_ts):
            return
        url = _API_BASE + 'tafsir?tafsir=%d&language=%s' % (tafsir_id, locale)
        resp = self._fetch(url)
        if resp is None:
            return
        audio_map = {}
        for audio in resp.get('tafasir', {}).get('soar', []):
            try:
                audio_map[int(audio['id'])] = {
                    'name': audio['name'],
                    'url': audio['url'],
                }
            except (KeyError, ValueError) as e:
                logger.warning('Mp3Quran: Skipping invalid tafsir audio entry: %s', e)
                continue
        data.tafsir_audio[tafsir_id] = audio_map
        data.tafsir_audio_ts = time.time()

    def tafsir_audio(self, locale: str, tafsir_id: int) -> List[Ref]:
        data = self._get_locale_data(locale)
        self._init_tafasir(locale, data)
        results = []
        tafsir_id = int(tafsir_id)
        if tafsir_id not in data.tafasir:
            logger.warning('Mp3Quran: Tafsir ID %d not found', tafsir_id)
            return results
        self._init_tafsir_audio(locale, data, tafsir_id)
        audio_map = data.tafsir_audio.get(tafsir_id, {})
        for audio_id, audio_info in audio_map.items():
            results.append(Ref.track(
                uri='mp3quran:%s:tafsir_audio:%d:%d' % (locale, tafsir_id, audio_id),
                name=audio_info['name'],
            ))
        return results

    def translate_tafsir_uri(self, tafsir_id: int, audio_id: int, locale: str = None) -> Optional[str]:
        tafsir_id = int(tafsir_id)
        audio_id = int(audio_id)
        lang = locale or _DEFAULT_LOCALE
        data = self._get_locale_data(lang)
        self._init_tafasir(lang, data)
        if tafsir_id not in data.tafasir:
            return None
        self._init_tafsir_audio(lang, data, tafsir_id)
        audio_info = data.tafsir_audio.get(tafsir_id, {}).get(audio_id)
        if audio_info:
            return audio_info['url']
        return None

    _FUZZY_THRESHOLD = 60.0

    def search(self, locale: str, query: dict, uris: list = None, exact: bool = False) -> SearchResult:
        """Search reciters, moshafs, suwar, and radios.

        Returns a SearchResult with artists, albums, and tracks,
        sorted by fuzzy match score (best first).
        """
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        self._init_suras(locale, data)
        self._init_radios(locale, data)

        scored = {'artists': {}, 'albums': {}, 'tracks': {}}

        for field, values in query.items():
            if isinstance(values, str):
                values = [values]
            for value in values:
                if field in ('any', 'artist', 'albumartist'):
                    self._merge(scored['artists'], self._match_reciters(data, locale, value, exact))
                if field in ('any', 'album'):
                    self._merge(scored['albums'], self._match_moshafs(data, locale, value, exact))
                if field in ('any', 'track_name'):
                    self._merge(scored['tracks'], self._match_suwar(data, locale, value, exact))
                if field == 'any':
                    self._merge(scored['tracks'], self._match_radios(data, locale, value, exact))

        if uris is not None:
            scopes = {u for u in uris if u.startswith('mp3quran:')}
            for category in scored:
                scored[category] = {
                    uri: v for uri, v in scored[category].items()
                    if any(uri.startswith(s) or uri.startswith(s.rstrip('s') + ':') for s in scopes)
                }

        return SearchResult(
            uri=Uri('mp3quran:search'),
            artists=tuple(v[0] for v in sorted(scored['artists'].values(), key=lambda x: x[1], reverse=True)),
            albums=tuple(v[0] for v in sorted(scored['albums'].values(), key=lambda x: x[1], reverse=True)),
            tracks=tuple(v[0] for v in sorted(scored['tracks'].values(), key=lambda x: x[1], reverse=True)),
        )

    @staticmethod
    def _merge(target: dict, refs: list) -> None:
        """Merge (ref, score) list into target dict, keeping best score per URI."""
        for ref, score in refs:
            if ref.uri not in target or score > target[ref.uri][1]:
                target[ref.uri] = (ref, score)

    def _match_reciters(self, data: _LocaleData, locale: str, query: str, exact: bool) -> list:
        choices = {reciter['name']: rid for rid, reciter in data.reciters.items()}
        return [(Artist(uri=Uri('mp3quran:%s:reciter:%d' % (locale, rid)), name=name), score)
                for name, score in self._fuzzy_match(query, list(choices.keys()), exact)
                for rid in [choices[name]]]

    def _match_moshafs(self, data: _LocaleData, locale: str, query: str, exact: bool) -> list:
        choices = {(rid, m['id']): (m['name'], rid) for rid, r in data.reciters.items() for m in r['moshaf']}
        name_to_keys = {}
        for (rid, mid), (mname, _) in choices.items():
            name_to_keys.setdefault(mname, []).append((rid, mid))
        return [(Album(
            uri=Uri('mp3quran:%s:moshaf:%d:%d' % (locale, rid, mid)),
            name=name,
            artists=frozenset([Artist(
                uri=Uri('mp3quran:%s:reciter:%d' % (locale, rid)),
                name=data.reciters[rid]['name'],
            )]),
        ), score)
            for name, score in self._fuzzy_match(query, list(name_to_keys.keys()), exact)
            for rid, mid in name_to_keys[name]]

    def _match_suwar(self, data: _LocaleData, locale: str, query: str, exact: bool) -> list:
        matched = {name: score for name, score in self._fuzzy_match(query, list(data.suras_name.values()), exact)}
        results = []
        for sura_no, sura_name in data.suras_name.items():
            if sura_name not in matched:
                continue
            for rid, reciter in data.reciters.items():
                for moshaf in reciter['moshaf']:
                    if sura_no in moshaf['surah_list']:
                        results.append((Track(
                            uri=Uri('mp3quran:%s:reciter:%d:%d:%d' % (locale, rid, moshaf['id'], sura_no)),
                            name=sura_name,
                            artists=frozenset([Artist(
                                uri=Uri('mp3quran:%s:reciter:%d' % (locale, rid)),
                                name=reciter['name'],
                            )]),
                            album=Album(
                                uri=Uri('mp3quran:%s:moshaf:%d:%d' % (locale, rid, moshaf['id'])),
                                name=moshaf['name'],
                            ),
                            track_no=sura_no,
                        ), matched[sura_name]))
        return results

    def _match_radios(self, data: _LocaleData, locale: str, query: str, exact: bool) -> list:
        choices = {radio['name']: rid for rid, radio in data.radios.items()}
        return [(Track(uri=Uri('mp3quran:%s:radio:%d' % (locale, rid)), name=name), score)
                for name, score in self._fuzzy_match(query, list(choices.keys()), exact)
                for rid in [choices[name]]]

    def _fuzzy_match(self, query: str, choices: List[str], exact: bool) -> List[tuple]:
        if not choices:
            return []
        query_lower = query.lower()
        choices_lower = {c.lower(): c for c in choices}
        if exact:
            return [(orig, 100.0) for lower, orig in choices_lower.items() if lower == query_lower]
        results = process.extract(
            query_lower, list(choices_lower.keys()), scorer=fuzz.partial_ratio,
            score_cutoff=self._FUZZY_THRESHOLD, limit=None,
        )
        return [(choices_lower[r[0]], r[1]) for r in results]

    def get_distinct(self, locale: str, field: str, query: dict = None) -> set:
        """Return distinct values for a field, optionally filtered by query."""
        data = self._get_locale_data(locale)
        self._init_reciters(locale, data)
        self._init_suras(locale, data)

        if field == 'artist' or field == 'albumartist':
            return self._distinct_reciters(data, query)
        elif field == 'album':
            return self._distinct_moshafs(data, query)
        elif field == 'track_name':
            return self._distinct_suwar(data, query)

        return set()

    def _distinct_reciters(self, data: _LocaleData, query: dict = None) -> set:
        """Return distinct reciter names, optionally filtered."""
        results = set()
        album_filter = None
        if query and 'album' in query:
            album_lower = [v.lower() for v in (query['album'] if isinstance(query['album'], list) else [query['album']])]
            album_filter = album_lower

        for reciter_id, reciter in data.reciters.items():
            if album_filter:
                if not any(af in m['name'].lower() for m in reciter['moshaf'] for af in album_filter):
                    continue
            results.add(reciter['name'])
        return results

    def _distinct_moshafs(self, data: _LocaleData, query: dict = None) -> set:
        """Return distinct moshaf names, optionally filtered."""
        results = set()
        artist_filter = None
        if query and 'artist' in query:
            artist_lower = [v.lower() for v in (query['artist'] if isinstance(query['artist'], list) else [query['artist']])]
            artist_filter = artist_lower

        for reciter_id, reciter in data.reciters.items():
            if artist_filter:
                if not any(af in reciter['name'].lower() for af in artist_filter):
                    continue
            for moshaf in reciter['moshaf']:
                results.add(moshaf['name'])
        return results

    def _distinct_suwar(self, data: _LocaleData, query: dict = None) -> set:
        """Return distinct surah names, optionally filtered."""
        reciter_ids = None
        if query and 'artist' in query:
            artist_lower = [v.lower() for v in (query['artist'] if isinstance(query['artist'], list) else [query['artist']])]
            reciter_ids = set()
            for reciter_id, reciter in data.reciters.items():
                if any(af in reciter['name'].lower() for af in artist_lower):
                    reciter_ids.add(reciter_id)

        moshaf_names = None
        if query and 'album' in query:
            album_lower = [v.lower() for v in (query['album'] if isinstance(query['album'], list) else [query['album']])]
            moshaf_names = set()
            for reciter_id, reciter in data.reciters.items():
                for moshaf in reciter['moshaf']:
                    if any(af in moshaf['name'].lower() for af in album_lower):
                        moshaf_names.add((reciter_id, moshaf['id']))

        sura_ids = None
        if reciter_ids is not None or moshaf_names is not None:
            sura_ids = set()
            for reciter_id, reciter in data.reciters.items():
                if reciter_ids is not None and reciter_id not in reciter_ids:
                    continue
                for moshaf in reciter['moshaf']:
                    if moshaf_names is not None and (reciter_id, moshaf['id']) not in moshaf_names:
                        continue
                    sura_ids.update(moshaf['surah_list'])

        results = set()
        for sid, name in data.suras_name.items():
            if sura_ids is not None and sid not in sura_ids:
                continue
            results.add(name)
        return results

    def refresh(self) -> None:
        """Force re-fetch all data from the API."""
        self.languages = []
        self._locales.clear()
        self._languages_timestamp = 0.0
        self._init_languages()
