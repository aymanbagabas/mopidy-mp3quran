from __future__ import absolute_import, unicode_literals

import logging
import os

from mopidy import config, ext


__version__ = '0.1'
__test__ = "test"

# If you need to log, use loggers named after the current Python module
logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopidy-Mp3Quran'
    ext_name = 'mp3quran'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        return schema

    def setup(self, registry):

        # Register a backend
        from .backend import Mp3QuranBackend
        registry.add('backend', Mp3QuranBackend)
