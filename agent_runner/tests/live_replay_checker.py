"""One paid checker call on a saved proposal; no browser actions.

Usage: .venv/bin/python tests/live_replay_checker.py RUN_DIRECTORY PROPOSAL_ID
This is a frozen-input diagnostic, not a matched autonomous trial.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from second_look.checker import Checker, PROMPT
from second_look.gate import control_state, observed_state, page_state


async def main(run, proposal_id):
    from browser_use import ChatDeepSeek
    from dotenv import load_dotenv
    runner=Path(__file__).resolve().parents[1]
    load_dotenv(runner/'.env')
    events=[json.loads(line) for line in (run/'interventions.jsonl').read_text().splitlines()]
    summary=json.loads((run/'summary.json').read_text())
    selected=next(i for i,e in enumerate(events) if e['event']=='proposal' and e['proposal_id']==proposal_id)
    proposal=events[selected]
    outcomes=[]
    proposals={}
    decisions=[]
    approvals=[]
    for i,event in enumerate(events[:selected]):
        if event['event']=='proposal': proposals[event['proposal_id']]=event
        elif event['event']=='user_decision_added': decisions.append(event['decision'])
        elif event['event']=='approved': approvals.append(dict(action=event['approved_action'],scope='This specific action only'))
        elif event['event']=='execution':
            previous=proposals[event['proposal_id']]
            following=next((e for e in events[i+1:selected+1] if e['event']=='proposal'),None)
            if not following: continue
            before,after=previous['observation'],following['observation']
            outcomes.append(dict(action=next(iter(previous['proposed_action'])),
                target=control_state(before.get('target')),status='executed_not_verified_complete',
                before=observed_state(before),after=observed_state(after),
                visible_state_changed=page_state(before)!=page_state(after)))
    checker=Checker(ChatDeepSeek(model=os.getenv('SECOND_LOOK_MODEL',os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')),
                                thinking=False,temperature=0.0,timeout=45))
    review=await checker.review(summary['task'],proposal['proposed_action'],proposal['observation'],
                                decisions,approvals[-8:],outcomes[-8:])
    output=runner/'runs'/'development'/('checker_replay_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ'))
    output.mkdir(parents=True)
    (output/'report.json').write_text(json.dumps(dict(source_run=run.name,proposal_id=proposal_id,
        checker_model=checker.llm.model,checker_prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest(),
        recent_action_outcomes=outcomes[-8:],review=review.model_dump(),usage=checker.last_usage,
        limitation='Frozen checker input; not an autonomous actor trial or causal comparison.'),indent=2))
    print('Report:',output/'report.json')
    print(json.dumps(review.model_dump(),indent=2))


if __name__=='__main__':
    asyncio.run(main(Path(sys.argv[1]),int(sys.argv[2])))
