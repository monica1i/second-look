(data) => {
  window.__secondLookCleanup?.();
  document.getElementById('second-look-host')?.remove();
  window.__secondLookReply = null;
  const previous = document.activeElement;
  const host = document.createElement('div'); host.id = 'second-look-host';
  const dialogs = [...document.querySelectorAll('[role=dialog],dialog')].filter(e => e.getClientRects().length);
  (dialogs.at(-1) || document.documentElement).appendChild(host);
  const root = host.attachShadow({mode:'open'});
  const style = document.createElement('style'); style.textContent = `
    :host{all:initial;font:14px/1.45 system-ui,sans-serif;color:#19212c}
    *{box-sizing:border-box}.card{position:fixed;z-index:2147483647;right:16px;bottom:16px;width:440px;max-width:calc(100vw - 32px);max-height:calc(100vh - 32px);display:flex;flex-direction:column;background:#fff;border:1px solid #9aa5b4;border-radius:14px;box-shadow:0 8px 36px #15233233}
    .body{padding:20px;overflow:auto;min-height:0}.status{font-size:12px;color:#526174;margin-bottom:8px}h2{font-size:20px;line-height:1.3;margin:0 0 16px}p{margin:8px 0 12px}.comparison{display:grid;grid-template-columns:112px minmax(0,1fr);gap:10px;margin:12px 0}.key{color:#526174}.value{overflow-wrap:anywhere}.scope-note,.evidence{font-size:12px;color:#526174}blockquote{margin:8px 0;padding:10px 12px;background:#f2f5f8;border-left:3px solid #6d82a0;white-space:pre-wrap;overflow-wrap:anywhere}
    button,summary{font:inherit;cursor:pointer}button{border:1px solid #7c8da3;border-radius:7px;padding:9px 11px;color:#19212c;background:#fff}button:hover{background:#edf2f7}button:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #2268bd;outline-offset:3px}.primary{background:#195ea6;color:white;border-color:#195ea6}.primary:hover{background:#12477e}.footer{flex:none;padding:12px;border-top:1px solid #dce2e9;background:#fff;border-radius:0 0 14px 14px}.actions{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:stretch}.approve{display:flex;position:relative;min-width:0}.approve>.primary{flex:1;min-width:0;overflow-wrap:anywhere}.approve.split>.primary{border-radius:7px 0 0 7px}.scope{position:relative;display:flex;margin:0}.scope>summary{list-style:none;background:#195ea6;color:#fff;padding:9px 8px;border:1px solid #195ea6;border-left-color:#ffffff66;border-radius:0 7px 7px 0;display:flex;align-items:center}.scope>summary::-webkit-details-marker{display:none}.scope-panel{position:absolute;bottom:calc(100% + 8px);right:0;width:280px;max-width:calc(100vw - 56px);padding:12px;background:#fff;border:1px solid #9aa5b4;border-radius:9px;box-shadow:0 4px 20px #15233233;z-index:1}.scope-panel button{width:100%;text-align:left}.scope-panel p{margin:0 0 8px}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.chips button{font-size:13px}textarea{width:100%;min-height:76px;font:inherit;border:1px solid #7c8da3;border-radius:6px;padding:8px}label{display:block;margin:12px 0 5px}details{margin-top:14px}summary{color:#344c68}.trace{font-size:12px;max-height:180px;overflow:auto}.item{border-top:1px solid #e2e7ed;padding:8px 0}.hidden{display:none}.compact{width:320px}.compact .body{padding:12px 16px}.compact details{margin:0}
    @media(max-width:480px){.actions{grid-template-columns:1fr 1fr}.approve{grid-column:1/-1}.comparison{grid-template-columns:1fr;gap:4px}.value{margin-bottom:6px}}
  `; root.appendChild(style);
  const card = document.createElement('section'); card.className = 'card' + (data.review ? '' : ' compact'); root.appendChild(card);
  const body = document.createElement('div'); body.className = 'body'; card.appendChild(body);
  const add = (tag, text, parent=body) => { const el=document.createElement(tag);el.textContent=text;parent.appendChild(el);return el; };
  const button = (text, fn, parent=body) => { const b=add('button',text,parent);b.type='button';b.onclick=fn;return b; };
  const footer = () => { const f=add('div','',card);f.className='footer';const a=add('div','',f);a.className='actions';return a; };
  let highlighted = null, oldOutline = '', oldOffset = '';
  const highlightPath = data.review?.activity && data.activity_xpath ? data.activity_xpath : data.xpath;
  if (highlightPath) { try {
    highlighted = document.evaluate(highlightPath.startsWith('/') ? highlightPath : '/'+highlightPath,document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;
    if (highlighted) { oldOutline=highlighted.style.outline;oldOffset=highlighted.style.outlineOffset;highlighted.style.outline='3px solid #2268bd';highlighted.style.outlineOffset='3px'; }
  } catch {} }
  let selectedSuggestion = '', scope = null;
  const finish = (choice, correction='') => {
    // Feedback stays inside the paused card while the browser bridge captures it.
    const status = root.querySelector('.status');
    if (status) status.textContent = choice==='continue_activity' ? 'Activity selected · Checking page…' : choice==='proceed' ? 'Step selected · Checking page…' : choice==='adjust' ? 'Change received · Replanning…' : choice==='stop' ? 'Stopping task…' : 'Updating control…';
    root.querySelectorAll('button').forEach(b=>b.disabled=true);
    window.__secondLookReply={choice,correction,...(choice==='adjust' && selectedSuggestion ? {selected_suggestion:selectedSuggestion} : {})};
  };
  if (data.recovery) {
    card.setAttribute('role','dialog');card.setAttribute('aria-label','Second Look: recovery');
    add('div','Second Look · Automation paused').className='status';
    add('h2',data.recovery_active ? 'You have control' : 'Would you like to take over?');
    add('p',data.recovery_active ? 'Use the page to make changes. Resume when you are ready; the next step will still be checked.' : 'You have reached the same page or action repeatedly. This next action has not happened. You can use the page yourself or stop here.');
    const actions=footer();
    button(data.recovery_active ? 'Resume automation' : 'Take over',()=>finish(data.recovery_active ? 'resume' : 'takeover'),actions).className='primary';
    button('Stop task',()=>finish('stop'),actions);
  } else if (data.review) {
    const review=data.review, activity=review.activity;
    card.setAttribute('role','dialog');card.setAttribute('aria-modal','false');card.setAttribute('aria-label','Second Look: paused before acting');
    add('div','Second Look · Paused before acting').className='status';
    add('div','This step hasn’t happened yet.').className='evidence';
    add('h2',review.title);
    const comparison=add('div','');comparison.className='comparison';
    if(data.request){add('div','You asked',comparison).className='key';add('div',data.request,comparison).className='value';}
    add('div','This would add',comparison).className='key';
    // The exact persistent instruction is visible, not a hidden broader permission.
    add('div',activity ? activity.continue_instruction : review.explanation,comparison).className='value';
    if(activity?.fields.length){add('div','Using',comparison).className='key';add('div',activity.fields.join(', '),comparison).className='value';}
    if(activity)add('p','Allowing this covers the activity above. New consequences will still be checked.').className='scope-note';
    const why=add('details','');add('summary','Why this was flagged',why);
    if(activity)add('p',review.explanation,why);
    for(const quote of review.evidence || [])add('blockquote',quote,why);
    if(!review.evidence?.length)add('p','No page quotation could be confirmed. Check the page before deciding.',why);
    const adjust=add('div','');adjust.className='hidden';adjust.id='sl-change-plan';
    const label=add('label','How should the agent continue?',adjust);label.htmlFor='sl-correction';
    const area=add('textarea','',adjust);area.id='sl-correction';area.maxLength=1500;area.placeholder='Tell the agent what you want it to do';
    area.addEventListener('input',()=>{selectedSuggestion='';});
    const chips=add('div','',adjust);chips.className='chips';
    for(const text of review.adjustments || [])button(text,()=>{selectedSuggestion=text;area.value=text;area.focus();},chips);
    button('Apply change',()=>{if(area.value.trim())finish('adjust',area.value.trim());},adjust).className='primary';
    const actions=footer();
    const approve=add('div','',actions);approve.className='approve'+(activity?' split':'');
    button(activity ? (activity.approval_label || 'Allow & continue') : 'Allow this step',()=>finish(activity ? 'continue_activity' : 'proceed'),approve).className='primary';
    if(activity){
      scope=add('details','',approve);scope.className='scope';
      const toggle=add('summary','▾',scope);toggle.setAttribute('aria-label','Approval options');
      toggle.title='Choose how much to allow';
      const panel=add('div','',scope);panel.className='scope-panel';
      add('p',review.step_description || 'Only the pending step, without allowing the rest of this activity.',panel).className='evidence';
      button('Allow only this step',()=>finish('proceed'),panel);
    }
    const change=button('Change plan…',()=>{
      adjust.classList.toggle('hidden');change.setAttribute('aria-expanded',String(!adjust.classList.contains('hidden')));
      if(scope)scope.open=false;positionCard();
      if(!adjust.classList.contains('hidden')){area.focus({preventScroll:true});adjust.scrollIntoView({block:'nearest'});}
    },actions);change.setAttribute('aria-expanded','false');change.setAttribute('aria-controls',adjust.id);
    button('Stop task',()=>finish('stop'),actions);
  }
  const details=add('details','');add('summary','Review history',details);
  const trace=add('div','',details);trace.className='trace';
  for(const e of (data.trace || []).slice(-30).reverse())add('div',e,trace).className='item';
  if(!data.trace?.length)add('p','No reviewed actions yet.',trace);
  if(data.review){card.tabIndex=-1;card.focus();}
  function positionCard(){
    if(!data.review)return;
    const r=highlighted?.getBoundingClientRect() || {top:16,left:0,right:window.innerWidth};
    const width=Math.min(440,window.innerWidth-32);
    card.style.maxHeight=Math.max(120,window.innerHeight-32)+'px';
    card.style.right='16px';card.style.left='auto';
    if(r.right+width+32<window.innerWidth){card.style.right='auto';card.style.left=(r.right+16)+'px';}
    else if(r.left>width+32){card.style.right='auto';card.style.left=(r.left-width-16)+'px';}
    card.style.bottom='auto';card.style.top=Math.max(16,Math.min(r.top,window.innerHeight-card.offsetHeight-16))+'px';
  }
  const onKey=event=>{if(event.key==='Escape' && scope?.open){event.preventDefault();event.stopPropagation();scope.open=false;scope.querySelector('summary').focus();}};
  const onPointer=event=>{if(scope?.open && !event.composedPath().includes(scope))scope.open=false;};
  root.addEventListener('keydown',onKey);document.addEventListener('pointerdown',onPointer);
  positionCard();
  const observer=new ResizeObserver(positionCard);observer.observe(card);
  window.addEventListener('resize',positionCard);window.addEventListener('scroll',positionCard,true);
  window.__secondLookCleanup=()=>{observer.disconnect();window.removeEventListener('resize',positionCard);window.removeEventListener('scroll',positionCard,true);document.removeEventListener('pointerdown',onPointer);if(highlighted){highlighted.style.outline=oldOutline;highlighted.style.outlineOffset=oldOffset;}if(previous?.isConnected)previous.focus({preventScroll:true});host.remove();};
  return true;
}
