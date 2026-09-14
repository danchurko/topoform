#!/usr/bin/env python3
"""Real Chromium regression suite. Emits exact cases, timings and warnings; no visual pass claims."""
from pathlib import Path
import argparse, copy, json, sys, tempfile, time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import diagram,browser_check
from playwright.sync_api import sync_playwright

def model(name,nodes,edges):return {'schemaVersion':1,'title':name,'nodes':nodes,'edges':edges}
def n(i,**kw):return {'id':i,'label':i,**kw}
def e(i,s,t,**kw):return {'id':i,'source':s,'target':t,**kw}
def fixtures():
 yield 'empty',model('Empty',[],[])
 yield 'single-without-icon',model('Single',[n('a')],[])
 yield 'disconnected',model('Disconnected',[n('a'),n('b'),n('c')],[])
 yield 'parallel-and-opposite',model('Parallel',[n('a'),n('b')],[e('ab','a','b',label='Primary'),e('ab2','a','b',label='Backup'),e('ba','b','a',label='Feedback')])
 yield 'cycle',model('Cycle',[n('a'),n('b'),n('c')],[e('ab','a','b'),e('bc','b','c'),e('ca','c','a')])
 yield 'self-loop',model('Self loop',[n('a'),n('b')],[e('aa','a','a',label='Retry'),e('ab','a','b')])
 yield 'undirected',model('Undirected',[n('a'),n('b'),n('c')],[e('ab','a','b',directed=False),e('bc','b','c')])
 yield 'nested-cross-boundary',model('Nested',[n('outer',kind='group'),n('inner',kind='group',parent='outer'),n('a',parent='inner'),n('b',parent='outer'),n('external')],[e('xa','external','a'),e('ab','a','b'),e('bx','b','external')])
 yield 'punctuation-ids',model('Stable IDs',[n('a.b:c-d_e'),n('node:b')],[e('link.v1:primary','a.b:c-d_e','node:b')])
 yield 'unicode-and-injection',model('Unicode & <script>',[n('a',label='Дослідження · 東京 · مرحبا · café / long_unbroken_identifier_12345678901234567890',description='</script><script>window.HACKED=true</script>'),n('b',label='</script><img src=x onerror="window.HACKED=true">')],[e('ab','a','b',label='Approved → verified')])
 nodes=[n(f'n{i}',icon='service') for i in range(60)];edges=[e(f'e{i}',f'n{i}',f'n{i+12}') for i in range(48)]
 yield 'sixty-node-dag',model('60-node rendering benchmark',nodes,edges)
 for p in sorted((ROOT/'examples').glob('*.json')):yield p.stem,diagram.read_json(p)

def run(out,mode):
 out.mkdir(parents=True,exist_ok=True)
 result={'ok':True,'loadMode':mode,'runtimeNetwork':'offline and request-blocked','visualReview':'not-run','cases':[],'browserVersion':None,'versions':diagram.read_json(ROOT/'assets/vendor/manifest.json')['versions']}
 with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
  browser=browser_check.launch(p);result['browserVersion']=browser.version
  def exercise(name,m,callback=None,replace=None,expect='ready'):
   start=time.monotonic();record={'case':name,'ok':False};ctx=None
   try:
    artifact=Path(tmp)/f'{name}.html';receipt=diagram.build(m,artifact,ROOT/'assets/icons',json.dumps(m).encode());assert receipt['ok'],receipt
    if replace:artifact.write_text(replace(artifact.read_text()))
    ctx=browser.new_context(viewport={'width':1440,'height':900},offline=True)
    requests=[];ctx.route('**/*',lambda route:(requests.append(route.request.url),route.abort()))
    page=ctx.new_page();pageerrors=[];page.on('pageerror',lambda ex:pageerrors.append(str(ex)))
    state=browser_check.load(page,artifact,mode);assert state==expect,page.evaluate('() => ({state:__DIAGRAM__.state,errors:__DIAGRAM__.errors})')
    if expect=='ready':
     a=page.evaluate(browser_check.AUDIT);assert not a['errors'],a['errors'];assert a['visibleEdges']==len(m['edges']),(a['visibleEdges'],len(m['edges']));assert not pageerrors,pageerrors
     assert not requests,requests
     assert page.evaluate('() => window.HACKED === undefined')
     assert page.evaluate('() => JSON.stringify(__DIAGRAM__.model)')==json.dumps(m,ensure_ascii=False,separators=(',',':'))
     record.update(nodes=len(m['nodes']),edges=len(m['edges']),warnings=a['warnings'],initialLabelPixels=a['labelPixels'])
     if callback:callback(page,m)
     if name in ['knowledge-workspace','creative-production','work-item-lifecycle','nested-cross-boundary','appearance-routing','unicode-and-injection','sixty-node-dag']:
      page.screenshot(path=str(out/(name+'.png')),full_page=True)
    else:
     assert page.locator('#status').get_attribute('class')=='error'
     assert page.locator('#relayout').is_disabled()
     assert page.evaluate('() => __DIAGRAM__.errors.length > 0')
     record['expectedFailure']=page.evaluate('() => __DIAGRAM__.errors')
    record['ok']=True
   except Exception as exc:record['error']=str(exc);result['ok']=False
   finally:
    if ctx:ctx.close()
    record['durationSeconds']=round(time.monotonic()-start,4);result['cases'].append(record)
  for name,m in fixtures():exercise(name,m)
  creative=diagram.read_json(ROOT/'examples/creative-production.json');knowledge=diagram.read_json(ROOT/'examples/knowledge-workspace.json')
  styled=model('Appearance and routing',[n('outer',kind='group',appearance={'fill':'#E0F2FE','stroke':'#0284C7','textColor':'#0C4A6E','strokeWidth':2}),n('inner',kind='group',parent='outer',icon='folder',appearance={'fill':'#F3E8FF','stroke':'#7C3AED','textColor':'#4C1D95','strokeWidth':2,'groupLabel':'inside'}),n('source',label='External customer\nauthentication\nportal',parent='inner',icon='service',appearance={'shape':'oval'}),n('decision',label='Review signing decision',parent='inner',appearance={'shape':'diamond'}),n('square',parent='inner',appearance={'shape':'square'}),n('input',parent='inner',appearance={'shape':'parallelogram'}),n('card',parent='inner',appearance={'shape':'rectangle'})],[e('source-decision','source','decision',label='Assess'),e('source-square','source','square',label='Store'),e('source-input','source','input',label='Transform'),e('decision-source','decision','source',label='Revise'),e('input-card','input','card',label='Publish')]);styled['layout']={'direction':'UP','spacing':80,'layerSpacing':140}
  def appearance(page,m):
   assert page.locator('#direction').input_value()=='UP'
   actual=page.evaluate('''() => Object.fromEntries(['source','decision','square','input','card'].map(id=>[id,__DIAGRAM__.cy.getElementById(id).pstyle('shape').value]))''')
   assert actual=={'source':'ellipse','decision':'diamond','square':'square','input':'rhomboid','card':'rectangle'},actual
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('decision').data('displayLabel')")=='Review\nsigning\ndecision'
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('inner').pstyle('text-halign').value")=='left'
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('inner').pstyle('background-width').pfValue[0]")==20
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('source').pstyle('background-width').pfValue[0]")==24
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('inner').parent().id()")=='outer'
   assert page.evaluate("() => __DIAGRAM__.cy.getElementById('source').parent().id()")=='inner'
  exercise('appearance-routing',styled,appearance)
  def repeat(page,m):
   a=page.evaluate('() => __DIAGRAM__.cy.nodes().map(n=>({id:n.id(),x:n.position("x"),y:n.position("y")}))')
   assert page.evaluate('() => __DIAGRAM__.layout()') is True
   b=page.evaluate('() => __DIAGRAM__.cy.nodes().map(n=>({id:n.id(),x:n.position("x"),y:n.position("y")}))')
   assert max(abs(x[k]-y[k]) for x,y in zip(a,b) for k in ['x','y'])<.1,(a,b)
  exercise('repeat-layout-stability',knowledge,repeat)
  def filtered(page,m):
   full=page.evaluate('() => __DIAGRAM__.cy.elements(":visible").boundingBox().w')
   page.evaluate('async () => await __DIAGRAM__.setView("assets")')
   visible=page.evaluate('() => __DIAGRAM__.cy.nodes(":visible").map(n=>n.id()).sort()')
   assert visible==['editor','library','production','studio'],visible
   assert page.evaluate('() => __DIAGRAM__.cy.edges(":visible").map(e=>e.id())')==['save']
   assert page.evaluate('() => __DIAGRAM__.cy.elements(":visible").boundingBox().w')<full
   before=page.evaluate('() => __DIAGRAM__.cy.getElementById("editor").width()')
   page.evaluate('() => __DIAGRAM__.focus("editor","downstream")')
   assert before==page.evaluate('() => __DIAGRAM__.cy.getElementById("editor").width()')
   assert page.evaluate('() => __DIAGRAM__.layout()') is True
   assert page.evaluate('() => __DIAGRAM__.cy.edges(":visible").map(e=>e.id())')==['save']
   page.evaluate('async () => await __DIAGRAM__.setView("all")')
   assert page.evaluate('() => __DIAGRAM__.cy.edges(":visible").length')==len(m['edges'])
  exercise('filter-ancestors-and-relayout',creative,filtered)
  def highlight(page,m):
   page.evaluate('() => __DIAGRAM__.focus("knowledge","upstream")')
   a=page.evaluate('() => __DIAGRAM__.cy.nodes(":visible").filter(n=>!n.isParent()&&!n.hasClass("dim")).map(n=>n.id()).sort()')
   assert a==['curation','documents','interviews','knowledge'],a
   page.evaluate('() => __DIAGRAM__.focus("knowledge","downstream")')
   a=page.evaluate('() => __DIAGRAM__.cy.nodes(":visible").filter(n=>!n.isParent()&&!n.hasClass("dim")).map(n=>n.id()).sort()')
   assert a==['answers','knowledge','reports'],a
  exercise('upstream-downstream-semantics',knowledge,highlight)
  def export_restore(page,m):
   page.evaluate('async () => {await __DIAGRAM__.setView("assets");__DIAGRAM__.focus("editor");}')
   state=page.evaluate('() => __DIAGRAM__.cy.elements().map(e=>[e.id(),e.classes()])')
   positions=page.evaluate('() => __DIAGRAM__.cy.nodes().filter(n=>!n.isParent()).map(n=>[n.id(),n.position()])')
   viewport=page.evaluate('() => ({zoom:__DIAGRAM__.cy.zoom(),pan:__DIAGRAM__.cy.pan()})')
   for all_ in [False,True]:
    assert page.evaluate('''async (all) => {const blob=await __DIAGRAM__.exportPNG(all);const url=URL.createObjectURL(blob);const img=new Image();img.src=url;await img.decode();URL.revokeObjectURL(url);return blob.type==='image/png'&&img.width>0&&img.height>0&&img.width<=1800&&img.height<=1200;}''',all_)
    current_state=page.evaluate('() => __DIAGRAM__.cy.elements().map(e=>[e.id(),e.classes()])');assert state==current_state,(state,current_state)
    current_positions=page.evaluate('() => __DIAGRAM__.cy.nodes().filter(n=>!n.isParent()).map(n=>[n.id(),n.position()])');assert positions==current_positions,(positions,current_positions)
    current_viewport=page.evaluate('() => ({zoom:__DIAGRAM__.cy.zoom(),pan:__DIAGRAM__.cy.pan()})');assert viewport==current_viewport,(viewport,current_viewport)
  exercise('png-view-all-restore',creative,export_restore)
  def search(page,m):
   page.evaluate('async () => await __DIAGRAM__.setView("assets")');page.fill('#search','Client');page.press('#search','Enter')
   assert page.evaluate('() => __DIAGRAM__.cy.getElementById("client").visible()')
   assert page.locator('#inspector h2').inner_text()=='Client'
   assert page.evaluate('() => __DIAGRAM__.cy.edges(":visible").length')==5
  exercise('keyboard-search-hidden-node',creative,search)
  def public_controls(page,m):
   page.select_option('#edge-kind','data')
   assert page.evaluate('() => __DIAGRAM__.cy.edges(":visible").map(e=>e.id())')==['save']
   page.select_option('#edge-kind','all')
   page.click('#text-view')
   assert page.locator('#text-dialog').is_visible()
   text=page.locator('#text-content').inner_text()
   assert m['nodes'][0]['label'] in text and m['edges'][0]['label'] in text
   page.click('[data-close="text-dialog"]')
   with page.expect_download() as pending:page.click('#download-model')
   assert json.loads(Path(pending.value.path()).read_text())==m
  exercise('relationship-filter-text-and-source-download',creative,public_controls)
  def down(page,m):
   page.select_option('#direction','DOWN');assert browser_check.wait_ready(page)=='ready'
   pairs=page.evaluate('() => __DIAGRAM__.cy.edges().map(e=>[e.source().position("y"),e.target().position("y")])')
   assert all(b>a for a,b in pairs),pairs
  exercise('change-direction',knowledge,down)
  def concurrency(page,m):
   x=page.evaluate('async () => {const a=__DIAGRAM__.layout();const b=__DIAGRAM__.layout();return [await a,await b]}');assert x==[True,False],x
  exercise('single-inflight-layout',knowledge,concurrency)
  exercise('visible-elk-rejection',knowledge,replace=lambda s:s.replace("'elk.algorithm':'layered'","'elk.algorithm':'definitely-invalid'"),expect='error')
  browser.close()
 result['passed']=sum(c['ok'] for c in result['cases']);result['total']=len(result['cases']);result['durationSeconds']=round(sum(c['durationSeconds'] for c in result['cases']),3)
 (out/'regression-report.json').write_text(json.dumps(result,indent=2)+'\n')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);p.add_argument('--load',choices=['file','content'],default='file');a=p.parse_args();r=run(a.out,a.load);print(json.dumps(r,indent=2));sys.exit(0 if r['ok'] else 1)
