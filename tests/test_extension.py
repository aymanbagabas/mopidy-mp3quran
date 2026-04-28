import os
from unittest import mock

from mopidy_mp3quran import Extension


class TestExtension:

    def test_ext_name(self):
        ext = Extension()
        assert ext.ext_name == "mp3quran"

    def test_dist_name(self):
        ext = Extension()
        assert ext.dist_name == "Mopidy-Mp3Quran"

    def test_version(self):
        from packaging.version import Version
        ext = Extension()
        assert Version(ext.version) == Version("0.2.1")

    def test_get_default_config_has_section(self):
        ext = Extension()
        config = ext.get_default_config()
        assert "[mp3quran]" in config

    def test_get_default_config_has_enabled(self):
        ext = Extension()
        config = ext.get_default_config()
        assert "enabled = true" in config

    def test_get_default_config_has_language(self):
        ext = Extension()
        config = ext.get_default_config()
        assert "language = english" in config

    def test_get_default_config_has_cache_ttl(self):
        ext = Extension()
        config = ext.get_default_config()
        assert "cache_ttl = 3600" in config

    def test_get_default_config_has_timeout(self):
        ext = Extension()
        config = ext.get_default_config()
        assert "timeout = 10" in config

    def test_get_config_schema_contains_all_keys(self):
        ext = Extension()
        schema = ext.get_config_schema()
        assert "enabled" in schema
        assert "language" in schema
        assert "cache_ttl" in schema
        assert "timeout" in schema

    def test_setup_registers_backend(self):
        registry = mock.Mock()
        ext = Extension()
        ext.setup(registry)
        registry.add.assert_called_once()
        args = registry.add.call_args
        assert args[0][0] == "backend"
        from mopidy_mp3quran.backend import Mp3QuranBackend
        assert args[0][1] is Mp3QuranBackend

    def test_get_default_config_file_exists(self):
        ext = Extension()
        conf_dir = os.path.dirname(os.path.abspath(ext.get_default_config.__code__.co_filename))
        conf_file = os.path.join(conf_dir, "ext.conf")
        assert os.path.exists(conf_file)
