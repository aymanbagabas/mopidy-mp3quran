import time
from unittest import mock

import pytest
import responses

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
            responses.add(responses.GET, _api_url('reciters?language=eng'), json=RECITERS_RESPONSE, status=200)
            responses.add(responses.GET, _api_url('radios?language=eng'), json=RADIOS_RESPONSE, status=200)
            c = Mp3Quran()
            data = c._get_locale_data('eng')
            c._ensure_loaded('eng')
            assert data.suras_name[1] == "Al-Fatihah"
            assert data.suras_name[2] == "Al-Baqarah"

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

    def test_search_reciter_by_name(self, client):
        refs = client.search('eng', "Mishary")
        assert len(refs) >= 1
        assert "Mishary" in refs[0].name

    def test_search_reciter_by_moshaf_name(self, client):
        refs = client.search('eng', "Warsh")
        assert len(refs) >= 1

    def test_search_radio(self, client):
        refs = client.search('eng', "24/7")
        assert len(refs) == 1
        assert refs[0].name == "Quran Radio 24/7"

    def test_search_case_insensitive(self, client):
        refs = client.search('eng', "mishary")
        assert len(refs) >= 1

    def test_search_no_results(self, client):
        refs = client.search('eng', "nonexistent")
        assert refs == []

    def test_search_radio_returns_track_ref(self, client):
        refs = client.search('eng', "Radio")
        radio_refs = [r for r in refs if r.uri.startswith("mp3quran:eng:radio:")]
        assert len(radio_refs) >= 1
        assert radio_refs[0].type == "track"

    def test_search_reciter_returns_directory_ref(self, client):
        refs = client.search('eng', "Mishary")
        assert refs[0].type == "directory"


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


class TestMp3QuranFuzzySearch:

    def test_fuzzy_match_typo(self, client):
        refs = client.search('eng', 'Meshary')  # typo: Meshary vs Mishary
        assert len(refs) >= 1
        assert any('Mishary' in r.name for r in refs)

    def test_fuzzy_match_partial(self, client):
        refs = client.search('eng', 'Rashid')
        assert len(refs) >= 1
        assert any('Mishary' in r.name for r in refs)

    def test_fuzzy_match_moshaf_name(self, client):
        refs = client.search('eng', 'Warsh')
        assert len(refs) >= 1
        assert any('Mishary' in r.name for r in refs)

    def test_fuzzy_match_radio(self, client):
        refs = client.search('eng', 'Quran FM')
        assert len(refs) >= 1
        assert any('Live Quran FM' == r.name for r in refs)

    def test_fuzzy_no_match(self, client):
        refs = client.search('eng', 'xyznonexistent123')
        assert refs == []


class TestMp3QuranFavorites:

    def test_add_and_get_favorite(self, client, tmp_path):
        fav_path = str(tmp_path / "favorites.json")
        client.favorites_path = fav_path
        client.add_favorite('mp3quran:eng:reciter:1', 'Mishary Rashid Alafasy')
        refs = client.get_favorites()
        assert len(refs) == 1
        assert refs[0].uri == 'mp3quran:eng:reciter:1'
        assert refs[0].name == 'Mishary Rashid Alafasy'

    def test_add_duplicate_ignored(self, client, tmp_path):
        fav_path = str(tmp_path / "favorites.json")
        client.favorites_path = fav_path
        client.add_favorite('mp3quran:eng:radio:1', 'Quran Radio')
        client.add_favorite('mp3quran:eng:radio:1', 'Quran Radio')
        refs = client.get_favorites()
        assert len(refs) == 1

    def test_remove_favorite(self, client, tmp_path):
        fav_path = str(tmp_path / "favorites.json")
        client.favorites_path = fav_path
        client.add_favorite('mp3quran:eng:reciter:1', 'Mishary')
        client.add_favorite('mp3quran:eng:radio:1', 'Radio')
        client.remove_favorite('mp3quran:eng:reciter:1')
        refs = client.get_favorites()
        assert len(refs) == 1
        assert refs[0].uri == 'mp3quran:eng:radio:1'

    def test_get_favorites_empty(self, client, tmp_path):
        fav_path = str(tmp_path / "favorites.json")
        client.favorites_path = fav_path
        refs = client.get_favorites()
        assert refs == []

    def test_track_type_favorite(self, client, tmp_path):
        fav_path = str(tmp_path / "favorites.json")
        client.favorites_path = fav_path
        client.add_favorite('mp3quran:eng:radio:1', 'Quran Radio', ref_type='track')
        refs = client.get_favorites()
        assert len(refs) == 1
        assert refs[0].type == 'track'
