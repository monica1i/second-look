import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from second_look.gate import create_agent_class


class ActorRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_action_requests_fresh_output(self):
        from browser_use.llm.exceptions import ModelProviderError
        cls=create_agent_class()
        instance=object.__new__(cls)
        instance.gate=None
        messages=[]
        expected=object()
        error=ModelProviderError(message='1 validation error: action Field required',status_code=400,model='test')
        with patch('browser_use.agent.service.Agent._get_model_output_with_retry',
                   AsyncMock(side_effect=[error,expected])) as request:
            result=await instance._get_model_output_with_retry(messages)
        self.assertIs(result,expected)
        self.assertEqual(request.call_count,2)
        self.assertEqual(len(messages),1)
        self.assertIn('action',messages[0].content)

    async def test_other_provider_errors_are_not_retried(self):
        from browser_use.llm.exceptions import ModelProviderError
        cls=create_agent_class()
        instance=object.__new__(cls)
        instance.gate=None
        error=ModelProviderError(message='Authentication failed',status_code=401,model='test')
        with patch('browser_use.agent.service.Agent._get_model_output_with_retry',
                   AsyncMock(side_effect=error)) as request:
            with self.assertRaises(ModelProviderError):
                await instance._get_model_output_with_retry([])
        self.assertEqual(request.call_count,1)
