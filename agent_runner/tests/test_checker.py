import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from second_look.checker import Checker, Review


class CheckerTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_mutating_action_is_decided_by_model(self):
        response=Review(decision='allow',category='ordinary',title='Allowed',explanation='Authorized.')
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        page={'url':'http://localhost/task/5','text':'Current page','controls':[]}
        result=await Checker(llm).review('Do the task',{'click':{'index':1}},page,[],[])
        self.assertEqual(result.decision,'allow')
        llm.ainvoke.assert_called_once()

    async def test_user_corrections_and_one_action_approvals_reach_checker(self):
        response=Review(decision='allow',category='ordinary',title='Allowed',explanation='Authorized.')
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        decisions=[{'instruction':'Continue with the required step',
                    'responding_to':{'question':'This adds a new requirement. Continue?'}}]
        approvals=[{'action':{'click':{'index':2}},'scope':'This specific action only'}]
        await Checker(llm).review('Post a comment',{'input':{'index':3,'text':'name'}},
                                  {'url':'http://localhost/task/13','text':'Create account'},
                                  decisions,approvals)
        payload=json.loads(llm.ainvoke.call_args.args[0][1].content)
        self.assertEqual(payload['active_user_decisions'],decisions)
        self.assertEqual(payload['prior_one_action_approvals'],approvals)
        self.assertEqual(payload['original_user_task'],'Post a comment')
        self.assertIn('current_page',payload)

    async def test_url_path_is_removed_from_checker_input(self):
        response=Review(decision='allow',category='ordinary',title='Allowed',explanation='Authorized.')
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        await Checker(llm).review('Task',{'click':{}},
                                  {'url':'http://localhost/task/13?agent=true','text':'Page'},[],[])
        payload=json.loads(llm.ainvoke.call_args.args[0][1].content)
        self.assertEqual(payload['current_page']['url'],'http://localhost')

    async def test_model_adjustment_suggestions_are_preserved(self):
        quote='This action shares your profile.'
        response=Review(decision='review',category='privacy',title='Profile sharing',
                        explanation='The action shares profile information.',evidence=[quote],
                        adjustments=['Continue without sharing my profile'])
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        result=await Checker(llm).review('Continue',{'click':{}},{'text':quote},[],[])
        self.assertEqual(result.adjustments,['Continue without sharing my profile'])

    async def test_recent_outcomes_reach_checker_but_are_not_quote_sources(self):
        response=Review(decision='review',category='uncertain',title='Continue?',
                        explanation='Uncertain',evidence=['Old prerequisite'])
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        outcomes=[{'action':'click','after':{'text':'Old prerequisite'}}]
        result=await Checker(llm).review('Finish',{'click':{}},{'text':'Current page'},[],[],outcomes)
        payload=json.loads(llm.ainvoke.call_args.args[0][1].content)
        self.assertEqual(payload['recent_action_outcomes'],outcomes)
        self.assertEqual(result.evidence,[])

    async def test_matched_user_instruction_is_preserved(self):
        instruction='Continue with the requirement shown in this warning.'
        response=Review(decision='allow',category='ordinary',title='Continue',
                        explanation='You already chose this.',matched_user_instruction=instruction)
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        result=await Checker(llm).review('Finish',{'input':{}},{'text':'Required details'},
            [{'instruction':instruction,'responding_to':{'question':'Continue?'}}],[])
        self.assertEqual(result.matched_user_instruction,instruction)

    async def test_fabricated_evidence_is_not_displayed(self):
        response=Review(decision='review',category='privacy',title='Sharing',
                        explanation='Bad',evidence=['Invented sharing clause'])
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        result=await Checker(llm).review('Read',{'click':{}},{'text':'Read an article'},[],[])
        self.assertEqual(result.category,'uncertain')
        self.assertEqual(result.evidence,[])

    async def test_exact_quotes_with_quotation_marks_are_retained(self):
        quote='Click "Join" to share your data.'
        response=Review(decision='review',category='privacy',title='Sharing',
                        explanation='Sharing selected.',evidence=[quote])
        llm=SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(completion=response)))
        result=await Checker(llm).review('Join',{'click':{}},{'text':quote},[],[])
        self.assertEqual(result.evidence,[quote])


if __name__=='__main__':
    unittest.main()
