import json

from django.test import Client, TestCase, override_settings


@override_settings(REGISTRY_WRITE_TOKEN="test-only-registry-token")
class RegistryAuthorizationTests(TestCase):
    endpoints = [('/api/policies/', {'name': 'sample'}), ('/api/credentials/', {'template_type': 'sample', 'claims_schema': {}})]

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_public_reads_and_authorized_writes(self):
        for url, payload in self.endpoints:
            self.assertEqual(self.client.get(url).status_code, 200)
            response = self.client.post(
                url, json.dumps(payload), content_type="application/json",
                HTTP_AUTHORIZATION="Bearer test-only-registry-token",
            )
            self.assertEqual(response.status_code, 201)

    def test_missing_wrong_and_non_ascii_tokens_cannot_create(self):
        for url, payload in self.endpoints:
            for token in ("", "Bearer wrong", "Bearer non-ascii-\u00e9"):
                response = self.client.post(
                    url, json.dumps(payload), content_type="application/json",
                    HTTP_AUTHORIZATION=token,
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(self.client.get(url).json(), [])

    @override_settings(REGISTRY_WRITE_TOKEN="")
    def test_unconfigured_token_disables_writes(self):
        for url, payload in self.endpoints:
            self.assertEqual(self.client.post(
                url, json.dumps(payload), content_type="application/json",
                HTTP_AUTHORIZATION="Bearer ",
            ).status_code, 401)
