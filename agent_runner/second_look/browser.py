"""Browser evidence and a human-only UI, removed before agent observations."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

ASSETS = Path(__file__).parent

# Keep the framework's other defaults; this extension-only flag triggers a
# Chrome warning and is unnecessary with default extensions disabled.
BROWSER_LAUNCH_OPTIONS = {
    'enable_default_extensions': False,
    'ignore_default_args': ['--extensions-on-chrome-urls'],
}


async def evaluate(page, function: str, *args):
    value = await page.evaluate(function, *args)
    if value in ('True', 'False'):
        return value == 'True'
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


async def snapshot(page, target: dict) -> dict:
    return await evaluate(page, (ASSETS / 'snapshot.js').read_text(), target)


async def resolve_target(page, node) -> dict:
    """Resolve the framework's backend element ID, not an inferred DOM XPath."""
    session_id = await page.session_id
    resolved = await page._client.send.DOM.resolveNode(
        {'backendNodeId':node.backend_node_id},session_id=session_id)
    object_id = resolved['object']['objectId']
    try:
        result = await page._client.send.Runtime.callFunctionOn({
            'objectId':object_id,'returnByValue':True,
            'functionDeclaration':'''function(){
                if(!this.isConnected)return null;
                const parts=[];let el=this;
                while(el && el.nodeType===1){
                    const tag=el.tagName.toLowerCase();
                    const siblings=el.parentElement ? [...el.parentElement.children].filter(x=>x.tagName===el.tagName) : [el];
                    parts.unshift(tag+'['+(siblings.indexOf(el)+1)+']');el=el.parentElement;
                }
                return '/'+parts.join('/');
            }'''
        },session_id=session_id)
        return {'xpath':result.get('result',{}).get('value'),
                'backend_node_id':node.backend_node_id}
    finally:
        await page._client.send.Runtime.releaseObject({'objectId':object_id},session_id=session_id)


async def remove_ui(page):
    await evaluate(page, '() => { window.__secondLookCleanup?.(); document.getElementById("second-look-host")?.remove(); return true; }')


async def mount(page, data: dict):
    await evaluate(page, (ASSETS / 'overlay.js').read_text(), data)


async def wait_decision(page, data: dict, capture=None) -> dict:
    await mount(page, data)
    if capture:
        await capture(page, 'Second Look: awaiting user', data['review']['title'])
    signature = None
    while True:
        # Human response has no automatic approval timeout.
        result = await evaluate(page, '() => window.__secondLookReply || null')
        if result:
            if capture:
                await capture(page, 'User response: ' + result.get('choice', 'unknown'),
                              result.get('correction', ''))
            await remove_ui(page)
            return result
        if capture:
            # Capture expansions and typed corrections, without generating a
            # duplicate screenshot on every polling tick during a long pause.
            current_ui = await evaluate(page, '''() => {
                const root=document.getElementById('second-look-host')?.shadowRoot;
                return root ? root.innerHTML + (root.querySelector('textarea')?.value || '') : '';
            }''')
            if signature is not None and current_ui != signature:
                await capture(page, 'Second Look: user inspecting or adjusting', data['review']['title'])
            signature = current_ui
        # If the page navigates, discard the proposal and re-observe it.
        current = await evaluate(page, '() => ({url:location.href, present:!!document.getElementById("second-look-host")})')
        if current['url'] != data['url'] or not current['present']:
            if data.get('recovery_active'):
                # Manual navigation is allowed during takeover. Restore only the
                # resume controls, never execute the old pending proposal.
                data = {**data, 'url': current['url']}
                await mount(page, data)
                continue
            return {'choice': 'stale', 'correction': ''}
        await asyncio.sleep(0.25)
