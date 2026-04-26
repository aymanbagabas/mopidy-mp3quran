from unittest import mock

import pytest
import responses

from mopidy.models import Ref, SearchResult
from mopidy_mp3quran.backend import (
    Mp3QuranBackend,
    Mp3QuranLibraryProvider,
    Mp3QuranPlaybackProvider,
    get_requests_session,
)
from mopidy_mp3quran.client import Mp3Quran, _API_BASE


SURAS_RESPONSE = {
    "suwar": [
        {"id": 1, "name": "Al-Fatihah "},
        {"id": 2, "name": "Al-Baqarah "},
        {"id": 3, "name": "Aal Imran"},
    ]
}

RIWAYAT_RESPONSE = {
    "riwayat": [
        {"id": 1, "name": "Rewayat Hafs A'n Assem"},
    ]
}

RECITERS_RESPONSE = {
    "reciters": [
        {
            "id": 1,
            "name": "Mishary Rashid Alafasy",
            "letter": "M",
            "date": "2025-09-06T00:39:03.000000Z",
            "moshaf": [
                {
                    "id": 1,
                    "name": "Rewayat Hafs A'n Assem - Murattal",
                    "rewaya_id": 1,
                    "server": "https://server.example.com/mishary/",
                    "surah_total": 3,
                    "moshaf_type": 11,
                    "surah_list": "1,2,3",
                },
            ],
        },
    ]
}

TAFASIR_LIST_RESPONSE = {
    "tafasir": [
        {
            "id": 1,
            "url": "https://www.mp3quran.net/api/v3/tafsir?tafsir=1&language=eng",
            "name": "Summary of Tafsir Al-Tabari",
        },
    ]
}

TAFASIR_DETAIL_RESPONSE = {
    "tafasir": {
        "name": "Summary of Tafsir Al-Tabari",
        "soar": [
            {"id": 9, "tafsir_id": 1, "name": "Surah Al-Fatihah", "url": "https://server17.mp3quran.net/tafseer/tabri/001.mp3", "sura_id": 1},
            {"id": 10, "tafsir_id": 1, "name": "Surah Al-Baqarah Ayat 1-25", "url": "https://server17.mp3quran.net/tafseer/tabri/002-1-25.mp3", "sura_id": 2},
        ]
    }
}

RADIOS_RESPONSE = {
    "radios": [
        {"id": 1, "name": "Quran Radio 24/7", "url": "https://stream.example.com/radio1"},
    ]
}

LANGUAGES_RESPONSE = {
    "language": [
        {
            "id": "1",
            "language": "Arabic",
            "native": "العربية",
            "locale": "ar",
            "surah": "https://mp3quran.net/api/v3/suwar?language=ar",
            "rewayah": "https://mp3quran.net/api/v3/riwayat?language=ar",
            "reciters": "https://mp3quran.net/api/v3/reciters?language=ar",
            "radios": "https://mp3quran.net/api/v3/radios?language=ar",
            "tafasir": "https://mp3quran.net/api/v3/tafasir?language=ar",
        },
        {
            "id": "2",
            "language": "English",
            "native": "English",
            "locale": "eng",
            "surah": "https://mp3quran.net/api/v3/suwar?language=eng",
            "rewayah": "https://mp3quran.net/api/v3/riwayat?language=eng",
            "reciters": "https://mp3quran.net/api/v3/reciters?language=eng",
            "radios": "https://mp3quran.net/api/v3/radios?language=eng",
            "tafasir": "https://mp3quran.net/api/v3/tafasir?language=eng",
        },
    ]
}


def _api_url(path):
    return _API_BASE + path


@pytest.fixture
def mock_config():
    return {
        "proxy": {"hostname": "", "port": "", "username": "", "password": ""},
        "mp3quran": {
            "enabled": True,
            "language": "eng",
            "cache_ttl": 3600,
            "timeout": 10,
        },
    }


@pytest.fixture
def mock_audio():
    return mock.Mock()


@pytest.fixture
def mocked_api():
    with responses.mock:
        responses.add(
            responses.GET,
            _api_url('languages'),
            json=LANGUAGES_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            _api_url('suwar?language=eng'),
            json=SURAS_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            _api_url('riwayat?language=eng'),
            json=RIWAYAT_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            _api_url('reciters?language=eng'),
            json=RECITERS_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            _api_url('radios?language=eng'),
            json=RADIOS_RESPONSE,
            status=200,
        )
        responses.add(
            responses.GET,
            _api_url('tafasir?language=eng'),
            json=TAFASIR_LIST_RESPONSE,
            status=200,
        )
        yield


@pytest.fixture
def backend(mocked_api, mock_config, mock_audio):
    return Mp3QuranBackend(config=mock_config, audio=mock_audio)


@pytest.fixture
def library(backend):
    return backend.library


@pytest.fixture
def playback(backend):
    return backend.playback


class TestMp3QuranBackend:

    def test_uri_schemes(self, backend):
        assert backend.uri_schemes == ["mp3quran"]

    def test_has_library_provider(self, backend):
        assert isinstance(backend.library, Mp3QuranLibraryProvider)

    def test_has_playback_provider(self, backend):
        assert isinstance(backend.playback, Mp3QuranPlaybackProvider)

    def test_proxy_config_key(self, mock_config, mock_audio):
        with mock.patch("mopidy_mp3quran.backend.get_requests_session") as mock_session:
            mock_session.return_value = mock.Mock()
            with mock.patch("mopidy_mp3quran.backend.client.Mp3Quran"):
                Mp3QuranBackend(config=mock_config, audio=mock_audio)
            call_kwargs = mock_session.call_args
            assert call_kwargs[1]["proxy_config"] == mock_config["proxy"]


class TestGetRequestsSession:

    def test_passes_proxy_config(self):
        with mock.patch("mopidy.httpclient.format_proxy", return_value="http://proxy:8080"):
            with mock.patch("mopidy.httpclient.format_user_agent", return_value="TestAgent/1.0"):
                session = get_requests_session(
                    proxy_config={"hostname": "proxy", "port": "8080"},
                    user_agent="TestAgent/1.0",
                )
                assert "http" in session.proxies
                assert session.proxies["http"] == "http://proxy:8080"

    def test_sets_user_agent(self):
        with mock.patch("mopidy.httpclient.format_proxy", return_value=""):
            with mock.patch("mopidy.httpclient.format_user_agent", return_value="Mp3Quran/0.2"):
                session = get_requests_session(
                    proxy_config={},
                    user_agent="Mp3Quran/0.2",
                )
                assert session.headers["user-agent"] == "Mp3Quran/0.2"


class TestMp3QuranLibraryProvider:

    def test_root_directory(self, library):
        assert library.root_directory.uri == "mp3quran:root"
        assert library.root_directory.name == "Mp3Quran"

    def test_browse_root(self, library):
        results = library.browse("mp3quran:root")
        assert len(results) == 5
        assert results[0].uri == "mp3quran:languages"
        assert results[1].uri == "mp3quran:eng:reciters"
        assert results[2].uri == "mp3quran:eng:riwayat"
        assert results[3].uri == "mp3quran:eng:radios"
        assert results[4].uri == "mp3quran:eng:tafasir"

    def test_browse_languages(self, library):
        results = library.browse("mp3quran:languages")
        assert len(results) == 2
        assert results[0].uri == "mp3quran:ar:language"
        assert results[0].name == "Arabic"
        assert results[1].uri == "mp3quran:eng:language"
        assert results[1].name == "English"

    def test_browse_language_shows_categories(self, library):
        results = library.browse("mp3quran:ar:language")
        assert len(results) == 4
        assert results[0].uri == "mp3quran:ar:reciters"
        assert results[1].uri == "mp3quran:ar:riwayat"
        assert results[2].uri == "mp3quran:ar:radios"
        assert results[3].uri == "mp3quran:ar:tafasir"

    def test_browse_reciters(self, library):
        results = library.browse("mp3quran:eng:reciters")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:reciter:1"
        assert results[0].type == Ref.DIRECTORY

    def test_browse_reciter_shows_moshaf(self, library):
        results = library.browse("mp3quran:eng:reciter:1")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:moshaf:1:1"
        assert results[0].name == "Rewayat Hafs A'n Assem - Murattal"
        assert results[0].type == Ref.DIRECTORY

    def test_browse_moshaf_shows_suras(self, library):
        results = library.browse("mp3quran:eng:moshaf:1:1")
        assert len(results) == 3
        assert results[0].uri == "mp3quran:eng:reciter:1:1:1"
        assert results[0].name == "Al-Fatihah"
        assert results[0].type == Ref.TRACK

    def test_browse_riwayat(self, library):
        results = library.browse("mp3quran:eng:riwayat")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:riwaya:1"
        assert results[0].name == "Rewayat Hafs A'n Assem"
        assert results[0].type == Ref.DIRECTORY

    def test_browse_riwaya_reciters(self, library):
        results = library.browse("mp3quran:eng:riwaya:1")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:moshaf:1:1"
        assert results[0].type == Ref.DIRECTORY

    def test_browse_radios(self, library):
        results = library.browse("mp3quran:eng:radios")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:radio:1"
        assert results[0].type == Ref.TRACK

    def test_browse_tafasir(self, library):
        results = library.browse("mp3quran:eng:tafasir")
        assert len(results) == 1
        assert results[0].uri == "mp3quran:eng:tafsir:1"
        assert results[0].name == "Summary of Tafsir Al-Tabari"
        assert results[0].type == Ref.DIRECTORY

    def test_browse_tafsir_audio(self, library):
        with responses.mock:
            responses.add(
                responses.GET,
                _api_url('tafsir?tafsir=1&language=eng'),
                json=TAFASIR_DETAIL_RESPONSE,
                status=200,
            )
            results = library.browse("mp3quran:eng:tafsir:1")
            assert len(results) == 2
            assert results[0].uri == "mp3quran:eng:tafsir_audio:1:9"
            assert results[0].type == Ref.TRACK

    def test_lookup_tafsir_audio(self, library):
        with responses.mock:
            responses.add(
                responses.GET,
                _api_url('tafsir?tafsir=1&language=eng'),
                json=TAFASIR_DETAIL_RESPONSE,
                status=200,
            )
            tracks = library.lookup("mp3quran:eng:tafsir_audio:1:9")
            assert len(tracks) == 1
            assert tracks[0].name == "Summary of Tafsir Al-Tabari"

    def test_browse_unknown_uri(self, library):
        results = library.browse("mp3quran:unknown")
        assert results == []

    def test_lookup_reciter_surah(self, library):
        tracks = library.lookup("mp3quran:eng:reciter:1:1:2")
        assert len(tracks) == 1
        track = tracks[0]
        assert track.uri == "mp3quran:eng:reciter:1:1:2"
        assert track.name == "Al-Baqarah"
        assert any(a.name == "Mishary Rashid Alafasy" for a in track.artists)
        assert track.album.name == "Rewayat Hafs A'n Assem - Murattal"
        assert track.track_no == 2

    def test_lookup_radio(self, library):
        tracks = library.lookup("mp3quran:eng:radio:1")
        assert len(tracks) == 1
        assert tracks[0].uri == "mp3quran:eng:radio:1"
        assert tracks[0].name == "Quran Radio 24/7"

    def test_lookup_invalid_uri(self, library):
        tracks = library.lookup("mp3quran:")
        assert tracks == []

    def test_lookup_unknown_variant(self, library):
        tracks = library.lookup("mp3quran:eng:unknown:1")
        assert tracks == []

    def test_lookup_nonexistent_reciter(self, library):
        tracks = library.lookup("mp3quran:eng:reciter:999:1:1")
        assert tracks == []

    def test_lookup_nonexistent_radio(self, library):
        tracks = library.lookup("mp3quran:eng:radio:99")
        assert tracks == []

    def test_lookup_invalid_identifier(self, library):
        tracks = library.lookup("mp3quran:eng:reciter:abc")
        assert tracks == []

    def test_refresh(self, library):
        with mock.patch.object(library.backend.mp3quran, "refresh") as mock_refresh:
            library.refresh()
            mock_refresh.assert_called_once()


class TestMp3QuranLibrarySearch:

    def test_search_reciter(self, library):
        result = library.search(query="Mishary")
        assert isinstance(result, SearchResult)
        assert len(result.artists) == 1
        assert result.artists[0].name == "Mishary Rashid Alafasy"

    def test_search_radio(self, library):
        result = library.search(query="Radio")
        assert isinstance(result, SearchResult)
        assert len(result.tracks) >= 1

    def test_search_returns_both_tracks_and_artists(self, library):
        result = library.search(query="Hafs")
        assert len(result.artists) >= 1

    def test_search_none_query(self, library):
        result = library.search(query=None)
        assert isinstance(result, SearchResult)
        assert len(result.tracks) == 0

    def test_search_empty_query(self, library):
        result = library.search(query="")
        assert isinstance(result, SearchResult)
        assert len(result.tracks) == 0

    def test_search_dict_query(self, library):
        result = library.search(query={"any": "Mishary"})
        assert len(result.artists) >= 1

    def test_search_dict_query_multiple_values(self, library):
        result = library.search(query={"any": ["Mishary", "Alafasy"]})
        assert isinstance(result, SearchResult)

    def test_search_no_results(self, library):
        result = library.search(query="nonexistentxyz123")
        assert isinstance(result, SearchResult)
        assert len(result.tracks) == 0
        assert len(result.artists) == 0


class TestMp3QuranPlaybackProvider:

    def test_translate_uri_reciter(self, playback):
        url = playback.translate_uri("mp3quran:eng:reciter:1:1:2")
        assert url == "https://server.example.com/mishary/002.mp3"

    def test_translate_uri_radio(self, playback):
        url = playback.translate_uri("mp3quran:eng:radio:1")
        assert url == "https://stream.example.com/radio1"

    def test_translate_uri_tafsir_audio(self, playback):
        with responses.mock:
            responses.add(
                responses.GET,
                _api_url('tafsir?tafsir=1&language=eng'),
                json=TAFASIR_DETAIL_RESPONSE,
                status=200,
            )
            url = playback.translate_uri("mp3quran:eng:tafsir_audio:1:9")
            assert url == "https://server17.mp3quran.net/tafseer/tabri/001.mp3"

    def test_translate_uri_invalid(self, playback):
        url = playback.translate_uri("mp3quran:invalid")
        assert url is None

    def test_is_live_radio(self, playback):
        assert playback.is_live("mp3quran:eng:radio:1") is True

    def test_is_live_reciter(self, playback):
        assert playback.is_live("mp3quran:eng:reciter:1:1:2") is False
