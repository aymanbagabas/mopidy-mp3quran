import logging
import re
from typing import List, Optional, Tuple

import requests as _requests
import pykka
import mopidy_mp3quran

from mopidy_mp3quran import client
from mopidy import backend, httpclient
from mopidy.models import Ref, Track, Album, Artist, SearchResult

logger = logging.getLogger(__name__)


def parse_uri(uri: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse mp3quran URI into (variant, identifier, sub_identifier)."""
    results = re.findall(
        r'^mp3quran:([a-z]+)(?::(\d+|[a-z]{2}))?(?::(\d+|[a-z]{2}))?$', uri
    )
    if results:
        return results[0]
    return None, None, None


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
            proxy_config=self.config,
            user_agent='%s/%s' % (
                mopidy_mp3quran.Extension.dist_name,
                mopidy_mp3quran.__version__)
        )

        mp3quran_config = config.get('mp3quran', {})
        self.mp3quran = client.Mp3Quran(
            session=self.session,
            language=mp3quran_config.get('language', 'English'),
            cache_ttl=mp3quran_config.get('cache_ttl', client._DEFAULT_CACHE_TTL),
            timeout=mp3quran_config.get('timeout', client._DEFAULT_TIMEOUT),
        )

        self.library = Mp3QuranLibraryProvider(backend=self)
        self.playback = Mp3QuranPlaybackProvider(audio=audio, backend=self)
        self.search = Mp3QuranSearchProvider(backend=self)


class Mp3QuranLibraryProvider(backend.LibraryProvider):
    """Library provider for browsing Quran reciters and radios."""

    root_directory = Ref.directory(uri='mp3quran:root', name='Mp3Quran')

    def browse(self, uri: str) -> List[Ref]:
        """Browse the library at the given URI."""
        results = []
        parsed = uri.split(':')
        variant = parsed[1] if len(parsed) >= 2 else None
        identifier = parsed[2] if len(parsed) == 3 else None

        if variant == 'root':
            results.append(Ref.directory(uri='mp3quran:reciters', name='Reciters'))
            results.append(Ref.directory(uri='mp3quran:radios', name='Radios'))
        elif variant == 'radios':
            results = self.backend.mp3quran.get_radios()
        elif variant == 'reciters':
            results = self.backend.mp3quran.get_reciters()
        elif variant == 'reciter' and identifier:
            results = self.backend.mp3quran.reciter_suras(identifier)
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

        if not parsed_uri or len(parsed_uri) < 2:
            logger.debug('Invalid uri format: %s', uri)
            return tracks

        try:
            variant = parsed_uri[0]
            identifier = int(parsed_uri[1])
        except (ValueError, IndexError) as e:
            logger.debug('Invalid uri %s: %s', uri, e)
            return tracks

        sura = None
        if len(parsed_uri) == 3:
            try:
                sura_no = int(parsed_uri[2])
                sura = self.backend.mp3quran.suras_name.get(sura_no)
            except ValueError:
                logger.debug('Invalid sura number in uri: %s', uri)
                return tracks

        if variant == 'reciter' and identifier in self.backend.mp3quran.reciters and sura:
            reciter = self.backend.mp3quran.reciters[identifier]
            artists = [Artist(name=reciter['name'])]
            album = Album(name=reciter['rewaya'])
            track_no = int(parsed_uri[2])
            tracks.append(Track(
                uri=uri, name=sura,
                artists=artists, album=album, track_no=track_no,
            ))
        elif variant == 'radio' and 0 <= identifier < len(self.backend.mp3quran.radios):
            radio = self.backend.mp3quran.radios[identifier]
            tracks.append(Track(uri=uri, name=radio['name']))
        else:
            logger.debug('Unknown uri: %s', uri)

        return tracks

class Mp3QuranPlaybackProvider(backend.PlaybackProvider):

    def __init__(self, audio, backend) -> None:
        super().__init__(audio, backend)
        self.config = backend.config
        self.session = backend.session

    def translate_uri(self, uri: str) -> Optional[str]:
        url = self.backend.mp3quran.translate_uri(uri)
        if url:
            logger.info('Stream URL: %s', url)
            return url
        else:
            logger.debug('URI could not be translated: %s', uri)
            return None


class Mp3QuranSearchProvider(backend.SearchProvider):

    def __init__(self, backend) -> None:
        super().__init__(backend)

    def search(self, query=None, uris=None, exact=False) -> SearchResult:
        if query is None:
            return SearchResult()

        # Extract query string from Mopidy query dict
        if isinstance(query, dict):
            query_str = ' '.join(
                v for vals in query.values() for v in (vals if isinstance(vals, list) else [vals])
            )
        else:
            query_str = str(query)

        if not query_str.strip():
            return SearchResult()

        results = self.backend.mp3quran.search(query_str)
        tracks = []
        for ref in results:
            if ref.type == Ref.TRACK:
                lookup_tracks = self.backend.library.lookup(ref.uri)
                tracks.extend(lookup_tracks)

        return SearchResult(tracks=tracks)
