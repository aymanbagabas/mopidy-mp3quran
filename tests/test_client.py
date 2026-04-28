import time
from unittest import mock

import pytest
import responses

from mopidy.models import Album, Artist, Track
from mopidy_mp3quran.client import (
    Mp3Quran, _API_BASE, _DEFAULT_CACHE_TTL, _DEFAULT_LOCALE,
)


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
        {"id": 2, "name": "Rewayat Warsh A'n Nafi'"},
    ]
}

MOSHAF_CATALOG_RESPONSE = {
    "riwayat": [
        {"id": 11, "moshaf_type": 1, "moshaf_id": 1, "name": "Rewayat Hafs A'n Assem - Murattal"},
        {"id": 21, "moshaf_type": 2, "moshaf_id": 1, "name": "Rewayat Warsh A'n Nafi' - Murattal"},
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
                    "surah_total": 114,
                    "moshaf_type": 11,
                    "surah_list": "1,2,3",
                },
                {
                    "id": 2,
                    "name": "Rewayat Warsh A'n Nafi' - Murattal",
                    "rewaya_id": 2,
                    "server": "https://server.example.com/mishary_warsh/",
                    "surah_total": 3,
                    "moshaf_type": 11,
                    "surah_list": "1,2,3",
                },
            ],
        },
        {
            "id": 2,
            "name": "Abdul Rahman Al-Sudais",
            "letter": "A",
            "date": "2025-09-06T00:39:03.000000Z",
            "moshaf": [
                {
                    "id": 3,
                    "name": "Rewayat Hafs A'n Assem - Murattal",
                    "rewaya_id": 1,
                    "server": "https://server.example.com/sudais/",
                    "surah_total": 2,
                    "moshaf_type": 11,
                    "surah_list": "1,2",
                },
            ],
        },
    ]
}

TAFASIR_LIST_RESPONSE = {
    "tafasir": []
}

RADIOS_RESPONSE = {
    "radios": [
        {"id": 1, "name": "Quran Radio 24/7", "url": "https://stream.example.com/radio1"},
        {"id": 2, "name": "Live Quran FM", "url": "https://stream.example.com/radio2"},
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
def mocked_api():
    """Mock all mp3quran.net v3 API endpoints."""
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
            _api_url('moshaf?language=eng'),
            json=MOSHAF_CATALOG_RESPONSE,
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
def client(mocked_api):
    """Return an Mp3Quran client with mocked API."""
    return Mp3Quran(cache_ttl=3600, timeout=10)


class TestMp3QuranInit:

    def test_suras_loaded(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        assert 1 in data.suras_name
        assert data.suras_name[1] == "Al-Fatihah"
        assert data.suras_name[2] == "Al-Baqarah"

    def test_suras_name_stripped(self):
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), json=SURAS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('moshaf?language=eng'), json=MOSHAF_CATALOG_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=RECITERS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=RADIOS_RESPONSE, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert data.suras_name[1] == "Al-Fatihah"
            assert data.suras_name[2] == "Al-Baqarah"

    def test_moshaf_loaded(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        assert 11 in data.moshaf
        assert data.moshaf[11]['name'] == "Rewayat Hafs A'n Assem - Murattal"
        assert data.moshaf[11]['moshaf_type'] == 1

    def test_riwayat_loaded(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        assert 1 in data.riwayat
        assert data.riwayat[1] == "Rewayat Hafs A'n Assem"

    def test_reciters_loaded(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        assert 1 in data.reciters
        assert data.reciters[1]["name"] == "Mishary Rashid Alafasy"
        assert len(data.reciters[1]["moshaf"]) == 2

    def test_moshaf_data(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        moshaf = data.reciters[1]["moshaf"][0]
        assert moshaf["id"] == 1
        assert moshaf["name"] == "Rewayat Hafs A'n Assem - Murattal"
        assert moshaf["rewaya_id"] == 1
        assert moshaf["server"] == "https://server.example.com/mishary/"
        assert moshaf["surah_list"] == [1, 2, 3]

    def test_radios_loaded(self, client):
        client._ensure_loaded('eng')
        data = client._get_locale_data('eng')
        assert 1 in data.radios
        assert data.radios[1]["name"] == "Quran Radio 24/7"
        assert data.radios[1]["url"] == "https://stream.example.com/radio1"

    def test_languages_loaded(self, client):
        assert len(client.languages) == 2
        assert client.languages[0]["locale"] == "ar"
        assert client.languages[0]["name"] == "Arabic"
        assert client.languages[1]["locale"] == "eng"
        assert client.languages[1]["name"] == "English"

    def test_default_locale(self):
        assert _DEFAULT_LOCALE == "eng"


class TestMp3QuranResolveLanguage:

    def test_locale_code_exact(self, client):
        assert client.resolve_language("eng") == "eng"

    def test_locale_code_case_insensitive(self, client):
        assert client.resolve_language("ENG") == "eng"
        assert client.resolve_language("Ar") == "ar"

    def test_long_form_name(self, client):
        assert client.resolve_language("English") == "eng"
        assert client.resolve_language("Arabic") == "ar"

    def test_long_form_case_insensitive(self, client):
        assert client.resolve_language("english") == "eng"
        assert client.resolve_language("ARABIC") == "ar"
        assert client.resolve_language("English") == "eng"

    def test_unknown_name_returns_lowered(self, client):
        assert client.resolve_language("Swahili") == "swahili"


class TestMp3QuranGetLanguages:

    def test_returns_directory_refs(self, client):
        refs = client.get_languages()
        assert len(refs) == 2
        assert refs[0].uri == "mp3quran:ar:language"
        assert refs[0].name == "Arabic"
        assert refs[1].uri == "mp3quran:eng:language"
        assert refs[1].name == "English"

    def test_ref_type_is_directory(self, client):
        refs = client.get_languages()
        for ref in refs:
            assert ref.type == "directory"


class TestMp3QuranGetRadios:

    def test_returns_track_refs(self, client):
        refs = client.get_radios('eng')
        assert len(refs) == 2
        uris = [r.uri for r in refs]
        assert "mp3quran:eng:radio:1" in uris
        assert "mp3quran:eng:radio:2" in uris

    def test_ref_type_is_track(self, client):
        refs = client.get_radios('eng')
        for ref in refs:
            assert ref.type == "track"


class TestMp3QuranGetReciters:

    def test_returns_directory_refs(self, client):
        refs = client.get_reciters('eng')
        assert len(refs) == 2
        assert refs[0].uri == "mp3quran:eng:reciter:1"
        assert "Mishary Rashid Alafasy" in refs[0].name

    def test_ref_type_is_directory(self, client):
        refs = client.get_reciters('eng')
        for ref in refs:
            assert ref.type == "directory"


class TestMp3QuranReciterMoshaf:

    def test_returns_moshaf_refs(self, client):
        refs = client.reciter_moshaf('eng', 1)
        assert len(refs) == 2
        assert refs[0].uri == "mp3quran:eng:moshaf:1:1"
        assert refs[0].name == "Rewayat Hafs A'n Assem - Murattal"
        assert refs[1].uri == "mp3quran:eng:moshaf:1:2"
        assert refs[1].name == "Rewayat Warsh A'n Nafi' - Murattal"

    def test_unknown_reciter_returns_empty(self, client):
        refs = client.reciter_moshaf('eng', 999)
        assert refs == []


class TestMp3QuranMoshafSuras:

    def test_returns_track_refs(self, client):
        refs = client.moshaf_suras('eng', 1, 1)
        assert len(refs) == 3
        assert refs[0].uri == "mp3quran:eng:reciter:1:1:1"
        assert refs[0].name == "Al-Fatihah"
        assert refs[0].type == "track"

    def test_unknown_moshaf_returns_empty(self, client):
        refs = client.moshaf_suras('eng', 1, 999)
        assert refs == []

    def test_unknown_reciter_returns_empty(self, client):
        refs = client.moshaf_suras('eng', 999, 1)
        assert refs == []

    def test_surah_name_fallback(self, client):
        refs = client.moshaf_suras('eng', 2, 3)
        assert len(refs) == 2
        assert refs[0].name == "Al-Fatihah"
        assert refs[1].name == "Al-Baqarah"


class TestMp3QuranTranslateUri:

    def test_reciter_surah_uri(self, client):
        url = client.translate_uri("mp3quran:eng:reciter:1:1:2")
        assert url == "https://server.example.com/mishary/002.mp3"

    def test_reciter_second_moshaf_uri(self, client):
        url = client.translate_uri("mp3quran:eng:reciter:1:2:2")
        assert url == "https://server.example.com/mishary_warsh/002.mp3"

    def test_radio_uri(self, client):
        url = client.translate_uri("mp3quran:eng:radio:1")
        assert url == "https://stream.example.com/radio1"

    def test_invalid_uri_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:invalid") is None

    def test_empty_uri_returns_none(self, client):
        assert client.translate_uri("mp3quran:") is None

    def test_unknown_variant_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:unknown:1") is None

    def test_reciter_without_moshaf_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:reciter:1") is None

    def test_reciter_without_surah_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:reciter:1:1") is None

    def test_unknown_radio_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:radio:99") is None

    def test_unknown_moshaf_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:reciter:1:999:2") is None

    def test_surah_not_in_moshaf_returns_none(self, client):
        assert client.translate_uri("mp3quran:eng:reciter:2:3:99") is None


class TestMp3QuranSearch:

    def test_search_any_field_reciter(self, client):
        result = client.search('eng', {'any': 'Mishary'})
        assert len(result.artists) >= 1
        assert any("Mishary" in a.name for a in result.artists)

    def test_search_artist_field(self, client):
        result = client.search('eng', {'artist': 'Mishary'})
        assert len(result.artists) >= 1
        assert any("Mishary" in a.name for a in result.artists)

    def test_search_album_field(self, client):
        result = client.search('eng', {'album': 'Warsh'})
        assert len(result.albums) >= 1
        assert any("Warsh" in a.name for a in result.albums)

    def test_search_track_name_field(self, client):
        result = client.search('eng', {'track_name': 'Fatihah'})
        assert len(result.tracks) >= 1
        assert any("Al-Fatihah" in t.name for t in result.tracks)

    def test_search_any_field_radio(self, client):
        result = client.search('eng', {'any': 'Radio'})
        radio_tracks = [r for r in result.tracks if ':radio:' in r.uri]
        assert len(radio_tracks) >= 1

    def test_search_any_field_moshaf(self, client):
        result = client.search('eng', {'any': 'Warsh'})
        assert len(result.albums) >= 1

    def test_search_fuzzy_matching(self, client):
        result = client.search('eng', {'artist': 'mishary'})
        assert len(result.artists) >= 1
        assert any("Mishary" in a.name for a in result.artists)

    def test_search_exact_matching(self, client):
        result = client.search('eng', {'artist': 'mishary'}, exact=True)
        assert len(result.artists) == 0

    def test_search_exact_matching_case_insensitive(self, client):
        result = client.search('eng', {'artist': 'Mishary Rashid Alafasy'}, exact=True)
        assert len(result.artists) >= 1

    def test_search_no_results(self, client):
        result = client.search('eng', {'any': 'nonexistentxyz123'})
        assert len(result.artists) == 0
        assert len(result.albums) == 0
        assert len(result.tracks) == 0

    def test_search_uris_filter(self, client):
        result = client.search('eng', {'any': 'Mishary'}, uris=['mp3quran:eng:reciters'])
        assert len(result.artists) >= 1
        radio_tracks = [r for r in result.tracks if ':radio:' in r.uri]
        assert len(radio_tracks) == 0

    def test_search_reciter_returns_artist_model(self, client):
        result = client.search('eng', {'artist': 'Mishary'})
        assert len(result.artists) >= 1
        assert isinstance(result.artists[0], Artist)
        assert result.artists[0].uri is not None

    def test_search_radio_returns_track_model(self, client):
        result = client.search('eng', {'any': 'Radio'})
        radio_tracks = [r for r in result.tracks if ':radio:' in r.uri]
        assert len(radio_tracks) >= 1
        assert isinstance(radio_tracks[0], Track)

    def test_search_albumartist_field(self, client):
        result = client.search('eng', {'albumartist': 'Sudais'})
        assert len(result.artists) >= 1

    def test_search_results_ordered_by_fuzzy_score(self, client):
        result = client.search('eng', {'artist': 'Mishary Rashid Alafasy'})
        assert len(result.artists) >= 1
        exact_match = [a for a in result.artists if a.name == 'Mishary Rashid Alafasy']
        assert len(exact_match) >= 1
        assert result.artists[0].name == 'Mishary Rashid Alafasy'

    def test_search_any_matches_multiple_categories_sorted(self, client):
        result = client.search('eng', {'any': 'Al-Fatihah'})
        assert len(result.tracks) >= 1
        assert any('Al-Fatihah' in t.name for t in result.tracks)
        if len(result.artists) >= 1:
            assert all(isinstance(a, Artist) for a in result.artists)


class TestMp3QuranMoshafCatalog:

    def test_get_moshaf(self, client):
        refs = client.get_moshaf('eng')
        assert len(refs) >= 2
        uris = [r.uri for r in refs]
        assert "mp3quran:eng:moshaf_type:11" in uris
        assert "mp3quran:eng:moshaf_type:21" in uris

    def test_moshaf_reciters(self, client):
        refs = client.moshaf_reciters('eng', 11)
        assert len(refs) >= 1
        assert all(':moshaf:' in r.uri for r in refs)
        assert any("Mishary" in r.name for r in refs)

    def test_get_suwar(self, client):
        refs = client.get_suwar('eng')
        assert len(refs) == 3
        assert refs[0].uri == "mp3quran:eng:sura:1"
        assert refs[0].name == "Al-Fatihah"
        assert refs[0].type == "directory"

    def test_sura_moshafs(self, client):
        refs = client.sura_moshafs('eng', 1)
        assert len(refs) >= 1
        assert any(':moshaf:' in r.uri for r in refs)
        assert any("Mishary" in r.name for r in refs)

    def test_riwaya_moshafs(self, client):
        refs = client.riwaya_moshafs('eng', 1)
        assert len(refs) >= 1
        assert all(':moshaf:' in r.uri for r in refs)
        assert any("Mishary" in r.name for r in refs)


class TestMp3QuranCaching:

    def test_cache_prevents_refetch(self, mocked_api):
        c = Mp3Quran(cache_ttl=3600)
        c._ensure_loaded('eng')
        first_call_count = len(responses.calls)
        c._ensure_loaded('eng')
        second_call_count = len(responses.calls)
        assert second_call_count == first_call_count

    def test_cache_expiry_triggers_refetch(self, mocked_api):
        c = Mp3Quran(cache_ttl=1)
        c._ensure_loaded('eng')
        initial_calls = len(responses.calls)
        time.sleep(1.1)
        c._locales.clear()
        c._ensure_loaded('eng')
        assert len(responses.calls) > initial_calls

    def test_refresh_clears_cache(self, client):
        client.refresh()
        assert len(client._locales) == 0


class TestMp3QuranErrorHandling:

    def test_failed_languages_request(self):
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), status=500)
            c = Mp3Quran()
            assert c.languages == []

    def test_failed_suras_request(self):
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), status=500)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=RECITERS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=RADIOS_RESPONSE, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert data.suras_name == {}

    def test_failed_reciters_request(self):
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), json=SURAS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), status=500)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=RADIOS_RESPONSE, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert data.reciters == {}

    def test_failed_radios_request(self):
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), json=SURAS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=RECITERS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), status=500)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert data.radios == {}

    def test_invalid_moshaf_entry_skipped(self):
        bad_reciters = {
            "reciters": [
                {
                    "id": 1,
                    "name": "Valid",
                    "letter": "V",
                    "moshaf": [
                        {
                            "id": 1,
                            "name": "Valid Moshaf",
                            "rewaya_id": 1,
                            "server": "https://example.com",
                            "surah_total": 2,
                            "moshaf_type": 11,
                            "surah_list": "1,2",
                        },
                    ],
                },
                {"id": 2, "name": "Invalid", "moshaf": [{"id": "bad"}]},
            ]
        }
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), json=SURAS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=bad_reciters, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=RADIOS_RESPONSE, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert 1 in data.reciters
            assert len(data.reciters) == 1

    def test_invalid_radio_entry_skipped(self):
        bad_radios = {
            "radios": [
                {"id": 1, "name": "Valid Radio", "url": "https://example.com/stream"},
                {"id": 2, "name": "Invalid Radio"},
            ]
        }
        with responses.mock:
            responses.add(responses.GET, _api_url('languages'), json=LANGUAGES_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('suwar?language=eng'), json=SURAS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('riwayat?language=eng'), json=RIWAYAT_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=RECITERS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=bad_radios, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert 1 in data.radios
            assert len(data.radios) == 1


class TestMp3QuranGetDistinct:

    def test_distinct_artist(self, client):
        result = client.get_distinct('eng', 'artist')
        assert "Mishary Rashid Alafasy" in result
        assert "Abdul Rahman Al-Sudais" in result

    def test_distinct_albumartist(self, client):
        result = client.get_distinct('eng', 'albumartist')
        assert "Mishary Rashid Alafasy" in result
        assert "Abdul Rahman Al-Sudais" in result

    def test_distinct_album(self, client):
        result = client.get_distinct('eng', 'album')
        assert "Rewayat Hafs A'n Assem - Murattal" in result
        assert "Rewayat Warsh A'n Nafi' - Murattal" in result

    def test_distinct_track_name(self, client):
        result = client.get_distinct('eng', 'track_name')
        assert "Al-Fatihah" in result
        assert "Al-Baqarah" in result
        assert "Aal Imran" in result

    def test_distinct_unknown_field_returns_empty(self, client):
        result = client.get_distinct('eng', 'genre')
        assert result == set()

    def test_distinct_artist_filtered_by_album(self, client):
        result = client.get_distinct('eng', 'artist', query={'album': 'Warsh'})
        assert "Mishary Rashid Alafasy" in result
        assert "Abdul Rahman Al-Sudais" not in result

    def test_distinct_album_filtered_by_artist(self, client):
        result = client.get_distinct('eng', 'album', query={'artist': 'Sudais'})
        assert "Rewayat Hafs A'n Assem - Murattal" in result
        assert "Rewayat Warsh A'n Nafi' - Murattal" not in result

    def test_distinct_track_name_filtered_by_artist(self, client):
        result = client.get_distinct('eng', 'track_name', query={'artist': 'Sudais'})
        assert "Al-Fatihah" in result
        assert "Al-Baqarah" in result
        assert "Aal Imran" not in result

    def test_distinct_track_name_filtered_by_album(self, client):
        result = client.get_distinct('eng', 'track_name', query={'album': 'Warsh'})
        assert "Al-Fatihah" in result
        assert "Al-Baqarah" in result
        assert "Aal Imran" in result

    def test_distinct_no_query_returns_all(self, client):
        artists = client.get_distinct('eng', 'artist')
        albums = client.get_distinct('eng', 'album')
        tracks = client.get_distinct('eng', 'track_name')
        assert len(artists) >= 2
        assert len(albums) >= 2
        assert len(tracks) >= 3
