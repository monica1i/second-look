"""Check real framework credential discovery and substitution without an API."""
import unittest
from types import SimpleNamespace

from pydantic import BaseModel
from browser_use.agent.message_manager.service import MessageManager
from browser_use.tools.registry.service import Registry
from run_task import scoped_credentials
from second_look.gate import actor_context, create_agent_class
from unittest.mock import AsyncMock, Mock, patch


class Input(BaseModel):
    text: str


class CredentialTests(unittest.TestCase):
    def test_actor_context_exposes_matching_names_only_and_preserves_decisions(self):
        url='http://localhost/form'
        manager=SimpleNamespace(sensitive_data=scoped_credentials(url,{'email':'fixture-private-value'}))
        gate=SimpleNamespace(user_decisions=[{'instruction':'Do not share my email'}],recent_outcomes=[])
        description=MessageManager._get_sensitive_data_description(manager,url)
        context=actor_context(gate,description)
        self.assertIn('  - email',context)
        self.assertIn('Do not share my email',context)
        self.assertNotIn('fixture-private-value',context)
        foreign=actor_context(gate,MessageManager._get_sensitive_data_description(manager,'https://other.test'))
        self.assertIn('No configured credential placeholders match',foreign)
        self.assertNotIn('  - email',foreign)
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


class ActorCredentialDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_page_availability_reaches_actor_even_without_history(self):
        cls=create_agent_class()
        actor=object.__new__(cls)
        actor.gate=SimpleNamespace(user_decisions=[],recent_outcomes=[])
        manager=SimpleNamespace(_get_sensitive_data_description=Mock(return_value='Available placeholder names: email'),
                                _add_context_message=Mock())
        actor._message_manager=manager
        with patch('browser_use.agent.service.Agent._get_next_action',AsyncMock()) as next_action:
            await actor._get_next_action(SimpleNamespace(url='https://example.test/current'))
        manager._get_sensitive_data_description.assert_called_once_with('https://example.test/current')
        context=manager._add_context_message.call_args.args[0].content
        self.assertIn('Available placeholder names: email',context)
        next_action.assert_awaited_once()
