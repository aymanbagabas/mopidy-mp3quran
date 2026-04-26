import time
import logging
from typing import Dict, List, Optional, Any

import requests
from mopidy.models import Ref

logger = logging.getLogger(__name__)

_API_BASE = 'https://www.mp3quran.net/api/'
_RADIO_API = _API_BASE + 'radio/radio_en.json'
_DEFAULT_CACHE_TTL = 3600  # 1 hour
_DEFAULT_TIMEOUT = 10  # seconds

class Mp3Quran:
    """Client for the mp3quran.net API with caching."""

    def __init__(
        self,
        session: requests.Session = None,
        language: str = 'English',
        cache_ttl: int = _DEFAULT_CACHE_TTL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self.session = session or requests.Session()
        self.language = '_' + language[0].lower() + language[1:]
        self.url = _API_BASE + self.language + '.json'
        self.suras_name_url = _API_BASE + self.language + '_sura.json'
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        self.reciters: Dict[int, Dict[str, Any]] = {}
        self.radios: List[Dict[str, str]] = []
        self.suras_name: Dict[int, str] = {}

        self._reciters_timestamp: float = 0.0
        self._radios_timestamp: float = 0.0
        self._suras_timestamp: float = 0.0

        self._init_suras()
        self.init_reciters()
        self.init_radios()

    def _is_cache_valid(self, timestamp: float) -> bool:
        if timestamp == 0.0:
            return False
        return (time.time() - timestamp) < self.cache_ttl

    def _init_suras(self) -> None:
        if self._is_cache_valid(self._suras_timestamp):
            return
        try:
            response = self.session.get(self.suras_name_url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            for sura in data.get('Suras_Name', []):
                self.suras_name[int(sura['id'])] = sura['name']
            self._suras_timestamp = time.time()
        except requests.RequestException as e:
            logger.error('Failed to fetch surah names: %s', e)
        except (KeyError, ValueError) as e:
            logger.error('Invalid surah names data: %s', e)

    def init_reciters(self) -> None:
        if self._is_cache_valid(self._reciters_timestamp):
            return
        try:
            response = self.session.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            for reciter in data.get('reciters', []):
                try:
                    suras = [int(n) for n in reciter['suras'].split(',')]
                    self.reciters[int(reciter['id'])] = {
                        'name': reciter['name'],
                        'url': reciter['Server'],
                        'suras': suras,
                        'rewaya': reciter['rewaya'],
                    }
                except (KeyError, ValueError) as e:
                    logger.warning('Skipping invalid reciter entry: %s', e)
                    continue
            self._reciters_timestamp = time.time()
        except requests.RequestException as e:
            logger.error('Failed to fetch reciters: %s', e)
        except (KeyError, ValueError) as e:
            logger.error('Invalid reciters data: %s', e)

    def init_radios(self) -> None:
        if self._is_cache_valid(self._radios_timestamp):
            return
        try:
            response = self.session.get(_RADIO_API, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            for radio in data.get('Radios', []):
                try:
                    self.radios.append({
                        'name': radio['Name'],
                        'url': radio['URL'],
                    })
                except (KeyError, ValueError) as e:
                    logger.warning('Skipping invalid radio entry: %s', e)
                    continue
            self._radios_timestamp = time.time()
        except requests.RequestException as e:
            logger.error('Failed to fetch radios: %s', e)
        except (KeyError, ValueError) as e:
            logger.error('Invalid radios data: %s', e)

    def translate_uri(self, uri: str) -> Optional[str]:
        """Translate a mopidy URI to a streaming URL."""
        parsed = uri.split(':')[1:]
        if not parsed:
            logger.debug('Could not translate uri: %s', uri)
            return None

        try:
            if len(parsed) == 3:
                variant, identifier, sura = parsed
                sura = int(sura)
            else:
                variant, identifier = parsed
                sura = None
            identifier = int(identifier)
        except (ValueError, IndexError) as e:
            logger.debug('Invalid uri format %s: %s', uri, e)
            return None

        if variant == 'reciter' and identifier in self.reciters and sura is not None:
            return self.reciters[identifier]['url'] + '/%03d' % sura + '.mp3'
        elif variant == 'radio' and 0 <= identifier < len(self.radios):
            return self.radios[identifier]['url']

        logger.debug('Could not translate uri: %s', uri)
        return None

    def get_radios(self) -> List[Ref]:
        results = []
        for k, radio in enumerate(self.radios):
            results.append(Ref.track(uri='mp3quran:radio:' + str(k), name=radio['name']))
        return results

    def get_reciters(self) -> List[Ref]:
        results = []
        for reciter_id, reciter in self.reciters.items():
            name = '%s (%s)' % (reciter['name'], reciter['rewaya'])
            results.append(Ref.directory(uri='mp3quran:reciter:%d' % reciter_id, name=name))
        return results

    def reciter_suras(self, reciter_id: int) -> List[Ref]:
        results = []
        reciter_id = int(reciter_id)
        if reciter_id not in self.reciters:
            logger.warning('Reciter ID %d not found', reciter_id)
            return results
        reciter = self.reciters[reciter_id]
        for sura_no in reciter['suras']:
            sura_name = self.suras_name.get(sura_no, 'Surah %d' % sura_no)
            results.append(
                Ref.track(
                    uri='mp3quran:reciter:%d:%d' % (reciter_id, sura_no),
                    name=sura_name,
                )
            )
        return results

    def search(self, query: str) -> List[Ref]:
        """Search reciters and radios by name (case-insensitive)."""
        results = []
        query_lower = query.lower()
        for reciter_id, reciter in self.reciters.items():
            if query_lower in reciter['name'].lower() or query_lower in reciter['rewaya'].lower():
                name = '%s (%s)' % (reciter['name'], reciter['rewaya'])
                results.append(Ref.directory(uri='mp3quran:reciter:%d' % reciter_id, name=name))
        for k, radio in enumerate(self.radios):
            if query_lower in radio['name'].lower():
                results.append(Ref.track(uri='mp3quran:radio:' + str(k), name=radio['name']))
        return results

    def refresh(self) -> None:
        """Force re-fetch all data from the API."""
        self.reciters = {}
        self.radios = []
        self.suras_name = {}
        self._reciters_timestamp = 0.0
        self._radios_timestamp = 0.0
        self._suras_timestamp = 0.0
        self._init_suras()
        self.init_reciters()
        self.init_radios()
