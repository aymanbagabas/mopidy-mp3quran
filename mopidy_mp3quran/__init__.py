import logging
import os

from mopidy import config, ext


__version__ = '0.2'

logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopidy-Mp3Quran'
    ext_name = 'mp3quran'
    version = __version__

    def get_default_config(self) -> str:
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self) -> config.ConfigSchema:
        schema = super().get_config_schema()
        schema['language'] = config.String(default='English')
        schema['cache_ttl'] = config.Integer(default=3600, minimum=0)
        schema['timeout'] = config.Integer(default=10, minimum=1)
        return schema

    def setup(self, registry) -> None:
        from .backend import Mp3QuranBackend
        registry.add('backend', Mp3QuranBackend)
