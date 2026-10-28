(target) => {
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const own = el => !!el?.closest?.('#second-look-host');
  const visible = el => { const s = getComputedStyle(el); return !own(el) && s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0; };
  let element = null;
  if (target.xpath) {
    try { element = document.evaluate(target.xpath.startsWith('/') ? target.xpath : '/' + target.xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; } catch {}
  }
  if (!element && target.selector) { try { element=document.querySelector(target.selector); } catch {} }
  if (!element && target.coordinate_x != null) element = document.elementFromPoint(target.coordinate_x, target.coordinate_y);
  // A click on a label, MUI span or SVG toggles its associated native input.
  // Report that input's actual state rather than the decorative wrapper's state.
  let control = null;
  if (element) {
    if (element.matches('input[type=checkbox],input[type=radio]')) control=element;
    const labelElement=element.closest('label');
    if (!control && labelElement) control=labelElement.control || labelElement.querySelector('input[type=checkbox],input[type=radio]');
    if (!control && element.matches('[role=checkbox]')) control=element;
  }
  const label = el => clean(el.labels ? [...el.labels].map(x => x.innerText).join(' ') : '') || clean(el.getAttribute('aria-label')) || (el.matches('input,textarea,select')?'':clean(el.innerText)) || clean(el.getAttribute('placeholder'));
  // Only presence is exported: never contents or lengths, including passwords.
  const filled = el => el.matches('textarea,select') || (el.matches('input') && !['checkbox','radio','button','submit','reset','hidden','file','range','color'].includes(el.type)) ? el.value !== '' : null;
  const describe = el => el ? ({tag:el.tagName.toLowerCase(), type:el.getAttribute('type'), role:el.getAttribute('role'), label:label(el).slice(0,700), icons:[...el.querySelectorAll('svg[data-testid],svg title')].map(s=>s.getAttribute('data-testid')||s.textContent), checked:el.matches('input[type=checkbox],input[type=radio]') ? el.checked : el.getAttribute('aria-checked'), filled:filled(el), disabled:!!el.disabled, id:el.id || null}) : null;
  const xpath = el => {
    const parts=[];
    while(el && el.nodeType===1){const siblings=el.parentElement?[...el.parentElement.children].filter(x=>x.tagName===el.tagName):[el];parts.unshift(el.tagName.toLowerCase()+'['+(siblings.indexOf(el)+1)+']');el=el.parentElement;}
    return '/'+parts.join('/');
  };
  const nodes = [...document.querySelectorAll('input,textarea,select,button,[role=checkbox],[role=button]')].filter(visible).slice(0,160);
  const controls = nodes.map(el=>({...describe(el),xpath:xpath(el)}));
  const dialogs = [...document.querySelectorAll('[role=dialog],dialog')].filter(visible);
  // textContent includes rendered terms below a scroll fold. It does not read
  // source files, hidden application state, or field contents.
  const textRoot = dialogs.length ? dialogs[dialogs.length-1] : document.body;
  const renderedText=root=>{
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const texts=[]; let n;
    while ((n=walker.nextNode())) {
      const p=n.parentElement;
      if (p && !own(p) && !p.closest('script,style,noscript,input,textarea,select') && visible(p)) {
        texts.push(n.textContent);
      }
    }
    return clean(texts.join(' '));
  };
  const text=renderedText(textRoot);
  // Capture the active form/dialog separately. Values are deliberately excluded.
  const formRoot=element?.closest('[role=dialog],dialog') || element?.closest('form') || dialogs.at(-1) ||
    [...document.querySelectorAll('form')].filter(visible).at(-1);
  let formContext=null;
  if(formRoot){
    const formFields=[...formRoot.querySelectorAll('input,textarea,select')].filter(visible);
    const fieldInfo=el=>({label:label(el),type:el.getAttribute('type')||el.tagName.toLowerCase(),name:el.getAttribute('name')||'',required:!!el.required,filled:filled(el)});
    const formText=renderedText(formRoot);
    formContext={xpath:xpath(formRoot),title:clean(formRoot.querySelector('h1,h2,h3,[role=heading]')?.innerText),
      text:formText.slice(0,16000),truncated:formText.length>16000 || formFields.length>40,
      fields:formFields.slice(0,40).map(fieldInfo),
      buttons:[...formRoot.querySelectorAll('button,[role=button]')].filter(visible).map(label),
      destination:formRoot.tagName==='FORM'?formRoot.getAttribute('action'):null,
      selected_options:formFields.filter(el=>el.matches('input[type=checkbox],input[type=radio]') && el.checked).map(label),
      target_member:!!element && formRoot.contains(element),
      target_kind:element?.closest('button,[role=button]')?'button':element?.matches('input,textarea,select')?'field':'other'};
  }
  const near = element?.closest('label') || element?.parentElement;
  const controlDescription=describe(control);
  const checked=controlDescription?.checked;
  const knownChecked=checked===true || checked===false || checked==='true' || checked==='false';
  const before=knownChecked ? checked===true || checked==='true' : null;
  let effect=control && knownChecked ? {
    kind:control.getAttribute('type')==='radio'?'select_radio':'toggle_checkbox',
    label:controlDescription.label, checked_before:before,
    checked_after:control.getAttribute('type')==='radio'?true:!before
  } : null;
  return {url:location.href, title:document.title, target:describe(control || element), target_found:!!element,
    form_context:formContext,
    action_effect:effect,
    context:clean(near?.innerText).slice(0,2500), controls, text:text.slice(0,24000),
    text_truncated:text.length>24000, unsupported_frames:document.querySelectorAll('iframe').length,
    target_xpath:target.xpath || null};
}
