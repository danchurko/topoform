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
 const labelPixels=cy.zoom()*14;
 if(leaves.length&&labelPixels<10)warnings.push('Overview text below 10 CSS px. Use a focused view or zoom; do not call this screenshot readable.');
 const iconStyles=cy.nodes().filter(n=>n.data('icon')).map(n=>({id:n.id(),fit:n.style('background-fit'),width:n.pstyle('background-width').pfValue[0],height:n.pstyle('background-height').pfValue[0]}));
 for(const n of iconStyles)if(n.fit!=='none'||n.width>32||n.height>32)errors.push('Icon scaling regression: '+n.id);
 return {state:a.state,viewerErrors:a.errors,cytoscapeVersion:cytoscape.version,nodes:nodes.length,leaves:leaves.length,edges:cy.edges().length,visibleEdges:cy.edges(':visible').length,zoom:cy.zoom(),labelPixels,errors,warnings,geometry:nodes,iconStyles};
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
                context.route('**/*',lambda route:(requests.append(route.request.url),route.abort()))
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
                        blob=page.evaluate('''async () => {const b=await __DIAGRAM__.exportPNG(true);return await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(b);});}''')
                        png=out/'export-all.png';png.write_bytes(base64.b64decode(blob.split(',',1)[1]));result['pngExport']=str(png.resolve())
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
