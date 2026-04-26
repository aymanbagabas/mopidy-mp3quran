import logging
from typing import List, Optional

import requests as _requests
import pykka
import mopidy_mp3quran

from mopidy_mp3quran import client
from mopidy import backend, httpclient
from mopidy.models import Ref, Track, Album, Artist, SearchResult

logger = logging.getLogger(__name__)


def get_requests_session(proxy_config, user_agent: str) -> _requests.Session:
    """Create a requests session with proxy and user agent settings."""
    proxy = httpclient.format_proxy(proxy_config)
    full_user_agent = httpclient.format_user_agent(user_agent)

    session = _requests.Session()
    session.proxies.update({'http': proxy, 'https': proxy})
    session.headers.update({'user-agent': full_user_agent})

    return session


class Mp3QuranBackend(pykka.ThreadingActor, backend.Backend):
    """Backend for streaming Quran from mp3quran.net."""

    uri_schemes = ['mp3quran']

    def __init__(self, config, audio) -> None:
        super().__init__()

        self.audio = audio
        self.config = config
        self.session = get_requests_session(
            proxy_config=self.config.get("proxy", {}),
            user_agent='%s/%s' % (
                mopidy_mp3quran.Extension.dist_name,
                mopidy_mp3quran.__version__)
        )

        mp3quran_config = config.get('mp3quran', {})
        self.mp3quran = client.Mp3Quran(
            session=self.session,
            cache_ttl=mp3quran_config.get('cache_ttl', client._DEFAULT_CACHE_TTL),
            timeout=mp3quran_config.get('timeout', client._DEFAULT_TIMEOUT),
        )

        self.library = Mp3QuranLibraryProvider(backend=self)
        self.playback = Mp3QuranPlaybackProvider(audio=audio, backend=self)


class Mp3QuranLibraryProvider(backend.LibraryProvider):
    """Library provider for browsing Quran reciters and radios."""

    root_directory = Ref.directory(uri='mp3quran:root', name='Mp3Quran')

    def browse(self, uri: str) -> List[Ref]:
        """Browse the library at the given URI."""
        results = []
        parsed = uri.split(':')
        mp3quran = self.backend.mp3quran

        # mp3quran:root
        if len(parsed) == 2 and parsed[1] == 'root':
            locale = mp3quran.resolve_language(
                self.backend.config.get('mp3quran', {}).get('language', client._DEFAULT_LOCALE)
            )
            results.append(Ref.directory(uri='mp3quran:languages', name='Languages'))
            results.extend(mp3quran.get_language_content(locale))
            return results

        # mp3quran:languages
        if len(parsed) == 2 and parsed[1] == 'languages':
            results = mp3quran.get_languages()
            return results

        # mp3quran:<locale>:<variant>[:<id>...]
        if len(parsed) < 3:
            logger.debug('Unknown uri: %s at library.browse', uri)
            return results

        locale = parsed[1]
        if not locale:
            logger.debug('Empty locale in uri: %s', uri)
            return results
        variant = parsed[2]
        identifier = parsed[3] if len(parsed) >= 4 else None
        extra = parsed[4] if len(parsed) >= 5 else None

        if variant == 'language':
            results = mp3quran.get_language_content(locale)
        elif variant == 'reciters':
            results = mp3quran.get_reciters(locale)
        elif variant == 'reciter' and identifier:
            results = mp3quran.reciter_moshaf(locale, int(identifier))
        elif variant == 'moshaf' and identifier and extra:
            results = mp3quran.moshaf_suras(locale, int(identifier), int(extra))
        elif variant == 'riwayat':
            results = mp3quran.get_riwayat(locale)
        elif variant == 'riwaya' and identifier:
            results = mp3quran.riwaya_reciters(locale, int(identifier))
        elif variant == 'radios':
            results = mp3quran.get_radios(locale)
        elif variant == 'tafasir':
            results = mp3quran.get_tafasir(locale)
        elif variant == 'tafsir' and identifier:
            results = mp3quran.tafsir_audio(locale, int(identifier))
        else:
            logger.debug('Unknown uri: %s at library.browse', uri)

        return results

    def refresh(self, uri: Optional[str] = None) -> None:
        self.backend.mp3quran.refresh()

    def lookup(self, uri: str) -> List[Track]:
        """Look up a track by URI."""
        tracks = []
        parsed_uri = uri.split(':')[1:]
        logger.debug('Looking up uri: %s', uri)

        if len(parsed_uri) < 3:
            logger.debug('Invalid uri format: %s', uri)
            return tracks

        try:
            locale = parsed_uri[0]
            variant = parsed_uri[1]
            if variant == 'reciter':
                if len(parsed_uri) != 5:
                    logger.debug('Invalid reciter uri format: %s', uri)
                    return tracks
                reciter_id = int(parsed_uri[2])
                moshaf_id = int(parsed_uri[3])
                sura_no = int(parsed_uri[4])
            elif variant == 'radio':
                radio_id = int(parsed_uri[2])
            elif variant == 'tafsir_audio':
                if len(parsed_uri) != 4:
                    logger.debug('Invalid tafsir_audio uri format: %s', uri)
                    return tracks
                tafsir_id = int(parsed_uri[2])
                audio_id = int(parsed_uri[3])
            else:
                logger.debug('Unknown variant in uri: %s', uri)
                return tracks
        except (ValueError, IndexError) as e:
            logger.debug('Invalid uri %s: %s', uri, e)
            return tracks

        mp3quran = self.backend.mp3quran
        data = mp3quran._get_locale_data(locale)

        if variant == 'reciter':
            mp3quran._init_reciters(locale, data)
            mp3quran._init_suras(locale, data)
            if reciter_id not in data.reciters:
                logger.debug('Reciter ID %d not found', reciter_id)
                return tracks
            reciter = data.reciters[reciter_id]
            moshaf_found = None
            for moshaf in reciter['moshaf']:
                if moshaf['id'] == moshaf_id:
                    moshaf_found = moshaf
                    break
            if moshaf_found is None:
                logger.debug('Moshaf ID %d not found for reciter %d', moshaf_id, reciter_id)
                return tracks
            sura_name = data.suras_name.get(sura_no, 'Surah %d' % sura_no)
            artists = [Artist(name=reciter['name'])]
            album = Album(name=moshaf_found['name'])
            tracks.append(Track(
                uri=uri, name=sura_name,
                artists=artists, album=album, track_no=sura_no,
            ))
        elif variant == 'radio':
            mp3quran._init_radios(locale, data)
            if radio_id in data.radios:
                radio = data.radios[radio_id]
                tracks.append(Track(uri=uri, name=radio['name']))
            else:
                logger.debug('Radio ID %d not found', radio_id)
        elif variant == 'tafsir_audio':
            mp3quran._init_tafasir(locale, data)
            url = mp3quran.translate_tafsir_uri(tafsir_id, audio_id, locale=locale)
            if url:
                tafsir_name = data.tafasir.get(tafsir_id, {}).get('name', 'Tafsir')
                tracks.append(Track(uri=uri, name=tafsir_name, album=Album(name=tafsir_name)))
            else:
                logger.debug('Tafsir audio %d/%d not found', tafsir_id, audio_id)

        return tracks

    def search(self, query=None, uris=None, exact=False) -> SearchResult:
        if query is None:
            return SearchResult()

        if isinstance(query, dict):
            query_str = ' '.join(
                v for vals in query.values() for v in (vals if isinstance(vals, list) else [vals])
            )
        else:
            query_str = str(query)

        if not query_str.strip():
            return SearchResult()

        mp3quran = self.backend.mp3quran
        locale = mp3quran.resolve_language(
            self.backend.config.get('mp3quran', {}).get('language', client._DEFAULT_LOCALE)
        )

        results = mp3quran.search(locale, query_str)
        tracks = []
        artists = []
        for ref in results:
            if ref.type == Ref.TRACK:
                lookup_tracks = self.lookup(ref.uri)
                tracks.extend(lookup_tracks)
            elif ref.type == Ref.DIRECTORY and ref.uri.startswith('mp3quran:'):
                try:
                    parts = ref.uri.split(':')
                    if len(parts) >= 4 and parts[2] == 'reciter':
                        reciter_id = int(parts[3])
                        data = mp3quran._get_locale_data(locale)
                        mp3quran._init_reciters(locale, data)
                        reciter = data.reciters[reciter_id]
                        artists.append(Artist(name=reciter['name']))
                except (IndexError, ValueError, KeyError):
                    logger.debug('Could not extract artist from ref: %s', ref.uri)

        return SearchResult(tracks=tracks, artists=artists)


class Mp3QuranPlaybackProvider(backend.PlaybackProvider):

    def __init__(self, audio, backend) -> None:
        super().__init__(audio, backend)
        self.config = backend.config
        self.session = backend.session

    def translate_uri(self, uri: str) -> Optional[str]:
        url = self.backend.mp3quran.translate_uri(uri)
        if url:
            logger.info('Mp3Quran: Stream URL: %s', url)
            return url
        else:
            logger.debug('URI could not be translated: %s', uri)
            return None

    def is_live(self, uri: str) -> bool:
        return uri.startswith('mp3quran:') and ':radio:' in uri
