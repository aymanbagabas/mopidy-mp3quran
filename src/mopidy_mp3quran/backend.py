import logging
from collections.abc import Iterable
from typing import List, Optional, Set

import requests as _requests
import pykka
import mopidy_mp3quran

from mopidy_mp3quran import client
from mopidy import backend, httpclient
from mopidy.models import Ref, Track, Album, Artist, SearchResult
from mopidy.types import DistinctField, Query, SearchField, Uri

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
            results = mp3quran.riwaya_moshafs(locale, int(identifier))
        elif variant == 'moshaf' and not identifier:
            results = mp3quran.get_moshaf(locale)
        elif variant == 'moshaf_type' and identifier:
            results = mp3quran.moshaf_reciters(locale, int(identifier))
        elif variant == 'suwar':
            results = mp3quran.get_suwar(locale)
        elif variant == 'sura' and identifier:
            results = mp3quran.sura_moshafs(locale, int(identifier))
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

    def get_distinct(
        self,
        field: DistinctField,
        query: Query[SearchField] = None,
    ) -> Set[str]:
        locale = self.backend.mp3quran.resolve_language(
            self.backend.config.get('mp3quran', {}).get('language', client._DEFAULT_LOCALE)
        )
        return self.backend.mp3quran.get_distinct(locale, field, query)

    def lookup_many(self, uris: Iterable[Uri]) -> dict[Uri, list[Track]]:
        mp3quran = self.backend.mp3quran
        locale = mp3quran.resolve_language(
            self.backend.config.get('mp3quran', {}).get('language', client._DEFAULT_LOCALE)
        )
        return mp3quran.lookup(locale, uris)

    def search(self, query=None, uris=None, exact=False) -> SearchResult:
        if query is None:
            return SearchResult(uri=Uri('mp3quran:search'))

        if not query:
            return SearchResult(uri=Uri('mp3quran:search'))

        if isinstance(query, dict):
            if not any(query.values()):
                return SearchResult(uri=Uri('mp3quran:search'))
        else:
            return SearchResult(uri=Uri('mp3quran:search'))

        mp3quran = self.backend.mp3quran
        locale = mp3quran.resolve_language(
            self.backend.config.get('mp3quran', {}).get('language', client._DEFAULT_LOCALE)
        )

        return mp3quran.search(locale, query, uris=uris, exact=exact)


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
