"""Check real framework credential discovery and substitution without an API."""
import unittest
from types import SimpleNamespace

from pydantic import BaseModel
from browser_use.agent.message_manager.service import MessageManager
from browser_use.tools.registry.service import Registry
from run_task import scoped_credentials


class Input(BaseModel):
    text: str


class CredentialTests(unittest.TestCase):
    def test_http_password_is_advertised_and_substituted(self):
        url = 'http://127.0.0.1:5173/AgentEval/#/task/1/shopping?agent=true'
        secrets = scoped_credentials(url, {'password': 'fictional-test-password'})
        manager = SimpleNamespace(sensitive_data=secrets)
        description = MessageManager._get_sensitive_data_description(manager, url)
        self.assertIn('  - password', description)
        self.assertNotIn('fictional-test-password', description)
        params = Registry()._replace_sensitive_data(
            Input(text='<secret>password</secret>'), secrets, url)
        self.assertEqual(params.text, 'fictional-test-password')

    def test_unrelated_host_and_wrong_scheme_do_not_advertise(self):
        secrets = scoped_credentials('http://127.0.0.1:5173', {'password': 'fictional'})
        manager = SimpleNamespace(sensitive_data=secrets)
        for url in ['http://example.com', 'https://127.0.0.1:5173']:
            self.assertEqual(MessageManager._get_sensitive_data_description(manager, url), '')

    def test_https_and_empty_credentials(self):
        url = 'https://example.com/page'
        manager = SimpleNamespace(sensitive_data=scoped_credentials(url, {'password': 'fictional'}))
        self.assertIn('  - password', MessageManager._get_sensitive_data_description(manager, url))
        self.assertEqual(scoped_credentials(url, {}), {})
