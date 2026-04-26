"""Stub mopidy modules for testing on Windows where Mopidy can't be installed."""
import sys
from unittest import mock

# Create mock mopidy package structure
_mopidy = mock.MagicMock()
_mopidy.config.String = lambda **kw: 'string'
_mopidy.config.Integer = lambda **kw: 'integer'
_mopidy.config.read = lambda path: '[mp3quran]\nenabled = true\nlanguage = english\ncache_ttl = 3600\ntimeout = 10\nfavorites_path =\n'
_mopidy.config.ConfigSchema = dict

class _BaseExtension:
    def get_config_schema(self):
        return {'enabled': 'boolean'}

_mopidy.ext.Extension = _BaseExtension

class _Backend:
    pass
class _LibraryProvider:
    def __init__(self, backend=None):
        self.backend = backend
class _PlaybackProvider:
    def __init__(self, audio=None, backend=None):
        self.audio = audio
        self.backend = backend
class _SearchProvider:
    def __init__(self, backend=None):
        self.backend = backend

_mopidy.backend.Backend = _Backend
_mopidy.backend.LibraryProvider = _LibraryProvider
_mopidy.backend.PlaybackProvider = _PlaybackProvider
_mopidy.backend.SearchProvider = _SearchProvider
_mopidy.httpclient.format_proxy = mock.MagicMock(return_value='')
_mopidy.httpclient.format_user_agent = mock.MagicMock(return_value='')

# Mock pykka
class _ThreadingActor:
    def __init__(self):
        pass

class _Pykka:
    ThreadingActor = _ThreadingActor

sys.modules['pykka'] = _Pykka()

sys.modules['mopidy'] = _mopidy
sys.modules['mopidy.config'] = _mopidy.config
sys.modules['mopidy.ext'] = _mopidy.ext
sys.modules['mopidy.backend'] = _mopidy.backend
sys.modules['mopidy.httpclient'] = _mopidy.httpclient
sys.modules['mopidy.models'] = _mopidy.models

# Ref types
_mopidy.models.Ref.TRACK = 'track'
_mopidy.models.Ref.DIRECTORY = 'directory'

# Make Ref, Track, Album, Artist, SearchResult callable and serializable
class _Ref:
    TRACK = 'track'
    DIRECTORY = 'directory'
    def __init__(self, uri='', name='', type='track'):
        self.uri = uri
        self.name = name
        self.type = type

class _Track:
    def __init__(self, uri='', name='', artists=None, album=None, track_no=0):
        self.uri = uri
        self.name = name
        self.artists = artists or []
        self.album = album
        self.track_no = track_no

class _Album:
    def __init__(self, name=''):
        self.name = name

class _Artist:
    def __init__(self, name=''):
        self.name = name

class _SearchResult:
    def __init__(self, tracks=None, artists=None):
        self.tracks = tracks or []
        self.artists = artists or []

_mopidy.models.Ref = _Ref
_mopidy.models.Track = _Track
_mopidy.models.Album = _Album
_mopidy.models.Artist = _Artist
_mopidy.models.SearchResult = _SearchResult

# Make Ref callable as factory
_mopidy.models.Ref.track = staticmethod(lambda uri='', name='': _Ref(uri=uri, name=name, type='track'))
_mopidy.models.Ref.directory = staticmethod(lambda uri='', name='': _Ref(uri=uri, name=name, type='directory'))
