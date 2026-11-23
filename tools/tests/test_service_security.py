"""Local configuration and HTTP-client checks; no PDO services are contacted."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location('isolated_service_config', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServiceSecurityTests(unittest.TestCase):
    def test_missing_secret_prevents_service_start(self):
        for kind in ('asset_registry', 'template_registry', 'pdo_client/webapp'):
            with self.subTest(kind=kind), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ImproperlyConfigured, 'DJANGO_SECRET_KEY'):
                    load(ROOT / kind / 'config/settings.py')

    def test_registries_default_to_debug_off_and_loopback_hosts(self):
        for kind in ('asset_registry', 'template_registry'):
            with self.subTest(kind=kind), patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'test-only'}, clear=True):
                config = load(ROOT / kind / 'config/settings.py')
                self.assertEqual(config.SECRET_KEY, 'test-only')
                self.assertFalse(config.DEBUG)
                self.assertNotIn('*', config.ALLOWED_HOSTS)
                self.assertEqual(config.REGISTRY_WRITE_TOKEN, '')
            with patch.dict(os.environ, {
                'DJANGO_SECRET_KEY': 'test-only', 'DJANGO_ALLOWED_HOSTS': 'one.example, two.example',
            }, clear=True):
                self.assertEqual(load(ROOT / kind / 'config/settings.py').ALLOWED_HOSTS,
                                 ['one.example', 'two.example'])

    def test_client_attaches_token_to_writes_only(self):
        from django.conf import settings
        if not settings.configured:
            settings.configure(ASSET_REGISTRY_URL='https://registry.invalid',
                               ASSET_REGISTRY_WRITE_TOKEN='test-only-token')
        client = load(ROOT / 'pdo_client/webapp/app/registry_client.py')
        with patch.object(client.requests, 'post', return_value=Mock()) as post, \
             patch.object(client.requests, 'patch', return_value=Mock()) as update, \
             patch.object(client.requests, 'get', return_value=Mock()) as get:
            client.register_asset('name', 'did')
            client.update_asset_metadata(1, {})
            client.list_assets()
            for request in (post, update):
                self.assertEqual(request.call_args.kwargs['headers'], {'Authorization': 'Bearer test-only-token'})
            self.assertNotIn('headers', get.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()
