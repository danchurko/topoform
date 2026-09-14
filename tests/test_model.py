"""Deterministic tests for schema, assets, injection boundaries, and atomic build behavior."""
from pathlib import Path
import copy, json, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import diagram

def base():return {'schemaVersion':1,'title':'Test','nodes':[{'id':'a','label':'Source'},{'id':'b','label':'Target'}],'edges':[{'id':'ab','source':'a','target':'b'}]}

class ModelTests(unittest.TestCase):
 def assertBad(self,m,code):
  r=diagram.validate(m);self.assertFalse(r['ok'],r);self.assertIn(code,{x['code'] for x in r['errors']})
 def test_examples(self):
  for p in (ROOT/'examples').glob('*.json'):
   with self.subTest(path=p.name):self.assertTrue(diagram.validate(diagram.read_json(p))['ok'])
 def test_empty(self):self.assertTrue(diagram.validate({'schemaVersion':1,'title':'Empty','nodes':[],'edges':[]})['ok'])
 def test_not_object(self):self.assertBad([], 'TYPE')
 def test_missing_arrays(self):self.assertBad({'title':'x','schemaVersion':1},'TYPE')
 def test_bool_schema(self):m=base();m['schemaVersion']=True;self.assertBad(m,'SCHEMA_VERSION')
 def test_unknown_field(self):m=base();m['ports']=[];self.assertBad(m,'UNKNOWN_FIELD')
 def test_duplicate_id(self):m=base();m['nodes'][1]['id']='a';self.assertBad(m,'DUPLICATE_ID')
 def test_edge_node_namespace(self):m=base();m['edges'][0]['id']='a';self.assertBad(m,'DUPLICATE_ID')
 def test_missing_endpoint(self):m=base();m['edges'][0]['target']='no';self.assertBad(m,'ENDPOINT_MISSING')
 def test_non_string_endpoint(self):m=base();m['edges'][0]['target']=[];self.assertBad(m,'ID')
 def test_missing_parent(self):m=base();m['nodes'][0]['parent']='missing';self.assertBad(m,'PARENT_MISSING')
 def test_multiple_parents_rejected(self):m=base();m['nodes'][0]['parent']=['b'];self.assertBad(m,'ID')
 def test_parent_kind(self):m=base();m['nodes'][0]['parent']='b';self.assertBad(m,'PARENT_KIND')
 def test_parent_cycle(self):m=base();m['nodes'][0].update(kind='group',parent='b');m['nodes'][1].update(kind='group',parent='a');self.assertBad(m,'PARENT_CYCLE')
 def test_empty_group(self):m=base();m['nodes'][0]['kind']='group';self.assertBad(m,'EMPTY_GROUP')
 def test_group_endpoint(self):m=base();m['nodes']+=[{'id':'g','kind':'group','label':'G'}];m['nodes'][0]['parent']='g';m['edges'][0]['source']='g';self.assertBad(m,'GROUP_ENDPOINT')
 def test_reserved_ids(self):
  for key in diagram.RESERVED:
   m=base();m['nodes'][0]['id']=key;self.assertBad(m,'ID')
 def test_punctuation_ids(self):m=base();m['nodes'][0]['id']='a.b:c-d_e';m['edges'][0]['source']='a.b:c-d_e';self.assertTrue(diagram.validate(m)['ok'])
 def test_layout_unknown(self):m=base();m['layout']={'ports':[]};self.assertBad(m,'UNKNOWN_FIELD')
 def test_layout_direction(self):m=base();m['layout']={'direction':'DIAGONAL'};self.assertBad(m,'DIRECTION')
 def test_spacing_nan(self):m=base();m['layout']={'spacing':float('nan')};self.assertBad(m,'SPACING')
 def test_spacing_boolean(self):m=base();m['layout']={'spacing':True};self.assertBad(m,'SPACING')
 def test_appearance_options(self):
  for shape in diagram.APPEARANCE_SHAPES:
   with self.subTest(shape=shape):m=base();m['nodes'][0]['appearance']={'shape':shape,'fill':'#E0F2FE','stroke':'#0369A1','textColor':'#0C4A6E','strokeWidth':2};self.assertTrue(diagram.validate(m)['ok'])
 def test_appearance_rejects_bad_values(self):
  for key,value,code in [('shape','hexagon','APPEARANCE_SHAPE'),('fill','#fff','APPEARANCE_COLOR'),('strokeWidth',7,'APPEARANCE_STROKE_WIDTH')]:
   with self.subTest(key=key):m=base();m['nodes'][0]['appearance']={key:value};self.assertBad(m,code)
 def test_appearance_shape_not_group(self):
  m=base();m['nodes'][0].update(kind='group');m['nodes'][1]['parent']='a';m['nodes'][0]['appearance']={'shape':'square'};self.assertBad(m,'APPEARANCE_SHAPE_GROUP')
 def test_appearance_group_label_only_group(self):
  m=base();m['nodes'][0]['appearance']={'groupLabel':'inside'};self.assertBad(m,'APPEARANCE_GROUP_LABEL_NODE')
  m=base();m['nodes'][0].update(kind='group');m['nodes'][1]['parent']='a';m['nodes'][0]['appearance']={'groupLabel':'inside'};m['edges']=[];self.assertTrue(diagram.validate(m)['ok'])
 def test_bad_kind(self):m=base();m['nodes'][0]['kind']={};self.assertBad(m,'TEXT')
 def test_bad_tags(self):m=base();m['nodes'][0]['tags']=[{}];self.assertBad(m,'TYPE')
 def test_links_reject_active_schemes(self):
  for u in ['javascript:alert(1)','data:text/html,test','//example.com','https://u:p@example.com','https://example.com/\nhi']:
   m=base();m['nodes'][0]['links']=[{'label':'x','url':u}];self.assertBad(m,'LINK_SCHEME')
 def test_https_link(self):m=base();m['nodes'][0]['links']=[{'label':'x','url':'https://example.org/a?q=1'}];self.assertTrue(diagram.validate(m)['ok'])
 def test_evidence_required(self):m=base();m['nodes'][0]['evidence']={'status':'observed'};self.assertBad(m,'EVIDENCE')
 def test_unknown_view_node(self):m=base();m['views']=[{'id':'v','label':'V','nodeIds':['x']}];self.assertBad(m,'VIEW_NODE')
 def test_reserved_view(self):m=base();m['views']=[{'id':'all','label':'V','nodeIds':['a']}];self.assertBad(m,'DUPLICATE_VIEW')
 def test_icon_unknown(self):m=base();m['nodes'][0]['icon']='unknown';r=diagram.validate(m,{'document'});self.assertFalse(r['ok'])
 def test_self_loop_warning_not_error(self):m=base();m['edges'][0]['target']='a';r=diagram.validate(m);self.assertTrue(r['ok']);self.assertIn('SELF_LOOP',{w['code'] for w in r['warnings']})
 def test_parallel_and_cycle(self):m=base();m['edges']+=[{'id':'ab2','source':'a','target':'b'},{'id':'ba','source':'b','target':'a'}];self.assertTrue(diagram.validate(m)['ok'])
 def test_duplicate_json_key(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{"a":1,"a":2}')
   with self.assertRaises(ValueError):diagram.read_json(p)
 def test_json_nan(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{"a":NaN}')
   with self.assertRaises(ValueError):diagram.read_json(p)
 def test_json_exponent_overflow(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{"a":1e9999}')
   with self.assertRaises(ValueError):diagram.read_json(p)
 def test_icon_registry_active_link(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);entry=copy.deepcopy(diagram.read_json(ROOT/'assets/icons/manifest.json')['person']);entry['source']='javascript:alert(1)';(p/'manifest.json').write_text(json.dumps({'person':entry}));m=base();m['nodes'][0]['icon']='person'
   with self.assertRaises(ValueError):diagram.icons_payload(m,p)
 def test_icon_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);entry=copy.deepcopy(diagram.read_json(ROOT/'assets/icons/manifest.json')['person']);(p/entry['path']).write_text('<svg viewBox="0 0 24 24"/>');(p/'manifest.json').write_text(json.dumps({'person':entry}));m=base();m['nodes'][0]['icon']='person'
   with self.assertRaises(ValueError):diagram.icons_payload(m,p)
 def test_safe_json(self):
  value={'x':'</script><img src=x onerror=alert(1)>\u2028&__RUNTIME__'};encoded=diagram.safe_json(value);self.assertNotIn('</script>',encoded);self.assertEqual(json.loads(encoded),value)
 def test_svg_static(self):
  svg=diagram.sanitize_svg('<svg width="640" height="512" viewBox="0 0 640 512"><path fill="currentColor" d="M0 0h640v512z"/></svg>')
  self.assertIn('#334155',svg);self.assertIn('width="24"',svg);self.assertIn('height="24"',svg);self.assertIn('viewBox="0 0 640 512"',svg)
 def test_svg_active_rejected(self):
  for body in ['<script>alert(1)</script>','<image href="https://x"/>','<foreignObject/>','<path onload="x"/>','<path fill="url(#a)"/>','<use href="#a"/>']:
   with self.subTest(body=body),self.assertRaises(ValueError):diagram.sanitize_svg('<svg viewBox="0 0 24 24">'+body+'</svg>')
 def test_svg_entities_rejected(self):
  with self.assertRaises(ValueError):diagram.sanitize_svg('<!DOCTYPE svg><svg viewBox="0 0 24 24"/>')
 def test_svg_invalid_viewbox(self):
  for vb in ['0 0 NaN 2','0 0 -1 20','0 0 0 4','0 0 10001 20','0 0 24']:
   with self.assertRaises(ValueError):diagram.sanitize_svg(f'<svg viewBox="{vb}"/>')
 def test_asset_path_escape(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'r';root.mkdir();outside=Path(d)/'x';outside.write_text('x')
   with self.assertRaises(ValueError):diagram.local_file(root,'../x')
   (root/'link').symlink_to(outside)
   with self.assertRaises(ValueError):diagram.local_file(root,'link')
 def test_vendor_integrity(self):self.assertEqual(diagram.vendor_payload()[2]['versions']['cytoscape'],'3.33.1')
 def test_all_icons_sanitise(self):
  for p in (ROOT/'assets/icons').glob('*.svg'):
   with self.subTest(icon=p.name):diagram.sanitize_svg(p.read_text())
 def test_build_determinism(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.html';m=base();r=diagram.build(m,p,ROOT/'assets/icons',b'{}');a=p.read_bytes();diagram.build(m,p,ROOT/'assets/icons',b'{}');self.assertEqual(a,p.read_bytes());self.assertTrue(r['ok'])
 def test_failed_validation_keeps_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.html';p.write_text('last-good');m=base();m['edges'][0]['target']='missing';r=diagram.build(m,p,ROOT/'assets/icons',b'{}');self.assertFalse(r['ok']);self.assertEqual(p.read_text(),'last-good')
 def test_build_script_payload_inert(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.html';m=base();m['nodes'][0]['label']='</script><script>window.HACKED=1</script>';diagram.build(m,p,ROOT/'assets/icons',b'{}');s=p.read_text();self.assertNotIn(m['nodes'][0]['label'],s)
if __name__=='__main__':unittest.main(verbosity=2)
