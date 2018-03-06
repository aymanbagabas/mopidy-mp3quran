import pykka
import requests
import mopidy_mp3quran
import re
import logging

from mopidy_mp3quran import client
from mopidy import backend, httpclient, stream, config
from mopidy.models import Ref, Track, Album, Artist

logger = logging.getLogger(__name__)

def parse_uri(uri):
    results = re.findall('^mp3quran:([a-z]+)(?::(\d+|[a-z]{2}))?(?::(\d+|[a-z]{2}))?$', uri)
    if results:
        return results[0]
    return None, None, None

def get_requests_session(proxy_config, user_agent):
    proxy = httpclient.format_proxy(proxy_config)
    full_user_agent = httpclient.format_user_agent(user_agent)

    session = requests.Session()
    session.proxies.update({'http': proxy, 'https': proxy})
    session.headers.update({'user-agent': full_user_agent})

    return session

class Mp3QuranBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['mp3quran']

    def __init__(self, config, audio):
        super(Mp3QuranBackend, self).__init__()

        self.audio = audio
        self.config = config
        self.session = get_requests_session(
            proxy_config=self.config,
            user_agent='%s/%s' % (
                mopidy_mp3quran.Extension.dist_name,
                mopidy_mp3quran.__version__)
        )

        self.mp3quran = client.Mp3Quran(session=self.session)

        self.library = Mp3QuranLibraryProvider(backend=self)
        self.playback = Mp3QuranPlaybackProvider(audio=audio, backend=self)


class Mp3QuranLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri='mp3quran:root', name='Mp3Quran')

    def browse(self, uri):
        results = []
        parsed = uri.split(':')
        variant, identifier = (parsed[1], parsed[2] if len(parsed) == 3 else None)
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
            logger.debug('Unknown uri: %s at library.browse' % uri)

        return results

    def refresh(self, uri=None):
        self.backend.mp3quran.refresh()

    def lookup(self, uri):
            tracks = []
            parsed_uri = uri.split(':')[1:]
            logger.debug(uri)
            if len(parsed_uri) == 3:
                variant, identifier, sura_no = parsed_uri
                sura = self.backend.mp3quran.suras_name[int(sura_no)]
            else:
                variant, identifier = parsed_uri
            identifier = int(identifier)
            if variant == 'reciter' and sura:
                reciter = self.backend.mp3quran.reciters[identifier]
                artists = [Artist(name=reciter['name'])]
                album = Album(name=reciter['rewaya'])
                track_no = int(sura_no)
                tracks.append(Track(uri=uri, name=sura, artists=artists, album=album, track_no=track_no))
            elif variant == 'radio':
                radio = self.backend.mp3quran.radios[identifier]
                tracks.append(Track(uri=uri, name=radio['name']))
            else:
                logger.debug('Unknown uri: %s' % uri)
            return tracks

class Mp3QuranPlaybackProvider(backend.PlaybackProvider):

    def __init__(self, audio, backend):
        super(Mp3QuranPlaybackProvider, self).__init__(audio, backend)
        self.config = backend.config
        self.session = backend.session

    def translate_uri(self, uri):
        url = self.backend.mp3quran.translate_uri(uri)
        if url:
            logger.info('Stream URL: %s' % url)
            return url
        else:
            logger.debug('URI could not be translated: %s' % uri)
            return None
