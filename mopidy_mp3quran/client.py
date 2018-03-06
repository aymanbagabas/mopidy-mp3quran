import requests
import re
import logging
from mopidy.models import Ref

logger = logging.getLogger(__name__)
api = 'https://www.mp3quran.net/api/'
reciter_api = api + 'get_json.php'
radio_api = api + 'radio/radio_en.json'

class Mp3Quran(object):

    def init_reciters(self):
        if not self.reciters:
            for reciter in self.session.get(self.url).json()['reciters']:
                suras = [int(n) for n in reciter['suras'].split(',')]  # suras as integers
                self.reciters[int(reciter['id'])] = {'name':reciter['name'], 
                        'url':reciter['Server'], 'suras':suras, 
                        'rewaya':reciter['rewaya']}

    def init_radios(self):
        if not self.radios:
            for radio in self.session.get(radio_api).json()['Radios']:
                self.radios.append({'name':radio['Name'], 'url':radio['URL']})

    def __init__(self, session=requests.Session(), language='English'):
        self.session = session
        # TODO: add language support
        self.language = '_' + language[0].lower() + language[1:] # change it to '_english'
        self.url = api + self.language + '.json'
        self.suras_name_url = api + self.language + '_sura.json'
        self.reciters = {}
        self.radios = []
        self.suras_name = {}
        for sura in self.session.get(self.suras_name_url).json()['Suras_Name']:
            self.suras_name[int(sura['id'])] = sura['name']

        self.init_reciters() # get all available reciters from api
        self.init_radios() # get all radio stations from api

    def translate_uri(self, uri):
        parsed = uri.split(':')[1:]
        if parsed:
            if len(parsed) == 3:
                variant, identifier, sura = parsed
                sura = int(sura)
            else:
                variant, identifier = parsed
            identifier = int(identifier)
            if variant == 'reciter' and identifier and sura:
                return self.reciters[identifier]['url'] + '/%03d' % sura + '.mp3'
            elif variant == 'radio' and identifier:
                return self.radios[identifier]['url']
        logger.debug('Could not translate uri: %s' % uri)
        return None

    def get_radios(self):
        results = []
        k = 0
        for radio in self.radios:
            results.append(Ref.track(uri='mp3quran:radio:' + str(k), name=radio['name']))
            k = k + 1
        return results

    def get_reciters(self):
        results = []
        for reciter in self.reciters.items():
            results.append(Ref.directory(uri='mp3quran:reciter:%d' % reciter[0], name='%s' % (reciter[1]['name'] + ' (%s)' % reciter[1]['rewaya'])))
        return results

    def reciter_suras(self, reciter_id):
        results = []
        reciter_id = int(reciter_id)
        reciter = self.reciters[reciter_id]
        for sura_no in reciter['suras']:
            results.append(Ref.track(uri='mp3quran:reciter:%d:%d' % (reciter_id, sura_no), name=self.suras_name[sura_no]))
        logger.info(results)
        return results

    def refresh(self):
        self.reciters = {}
        self.radios = []
        self.init_reciters()
        self.init_radios()
