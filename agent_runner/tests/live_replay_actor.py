"""One paid actor call at the last saved state; no browser actions or real values.

Usage: .venv/bin/python tests/live_replay_actor.py RUN_DIRECTORY
Preserves the saved system prompt, request and page observation, replacing only
the current execution context with the production helper. This is a diagnostic.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from second_look.gate import actor_context
from second_look.tools import create_tools
from run_task import scoped_credentials


async def main(run):
    from browser_use import ChatDeepSeek
    from browser_use.agent.views import AgentOutput
    from browser_use.agent.message_manager.service import MessageManager
    from browser_use.llm.messages import SystemMessage, UserMessage
    from dotenv import load_dotenv
    runner=Path(__file__).resolve().parents[1]
    load_dotenv(runner/'.env')
    history=json.loads((run/'history.json').read_text())['history']
    state=history[-1]['state_message']
    transcript=sorted((run/'conversations').glob('*.txt'),key=lambda p:int(p.stem.rsplit('_',1)[-1]))[-1].read_text()
    system=transcript.split('\n user \n',1)[0].removeprefix(' system \n')
    section=re.search(r'<sensitive_data>(.*?)</sensitive_data>',state,re.S)
    names=re.findall(r'^  - (.+)$',section.group(1),re.M) if section else []
    manager=SimpleNamespace(sensitive_data=scoped_credentials(history[-1]['state']['url'],
        {name:'replay-only-unused-value' for name in names}))
    description=MessageManager._get_sensitive_data_description(manager,history[-1]['state']['url'])
    events=[json.loads(line) for line in (run/'interventions.jsonl').read_text().splitlines()]
    gate=SimpleNamespace(user_decisions=[e['decision'] for e in events if e['event']=='user_decision_added'],
        recent_outcomes=[e['outcome'] for e in events if e['event']=='action_outcome' and e['outcome']['action']!='done'][-8:])
    context=actor_context(gate,description)
    llm=ChatDeepSeek(model=os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash'),thinking=False,temperature=0.0,timeout=45)
    response=await llm.ainvoke([SystemMessage(content=system),UserMessage(content=state),UserMessage(content=context)],
        output_format=AgentOutput.type_with_custom_actions(create_tools().registry.create_action_model()))
    result=response.completion.model_dump(mode='json')
    output=runner/'runs'/'development'/('actor_replay_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%SZ'))
    output.mkdir(parents=True)
    (output/'report.json').write_text(json.dumps(dict(source_run=run.name,model=llm.model,
        actor_context_sha256=hashlib.sha256(context.encode()).hexdigest(),available_placeholder_names=names,
        actor_output=result,limitation='One frozen actor proposal, no actions executed, no real credential values supplied.'),indent=2))
    print('Report:',output/'report.json')
    print('Proposed actions:',json.dumps(result['action']))
    assert result['action'] and not all('done' in action for action in result['action']), 'Actor still terminated; inspect retained report.'


if __name__=='__main__':
    asyncio.run(main(Path(sys.argv[1])))
