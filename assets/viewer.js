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
for(const [kind,color] of colors){const item=el('span');const sw=el('i',undefined,'swatch');sw.style.background=model.nodes.find(n=>(n.kind||'element')===kind)?.appearance?.stroke||color;item.append(sw,document.createTextNode(kind));$('legend').append(item);}
if(model.nodes.some(n=>n.kind==='group'))$('legend').append(el('span','Dashed box = containment'));
$('legend').append(el('span','Arrow = authored direction','hint'));

// Labels sit inside explicitly measured leaf cards. ELK receives these dimensions.
const measure=document.createElement('canvas').getContext('2d');
measure.font='600 14px system-ui';
function lines(text,width){
  const result=[];
  for(const para of text.split('\n')){
    let line='';
    for(const word of para.split(/\s+/)){
      const candidate=line?`${line} ${word}`:word;if(measure.measureText(candidate).width<=width){line=candidate;continue;}
      if(line){result.push(line);line='';}
      if(measure.measureText(word).width<=width){line=word;continue;}
      for(const char of word){if(measure.measureText(line+char).width>width&&line){result.push(line);line='';}line+=char;}
    }
    result.push(line);
  }
  return result;
}
const nodes=model.nodes.map(n=>{
  const group=n.kind==='group',appearance=n.appearance||{},shape={'oval':'ellipse','parallelogram':'rhomboid'}[appearance.shape]||appearance.shape||'round-rectangle';
  const labelWidth=appearance.shape==='diamond'?88:appearance.shape==='parallelogram'?104:appearance.shape==='oval'?120:appearance.shape==='square'?112:160,displayLabel=lines(n.label,labelWidth).join('\n');
  const labelHeight=displayLabel.split('\n').length*19,contentHeight=labelHeight+(n.icon?30:0)+24;
  let width=group?180:188,height=Math.max(86,contentHeight);
  if(appearance.shape==='square')width=height=Math.max(132,height);
  if(appearance.shape==='diamond')width=height=Math.max(176,Math.ceil(labelWidth+contentHeight+24));
  if(appearance.shape==='oval'){width=Math.max(220,width);height=Math.max(132,Math.ceil(contentHeight*1.45));}
  if(appearance.shape==='parallelogram'){width=Math.max(220,width);height=Math.max(140,Math.ceil(contentHeight*1.4));}
  const groupLabelWidth=Math.min(300,measure.measureText(n.label).width),iconTop=n.icon?Math.max(10,(height-labelHeight-30)/2):0;
  return {data:{id:n.id,label:n.label,displayLabel,kind:n.kind||'element',...(n.parent?{parent:n.parent}:{}),width,height,labelWidth,labelHeight,shape,icon:icons[n.icon]||null,iconTop,fill:appearance.fill||'#ffffff',stroke:appearance.stroke||colors.get(n.kind||'element')||'#7c8899',strokeWidth:appearance.strokeWidth||1.7,textColor:appearance.textColor||'#203047',groupLabel:appearance.groupLabel||'top',groupPadding:appearance.groupLabel==='inside'?46:30,groupTextX:appearance.groupLabel==='inside'?(n.icon?42:14)+groupLabelWidth:0}};
});
const edges=model.edges.map(e=>({data:{id:e.id,source:e.source,target:e.target,label:e.label||'',kind:e.kind||'flow',directed:e.directed!==false,curveStyle:'straight',segmentWeights:'0.5',segmentDistances:'0',routeLabelX:0,routeLabelY:0,sourceEndpoint:'outside-to-node',targetEndpoint:'outside-to-node'}}));
const cy=api.cy=cytoscape({
  container:$('cy'),elements:{nodes,edges},layout:{name:'preset'},
  minZoom:0.03,maxZoom:3.5,pixelRatio:Math.min(window.devicePixelRatio||1,2),
  autoungrabify:true,boxSelectionEnabled:false,
  style:[
    {selector:'node',style:{'shape':'data(shape)','width':'data(width)','height':'data(height)','background-color':'data(fill)','border-width':'data(strokeWidth)','border-color':'data(stroke)','label':'data(displayLabel)','font-family':'system-ui','font-size':14,'font-weight':600,'color':'data(textColor)','text-valign':'center','text-halign':'center','text-wrap':'wrap','text-max-width':'data(labelWidth)','text-justification':'center','text-margin-y':0,'padding':0,'overlay-opacity':0}},
    {selector:'node[icon]',style:{'background-image':n=>n.data('icon')||'none','background-fit':'none','background-width':24,'background-height':24,'background-position-x':'50%','background-position-y':'data(iconTop)','text-margin-y':15}},
    {selector:'node:parent',style:{'shape':'round-rectangle','background-color':'data(fill)','background-opacity':0.22,'border-color':'data(stroke)','border-width':'data(strokeWidth)','border-style':'dashed','padding':'data(groupPadding)','label':'data(label)','font-size':12,'font-weight':600,'color':'data(textColor)','text-valign':'top','text-halign':'center','text-margin-x':0,'text-margin-y':-9,'compound-sizing-wrt-labels':'include','background-image':'none','text-wrap':'wrap','text-max-width':300}},
    {selector:'node:parent[groupLabel="inside"]',style:{'text-halign':'left','text-valign':'top','text-margin-x':'data(groupTextX)','text-margin-y':15}},
    {selector:'node:parent[groupLabel="inside"][icon]',style:{'background-image':n=>n.data('icon')||'none','background-fit':'none','background-width':20,'background-height':20,'background-position-x':'16px','background-position-y':'14px'}},
    {selector:'edge',style:{'curve-style':'data(curveStyle)','edge-distances':'node-position','segment-weights':'data(segmentWeights)','segment-distances':'data(segmentDistances)','source-endpoint':'data(sourceEndpoint)','target-endpoint':'data(targetEndpoint)','line-color':'#96a5bb','target-arrow-color':'#96a5bb','target-arrow-shape':e=>e.data('directed')?'triangle':'none','width':1.6,'arrow-scale':0.85,'label':'data(label)','font-family':'system-ui','font-size':11,'color':'#526277','text-background-color':'#fcfcfd','text-background-opacity':0.95,'text-background-padding':4,'text-background-shape':'roundrectangle','text-wrap':'wrap','text-max-width':Math.max(44,Math.min(120,(model.layout?.layerSpacing||120)-20)),'text-rotation':'none','text-margin-x':'data(routeLabelX)','text-margin-y':'data(routeLabelY)','overlay-opacity':0}},
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
function portPoint(node,side,t){
  const w=node.data('width'),h=node.data('height'),shape=node.data('shape'),horizontal=side==='NORTH'||side==='SOUTH';let x=horizontal?t:0,y=horizontal?0:t;
  if(shape==='ellipse'){if(horizontal)y=(side==='SOUTH'?1:-1)*Math.sqrt(1-x*x);else x=(side==='EAST'?1:-1)*Math.sqrt(1-y*y);}
  else if(shape==='diamond'){if(horizontal)y=(side==='SOUTH'?1:-1)*(1-Math.abs(x));else x=(side==='EAST'?1:-1)*(1-Math.abs(y));}
  else if(shape==='rhomboid'){if(horizontal){x=(side==='SOUTH'?1/3:-1/3)+2*t/3;y=side==='SOUTH'?1:-1;}else x=(side==='EAST'?2/3:-2/3)+y/3;}
  else if(horizontal)y=side==='SOUTH'?1:-1;else x=side==='EAST'?1:-1;
  return {x:w*(x+1)/2,y:h*(y+1)/2};
}
function segmentValues(points,source,target){
  const dx=target.x-source.x,dy=target.y-source.y,length=Math.hypot(dx,dy),square=length*length;
  if(!length||!points.length)return {weights:'0.5',distances:'0'};
  const weights=[],distances=[];
  for(const p of points){weights.push(((p.x-source.x)*dx+(p.y-source.y)*dy)/square);distances.push(((p.x-source.x)*-dy+(p.y-source.y)*dx)/length);}
  return {weights:weights.join(' '),distances:distances.join(' ')};
}
function stubLength(node,side,point,assigned){
  const clearance={EAST:node.data('width')-point.x,WEST:point.x,SOUTH:node.data('height')-point.y,NORTH:point.y}[side]+18;
  return Math.max(assigned,clearance);
}
function crossesNode(a,b,node){
  const c=node.position(),w=node.data('width')/2,h=node.data('height')/2,ax=(a.x-c.x)/w,ay=(a.y-c.y)/h,bx=(b.x-c.x)/w,by=(b.y-c.y)/h,dx=bx-ax,dy=by-ay,t=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy||1))),x=ax+t*dx,y=ay+t*dy,shape=node.data('shape'),m=.98;
  if(shape==='ellipse')return x*x+y*y<m*m;
  if(shape==='diamond')return Math.abs(x)+Math.abs(y)<m;
  if(shape==='rhomboid'){if(Math.abs(ay-by)<.001){if(Math.abs(ay)>=m)return false;return Math.max(Math.min(ax,bx),(-2*m+ay)/3)<Math.min(Math.max(ax,bx),(2*m+ay)/3);}const low=Math.max(-m,3*ax-2*m),high=Math.min(m,3*ax+2*m);return Math.max(Math.min(ay,by),low)<Math.min(Math.max(ay,by),high);}
  return Math.abs(x)<m&&Math.abs(y)<m;
}
async function arrange(elements){
  const spacing=model.layout?.spacing||65,layerSpacing=model.layout?.layerSpacing||120;
  const elk={'elk.algorithm':'layered','elk.direction':$('direction').value,'elk.hierarchyHandling':'INCLUDE_CHILDREN','elk.edgeRouting':'ORTHOGONAL','elk.spacing.nodeNode':spacing,'elk.spacing.edgeNode':Math.max(32,spacing/2),'elk.spacing.edgeEdge':24,'elk.layered.spacing.nodeNodeBetweenLayers':layerSpacing,'elk.layered.spacing.edgeNodeBetweenLayers':Math.max(36,layerSpacing/3),'elk.layered.spacing.edgeEdgeBetweenLayers':24,'elk.padding':'[top=40,left=40,bottom=40,right=40]','elk.randomSeed':17};
  await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Layout exceeded 15 seconds. Split the diagram or use a worker-based integration.')),15000),success=()=>{clearTimeout(timer);pendingFailure=null;resolve();};pendingFailure=e=>{clearTimeout(timer);reject(e);};elements.layout({name:'elk',fit:false,animate:false,nodeDimensionsIncludeLabels:false,nodeLayoutOptions:node=>node.isParent()?{...elk,'elk.padding':node.data('groupLabel')==='inside'?'[top=76,left=42,bottom=42,right=42]':'[top=50,left=36,bottom=36,right=36]'}:{},elk,stop:success}).run();});
}
async function route(elements,retryEdge=null){
  const visible=elements.edges(':visible'),records=[],ports=new Map(),occupied=[];
  const side=(a,b)=>{const dx=b.x-a.x,dy=b.y-a.y;if(Math.abs(dx)>=Math.abs(dy))return dx>=0?'EAST':'WEST';return dy>=0?'SOUTH':'NORTH';},opposite={EAST:'WEST',WEST:'EAST',NORTH:'SOUTH',SOUTH:'NORTH'},vector={EAST:[1,0],WEST:[-1,0],NORTH:[0,-1],SOUTH:[0,1]};
  visible.forEach(edge=>{if(edge.isLoop()){edge.data({curveStyle:'bezier',routeLabelX:0,routeLabelY:-28});return;}const source=edge.source().position(),target=edge.target().position(),sourceSide=side(source,target),targetSide=opposite[sourceSide],record={edge,source,target,sourceSide,targetSide};records.push(record);for(const [node,which,s,peer] of [[edge.source(),'source',sourceSide,target],[edge.target(),'target',targetSide,source]]){const key=`${node.id()}:${s}`;if(!ports.has(key))ports.set(key,[]);ports.get(key).push({record,which,peer});}});
  for(const entries of ports.values()){const vertical=['EAST','WEST'].includes(entries[0].record[`${entries[0].which}Side`]);entries.sort((a,b)=>(vertical?a.peer.y-b.peer.y:a.peer.x-b.peer.x)||a.record.edge.id().localeCompare(b.record.edge.id()));entries.forEach((entry,i)=>{entry.record[`${entry.which}Port`]=entries.length===1?0:-.6+1.2*i/(entries.length-1);entry.record[`${entry.which}Stub`]=24+i*12;});}
  const obstacles=elements.nodes(':visible').filter(n=>!n.isParent()).map(n=>{const p=n.position(),pad=12;return{id:n.id(),x1:p.x-n.data('width')/2-pad,y1:p.y-n.data('height')/2-pad,x2:p.x+n.data('width')/2+pad,y2:p.y+n.data('height')/2+pad};}),xs=obstacles.flatMap(o=>[o.x1-18,o.x2+18]),ys=obstacles.flatMap(o=>[o.y1-18,o.y2+18]);
  const segments=path=>path.slice(1).map((p,i)=>[path[i],p]),intersects=(a,b,o)=>Math.abs(a.y-b.y)<.5?a.y>o.y1&&a.y<o.y2&&Math.max(a.x,b.x)>o.x1&&Math.min(a.x,b.x)<o.x2:a.x>o.x1&&a.x<o.x2&&Math.max(a.y,b.y)>o.y1&&Math.min(a.y,b.y)<o.y2;
  const overlap=(a,b,c,d)=>{const ah=Math.abs(a.y-b.y)<.5,ch=Math.abs(c.y-d.y)<.5;if(ah!==ch)return 0;if(ah&&Math.abs(a.y-c.y)<1)return Math.max(0,Math.min(Math.max(a.x,b.x),Math.max(c.x,d.x))-Math.max(Math.min(a.x,b.x),Math.min(c.x,d.x)));if(!ah&&Math.abs(a.x-c.x)<1)return Math.max(0,Math.min(Math.max(a.y,b.y),Math.max(c.y,d.y))-Math.max(Math.min(a.y,b.y),Math.min(c.y,d.y)));return 0;};
  const crossing=(a,b,c,d)=>{const ah=Math.abs(a.y-b.y)<.5,ch=Math.abs(c.y-d.y)<.5;if(ah===ch)return false;const h=ah?[a,b]:[c,d],v=ah?[c,d]:[a,b];return v[0].x>Math.min(h[0].x,h[1].x)&&v[0].x<Math.max(h[0].x,h[1].x)&&h[0].y>Math.min(v[0].y,v[1].y)&&h[0].y<Math.max(v[0].y,v[1].y);};
  const compact=path=>{const out=[];for(const p of path){const n=out.length,vertical=n>1&&Math.abs(out[n-2].x-out[n-1].x)<.5&&Math.abs(out[n-1].x-p.x)<.5&&(out[n-1].y-out[n-2].y)*(p.y-out[n-1].y)>=0,horizontal=n>1&&Math.abs(out[n-2].y-out[n-1].y)<.5&&Math.abs(out[n-1].y-p.y)<.5&&(out[n-1].x-out[n-2].x)*(p.x-out[n-1].x)>=0;if(vertical||horizontal)out[n-1]=p;else if(!n||Math.abs(p.x-out[n-1].x)>.5||Math.abs(p.y-out[n-1].y)>.5)out.push(p);}return out;};
  for(const [lane,r] of records.sort((a,b)=>(a.edge.id()===retryEdge?-1:b.edge.id()===retryEdge?1:0)||(Math.abs(a.target.x-a.source.x)+Math.abs(a.target.y-a.source.y))-(Math.abs(b.target.x-b.source.x)+Math.abs(b.target.y-b.source.y))||a.edge.id().localeCompare(b.edge.id())).entries()){
    const sourcePoint=portPoint(r.edge.source(),r.sourceSide,r.sourcePort),targetPoint=portPoint(r.edge.target(),r.targetSide,r.targetPort),start={x:r.source.x+sourcePoint.x-r.edge.source().data('width')/2,y:r.source.y+sourcePoint.y-r.edge.source().data('height')/2},end={x:r.target.x+targetPoint.x-r.edge.target().data('width')/2,y:r.target.y+targetPoint.y-r.edge.target().data('height')/2},sv=vector[r.sourceSide],tv=vector[r.targetSide],sourceStub=stubLength(r.edge.source(),r.sourceSide,sourcePoint,r.sourceStub),targetStub=stubLength(r.edge.target(),r.targetSide,targetPoint,r.targetStub),stub={x:start.x+sv[0]*sourceStub,y:start.y+sv[1]*sourceStub},finish={x:end.x+tv[0]*targetStub,y:end.y+tv[1]*targetStub},usedX=occupied.filter(([a,b])=>Math.abs(a.x-b.x)<.5).flatMap(([a])=>[a.x-12,a.x+12]),usedY=occupied.filter(([a,b])=>Math.abs(a.y-b.y)<.5).flatMap(([a])=>[a.y-12,a.y+12]),channelsX=[(stub.x+finish.x)/2,...xs,...usedX,Math.min(...xs)-24-lane*8,Math.max(...xs)+24+lane*8],channelsY=[(stub.y+finish.y)/2,...ys,...usedY,Math.min(...ys)-24-lane*8,Math.max(...ys)+24+lane*8],candidates=[[start,stub,{x:finish.x,y:stub.y},finish,end],[start,stub,{x:stub.x,y:finish.y},finish,end],...channelsX.map(x=>[start,stub,{x,y:stub.y},{x,y:finish.y},finish,end]),...channelsY.map(y=>[start,stub,{x:stub.x,y},{x:finish.x,y},finish,end])].map(compact),skip=new Set([r.edge.source().id(),r.edge.target().id()]);
    const select=paths=>paths.map(path=>{const parts=segments(path);let score=parts.reduce((sum,[a,b])=>sum+Math.abs(a.x-b.x)+Math.abs(a.y-b.y),0)+(path.length-2)*28,blocked=false;for(const [a,b] of parts){blocked ||= obstacles.some(o=>skip.has(o.id)?crossesNode(a,b,cy.getElementById(o.id)):intersects(a,b,o));for(const [c,d] of occupied){blocked ||= overlap(a,b,c,d)>3;score+=crossing(a,b,c,d)?180:0;}}return{path,score,blocked};}).filter(choice=>!choice.blocked).sort((a,b)=>a.score-b.score||JSON.stringify(a.path).localeCompare(JSON.stringify(b.path)))[0];
    let scored=select(candidates);
    if(!scored){const detours=[];for(const x of [...new Set(channelsX)])for(const y of [...new Set(channelsY)])detours.push(compact([start,stub,{x,y:stub.y},{x,y},{x:finish.x,y},finish,end]),compact([start,stub,{x:stub.x,y},{x,y},{x,y:finish.y},finish,end]));scored=select(detours);}
    if(!scored){if(!retryEdge)return route(elements,r.edge.id());throw new Error(`No collision-free orthogonal route for ${r.edge.id()}.`);}const path=scored.path,bends=path.slice(1,-1),values=segmentValues(bends,r.source,r.target);occupied.push(...segments(path));r.edge.data({curveStyle:bends.length?'segments':'straight',segmentWeights:values.weights,segmentDistances:values.distances,sourceEndpoint:`${start.x-r.source.x}px ${start.y-r.source.y}px`,targetEndpoint:`${end.x-r.target.x}px ${end.y-r.target.y}px`,routeLabelX:0,routeLabelY:0});
  }
  cy.style().update();await new Promise(resolve=>requestAnimationFrame(resolve));
  const placed=[],groupBoxes=elements.nodes(':visible').filter(n=>n.isParent()).map(n=>{n.boundingBox({includeLabels:true,includeOverlays:false});return n._private.labelBounds.main;}),nodeBoxes=[...obstacles.map(o=>({x1:o.x1,y1:o.y1,x2:o.x2,y2:o.y2})),...groupBoxes],area=(a,b)=>Math.max(0,Math.min(a.x2,b.x2)-Math.max(a.x1,b.x1))*Math.max(0,Math.min(a.y2,b.y2)-Math.max(a.y1,b.y1));
  for(const r of records){if(!r.edge.data('label'))continue;const s=r.edge._private.rscratch,z=r.edge._private.rstyle;if(!Number.isFinite(s.labelX))continue;let best;const offsets=[0,-24,24,-48,48,-72,72,-96,96,-120,120];for(const x of offsets)for(const y of offsets){const box={x1:s.labelX+x-z.labelWidth/2,y1:s.labelY+y-z.labelHeight/2,x2:s.labelX+x+z.labelWidth/2,y2:s.labelY+y+z.labelHeight/2},collision=[...nodeBoxes,...placed].reduce((n,b)=>n+area(box,b),0),score=collision*1000+Math.abs(x)+Math.abs(y);if(!best||score<best.score)best={x,y,box,score};}r.edge.data({routeLabelX:best.x,routeLabelY:best.y});placed.push(best.box);}
  cy.style().update();
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
      await route(visible);
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
  const routes=new Map(cy.edges().map(e=>[e.id(),Object.fromEntries(['sourceEndpoint','targetEndpoint','curveStyle','segmentWeights','segmentDistances','routeLabelX','routeLabelY'].map(k=>[k,e.data(k)]))]));
  const viewport={zoom:cy.zoom(),pan:cy.pan()};
  busy=true;api.state='export';document.querySelectorAll('.toolbar button,.toolbar select,#png-view,#png-all').forEach(b=>b.disabled=true);
  cy.elements().removeClass('dim highlight');if(all){cy.elements().removeClass('hidden');cy.elements().forEach(e=>e.style('display'));}
  try{
    if(!cy.nodes(':visible').length)throw new Error('This view has no elements to export.');
    if(all){await arrange(cy.elements());await route(cy.elements());}
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
    cy.batch(()=>{cy.nodes().filter(n=>!n.isParent()).positions(n=>positions.get(n.id()));cy.edges().forEach(e=>e.data(routes.get(e.id())));states.forEach(s=>cy.getElementById(s.id).classes(s.classes));});
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
