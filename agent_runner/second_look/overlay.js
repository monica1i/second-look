(data) => {
  window.__secondLookCleanup?.();
  document.getElementById('second-look-host')?.remove();
  window.__secondLookReply=null;
  const host=document.createElement('div'); host.id='second-look-host';
  const dialogs=[...document.querySelectorAll('[role=dialog],dialog')].filter(e=>e.getClientRects().length);
  // Place inside the active dialog so its focus trap also contains our controls.
  (dialogs.at(-1)||document.documentElement).appendChild(host);
  const root=host.attachShadow({mode:'open'});
  const style=document.createElement('style'); style.textContent=`
    :host{all:initial;font:15px/1.45 system-ui,sans-serif;color:#19212c}
    *{box-sizing:border-box} .card{position:fixed;z-index:2147483647;right:20px;bottom:20px;width:380px;max-width:calc(100vw - 32px);max-height:80vh;overflow:auto;background:white;border:1px solid #9aa5b4;border-radius:14px;box-shadow:0 8px 36px #15233233;padding:20px}
    .status{font-size:12px;color:#526174;margin-bottom:8px}h2{font-size:20px;line-height:1.25;margin:0 0 10px}p{margin:8px 0 14px}blockquote{margin:8px 0 16px;padding:10px 12px;background:#f2f5f8;border-left:3px solid #6d82a0;font-size:14px;white-space:pre-wrap}
    button{font:inherit;cursor:pointer;border:1px solid #7c8da3;border-radius:7px;padding:8px 11px;color:#19212c;background:white}button:hover{background:#edf2f7}button:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #2268bd;outline-offset:3px}.actions{display:flex;gap:8px;flex-wrap:wrap}.chips{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.chips .evidence{width:100%}.chips button{font-size:13px}textarea{width:100%;min-height:74px;font:inherit;border:1px solid #7c8da3;border-radius:6px;padding:8px}label{display:block;margin:10px 0 5px}.evidence{font-size:12px;color:#526174}details{margin-top:14px}summary{cursor:pointer}.trace{font-size:13px;max-height:180px;overflow:auto}.item{border-top:1px solid #e2e7ed;padding:8px 0}.hidden{display:none}.compact{padding:10px 15px;width:auto;max-width:350px}
  `; root.appendChild(style);
  const card=document.createElement('section'); card.className='card'+(data.review?'':' compact'); root.appendChild(card);
  const add=(tag,text,parent=card)=>{const el=document.createElement(tag);el.textContent=text;parent.appendChild(el);return el};
  const button=(text,fn,parent)=>{const b=add('button',text,parent);b.type='button';b.onclick=fn;return b};
  let highlighted=null, oldOutline='',oldOffset='';
  if(data.xpath){try{highlighted=document.evaluate(data.xpath.startsWith('/')?data.xpath:'/'+data.xpath,document,null,XPathResult.FIRST_ORDERED_NODE_TYPE,null).singleNodeValue;if(highlighted){oldOutline=highlighted.style.outline;oldOffset=highlighted.style.outlineOffset;highlighted.style.outline='3px solid #2268bd';highlighted.style.outlineOffset='3px';}}catch{}}
  const previous=document.activeElement;
  let selectedSuggestion='';
  const finish=(choice,correction='')=>{window.__secondLookReply={choice,correction,...(choice==='adjust'&&selectedSuggestion?{selected_suggestion:selectedSuggestion}:{})};};
  if(data.recovery){
    card.setAttribute('role','dialog');card.setAttribute('aria-label','Second Look: recovery');
    add('div','Second Look · Automation paused').className='status';
    add('h2',data.recovery_active?'You have control':'Would you like to take over?');
    add('p',data.recovery_active?
      'Use the page to make changes. Resume when you are ready; the next step will still be checked.':
      'You have reached the same page or action repeatedly. This next action has not happened. You can use the page yourself or stop here.');
    const actions=add('div','');actions.className='actions';
    button(data.recovery_active?'Resume automation':'Take over',()=>finish(data.recovery_active?'resume':'takeover'),actions);
    button('Stop task',()=>finish('stop'),actions);
    card.tabIndex=-1;card.focus();
  }else if(data.review){
    card.setAttribute('role','dialog');card.setAttribute('aria-modal','false');card.setAttribute('aria-label','Second Look: agent paused');
    add('div','Second Look · Action paused').className='status';
    add('h2',data.review.title);add('p',data.review.explanation);
    add('p','This has not happened yet.').className='evidence';
    if(data.review.evidence?.length){
      add('div','Page says:').className='evidence';
      add('blockquote',data.review.evidence[0]);
      if(data.review.evidence.length>1){const more=add('details','');add('summary','More evidence',more);for(const q of data.review.evidence.slice(1))add('blockquote',q,more);}
    }
    const actions=add('div','');actions.className='actions';
    button('Proceed once',()=>finish('proceed'),actions);
    const adjust=add('div','');adjust.className='hidden';
    const adjustButton=button('Adjust',()=>{adjust.classList.toggle('hidden');adjustButton.setAttribute('aria-expanded',String(!adjust.classList.contains('hidden')));positionCard();if(!adjust.classList.contains('hidden'))area.focus({preventScroll:true});},actions);adjustButton.setAttribute('aria-expanded','false');
    button('Stop task',()=>finish('stop'),actions);
    const lbl=add('label','How should the agent continue?',adjust);lbl.htmlFor='sl-correction';
    const area=add('textarea','',adjust);area.id='sl-correction';area.maxLength=1500;
    area.placeholder='Tell the agent what you want it to do';
    area.addEventListener('input',()=>{selectedSuggestion='';});
    const chips=add('div','',adjust);chips.className='chips';
    if(data.review.adjustments?.length)add('div','Or choose a direction:',chips).className='evidence';
    for(const text of data.review.adjustments||[])button(text,()=>{selectedSuggestion=text;area.value=text;area.focus();},chips);
    const send=button('Apply correction',()=>{if(area.value.trim())finish('adjust',area.value.trim());},adjust);
    send.title='The agent will propose a new action for review';
    // Focus the neutral dialog rather than preselecting an action.
    card.tabIndex=-1;card.focus();
  }
  const details=add('details','');add('summary','Second Look trace',details);
  const trace=add('div','',details);trace.className='trace';
  for(const e of (data.trace||[]).slice(-30).reverse())add('div',e,trace).className='item';
  if(!data.trace?.length)add('p','No reviewed actions yet.',trace);
  function positionCard(){
    if(!data.review)return;
    const anchor=highlighted;
    const r=anchor?.getBoundingClientRect() || {top:16,left:0,right:window.innerWidth};
    const width=Math.min(380,window.innerWidth-32);
    card.style.maxHeight=Math.max(120,window.innerHeight-32)+'px';
    card.style.right='16px';card.style.left='auto';
    if(r.right+width+32<window.innerWidth){card.style.right='auto';card.style.left=(r.right+16)+'px';}
    else if(r.left>width+32){card.style.right='auto';card.style.left=(r.left-width-16)+'px';}
    card.style.bottom='auto';card.style.top=Math.max(16,Math.min(r.top,window.innerHeight-card.offsetHeight-16))+'px';
    const actual=card.getBoundingClientRect();
    if(actual.top<16)card.style.top=(parseFloat(card.style.top)+16-actual.top)+'px';
    else if(actual.bottom>window.innerHeight-16)card.style.top=(parseFloat(card.style.top)-(actual.bottom-window.innerHeight+16))+'px';
  }
  positionCard();
  const resizeObserver=new ResizeObserver(positionCard);resizeObserver.observe(card);
  window.addEventListener('resize',positionCard);
  window.__secondLookCleanup=()=>{resizeObserver.disconnect();window.removeEventListener('resize',positionCard);if(highlighted){highlighted.style.outline=oldOutline;highlighted.style.outlineOffset=oldOffset;}if(previous?.isConnected)previous.focus({preventScroll:true});host.remove();};
  return true;
}
