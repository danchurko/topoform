/* Viewer glue for Cytoscape.js + cytoscape-elk. Original skill code, MIT. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const model = JSON.parse($('diagram-model').textContent);
const icons = JSON.parse($('diagram-icons').textContent);
const credits = JSON.parse($('diagram-credits').textContent);
const freeze = o => { if (o && typeof o === 'object') { Object.freeze(o); Object.values(o).forEach(freeze); } return o; };
freeze(model);
const api = window.__DIAGRAM__ = { version:'1.0.0', model, state:'loading', errors:[], layoutRuns:0, cy:null };
let currentView = 'all', currentKind = 'all', selectedId = null, busy = false, failed = false;
let pendingFailure = null;
const defaultInspector = $('inspector').cloneNode(true);
const palette = ['#4862b2','#24857c','#a97537','#895cb0','#497c9b','#91734f'];
const kinds = [...new Set(model.nodes.filter(n => n.kind !== 'group').map(n => n.kind || 'element'))].sort();
const colors = new Map(kinds.map((kind,i) => [kind,palette[i % palette.length]]));
const nmap = new Map(model.nodes.map(n => [n.id,n]));
const emap = new Map(model.edges.map(e => [e.id,e]));
const el = (tag,text,cls) => { const e=document.createElement(tag); if(text!==undefined)e.textContent=text; if(cls)e.className=cls; return e; };
const on = (id,fn) => $(id).addEventListener('click',fn);
function setStatus(text,error=false){ $('status').textContent=text; $('status').classList.toggle('error',error); }
function showFailure(reason){
  const text=String(reason && reason.message || reason);
  api.errors.push(text); api.state='error'; failed=true; busy=false;
  setStatus('Layout failed. Reload after correcting the model. '+text,true);
  document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=true);
  if(pendingFailure){const reject=pendingFailure;pendingFailure=null;reject(new Error(text));}
}
window.addEventListener('unhandledrejection',event=>{event.preventDefault();showFailure(event.reason);});
window.addEventListener('error',event=>showFailure(event.error || event.message));
$('title').textContent=model.title;
$('description').textContent=model.description || '';
$('node-count').textContent=String(model.nodes.filter(n=>n.kind!=='group').length);
$('edge-count').textContent=String(model.edges.length);
$('direction').value=model.layout?.direction || 'RIGHT';
for(const v of model.views || []) { const opt=el('option',v.label);opt.value=v.id;$('view').append(opt); }
for(const kind of [...new Set(model.edges.map(e=>e.kind||'flow'))].sort()){const opt=el('option',kind);opt.value=kind;$('edge-kind').append(opt);}
for(const [kind,color] of colors){const item=el('span');const sw=el('i',undefined,'swatch');sw.style.background=color;item.append(sw,document.createTextNode(kind));$('legend').append(item);}
if(model.nodes.some(n=>n.kind==='group'))$('legend').append(el('span','Dashed box = containment'));
$('legend').append(el('span','Arrow = authored direction','hint'));

// Labels sit inside explicitly measured leaf cards. ELK receives these dimensions.
const measure=document.createElement('canvas').getContext('2d');
measure.font='600 14px system-ui';
function lines(text,width){
  const result=[];
  for(const para of text.split('\n')){
    let line='';
    for(const char of para){if(measure.measureText(line+char).width>width && line){result.push(line);line='';}line+=char;}
    result.push(line);
  }
  return result;
}
const nodes=model.nodes.map(n=>{
  const width=n.kind==='group'?180:188;
  const displayLabel=lines(n.label,160).join('\n');
  const height=Math.max(86,displayLabel.split('\n').length*19+(n.icon?46:26));
  return {data:{id:n.id,label:n.label,displayLabel,kind:n.kind||'element',...(n.parent?{parent:n.parent}:{}),width,height,icon:icons[n.icon]||null,color:colors.get(n.kind||'element')||'#7c8899'}};
});
const routeTurns=['32%','41%','50%','59%','68%'];
const routeLabelOffsets=[-28,-14,0,14,28];
const edges=model.edges.map((e,i)=>({data:{id:e.id,source:e.source,target:e.target,label:e.label||'',kind:e.kind||'flow',directed:e.directed!==false,routeTurn:routeTurns[i%routeTurns.length],routeLabelOffset:routeLabelOffsets[i%routeLabelOffsets.length]}}));
const cy=api.cy=cytoscape({
  container:$('cy'),elements:{nodes,edges},layout:{name:'preset'},
  minZoom:0.03,maxZoom:3.5,pixelRatio:Math.min(window.devicePixelRatio||1,2),
  autoungrabify:true,boxSelectionEnabled:false,
  style:[
    {selector:'node',style:{'shape':'round-rectangle','width':'data(width)','height':'data(height)','background-color':'#ffffff','border-width':1.7,'border-color':'data(color)','label':'data(displayLabel)','font-family':'system-ui','font-size':14,'font-weight':600,'color':'#203047','text-valign':'center','text-halign':'center','text-wrap':'wrap','text-max-width':164,'text-justification':'center','text-margin-y':0,'padding':0,'overlay-opacity':0}},
    {selector:'node[icon]',style:{'background-image':n=>n.data('icon')||'none','background-fit':'none','background-width':23,'background-height':23,'background-position-x':'50%','background-position-y':'13px','text-margin-y':16}},
    {selector:'node:parent',style:{'shape':'round-rectangle','background-color':'#e8edf7','background-opacity':0.28,'border-color':'#a9b7cc','border-width':1.2,'border-style':'dashed','padding':30,'label':'data(label)','font-size':12,'font-weight':600,'color':'#526783','text-valign':'top','text-halign':'center','text-margin-y':-9,'compound-sizing-wrt-labels':'include','background-image':'none','text-wrap':'wrap','text-max-width':300}},
    {selector:'edge',style:{'curve-style':'round-taxi','taxi-direction':'auto','taxi-turn':'data(routeTurn)','taxi-turn-min-distance':32,'line-color':'#96a5bb','target-arrow-color':'#96a5bb','target-arrow-shape':e=>e.data('directed')?'triangle':'none','width':1.6,'arrow-scale':0.85,'label':'data(label)','font-family':'system-ui','font-size':11,'color':'#526277','text-background-color':'#fcfcfd','text-background-opacity':0.95,'text-background-padding':4,'text-background-shape':'roundrectangle','text-wrap':'wrap','text-max-width':Math.max(44,Math.min(120,(model.layout?.layerSpacing||120)-20)),'text-rotation':'none','text-margin-y':'data(routeLabelOffset)','loop-direction':'-45deg','loop-sweep':'55deg','overlay-opacity':0}},
    {selector:'edge:loop',style:{'curve-style':'bezier','control-point-step-size':150,'loop-direction':'0deg','loop-sweep':'65deg'}},
    {selector:'edge[kind="event"], edge[kind="async"]',style:{'line-style':'dashed'}},
    {selector:'.dim',style:{'opacity':0.17}},
    {selector:'node.highlight',style:{'border-width':3,'border-color':'#304ba5'}},
    {selector:'edge.highlight',style:{'line-color':'#3955af','target-arrow-color':'#3955af','width':2.7}},
    {selector:'.hidden',style:{'display':'none'}}
  ]
});

function clearFocus(){cy.elements().removeClass('dim highlight');selectedId=null;$('inspector').replaceChildren(...[...defaultInspector.childNodes].map(n=>n.cloneNode(true)));}
function ancestors(ids){const out=new Set(ids);for(const id of ids){let n=nmap.get(id);while(n?.parent){out.add(n.parent);n=nmap.get(n.parent);}}return out;}
function viewNodes(){
  const v=(model.views||[]).find(v=>v.id===currentView);
  if(!v)return new Set(model.nodes.map(n=>n.id));
  // Selecting a group explicitly includes its descendants; ancestors are added only for context.
  const desired=new Set(v.nodeIds);let changed=true;
  while(changed){changed=false;for(const n of model.nodes)if(n.parent&&desired.has(n.parent)&&!desired.has(n.id)){desired.add(n.id);changed=true;}}
  return ancestors(desired);
}
function applyFilter(){
  clearFocus();const ids=viewNodes();const v=(model.views||[]).find(v=>v.id===currentView);
  cy.batch(()=>{
    cy.nodes().forEach(n=>n.toggleClass('hidden',!ids.has(n.id())));
    cy.edges().forEach(e=>e.toggleClass('hidden',!ids.has(e.data('source'))||!ids.has(e.data('target'))||(currentKind!=='all'&&e.data('kind')!==currentKind)||Boolean(v?.edgeKinds&&!v.edgeKinds.includes(e.data('kind')))));
  });
  // Flush lazy styles before visibility queries, including headless checks in the same turn.
  cy.elements().forEach(e=>e.style('display'));
  const count=cy.nodes(':visible').filter(n=>!n.isParent()).length;
  $('empty').hidden=count>0;
  if(!busy&&!failed)setStatus(`${count} visible elements · ${cy.edges(':visible').length} relationships`);
}
function focus(id,mode='neighbors'){
  const n=cy.getElementById(id);if(!n.length||!n.visible())return;
  const ids=new Set([id]), edgeIds=new Set();
  if(n.isNode()){
    let frontier=[id];
    while(frontier.length){const next=[];for(const cur of frontier){cy.edges(':visible').forEach(e=>{
      const s=e.data('source'),t=e.data('target'),dir=e.data('directed');let peer=null;
      if(mode==='neighbors'){if(s===cur)peer=t;else if(t===cur)peer=s;}
      if(mode==='upstream'){if(t===cur)peer=s;else if(!dir&&s===cur)peer=t;}
      if(mode==='downstream'){if(s===cur)peer=t;else if(!dir&&t===cur)peer=s;}
      if(peer!==null){edgeIds.add(e.id());if(!ids.has(peer)){ids.add(peer);next.push(peer);}}
    });}frontier=mode==='neighbors'?[]:next;}
  }else{ids.add(n.data('source'));ids.add(n.data('target'));edgeIds.add(id);}
  const visibleIds=ancestors(ids);
  cy.batch(()=>{cy.elements().removeClass('dim highlight');cy.elements(':visible').forEach(e=>{if(!visibleIds.has(e.id())&&!edgeIds.has(e.id()))e.addClass('dim');});n.addClass('highlight');edgeIds.forEach(e=>cy.getElementById(e).addClass('highlight'));});
  selectedId=id;inspect(id,mode);
}
function appendDetail(dl,key,value){dl.append(el('dt',key),el('dd',typeof value==='object'?JSON.stringify(value,null,2):String(value)));}
function inspect(id,mode){
  const data=nmap.get(id)||emap.get(id);if(!data)return;
  const panel=$('inspector');panel.replaceChildren(el('span',data.kind||'element','badge'),el('h2',data.label||id));
  if(data.description)panel.append(el('p',data.description));
  const dl=el('dl');appendDetail(dl,'Stable ID',id);
  if(data.source){appendDetail(dl,'From',nmap.get(data.source)?.label||data.source);appendDetail(dl,'To',nmap.get(data.target)?.label||data.target);appendDetail(dl,'Direction',data.directed===false?'Undirected':'Source → target');}
  if(data.parent)appendDetail(dl,'Contained in',nmap.get(data.parent)?.label||data.parent);
  if(data.evidence)appendDetail(dl,'Evidence',data.evidence);
  if(data.tags?.length)appendDetail(dl,'Tags',data.tags.join(', '));
  for(const [key,value] of Object.entries(data.metadata||{}))appendDetail(dl,key,value);
  panel.append(dl);
  for(const link of data.links||[]){const p=el('p'),a=el('a',link.label);a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';p.append(a);panel.append(p);}
  if(nmap.has(id)&&data.kind!=='group'){
    const bar=el('div',undefined,'focus-actions');
    for(const [label,m] of [['Neighbors','neighbors'],['Upstream','upstream'],['Downstream','downstream']]){const b=el('button',label);b.addEventListener('click',()=>focus(id,m));bar.append(b);}
    panel.append(bar,el('p',`Highlight: ${mode||'neighbors'}. Authored relationships in this view only; not a live impact analysis.`,'secondary'));
  }
}
function fit(){if(cy.nodes(':visible').length)cy.fit(cy.elements(':visible'),48);}
async function arrange(elements){
  const spacing=model.layout?.spacing||65,layerSpacing=model.layout?.layerSpacing||120;
  const elk={'elk.algorithm':'layered','elk.direction':$('direction').value,'elk.hierarchyHandling':'INCLUDE_CHILDREN','elk.edgeRouting':'ORTHOGONAL','elk.spacing.nodeNode':spacing,'elk.spacing.edgeNode':Math.max(32,spacing/2),'elk.spacing.edgeEdge':24,'elk.layered.spacing.nodeNodeBetweenLayers':layerSpacing,'elk.layered.spacing.edgeNodeBetweenLayers':Math.max(36,layerSpacing/3),'elk.layered.spacing.edgeEdgeBetweenLayers':24,'elk.padding':'[top=40,left=40,bottom=40,right=40]','elk.randomSeed':17};
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Layout exceeded 15 seconds. Split the diagram or use an explicitly configured worker integration.')),15000);
    const success=()=>{clearTimeout(timer);pendingFailure=null;resolve();};
    pendingFailure=e=>{clearTimeout(timer);reject(e);};
    elements.layout({name:'elk',fit:false,animate:false,nodeDimensionsIncludeLabels:false,nodeLayoutOptions:node=>node.isParent()?{...elk,'elk.padding':'[top=50,left=36,bottom=36,right=36]'}:{},elk,stop:success}).run();
  });
}
async function layout(){
  if(busy||failed)return false;
  busy=true;api.state='layout';api.layoutRuns++;setStatus('Arranging elements with ELK…');
  document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=true);
  cy.elements().removeClass('dim highlight');
  try{
    const visible=cy.elements(':visible');
    if(visible.nodes().length){
      await arrange(visible);
      const bad=cy.nodes().filter(n=>!Number.isFinite(n.position('x'))||!Number.isFinite(n.position('y')));
      if(bad.length)throw new Error('Non-finite node coordinates.');
    }
    busy=false;api.state='ready';applyFilter();fit();return true;
  }catch(error){showFailure(error);return false;}
  finally{pendingFailure=null;if(!failed)document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=false);}
}
function download(blob,name){const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);}
async function exportPNG(all=false){
  if(busy||failed)throw new Error('The diagram must be ready before export.');
  const states=cy.elements().map(e=>({id:e.id(),classes:e.classes()}));
  const positions=new Map(cy.nodes().filter(n=>!n.isParent()).map(n=>[n.id(),{x:n.position('x'),y:n.position('y')}]));
  const viewport={zoom:cy.zoom(),pan:cy.pan()};
  busy=true;api.state='export';document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=true);
  cy.elements().removeClass('dim highlight');if(all)cy.elements().removeClass('hidden');
  try{
    if(!cy.nodes(':visible').length)throw new Error('This view has no elements to export.');
    if(all)await arrange(cy.elements());
    cy.fit(cy.elements(':visible'),48);
    const uri=cy.png({full:false,bg:'#fcfcfd',maxWidth:1752,maxHeight:1040});
    const img=new Image();img.src=uri;await img.decode();
    const bounds=cy.elements(':visible').renderedBoundingBox({includeLabels:true,includeOverlays:false}),scaleX=img.width/cy.width(),scaleY=img.height/cy.height(),padding=24;
    const sx=Math.max(0,(bounds.x1-padding)*scaleX),sy=Math.max(0,(bounds.y1-padding)*scaleY),sw=Math.min(img.width-sx,(bounds.w+padding*2)*scaleX),sh=Math.min(img.height-sy,(bounds.h+padding*2)*scaleY);
    const canvas=document.createElement('canvas');canvas.width=Math.max(Math.ceil(sw)+48,800);canvas.height=Math.ceil(sh)+160;
    const ctx=canvas.getContext('2d');ctx.fillStyle='#fcfcfd';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,sx,sy,sw,sh,(canvas.width-sw)/2,88,sw,sh);
    ctx.fillStyle='#203047';ctx.font='600 23px system-ui';ctx.fillText(model.title,24,38,canvas.width-48);
    ctx.font='13px system-ui';ctx.fillStyle='#637187';ctx.fillText(all?'All authored elements':'Current view (filters applied)',24,60);
    // Keep attribution attached to raster exports as well as HTML.
    const attribution=[...new Set(credits.map(c=>`${c.attribution} (${c.license})`))].join('; ');
    ctx.font='11px system-ui';const label=attribution?`Icons: ${attribution} — see HTML credits for sources`:'Generated with Cytoscape.js + ELK.js';
    ctx.fillText(label,24,canvas.height-18,canvas.width-48);
    return await new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('PNG encoding failed.')),'image/png'));
  }finally{
    cy.batch(()=>{cy.nodes().filter(n=>!n.isParent()).positions(n=>positions.get(n.id()));states.forEach(s=>cy.getElementById(s.id).classes(s.classes));});
    cy.viewport(viewport);pendingFailure=null;busy=false;if(!failed){api.state='ready';document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=false);setStatus(`${cy.nodes(':visible').filter(n=>!n.isParent()).length} visible elements · ${cy.edges(':visible').length} relationships`);}
  }
}
function table(headers,rows){const t=el('table'),head=el('thead'),tr=el('tr');headers.forEach(h=>tr.append(el('th',h)));head.append(tr);t.append(head);const body=el('tbody');rows.forEach(row=>{const r=el('tr');row.forEach(v=>r.append(el('td',v)));body.append(r);});t.append(body);return t;}
$('text-content').append(el('h3','Elements'),table(['ID','Label','Kind','Parent'],model.nodes.map(n=>[n.id,n.label,n.kind||'element',n.parent||'—'])),el('h3','Relationships'),table(['From','To','Label','Kind','Direction'],model.edges.map(e=>[nmap.get(e.source)?.label,nmap.get(e.target)?.label,e.label||'—',e.kind||'flow',e.directed===false?'Undirected':'Directed'])));
for(const c of credits){const p=el('p',`${c.id} — ${c.attribution}; ${c.license}. ${c.modifications||''} `),a=el('a','Source');a.href=c.source;a.rel='noopener noreferrer';a.target='_blank';p.append(a);$('icon-credits').append(p);}
const elkSource=el('p','ELK.js is distributed under EPL-2.0. Source is available under that license: ');const sourceLink=el('a','kieler/elkjs 0.9.3');sourceLink.href='https://github.com/kieler/elkjs/tree/0.9.3';sourceLink.target='_blank';sourceLink.rel='noopener noreferrer';elkSource.append(sourceLink);$('icon-credits').append(elkSource);
cy.on('tap','node, edge',event=>focus(event.target.id()));
cy.on('tap',event=>{if(event.target===cy)clearFocus();});
$('search').addEventListener('input',()=>{
  const q=$('search').value.trim().toLocaleLowerCase();$('results').replaceChildren();if(!q)return;
  const matches=model.nodes.filter(n=>(n.label+' '+n.id+' '+(n.tags||[]).join(' ')).toLocaleLowerCase().includes(q)).slice(0,10);
  for(const n of matches){const b=el('button',n.label);b.addEventListener('click',()=>{if(!cy.getElementById(n.id).visible()){currentView='all';currentKind='all';$('view').value='all';$('edge-kind').value='all';applyFilter();}focus(n.id);cy.center(cy.getElementById(n.id));$('results').replaceChildren();});$('results').append(b);}
  if(!matches.length)$('results').append(el('p','No matching elements.','secondary'));
});
$('search').addEventListener('keydown',e=>{if(e.key==='Escape'){$('results').replaceChildren();$('search').value='';}if(e.key==='Enter')$('results').querySelector('button')?.click();});
$('view').addEventListener('change',async()=>{currentView=$('view').value;applyFilter();await layout();});
$('edge-kind').addEventListener('change',()=>{currentKind=$('edge-kind').value;applyFilter();});
$('direction').addEventListener('change',()=>layout());
on('fit',fit);on('clear',clearFocus);on('relayout',()=>layout());
on('zoom-in',()=>cy.zoom({level:Math.min(cy.maxZoom(),cy.zoom()*1.2),renderedPosition:{x:cy.width()/2,y:cy.height()/2}}));
on('zoom-out',()=>cy.zoom({level:Math.max(cy.minZoom(),cy.zoom()/1.2),renderedPosition:{x:cy.width()/2,y:cy.height()/2}}));
on('download-model',()=>download(new Blob([JSON.stringify(model,null,2)+'\n'],{type:'application/json'}),'diagram.json'));
on('png-all',async()=>{try{download(await exportPNG(true),'diagram-all.png');}catch(e){setStatus(e.message,true);}});
on('png-view',async()=>{try{download(await exportPNG(false),'diagram-view.png');}catch(e){setStatus(e.message,true);}});
on('text-view',()=>$('text-dialog').showModal());on('credits',()=>$('credits-dialog').showModal());
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.close).close()));
let resizeFrame=null;
new ResizeObserver(()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{cy.resize();if(api.state==='ready')fit();});}).observe($('cy'));
async function setView(id,kind='all'){currentView=id;currentKind=kind;$('view').value=id;$('edge-kind').value=kind;applyFilter();return layout();}
Object.assign(api,{layout,focus,clearFocus,exportPNG,setView,fit});
api.ready=(async()=>{
  try{
    await document.fonts.ready;
    await Promise.all(Object.values(icons).map(src=>new Promise((resolve,reject)=>{const image=new Image();const t=setTimeout(()=>reject(new Error('Icon decode timeout.')),5000);image.onload=()=>{clearTimeout(t);resolve();};image.onerror=()=>{clearTimeout(t);reject(new Error('Icon decode failed.'));};image.src=src;})));
    await layout();
  }catch(error){showFailure(error);}
  return api.state;
})();
})();
