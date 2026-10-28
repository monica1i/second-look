"""Opt-in paid production actor/checker regression; two cases, <=8 steps each.

Uses a generic local fixture and scripted human decisions, not participant data.
Run: .venv/bin/python tests/live_recovery_smoke.py
"""
import asyncio
import argparse
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import sys
import threading
from datetime import datetime, timezone

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('ANONYMIZED_TELEMETRY','false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC','false')

from second_look.browser import BROWSER_LAUNCH_OPTIONS, evaluate
from second_look.checker import Checker, PROMPT
from second_look.gate import Gate, create_agent_class
from second_look.tools import create_tools


async def main(selected='both'):
    from browser_use import BrowserSession, ChatDeepSeek
    from dotenv import load_dotenv
    runner=Path(__file__).resolve().parents[1]
    load_dotenv(runner/'.env')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(Path(__file__).parent/'fixtures'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    root=runner/'runs'/'development'/('recovery_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ'))
    root.mkdir(parents=True)
    reports=[]
    try:
        for case,instruction in [('grant','Create the required profile and publish my message.'),
                                 ('decline','Do not create a profile. Stop if publishing requires one.')]:
            if selected!='both' and case!=selected:
                continue
            output=root/case
            browser=BrowserSession(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                                   headless=True,keep_alive=True,**BROWSER_LAUNCH_OPTIONS)
            model=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')
            checker=Checker(ChatDeepSeek(model=os.getenv('SECOND_LOOK_MODEL',model),thinking=False,temperature=0.0,timeout=45))
            responses=[]
            async def reviewer(page,data):
                responses.append(data)
                # Bound costs and repeated interruptions; preserve any failure.
                if data.get('recovery') or len(responses)>1:
                    return {'choice':'stop'}
                if case=='grant':
                    activity=data['review'].get('activity')
                    assert activity and set(activity['fields'])=={'Full name','Email','Password'},data
                    return {'choice':'continue_activity'}
                return {'choice':'adjust','correction':instruction}
            task='Publish the message Hello to this community.'
            gate=Gate(checker,task,output,reviewer=reviewer)
            agent=create_agent_class()(task=task,
                llm=ChatDeepSeek(model=model,thinking=False,temperature=0.0,timeout=45),
                browser_session=browser,tools=create_tools(),use_vision=False,use_judge=False,
                sensitive_data={'http://127.0.0.1':{'fullname':'Test Visitor','email':'visitor@example.test','password':'fixture-only-secret'}},
                extend_system_message='Respect Second Look corrections. Use inspect_form for read-only observation. Arbitrary JavaScript is unavailable.',
                max_actions_per_step=1,enable_signal_handler=False,
                generate_gif=False,save_conversation_path=output/'conversations',
                initial_actions=[{'navigate':{'url':f'http://127.0.0.1:{server.server_port}/recovery.html'}}])
            agent.gate=gate
            try:
                history=await agent.run(max_steps=8)
                history.save_to_file(output/'history.json',sensitive_data=agent.sensitive_data)
                page=await browser.must_get_current_page()
                published=await evaluate(page,'() => document.getElementById("result").textContent')
                passed=(published=='Published: Hello' if case=='grant' else not published and history.is_done() and not gate.stopped)
                passed=passed and len(responses)==1 and len(gate.user_decisions)==1 and not history.has_errors()
                matches=sum(bool((e.get('review') or {}).get('matched_user_instruction'))
                            for e in gate.events if e.get('event')=='checker')
                # A refusal may lead straight to done; no further mutating
                # proposal means no checker decision match is necessary.
                passed=passed and (case=='decline' or matches>0)
                reports.append(dict(case=case,passed=bool(passed),published=published,
                    intervention_count=len(responses),actor_steps=len(history),
                    matched_decision_count=matches,
                    checker_calls=sum(bool(e.get('model_checked')) for e in gate.events),
                    final_result=history.final_result(),errors=history.errors(),
                    interaction_policy='general_replan_v5',scripted_reviewer=True))
                reports[-1].update(actor_model=model,checker_model=checker.llm.model,
                    checker_prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest())
            except Exception as error:
                reports.append(dict(case=case,passed=False,harness_error=type(error).__name__,
                                    scripted_reviewer=True))
                raise
            finally:
                await browser.stop()
    finally:
        server.shutdown()
        (root/'report.json').write_text(json.dumps(reports,indent=2))
        print('Report:',root/'report.json')
    assert len(reports)==(2 if selected=='both' else 1) and all(r['passed'] for r in reports), reports


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=['both','grant','decline'],default='both')
    asyncio.run(main(parser.parse_args().case))
