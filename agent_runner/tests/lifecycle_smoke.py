"""Real Chrome/agent loop: no transient trace mounts and no unsupported flag.

Uses a deterministic local model, so this check spends no API credits.
Run from agent_runner while Vite is running.
"""
import asyncio
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('ANONYMIZED_TELEMETRY','false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC','false')

from second_look.browser import BROWSER_LAUNCH_OPTIONS, evaluate
from second_look.checker import Review
from second_look.gate import Gate, create_agent_class


async def main():
    from browser_use import BrowserSession, ChatDeepSeek
    from browser_use.llm.views import ChatInvokeCompletion

    class LocalModel(ChatDeepSeek):
        async def ainvoke(self,messages,output_format=None,**kwargs):
            turn=getattr(self,'turn',0)
            self.turn=turn+1
            action=({'inspect_form':{}} if turn==0 else {'wait':{'seconds':1}}) if turn<2 else {'done':{'success':True,'text':'Lifecycle test complete.'}}
            output=output_format.model_validate(dict(action=[action],evaluation_previous_goal='Test step',
                memory='Deterministic lifecycle test',next_goal='Wait or finish'))
            return ChatInvokeCompletion(completion=output,usage=None)

    class AllowChecker:
        async def review(self,*args):
            return Review(decision='allow',category='ordinary',title='Open test page',explanation='Local test.')

    browser=BrowserSession(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                           headless=True,keep_alive=True,args=['--enable-automation'],**BROWSER_LAUNCH_OPTIONS)
    observations=[]
    try:
        with tempfile.TemporaryDirectory() as directory:
            from second_look.tools import create_tools
            agent=create_agent_class()(task='Exercise the local lifecycle without taking page actions.',
                llm=LocalModel(),browser_session=browser,use_vision=False,use_judge=False,
                tools=create_tools(),
                enable_planning=False,message_compaction=False,enable_signal_handler=False,
                initial_actions=[{'navigate':{'url':'http://127.0.0.1:5173/AgentEval/#/task/5?agent=true'}}])
            from second_look.recording import Replay
            replay = Replay(Path(directory))
            agent.gate=Gate(AllowChecker(),agent.task,Path(directory),replay=replay)

            async def begin(agent):
                page=await browser.must_get_current_page()
                await evaluate(page,'''() => {
                    if(window.__slMountObserver)return;
                    window.__slMountCount=0;
                    window.__slMountObserver=new MutationObserver(records=>{
                        for(const record of records)for(const node of record.addedNodes){
                            if(node.nodeType===1 && (node.id==='second-look-host' || node.querySelector?.('#second-look-host')))window.__slMountCount++;
                        }
                    });
                    window.__slMountObserver.observe(document.documentElement,{childList:true,subtree:true});
                }''')

            async def end(agent):
                page=await browser.must_get_current_page()
                observations.append(await evaluate(page,'() => ({mounts:window.__slMountCount,present:!!document.getElementById("second-look-host")})'))

            history=await agent.run(max_steps=4,on_step_start=begin,on_step_end=end)
            assert history.is_successful(),history.errors()
            assert not history.has_errors(),history.errors()
            assert len(observations)==3,observations
            assert all(o['mounts']==0 and not o['present'] for o in observations),observations
            replay.finalize()
            assert not replay.errors,replay.errors
            assert any(f['phase'].startswith('Actor action completed') for f in replay.frames)
            assert (Path(directory)/'agent_history.gif').exists()
            command=await browser.cdp_client.send.Browser.getBrowserCommandLine()
            assert '--extensions-on-chrome-urls' not in command['arguments'],command['arguments']
            print('PASS: zero overlay mounts across 3 routine agent steps; actual Chrome command line excludes unsupported flag.')
    finally:
        await browser.stop()


if __name__=='__main__':
    asyncio.run(main())
