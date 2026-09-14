#!/usr/bin/env python3
"""Render a compiled HTML file in Chromium; report structural checks and save screenshots.
Requires playwright. No browser-policy bypasses. --load content tests exact inline bytes
when local URL navigation is prohibited; this is reported, not passed off as file:// testing.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, shutil, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def wait_ready(page, timeout=22):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        state = page.evaluate('() => window.__DIAGRAM__?.state')
        if state in ('ready', 'error'):
            return state
        time.sleep(.05)
    raise TimeoutError('Viewer did not reach ready/error state.')

def launch(p, executable=None):
    executable = executable or os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('chromium-browser')
    kwargs = {'headless': True}
    if executable: kwargs['executable_path'] = executable
    # Chromium needs this only when this test process is root inside a container.
    if hasattr(os, 'geteuid') and os.geteuid() == 0: kwargs['args'] = ['--no-sandbox']
    return p.chromium.launch(**kwargs)

def load(page, artifact: Path, mode='file'):
    if mode == 'file': page.goto(artifact.resolve().as_uri(), wait_until='load')
    else: page.set_content(artifact.read_text(encoding='utf-8'), wait_until='load')
    return wait_ready(page)

def block_external_requests(context, requests):
    def handle(route):
        if route.request.url.startswith(('data:','blob:','file:')):route.continue_()
        else:requests.append(route.request.url);route.abort()
    context.route('**/*',handle)

AUDIT = r'''() => {
 const a=__DIAGRAM__,cy=a.cy;
 const nodes=cy.nodes().map(n=>({id:n.id(),parent:n.data('parent')||null,isParent:n.isParent(),visible:n.visible(),position:n.position(),bb:n.boundingBox({includeLabels:false,includeOverlays:false}),icon:Boolean(n.data('icon'))}));
 const errors=[],warnings=[];
 for(const n of nodes){
   if(!Number.isFinite(n.position.x)||!Number.isFinite(n.position.y)||!Number.isFinite(n.bb.w)||!Number.isFinite(n.bb.h))errors.push('Non-finite geometry: '+n.id);
   if(n.visible&&n.parent){const p=nodes.find(v=>v.id===n.parent); if(n.bb.x1<p.bb.x1-1||n.bb.y1<p.bb.y1-1||n.bb.x2>p.bb.x2+1||n.bb.y2>p.bb.y2+1)errors.push('Child outside parent: '+n.id);}
 }
 for(const e of cy.edges(':visible')){
   const points=[e.sourceEndpoint(),e.targetEndpoint(),e.midpoint(),...(e.controlPoints()||[])];
   if(points.some(p=>!p||!Number.isFinite(p.x)||!Number.isFinite(p.y)))errors.push('Non-finite edge geometry: '+e.id());
 }
 const leaves=nodes.filter(n=>!n.isParent&&n.visible);
 for(let i=0;i<leaves.length;i++)for(let j=i+1;j<leaves.length;j++){
   const a=leaves[i],b=leaves[j];
   if(Math.min(a.bb.x2,b.bb.x2)-Math.max(a.bb.x1,b.bb.x1)>1&&Math.min(a.bb.y2,b.bb.y2)-Math.max(a.bb.y1,b.bb.y1)>1)errors.push('Leaf overlap: '+a.id+' / '+b.id);
 }
 if(document.documentElement.scrollWidth>innerWidth+2)errors.push('Horizontal page overflow');
 const graph=cy.elements(':visible').renderedBoundingBox({includeLabels:true,includeOverlays:false});
 const centerOffset={x:Math.abs((graph.x1+graph.x2)/2-cy.width()/2),y:Math.abs((graph.y1+graph.y2)/2-cy.height()/2)};
 if(leaves.length&&(centerOffset.x>8||centerOffset.y>8))errors.push(`Visible graph is not centered: ${centerOffset.x.toFixed(1)}px × ${centerOffset.y.toFixed(1)}px offset`);
 if(leaves.length&&(graph.x1<-1||graph.y1<-1||graph.x2>cy.width()+1||graph.y2>cy.height()+1))errors.push('Visible graph is clipped by the canvas bounds.');
 const nodeLabels=cy.nodes(':visible').filter(n=>!n.isParent()||n.data('groupLabel')==='inside').map(n=>({id:n.id(),body:n.boundingBox({includeLabels:false,includeOverlays:false}),withLabel:n.boundingBox({includeLabels:true,includeOverlays:false}),marginX:n.pstyle('text-margin-x').pfValue,labelBounds:n._private.labelBounds.main}));
 for(const n of nodeLabels)if(n.withLabel.x1<n.body.x1-2||n.withLabel.y1<n.body.y1-2||n.withLabel.x2>n.body.x2+2||n.withLabel.y2>n.body.y2+2)errors.push('Node label crosses its shape boundary: '+n.id);
 const insideShape=(n,p)=>{const c=n.position(),x=(p.x-c.x)/(n.width()/2),y=(p.y-c.y)/(n.height()/2),shape=n.data('shape');if(shape==='ellipse')return x*x+y*y<=1.04;if(shape==='diamond')return Math.abs(x)+Math.abs(y)<=1.04;if(shape==='rhomboid'){const s=n.data('slant'),q=[[-1,-1],[1-s,-1],[1,1],[-1+s,1]];let sign=0;for(let i=0;i<q.length;i++){const a=q[i],b=q[(i+1)%q.length],cross=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]);if(Math.abs(cross)<.04)continue;const next=Math.sign(cross);if(sign&&next!==sign)return false;sign=next;}return true;}return true;};
 for(const n of cy.nodes(':visible').filter(n=>!n.isParent()&&['ellipse','diamond','rhomboid'].includes(n.data('shape')))){n.boundingBox({includeLabels:true,includeOverlays:false});const b=n._private.labelBounds.main,corners=[{x:b.x1,y:b.y1},{x:b.x2,y:b.y1},{x:b.x2,y:b.y2},{x:b.x1,y:b.y2}];if(corners.some(p=>!insideShape(n,p)))errors.push('Node label crosses its curved or sloped boundary: '+n.id());}
 const segmentDistance=(p,a,b)=>{const dx=b.x-a.x,dy=b.y-a.y,t=Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy)));return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);};
 const surfaceError=(node,point)=>{const pos=node.position(),p={x:(point.x-pos.x)/(node.width()/2),y:(point.y-pos.y)/(node.height()/2)},shape=node.data('shape');if(shape==='ellipse')return Math.abs(p.x*p.x+p.y*p.y-1);if(shape==='diamond')return Math.abs(Math.abs(p.x)+Math.abs(p.y)-1);if(shape==='rhomboid'){const s=node.data('slant'),q=[{x:-1,y:-1},{x:1-s,y:-1},{x:1,y:1},{x:-1+s,y:1}];return Math.min(...q.map((a,i)=>segmentDistance(p,a,q[(i+1)%q.length])));}return Math.min(Math.abs(Math.abs(p.x)-1),Math.abs(Math.abs(p.y)-1));};
 const routes=cy.edges(':visible').map(e=>{const points=[...(e._private.rscratch.allpts||[])];return{id:e.id(),source:e.source().id(),target:e.target().id(),style:e.pstyle('curve-style').value,labelX:e.data('routeLabelX'),labelY:e.data('routeLabelY'),sourcePoint:e.sourceEndpoint(),targetPoint:e.targetEndpoint(),path:e.isLoop()?Array.from({length:points.length/2},(_,i)=>({x:points[i*2],y:points[i*2+1]})):[e.sourceEndpoint(),...(e.segmentPoints()||[]),e.targetEndpoint()],points};});
 for(const route of routes){
   if(route.source!==route.target&&!['straight','segments'].includes(route.style))errors.push('Non-loop edge is not rectilinear: '+route.id);
   if(route.points.some(v=>!Number.isFinite(v)))errors.push('Non-finite routed edge geometry: '+route.id);
   if(route.source!==route.target&&route.path.some((p,i)=>i&&Math.abs(p.x-route.path[i-1].x)>1&&Math.abs(p.y-route.path[i-1].y)>1))errors.push('Non-orthogonal routed segment: '+route.id);
   if(route.source!==route.target&&surfaceError(cy.getElementById(route.source),route.sourcePoint)>.12)errors.push('Source endpoint is detached from its node surface: '+route.id);
   if(route.source!==route.target&&surfaceError(cy.getElementById(route.target),route.targetPoint)>.12)errors.push('Target endpoint is detached from its node surface: '+route.id);
 }
 const crossesNode=(a,b,n)=>{const c=n.position(),w=n.width()/2,h=n.height()/2,ax=(a.x-c.x)/w,ay=(a.y-c.y)/h,bx=(b.x-c.x)/w,by=(b.y-c.y)/h,dx=bx-ax,dy=by-ay,t=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy||1))),x=ax+t*dx,y=ay+t*dy,shape=n.data('shape'),m=.94;if(shape==='ellipse')return x*x+y*y<m*m;if(shape==='diamond')return Math.abs(x)+Math.abs(y)<m;if(shape==='rhomboid'){const s=n.data('slant');if(Math.abs(ay-by)<.001){if(Math.abs(ay)>=m)return false;const shift=s*ay/2;return Math.max(Math.min(ax,bx),-m+s*m/2+shift)<Math.min(Math.max(ax,bx),m-s*m/2+shift);}const low=Math.max(-m,2*ax/s-2*m/s+m),high=Math.min(m,2*ax/s+2*m/s-m);return Math.max(Math.min(ay,by),low)<Math.min(Math.max(ay,by),high);}return Math.abs(x)<m&&Math.abs(y)<m;};
 const rhomboidProbe={position:()=>({x:0,y:0}),width:()=>220,height:()=>140,data:key=>key==='shape'?'rhomboid':key==='slant'?2*140*Math.tan(Math.PI/12)/220:undefined};
 if(!crossesNode({x:100,y:0},{x:100,y:63},rhomboidProbe))errors.push('Rhomboid segment collision regression.');
 for(const route of routes)if(route.source!==route.target)for(const [a,b] of route.path.slice(1).map((p,i)=>[route.path[i],p]))for(const n of cy.nodes(':visible').filter(n=>!n.isParent()))if(crossesNode(a,b,n))errors.push('Routed edge crosses node interior: '+route.id+' / '+n.id());
 const routeSegments=r=>r.path.slice(1).map((p,i)=>[r.path[i],p]),parallelGap=(a,b,c,d)=>{const ah=Math.abs(a.y-b.y)<1,ch=Math.abs(c.y-d.y)<1;if(ah!==ch)return Infinity;const shared=ah?Math.min(Math.max(a.x,b.x),Math.max(c.x,d.x))-Math.max(Math.min(a.x,b.x),Math.min(c.x,d.x)):Math.min(Math.max(a.y,b.y),Math.max(c.y,d.y))-Math.max(Math.min(a.y,b.y),Math.min(c.y,d.y));return shared>3?Math.abs(ah?a.y-c.y:a.x-c.x):Infinity;};
 const groupBodies=cy.nodes(':visible').filter(n=>n.isParent()).map(n=>({id:n.id(),...n.boundingBox({includeLabels:false,includeOverlays:false})}));
 const groupAncestors=n=>new Set(n.ancestors().map(g=>g.id())),segmentEnters=(a,b,g)=>Math.abs(a.y-b.y)<1?a.y>g.y1&&a.y<g.y2&&Math.max(a.x,b.x)>g.x1&&Math.min(a.x,b.x)<g.x2:a.x>g.x1&&a.x<g.x2&&Math.max(a.y,b.y)>g.y1&&Math.min(a.y,b.y)<g.y2,leavesOnce=(path,g,fromSource)=>{const points=fromSource?path:[...path].reverse(),inside=p=>p.x>=g.x1&&p.x<=g.x2&&p.y>=g.y1&&p.y<=g.y2,i=points.findIndex(p=>!inside(p));return i>0&&!points.slice(i).some(inside)&&!routeSegments({path:points.slice(i)}).some(([a,b])=>segmentEnters(a,b,g));};
 for(const route of routes.filter(r=>r.source!==r.target)){const sourceNode=cy.getElementById(route.source),targetNode=cy.getElementById(route.target),sourceGroups=groupAncestors(sourceNode),targetGroups=groupAncestors(targetNode);for(const g of groupBodies){const sourceInside=sourceGroups.has(g.id),targetInside=targetGroups.has(g.id);if(sourceInside&&targetInside&&route.path.some(p=>p.x<g.x1+18||p.x>g.x2-18||p.y<g.y1+18||p.y>g.y2-18))errors.push('Internal route leaves group padding: '+route.id+' / '+g.id);if(sourceInside!==targetInside&&!leavesOnce(route.path,g,sourceInside))errors.push('Cross-boundary route leaves or enters its group more than once: '+route.id+' / '+g.id);if(!sourceInside&&!targetInside&&routeSegments(route).some(([a,b])=>segmentEnters(a,b,g)))errors.push('Unrelated route enters group: '+route.id+' / '+g.id);for(const [a,b] of routeSegments(route)){const horizontal=Math.abs(a.y-b.y)<1,overlap=horizontal?Math.min(Math.max(a.x,b.x),g.x2)-Math.max(Math.min(a.x,b.x),g.x1):Math.min(Math.max(a.y,b.y),g.y2)-Math.max(Math.min(a.y,b.y),g.y1),distance=horizontal?Math.min(Math.abs(a.y-g.y1),Math.abs(a.y-g.y2)):Math.min(Math.abs(a.x-g.x1),Math.abs(a.x-g.x2));if(!(sourceInside&&targetInside)&&overlap>3&&distance<18)errors.push('Route hugs group boundary: '+route.id+' / '+g.id);}}}
 for(const g of cy.nodes(':visible').filter(n=>n.isParent())){const children=g.children(':visible');if(!children.length)continue;const body=g.boundingBox({includeLabels:false,includeOverlays:false}),content=children.boundingBox({includeLabels:false,includeOverlays:false}),left=content.x1-body.x1,right=body.x2-content.x2,top=content.y1-body.y1,bottom=body.y2-content.y2;if(Math.min(left,right,top,bottom)<28)errors.push('Group content padding is too small: '+g.id());if(Math.abs(left-right)>1||Math.abs(top-bottom)>1)errors.push('Group content is not centered: '+g.id());}
 for(let i=0;i<routes.length;i++)for(let j=i+1;j<routes.length;j++)if(routes[i].source!==routes[i].target&&routes[j].source!==routes[j].target)for(const [a,b] of routeSegments(routes[i]))for(const [c,d] of routeSegments(routes[j]))if(parallelGap(a,b,c,d)<14)errors.push('Parallel routes lack separation: '+routes[i].id+' / '+routes[j].id);
 for(let i=0;i<routes.length;i++)for(let j=i+1;j<routes.length;j++){
   const a=routes[i],b=routes[j],same=a.source===b.source&&a.target===b.target,reverse=a.source===b.target&&a.target===b.source;
   if((same||reverse)&&a.points.length&&JSON.stringify(a.points)===JSON.stringify(reverse?[...b.points].reverse():b.points))errors.push('Coincident parallel route: '+a.id+' / '+b.id);
   if(a.source===b.source&&Math.hypot(a.sourcePoint.x-b.sourcePoint.x,a.sourcePoint.y-b.sourcePoint.y)<1)errors.push('Coincident source endpoint: '+a.id+' / '+b.id);
   if(a.target===b.target&&Math.hypot(a.targetPoint.x-b.targetPoint.x,a.targetPoint.y-b.targetPoint.y)<1)errors.push('Coincident target endpoint: '+a.id+' / '+b.id);
 }
 const edgeLabels=cy.edges(':visible').filter(e=>e.data('label')).map(e=>{const s=e._private.rscratch,r=e._private.rstyle,x=s.labelX+e.pstyle('text-margin-x').pfValue,y=s.labelY+e.pstyle('text-margin-y').pfValue;return {id:e.id(),x,y,x1:x-r.labelWidth/2,y1:y-r.labelHeight/2,x2:x+r.labelWidth/2,y2:y+r.labelHeight/2};});
 for(let i=0;i<edgeLabels.length;i++)for(let j=i+1;j<edgeLabels.length;j++){const a=edgeLabels[i],b=edgeLabels[j];if(Math.min(a.x2,b.x2)-Math.max(a.x1,b.x1)>2&&Math.min(a.y2,b.y2)-Math.max(a.y1,b.y1)>2)errors.push('Overlapping edge labels: '+a.id+' / '+b.id);}
 for(const label of edgeLabels)for(const node of leaves){if(Math.min(label.x2,node.bb.x2)-Math.max(label.x1,node.bb.x1)>2&&Math.min(label.y2,node.bb.y2)-Math.max(label.y1,node.bb.y1)>2)errors.push('Edge label overlaps node: '+label.id+' / '+node.id);}
 const groupLabels=cy.nodes(':visible').filter(n=>n.isParent()).map(n=>{n.boundingBox({includeLabels:true,includeOverlays:false});return {id:n.id(),...n._private.labelBounds.main};});
 for(const label of edgeLabels)for(const group of groupLabels){if(Math.min(label.x2,group.x2)-Math.max(label.x1,group.x1)>2&&Math.min(label.y2,group.y2)-Math.max(label.y1,group.y1)>2)errors.push('Edge label overlaps group title: '+label.id+' / '+group.id);}
 for(const label of edgeLabels){const route=routes.find(r=>r.id===label.id);if(!routeSegments(route).some(([a,b])=>segmentDistance(label,a,b)<1.5))errors.push('Edge label is detached from its route: '+label.id);}
 for(const label of edgeLabels){const box={x1:label.x1-4,y1:label.y1-4,x2:label.x2+4,y2:label.y2+4};for(const route of routes.filter(r=>r.id!==label.id))for(const [a,b] of routeSegments(route)){const horizontal=Math.abs(a.x-b.x)>=Math.abs(a.y-b.y),overlap=horizontal?Math.min(Math.max(a.x,b.x),box.x2)-Math.max(Math.min(a.x,b.x),box.x1):Math.min(Math.max(a.y,b.y),box.y2)-Math.max(Math.min(a.y,b.y),box.y1),inside=horizontal?a.y>box.y1&&a.y<box.y2:a.x>box.x1&&a.x<box.x2;if(inside&&overlap>2)errors.push('Edge label interrupts another route: '+label.id+' / '+route.id);}}
 if(cy.edges(':visible').some(e=>e.data('label')&&(e.pstyle('text-background-opacity').value<.99||e.pstyle('text-border-width').pfValue<1)))errors.push('Edge labels need an opaque bordered interruption.');
 for(const n of cy.nodes(':visible').filter(n=>n.data('shape')==='rhomboid')){const angle=Math.atan(n.data('slant')*n.width()/(2*n.height()))*180/Math.PI;if(Math.abs(angle-15)>.2)errors.push('Parallelogram side angle is not 15 degrees: '+n.id());}
 for(const n of cy.nodes(':visible').filter(n=>['square','diamond'].includes(n.data('shape'))))if(Math.abs(n.width()-n.height())>.2)errors.push('Square figure does not have equal sides: '+n.id());
 for(const n of cy.nodes(':visible').filter(n=>['ellipse','rhomboid'].includes(n.data('shape'))))if(n.width()<=n.height())errors.push('Wide figure has invalid default proportions: '+n.id());
 const labelPixels=cy.zoom()*14;
 if(leaves.length&&labelPixels<10)warnings.push('Overview text below 10 CSS px. Use a focused view or zoom; do not call this screenshot readable.');
 const iconStyles=cy.nodes().filter(n=>n.data('icon')&&(!n.isParent()||n.data('groupLabel')==='inside')).map(n=>({id:n.id(),parent:n.isParent(),fit:n.style('background-fit'),width:n.pstyle('background-width').pfValue[0],height:n.pstyle('background-height').pfValue[0]}));
 for(const n of iconStyles){const expected=n.parent?20:24;if(n.fit!=='none'||Math.abs(n.width-expected)>0.1||Math.abs(n.height-expected)>0.1)errors.push('Icon scaling regression: '+n.id);}
 for(const n of cy.nodes(':visible').filter(n=>!n.isParent()&&n.data('icon'))){const contentCenter=n.data('iconTop')+(24+6+n.data('labelHeight'))/2;if(Math.abs(contentCenter-n.data('height')/2)>1)errors.push('Icon and label are not jointly centered: '+n.id());}
 for(const n of cy.nodes(':visible').filter(n=>n.isParent()&&n.data('groupLabel')==='top')){n.boundingBox({includeLabels:true,includeOverlays:false});const label=n._private.labelBounds.main;if(Math.abs((label.x1+label.x2)/2-n.position('x'))>2)errors.push('Top group title is not centered: '+n.id());}
 if(cy.nodes(':visible').filter(n=>n.isParent()).some(n=>n.pstyle('text-background-opacity').value<.99))errors.push('Group titles need an opaque route interruption.');
 return {state:a.state,viewerErrors:a.errors,cytoscapeVersion:cytoscape.version,nodes:nodes.length,leaves:leaves.length,edges:cy.edges().length,visibleEdges:cy.edges(':visible').length,zoom:cy.zoom(),labelPixels,centerOffset,routes,nodeLabels,edgeLabels,groupLabels,errors,warnings,geometry:nodes,iconStyles};
}'''

def run(artifact: Path, out: Path, mode='file', executable=None):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    result={'ok':False,'artifact':str(artifact.resolve()),'artifactSha256':hashlib.sha256(artifact.read_bytes()).hexdigest(),'loadMode':mode,'network':'blocked by route and offline context','visualReview':'not-run','screenshots':[],'errors':[],'warnings':[]}
    start=time.monotonic()
    with sync_playwright() as p:
        browser=launch(p,executable);result['browserVersion']=browser.version
        try:
            for label,width,height in [('desktop',1440,900),('wide',1920,1080),('mobile',390,844)]:
                context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,offline=True,accept_downloads=True)
                requests=[];page_errors=[];console_errors=[]
                block_external_requests(context,requests)
                page=context.new_page();page.on('pageerror',lambda e:page_errors.append(str(e)))
                page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
                state=load(page,artifact,mode)
                audit=page.evaluate(AUDIT)
                if state!='ready':audit['errors'].append('Viewer is not ready.')
                audit['errors']+=page_errors+console_errors
                audit['errors']+=['Unexpected runtime request: '+u for u in requests if not u.startswith(('data:','blob:','file:'))]
                if audit['visibleEdges']!=audit['edges']:audit['errors'].append('Initial view does not expose all authored edges.')
                screenshot=out/f'{label}.png';page.screenshot(path=str(screenshot),full_page=True)
                result['screenshots'].append({'viewport':label,'width':width,'height':height,'path':str(screenshot.resolve()),'sha256':hashlib.sha256(screenshot.read_bytes()).hexdigest(),'audit':audit})
                result['errors'] += [label+': '+e for e in audit['errors']+audit['viewerErrors']]
                result['warnings'] += [label+': '+e for e in audit['warnings']]
                if label=='desktop':
                    # Exercise source immutability, PNG decode, both view modes and basic controls.
                    source=page.evaluate('() => JSON.stringify(__DIAGRAM__.model)')
                    leaves=page.evaluate('() => __DIAGRAM__.cy.nodes().filter(n=>!n.isParent()).map(n=>n.id())')
                    if leaves:
                        before=page.evaluate('(id) => __DIAGRAM__.cy.getElementById(id).width()',leaves[0])
                        page.evaluate('(id) => __DIAGRAM__.focus(id,"downstream")',leaves[0])
                        after=page.evaluate('(id) => __DIAGRAM__.cy.getElementById(id).width()',leaves[0])
                        if before!=after:result['errors'].append('Highlight changed node width.')
                        viewport=page.evaluate('() => ({zoom:__DIAGRAM__.cy.zoom(),pan:__DIAGRAM__.cy.pan()})')
                        blob=page.evaluate('''async () => {const b=await __DIAGRAM__.exportPNG(true);return await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(b);});}''')
                        png=out/'export-all.png';png.write_bytes(base64.b64decode(blob.split(',',1)[1]));result['pngExport']=str(png.resolve())
                        png_size=page.evaluate('''async data => {const i=new Image();i.src=data;await i.decode();return [i.width,i.height]}''',blob)
                        if png_size[0]>1800 or png_size[1]>1200:result['errors'].append(f'PNG exceeds 1800×1200: {png_size[0]}×{png_size[1]}')
                        if viewport!=page.evaluate('() => ({zoom:__DIAGRAM__.cy.zoom(),pan:__DIAGRAM__.cy.pan()})'):result['errors'].append('PNG export changed the viewport.')
                        page.evaluate('() => __DIAGRAM__.clearFocus()')
                    if source!=page.evaluate('() => JSON.stringify(__DIAGRAM__.model)'):result['errors'].append('Viewer mutated the source model.')
                    page.click('#text-view');page.click('[data-close="text-dialog"]')
                    page.click('#credits');page.click('[data-close="credits-dialog"]')
                context.close()
        finally:browser.close()
    result['durationSeconds']=round(time.monotonic()-start,3);result['ok']=not result['errors']
    (out/'browser-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifact',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--load',choices=['file','content'],default='file');p.add_argument('--browser');a=p.parse_args()
    try:r=run(a.artifact,a.out,a.load,a.browser)
    except Exception as e:
        r={'ok':False,'errors':[str(e)],'visualReview':'not-run','loadMode':a.load};a.out.mkdir(parents=True,exist_ok=True);(a.out/'browser-report.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2));return 0 if r['ok'] else 1
if __name__=='__main__':sys.exit(main())
