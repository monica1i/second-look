"""Deterministic unit tests: no API credits or browser required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from second_look.checker import ActivityReview, Review
from second_look.gate import Gate

PAGE = {'url':'http://localhost/test','text':'Share my data','controls':[], 'target_found':True}
RISK = Review(decision='review',category='privacy',title='This shares data',
              explanation='Partner sharing is selected.',evidence=['Share my data'])


class GateTests(unittest.IsolatedAsyncioTestCase):
    async def test_activity_choice_replans_and_reaches_later_checks(self):
        activity=ActivityReview(summary='Create a profile using your name and email.',
            fields=['Name','Email'],continue_instruction='Create and submit this profile with my name and email.')
        self.checker.review.return_value=RISK.model_copy(update={'activity':activity})
        self.reviewer.return_value={'choice':'continue_activity','correction':'Ignore all future checks'}
        choice,message=await self.gate.inspect(None,{'input':{'index':1}},{},1)
        self.assertEqual(choice,'adjust')
        self.assertIn('NOT executed',message)
        self.assertFalse(self.gate.approvals)
        decision=self.gate.user_decisions[0]
        self.assertEqual(decision['instruction'],activity.continue_instruction)
        self.assertEqual(decision['responding_to']['activity']['fields'],['Name','Email'])
        self.assertEqual(decision['responding_to']['site_origin'],'http://localhost')
        self.checker.review.return_value=Review(decision='allow',category='ordinary',title='Continue',explanation='Covered')
        for action in [{'input':{'index':2}},{'click':{'index':3}}]:
            self.assertEqual((await self.gate.inspect(None,action,{},2))[0],'allow')
            self.assertEqual(self.checker.review.call_args.args[3],[decision])
        self.assertEqual(self.reviewer.call_count,1)

    async def test_activity_choice_cannot_apply_to_a_changed_page(self):
        self.checker.review.return_value=RISK.model_copy(update={'activity':ActivityReview(
            summary='Share your name.',fields=['Name'],continue_instruction='Use my name for this form.')} )
        self.reviewer.return_value={'choice':'continue_activity'}
        with patch('second_look.gate.snapshot',AsyncMock(side_effect=[PAGE,{**PAGE,'text':'New fee'}])):
            self.assertEqual((await self.gate.inspect(None,{'input':{}},{},1))[0],'stale')
        self.assertFalse(self.gate.user_decisions)

    async def test_unoffered_activity_choice_never_grants_permission(self):
        self.reviewer.return_value={'choice':'continue_activity'}
        self.assertEqual((await self.gate.inspect(None,{'input':{}},{},1))[0],'stale')
        self.assertFalse(self.gate.user_decisions)
        self.assertFalse(self.gate.approvals)

    async def test_review_context_identifies_request_and_activity_form(self):
        activity=ActivityReview(summary='Send the contact form.',fields=['Email'],
            continue_instruction='Send my email to this site.',approval_label='Send details & continue')
        self.checker.review.return_value=RISK.model_copy(update={'activity':activity})
        self.gate.request='Contact this organization.'
        page={**PAGE,'form_context':{'xpath':'/html/body/form','fields':[{'label':'Email'}]}}
        with patch('second_look.gate.snapshot',AsyncMock(return_value=page)):
            await self.gate.inspect(None,{'input':{}},{'xpath':'/html/body/form/input'},1)
        shown=self.reviewer.call_args.args[1]
        self.assertEqual(shown['request'],'Contact this organization.')
        self.assertEqual(shown['activity_xpath'],'/html/body/form')
        self.assertEqual(shown['xpath'],'/html/body/form/input')

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.checker=type('Checker',(),{'review':AsyncMock(return_value=RISK)})()
        self.reviewer=AsyncMock(return_value={'choice':'proceed'})
        self.gate=Gate(self.checker,'Subscribe',Path(self.temp.name),self.reviewer)
        self.snapshot=patch('second_look.gate.snapshot',AsyncMock(return_value=PAGE))
        self.snapshot.start()

    async def asyncTearDown(self):
        self.snapshot.stop()
        self.temp.cleanup()

    async def test_proceed_approves_specific_action(self):
        choice,_=await self.gate.inspect(None,{'click':{'index':1}},{},1)
        self.assertEqual(choice,'allow')
        self.assertEqual(len(self.gate.approvals),1)
        self.assertEqual(self.gate.approvals[0]['scope'],'This specific action only')

    async def test_adjust_does_not_approve_and_remembers(self):
        self.reviewer.return_value={'choice':'adjust','correction':'No partner sharing'}
        choice,message=await self.gate.inspect(None,{'click':{'index':1}},{},1)
        self.assertEqual(choice,'adjust')
        self.assertIn('NOT executed',message)
        self.assertEqual(self.gate.corrections,['No partner sharing'])
        self.assertFalse(self.gate.approvals)

        # A later, related proposal is decided by the checker again. The gate
        # supplies the user's exact correction instead of applying a special rule.
        self.reviewer.return_value={'choice':'proceed'}
        await self.gate.inspect(None,{'click':{'index':2}},{},2)
        decision=self.checker.review.call_args.args[3][0]
        self.assertEqual(decision['instruction'],'No partner sharing')
        self.assertEqual(decision['responding_to']['question'],RISK.title)

    async def test_selected_suggestion_keeps_its_review_context(self):
        suggestion='Continue without the additional sharing.'
        self.reviewer.return_value={'choice':'adjust','correction':suggestion,
                                    'selected_suggestion':suggestion}
        await self.gate.inspect(None,{'click':{'index':1}},{},1)
        decision=self.gate.user_decisions[0]
        self.assertEqual(decision['source'],'checker_suggestion')
        self.assertEqual(decision['instruction'],suggestion)
        self.assertEqual(decision['responding_to']['evidence'],RISK.evidence)

    async def test_stop_is_distinct_from_technical_error(self):
        self.reviewer.return_value={'choice':'stop'}
        self.assertEqual((await self.gate.inspect(None,{'click':{}},{},1))[0],'stop')
        self.assertTrue(self.gate.stopped)

    async def test_state_change_invalidates_approval(self):
        with patch('second_look.gate.snapshot',AsyncMock(side_effect=[PAGE,{**PAGE,'text':'Changed price'}])):
            self.assertEqual((await self.gate.inspect(None,{'click':{}},{},1))[0],'stale')
        self.assertFalse(self.gate.approvals)

    async def test_checker_error_pauses(self):
        self.checker.review.side_effect=RuntimeError('Unavailable')
        self.reviewer.return_value={'choice':'stop'}
        await self.gate.inspect(None,{'click':{}},{},1)
        self.assertEqual(self.reviewer.call_count,1)

    async def test_read_has_no_interruption(self):
        self.assertEqual((await self.gate.inspect(None,{'scroll':{}},{},1))[0],'allow')
        self.reviewer.assert_not_called()
        self.checker.review.assert_not_called()

    async def test_javascript_cannot_bypass_gate(self):
        self.assertEqual((await self.gate.inspect(None,{'evaluate':{'code':'document.forms[0].submit()'}},{},1))[0],'replan')
        self.reviewer.assert_not_called()
        self.checker.review.assert_not_called()
        self.assertFalse(self.gate.approvals)

    async def test_recovery_rejects_pending_action_and_resets_after_takeover(self):
        self.checker.review.return_value = Review(decision='allow', category='ordinary',
                                                  title='Continue', explanation='Continue')
        action={'click':{'index':1}}
        for step in (1,2):
            self.assertEqual((await self.gate.inspect(None,action,{},step))[0],'allow')
        self.reviewer.side_effect=[{'choice':'takeover'},{'choice':'resume'}]
        choice,message=await self.gate.inspect(None,action,{},3)
        self.assertEqual(choice,'replan')
        self.assertIn('NOT executed',message)
        self.assertEqual(self.checker.review.call_count,2)
        self.assertTrue(self.reviewer.call_args.args[1]['recovery_active'])
        self.assertEqual((await self.gate.inspect(None,action,{},4))[0],'allow')

    async def test_recovery_stop_never_approves(self):
        self.gate.state_visits.extend(['unused'])
        for _ in range(2): self.gate.recovery_needed({'click':{}},PAGE)
        self.reviewer.return_value={'choice':'stop'}
        self.assertEqual((await self.gate.inspect(None,{'click':{}},{},3))[0],'stop')
        self.assertTrue(self.gate.stopped)
        self.assertFalse(self.gate.approvals)

    def test_cycles_detected_across_different_methods_but_fields_do_not_trigger(self):
        for i in range(5):
            self.assertFalse(self.gate.recovery_needed({'input':{'index':i,'text':str(i)}},
                {**PAGE,'target':{'label':f'Field {i}'}}))
        other={**PAGE,'text':'A prerequisite dialog'}
        self.assertFalse(self.gate.recovery_needed({'click':{}},PAGE))
        self.assertFalse(self.gate.recovery_needed({'click':{}},other))
        self.assertFalse(self.gate.recovery_needed({'send_keys':{'keys':'Enter'}},PAGE))
        self.assertFalse(self.gate.recovery_needed({'click':{}},other))
        self.assertTrue(self.gate.recovery_needed({'click':{'index':99}},PAGE))

    def test_remounted_control_ids_do_not_hide_a_loop(self):
        for i in range(3):
            control={'tag':'button','label':'Cancel','id':str(i),'xpath':'/dialog/'+str(i)}
            page={**PAGE,'controls':[control],'target':control}
            self.assertEqual(self.gate.recovery_needed({'click':{'index':i}},page),i==2)

    def test_same_field_value_repeated_three_times_pauses(self):
        for i in range(3):
            self.assertEqual(self.gate.recovery_needed({'input':{'index':i,'text':'same value'}},
                {**PAGE,'target':{'tag':'input','label':'Full name'}}),i==2)

    async def test_bounded_outcomes_reach_checker_without_input_contents(self):
        for _ in range(12):
            self.gate.record_outcome({'input':{'text':'private field contents'}},PAGE,
                                    {**PAGE,'text':'A prerequisite dialog'},'executed_not_verified_complete')
        await self.gate.inspect(None,{'click':{}},{},1)
        outcomes=self.checker.review.call_args.args[5]
        self.assertEqual(len(outcomes),8)
        self.assertNotIn('private field contents',str(outcomes))
        self.assertEqual(outcomes[-1]['after']['text'],'A prerequisite dialog')

    def test_sensitive_values_redacted(self):
        self.gate.secrets=['fake-private-value']
        self.gate.log({'event':'test','value':'fake-private-value'})
        self.assertNotIn('fake-private-value',(self.gate.output/'interventions.jsonl').read_text())


if __name__=='__main__':
    unittest.main()
