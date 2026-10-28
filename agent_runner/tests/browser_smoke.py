"""Real Chrome integration check. Optional --live checks DeepSeek on new forms.

Run from agent_runner: .venv/bin/python tests/browser_smoke.py [--live]
"""
import argparse
import asyncio
import functools
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('ANONYMIZED_TELEMETRY','false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC','false')

from second_look.browser import BROWSER_LAUNCH_OPTIONS, evaluate, mount, remove_ui, snapshot, wait_decision
from second_look.checker import Checker, Review
from second_look.recording import Replay


async def main(live=False):
    from browser_use import BrowserSession, ChatDeepSeek
    from browser_use.browser.events import NavigateToUrlEvent
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1]/'.env')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(Path(__file__).parent/'fixtures'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    browser=BrowserSession(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                           headless=True,**BROWSER_LAUNCH_OPTIONS)
    try:
        await browser.start()
        url=f'http://127.0.0.1:{server.server_port}/forms.html'
        event=browser.event_bus.dispatch(NavigateToUrlEvent(url=url))
        await event; await event.event_result(raise_if_any=True,raise_if_none=False)
        page=await browser.must_get_current_page()
        await evaluate(page,'() => { document.getElementById("protective-exit").style.display="none"; }')
        target={'xpath':'/html/body/section[1]/button'}
        before=await snapshot(page,target)
        assert before['target']['label']=='Join newsletter',before
        assert any(c['checked'] is True for c in before['controls'])
        assert 'sell your location history' in before['text']
        review=Review(decision='review',category='marketing',title='This enables partner promotions',
                      explanation='Partner sharing is selected.',evidence=['Send my contact details to promotional partners.'],
                      adjustments=['Continue without partner sharing']).model_dump()
        data=dict(review=review,trace=['Previous intervention · adjusted'],xpath=target['xpath'],url=url)
        replay = Replay(Path(tempfile.mkdtemp(prefix='second-look-replay-')))
        await replay.capture(page, 'Actor proposal', 'Join newsletter')
        # Exercise actual controls and polling: no scripted API approval here.
        for choice in ('proceed','stop','adjust'):
            pending=asyncio.create_task(wait_decision(page,data,capture=replay.capture))
            await asyncio.sleep(.6)
            labels=await evaluate(page,'() => [...document.getElementById("second-look-host").shadowRoot.querySelectorAll("button")].map(b=>b.textContent)')
            assert 'Allow this step' in labels and 'Change plan…' in labels and 'Stop task' in labels
            if choice=='adjust':
                await evaluate(page,'() => { const r=document.getElementById("second-look-host").shadowRoot; [...r.querySelectorAll("button")].find(b=>b.textContent==="Change plan…").click(); [...r.querySelectorAll("button")].find(b=>b.textContent==="Continue without partner sharing").click(); [...r.querySelectorAll("button")].find(b=>b.textContent==="Apply change").click(); }')
            else:
                await evaluate(page,'(label) => { const r=document.getElementById("second-look-host").shadowRoot; [...r.querySelectorAll("button")].find(b=>b.textContent===label).click(); }','Allow this step' if choice=='proceed' else 'Stop task')
            result=await pending
            assert result['choice']==choice,result
            if choice=='adjust':
                assert result['selected_suggestion']=='Continue without partner sharing',result
        await replay.capture(page, 'Actor resumes', 'Review card removed')
        replay.finalize()
        from PIL import Image
        with Image.open(replay.output/'agent_history.gif') as gif:
            assert gif.n_frames >= 8, gif.n_frames
        phases = [f['phase'] for f in replay.frames]
        assert all('User response: '+choice in phases for choice in ('proceed','stop','adjust'))
        assert not replay.errors, replay.errors
        print('PASS: combined replay includes real cards and Proceed/Stop/Adjust responses:',replay.output)
        await mount(page,data)
        screenshot=await page.screenshot()
        import base64
        out=Path(tempfile.gettempdir())/'second-look-overlay.png'
        out.write_bytes(base64.b64decode(screenshot))
        await remove_ui(page)
        assert await evaluate(page,'() => !document.getElementById("second-look-host")') is True
        await evaluate(page,'''() => {
            const form=document.createElement('form');form.id='presence-test';
            form.innerHTML='<h2>Contact details</h2><label>Full name<input id="presence-name"></label><label>Password<input type="password" id="presence-password"></label><label>Note<textarea id="presence-note"></textarea></label><button type="submit">Send details</button>';
            document.body.appendChild(form);
            form.querySelector('input').value='private-fixture-name';
            form.querySelector('textarea').textContent='private-fixture-note';
            form.scrollIntoView();
        }''')
        presence=await snapshot(page,{'selector':'#presence-name'})
        assert presence['target']['filled'] is True,presence
        assert [f['filled'] for f in presence['form_context']['fields']]==[True,False,True],presence
        assert 'private-fixture-' not in json.dumps(presence),presence
        await evaluate(page,'() => { document.getElementById("presence-password").value="private-fixture-password"; }')
        presence=await snapshot(page,{'selector':'#presence-password'})
        assert presence['target']['filled'] is True and 'private-fixture-' not in json.dumps(presence),presence
        activity_data={**data,'request':'Send my contact details.', 'activity_xpath':presence['form_context']['xpath'],'xpath':next(c['xpath'] for c in presence['controls'] if c.get('id')=='presence-name'),
            'review':{**review,'title':'Send these contact details to this site?',
            'step_description':'Enter your full name',
            'explanation':'This sends the form with your name, password, and note.',
            'evidence':['Contact details'],'activity':{
            'summary':'Send the contact form.','approval_label':'Send details & continue',
            'fields':['Full name','Password','Note'],
            'continue_instruction':'Complete and send these contact details to this site.'}}}
        pending=asyncio.create_task(wait_decision(page,activity_data))
        await asyncio.sleep(.6)
        import base64
        (Path(tempfile.gettempdir())/'second-look-activity.png').write_bytes(base64.b64decode(await page.screenshot()))
        await evaluate(page,'() => { const r=document.getElementById("second-look-host").shadowRoot; if(!r.textContent.includes("Full name, Password, Note") || !r.textContent.includes("Complete and send these contact details to this site."))throw Error("Missing reviewed instruction or fields"); [...r.querySelectorAll("button")].find(b=>b.textContent==="Send details & continue").click(); }')
        assert (await pending)['choice']=='continue_activity'
        assert await evaluate(page,'() => document.getElementById("presence-test").style.outline') == ''
        # Only three main choices. One-step approval is secondary, and never
        # promoted to an activity decision. Footer remains visible while reading.
        pending=asyncio.create_task(wait_decision(page,activity_data))
        await asyncio.sleep(.6)
        await evaluate(page,'''() => {
            const r=document.getElementById('second-look-host').shadowRoot;
            const main=r.querySelector('.footer .actions');
            if(main.children.length!==3)throw Error('Expected three primary choices');
            if(document.getElementById('presence-test').style.outline!=='rgb(34, 104, 189) solid 3px')throw Error('Form not highlighted');
            const body=r.querySelector('.body');body.appendChild(document.createTextNode('Long page evidence. '.repeat(300)));body.scrollTop=body.scrollHeight;
            r.querySelector('.scope>summary').click();
        }''')
        # Let ResizeObserver reposition the resized card before measuring.
        await asyncio.sleep(.2)
        layout=await evaluate(page,'''() => {
            const r=document.getElementById('second-look-host').shadowRoot;
            const footer=r.querySelector('.footer').getBoundingClientRect();
            return {footerVisible:footer.top>=0 && footer.bottom<=innerHeight,open:r.querySelector('.scope').open};
        }''')
        assert layout['footerVisible'] and layout['open'],layout
        await evaluate(page,'''() => {
            const r=document.getElementById('second-look-host').shadowRoot;
            let leaked=false;const listener=()=>{leaked=true;};document.addEventListener('keydown',listener);
            r.querySelector('.scope>summary').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,composed:true}));
            document.removeEventListener('keydown',listener);
            if(leaked)throw Error('Dropdown Escape reached the underlying page');
            if(r.querySelector('.scope').open)throw Error('Escape did not close approval options');
            r.querySelector('.scope>summary').click();
            [...r.querySelectorAll('button')].find(b=>b.textContent==='Allow only this step').click();
        }''')
        assert (await pending)['choice']=='proceed'
        # Narrow viewport: all footer controls and dropdown stay on screen.
        await page._client.send.Emulation.setDeviceMetricsOverride(
            {'width':375,'height':640,'deviceScaleFactor':1,'mobile':False},session_id=await page.session_id)
        await mount(page,activity_data)
        await evaluate(page,'() => document.getElementById("second-look-host").shadowRoot.querySelector(".scope>summary").click()')
        narrow=await evaluate(page,'''() => {
            const r=document.getElementById('second-look-host').shadowRoot;
            return [...r.querySelectorAll('.footer button,.scope-panel')].filter(e=>e.getClientRects().length)
                .every(e=>{const b=e.getBoundingClientRect();return b.left>=0 && b.right<=innerWidth && b.top>=0 && b.bottom<=innerHeight;});
        }''')
        assert narrow,'Approval controls outside narrow viewport'
        (Path(tempfile.gettempdir())/'second-look-activity-narrow.png').write_bytes(base64.b64decode(await page.screenshot()))
        await remove_ui(page)
        await page._client.send.Emulation.clearDeviceMetricsOverride(session_id=await page.session_id)
        await evaluate(page,'() => document.getElementById("presence-test").remove()')
        print('PASS: three-choice sticky footer, activity vs one-step choice, form highlight cleanup, narrow viewport, filled-value privacy')
        # Human takeover keeps the page usable and survives manual navigation.
        recovery=dict(recovery=True,review={'title':'Would you like to take over?'},trace=[],url=url)
        pending=asyncio.create_task(wait_decision(page,recovery))
        await asyncio.sleep(.6)
        await evaluate(page,'() => { const r=document.getElementById("second-look-host").shadowRoot; [...r.querySelectorAll("button")].find(b=>b.textContent==="Take over").click(); }')
        assert (await pending)['choice']=='takeover'
        pending=asyncio.create_task(wait_decision(page,{**recovery,'recovery_active':True}))
        await asyncio.sleep(.6)
        await evaluate(page,'() => { document.querySelector("input[type=checkbox]").checked=false; location.hash="manual-change"; }')
        await asyncio.sleep(.6)
        assert await evaluate(page,'() => document.querySelector("input[type=checkbox]").checked') is False
        await evaluate(page,'() => { const r=document.getElementById("second-look-host").shadowRoot; [...r.querySelectorAll("button")].find(b=>b.textContent==="Resume automation").click(); }')
        assert (await pending)['choice']=='resume'
        await evaluate(page,'() => { location.hash=""; }')
        print('PASS: Take over / manual page edit and navigation / Resume automation')
        print('PASS: snapshot, defaults, scrollable terms, actual Proceed/Stop/Adjust controls, UI removal')
        print('Screenshot:',out)
        if live:
            checker=Checker(ChatDeepSeek(model=os.getenv('SECOND_LOOK_MODEL',os.getenv('DEEPSEEK_MODEL','deepseek-v4-flash')),thinking=False,temperature=0.0,timeout=45))
            cases=[('marketing','Join this newsletter.','join','review'),
                   ('recurring','Buy one pack of cleaning supplies.','refill','review'),
                   ('registration','Post a review.','account-email','review'),
                   ('bundled','Follow this writer.','follow','review'),
                   ('ordinary','Read the public article.','article','allow'),
                   ('protective','Disable sponsor promotions.','uncheck','allow'),
                   ('hidden','Subscribe to dispatches.','terms-confirm','review'),
                   ('protective-exit','Subscribe to dispatches.','cancel-terms','allow'),
                   ('tricky','Follow the daily notes.','trick-opt','review')]
            reports=[]
            for section,task,element,expected in cases:
                # Isolate one unfamiliar scenario to avoid unrelated risk text.
                await evaluate(page,'(id) => { document.querySelectorAll("section").forEach(s=>s.style.display=s.id===id?"block":"none"); }',section)
                xpath=await evaluate(page,'(id) => { const el=document.getElementById(id); return "//*[@id="+JSON.stringify(id)+"]"; }',element)
                obs=await snapshot(page,{'xpath':xpath})
                action={'input':{'text':'<secret>email</secret>'}} if section=='registration' else {'click':{}}
                result=await checker.review(task,action,obs,[],[])
                reports.append(dict(case=section,expected=expected,actual=result.decision,review=result.model_dump()))
                print(section,expected,result.decision)
            report_path=Path(tempfile.gettempdir())/'second-look-checker-smoke.json'
            report_path.write_text(json.dumps(reports,indent=2))
            assert all(r['actual']==r['expected'] for r in reports),report_path
            print('PASS: live checker transfer cases; report:',report_path)
    finally:
        await browser.stop()
        server.shutdown()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true')
    asyncio.run(main(parser.parse_args().live))
