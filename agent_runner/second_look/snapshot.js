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
  const controlSelector='input,textarea,select,button,[role=checkbox],[role=button],a[href],[role=link]';
  const allNodes = [...document.querySelectorAll(controlSelector)].filter(visible);
  const nodes = allNodes.slice(0,160);
  const scopedNodes=root=>allNodes.filter(el=>root.contains(el));
  const dialogs = [...document.querySelectorAll('[role=dialog],dialog')].filter(visible);
  // textContent includes rendered terms below a scroll fold. It does not read
  // source files, hidden application state, or field contents.
  const textRoot = dialogs.length ? dialogs[dialogs.length-1] : document.body;
  const textCache=new WeakMap();
  const renderedText=root=>{
    if(textCache.has(root))return textCache.get(root);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const texts=[]; let n;
    while ((n=walker.nextNode())) {
      const p=n.parentElement;
      if (p && !own(p) && !p.closest('script,style,noscript,input,textarea,select') && visible(p)) {
        texts.push(n.textContent);
      }
    }
    const value=clean(texts.join(' '));textCache.set(root,value);return value;
  };
  const text=renderedText(textRoot);
  // Infer a local information-entry group when the page uses ordinary containers.
  // This observes boundaries; it does not identify a workflow or approve anything.
  const isDataField=el=>el.matches('input,textarea,select') && filled(el)!==null;
  const isEntryControl=el=>isDataField(el) || el.matches('input[type=checkbox],input[type=radio]');
  const fieldsIn=root=>scopedNodes(root).filter(isEntryControl);
  const actionButtons=root=>scopedNodes(root).filter(el=>el.matches('button,[role=button]') &&
    (clean(el.innerText) || el.getAttribute('type')==='submit'));
  const candidateFor=anchor=>{
    let node=anchor?.parentElement;
    for(let depth=0;node && depth<12 && !node.matches('body,html');depth++,node=node.parentElement){
      if(fieldsIn(node).length && actionButtons(node).length)return node;
    }
    return null;
  };
  const explicitRoots=[...document.querySelectorAll('form,[role=form],[role=dialog],dialog')].filter(visible);
  const inferredRoots=[...new Set(allNodes.filter(isEntryControl).map(candidateFor).filter(Boolean))]
    .filter(root=>!explicitRoots.some(explicit=>explicit.contains(root)));
  const formRoots=[...new Set([...explicitRoots,...inferredRoots])];
  const explicitFor=element?.closest('[role=dialog],dialog,form,[role=form]');
  const inferredFor=element ? inferredRoots.filter(root=>root.contains(element)) : [];
  const formRoot=explicitFor || inferredFor.sort((a,b)=>a.contains(b)?1:b.contains(a)?-1:0)[0] ||
    (!element && (dialogs.at(-1) || (formRoots.length===1?formRoots[0]:null)));
  const describeForm=(root,limit)=>{
    const formFields=scopedNodes(root).filter(el=>el.matches('input,textarea,select'));
    const dataFields=formFields.filter(isDataField);
    const options=formFields.filter(el=>el.matches('input[type=checkbox],input[type=radio]'));
    const fieldInfo=el=>({label:label(el),type:el.getAttribute('type')||el.tagName.toLowerCase(),name:el.getAttribute('name')||'',required:!!el.required,filled:filled(el)});
    const formText=renderedText(root);
    const ambiguous=!explicitRoots.includes(root) && formRoots.some(other=>other!==root && root.contains(other));
    return {xpath:xpath(root),title:clean(root.querySelector('h1,h2,h3,[role=heading]')?.innerText),
      association:explicitRoots.includes(root)?'explicit':'inferred',ambiguous,
      text:formText.slice(0,limit),truncated:formText.length>limit || dataFields.length>40 || options.length>40,
      fields:dataFields.slice(0,40).map(fieldInfo),
      options:options.slice(0,40).map(el=>({...describe(el),xpath:xpath(el)})),
      buttons:scopedNodes(root).filter(el=>el.matches('button,[role=button]')).map(label),
      destination:root.tagName==='FORM'?root.getAttribute('action'):null,
      selected_options:options.filter(el=>el.checked).map(label),
      target_member:!!element && root.contains(element),
      target_kind:element?.closest('button,[role=button]')?'button':element?.matches('input,textarea,select')?'field':'other'};
  };
  const formContext=formRoot?describeForm(formRoot,16000):null;
  const formGroups=formRoots.slice(0,8).map(root=>describeForm(root,2000));

  // Associate controls with repeated rows/cards using only rendered DOM structure.
  // No product/risk words, event-handler inspection, removal projection or policy.
  const substantive=node=>{
    if(!scopedNodes(node).length)return false;
    if(node.querySelector('h1,h2,h3,h4,[role=heading],img[alt]'))return true;
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);const parts=[];let n;
    while((n=walker.nextNode())){const p=n.parentElement;if(p && visible(p) && !own(p) &&
      !p.closest('button,[role=button],input,textarea,select,script,style'))parts.push(n.textContent);}
    return clean(parts.join(' ')).length>=12;
  };
  const groupFor=anchor=>{
    let node=anchor?.parentElement;
    for(let depth=0;node && depth<12 && !node.matches('body,html');depth++,node=node.parentElement){
      if(!substantive(node))continue;
      if(node.matches('li,tr,article,[role=listitem],[role=row]'))return node;
      const peers=[...node.parentElement.children].filter(s=>s.tagName===node.tagName && visible(s) && substantive(s));
      if(peers.length>1)return node;
    }
    return null;
  };
  const roots=[...new Set(nodes.map(groupFor).filter(Boolean))];
  const groupRoots=roots.filter(root=>!roots.some(other=>other!==root && root.contains(other)) &&
    (root.matches('li,tr,article,[role=listitem],[role=row]') || roots.some(other=>other!==root && other.parentElement===root.parentElement)));
  const targetGroupRoot=element ? groupRoots.find(root=>root.contains(element)) : null;
  const describeGroup=root=>{
    const groupText=renderedText(root), members=scopedNodes(root);
    return {xpath:xpath(root),parent_xpath:xpath(root.parentElement),association:'inferred_dom_group',
      title:clean(root.querySelector('h1,h2,h3,h4,[role=heading]')?.innerText) ||
        root.querySelector('img[alt]')?.getAttribute('alt') || root.getAttribute('aria-label') || null,
      text:groupText.slice(0,1800),controls:members.slice(0,20).map(el=>({...describe(el),xpath:xpath(el)})),
      truncated:groupText.length>1800 || members.length>20};
  };
  const contentGroups=groupRoots.slice(0,12).map(describeGroup);
  const targetGroup=targetGroupRoot?describeGroup(targetGroupRoot):null;
  const siblingRoots=targetGroupRoot?groupRoots.filter(root=>root!==targetGroupRoot && root.parentElement===targetGroupRoot.parentElement):[];
  const siblings=siblingRoots.slice(0,8).map(describeGroup);
  const controls=nodes.map(el=>({...describe(el),xpath:xpath(el),
    group_xpath:groupRoots.find(root=>root.contains(el))?xpath(groupRoots.find(root=>root.contains(el))):null}));
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
    form_groups:formGroups,form_groups_truncated:formRoots.length>8,
    target_group:targetGroup,sibling_groups:siblings,sibling_groups_truncated:siblingRoots.length>8,content_groups:contentGroups,
    content_groups_truncated:groupRoots.length>12,controls_truncated:allNodes.length>160,
    action_effect:effect,
    context:clean(near?.innerText).slice(0,2500), controls, text:text.slice(0,24000),
    text_truncated:text.length>24000, unsupported_frames:document.querySelectorAll('iframe').length,
    target_xpath:target.xpath || null};
}
