import logging
import os

from importlib.metadata import version as _version

from mopidy import config, ext


__version__ = _version("Mopidy-Mp3Quran")

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
        schema['language'] = config.String()
        schema['cache_ttl'] = config.Integer(minimum=0)
        schema['timeout'] = config.Integer(minimum=1)
        schema['favorites_path'] = config.String(optional=True)
        return schema

    def setup(self, registry) -> None:
        from .backend import Mp3QuranBackend
        registry.add('backend', Mp3QuranBackend)
