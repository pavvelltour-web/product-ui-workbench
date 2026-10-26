"""Synthetic evidence gates only; uniform fixture PNGs are not design-quality observations."""
from pathlib import Path
import copy,hashlib,json,sys,tempfile,unittest,struct,zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from theme_matrix import validate,verify
from pipeline import GateError

def plan():
 return {'version':'1.0','theme_contract':'Same job, fixture and geometry; independently tuned paired colors','concepts':[{'id':'example','product':'operations','family':'glass','first':'Inspect itemA','layout':'Queue and context','themes':['light','dark'],'viewports':{'desktop':[320,400],'mobile':[300,400]}}],'type_contract':{'roles':{r:[14,20,500] for r in ['page','section','entity','body','label','meta']}},'qa_contract':['local-fixture-check']}

def png(w,h):
 def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(w*3))*h))+chunk(b'IEND',b'')

class MatrixTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.r=Path(self.temp.name).resolve();(self.r/'build').mkdir();(self.r/'build/index.html').write_text('Synthetic closure; not real browser execution');self.write('matrix.json',plan());self.write('manifest.json',{'root':'build','entry':'index.html','ownership':'active','files':[{'path':'index.html','sha256':self.pin('build/index.html')['sha256']}]});self.index={'version':'1.0','matrix_sha256':self.pin('matrix.json')['sha256'],'captures':[]};self.qa={'passed':True,'closure_unchanged':True,'matrix_sha256':self.pin('matrix.json')['sha256'],'source_manifest':self.pin('manifest.json'),'cases':[]}
  for t in ['light','dark']:
   shots=[]
   for v,wh in plan()['concepts'][0]['viewports'].items():
    n=f'{t}-{v}.png';(self.r/n).write_bytes(png(*wh));shots.append({'state':v,**self.pin(n)})
    self.qa['cases'].append({'variant':'example','theme':t,'viewport':v,'passed':True,'checks':{'local-fixture-check':True},'semantic':{'record':'A','count':1},'geometry':{'width':200,'height':44}})
   cap={'passed':True,'view_query':'variant=example&theme='+t,'source_manifest':{**self.pin('manifest.json'),'closure':json.loads((self.r/'manifest.json').read_text())},'screenshots':shots};self.write(t+'.json',cap);self.index['captures'].append({'study_id':'example','theme':t,'capture':self.pin(t+'.json')})
  self.save()
 def tearDown(self):self.temp.cleanup()
 def write(self,n,data):(self.r/n).write_text(json.dumps(data),encoding='utf-8')
 def pin(self,n):return {'path':n,'sha256':hashlib.sha256((self.r/n).read_bytes()).hexdigest()}
 def save(self):self.write('index.json',self.index);self.write('qa.json',self.qa)
 def runcheck(self):return verify(self.r,'matrix.json','index.json','qa.json')
 def test_complete_pair_and_both_viewports(self):self.assertEqual(self.runcheck()['viewport_cases'],4)
 def test_missing_or_duplicate_dark_capture(self):
  self.index['captures'][1]=self.index['captures'][0];self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_wrong_declared_theme_route(self):
  p=self.r/'dark.json';c=json.loads(p.read_text());c['view_query']='variant=example&theme=light';self.write('dark.json',c);self.index['captures'][1]['capture']=self.pin('dark.json');self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_stale_png_rejected(self):
  (self.r/'dark-mobile.png').write_bytes(png(301,400))
  with self.assertRaises(GateError):self.runcheck()
 def test_wrong_image_dimensions_rejected_even_after_repin(self):
  (self.r/'dark-mobile.png').write_bytes(png(301,400));c=json.loads((self.r/'dark.json').read_text());c['screenshots'][1]=dict(state='mobile',**self.pin('dark-mobile.png'));self.write('dark.json',c);self.index['captures'][1]['capture']=self.pin('dark.json');self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_pair_semantic_drift_rejected(self):
  self.qa['cases'][2]['semantic']['record']='B';self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_pair_geometry_drift_rejected(self):
  self.qa['cases'][2]['geometry']['width']=240;self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_missing_viewport_or_claim_only_fails(self):
  self.qa['cases'].pop();self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_failing_named_check_not_hidden_by_summary(self):
  self.qa['cases'][0]['checks']['local-fixture-check']=False;self.save()
  with self.assertRaises(GateError):self.runcheck()
 def test_incomplete_and_duplicate_contract_rejected(self):
  for mutate in [lambda d:d['concepts'][0].update(themes=['light']),lambda d:d['concepts'].append(copy.deepcopy(d['concepts'][0])),lambda d:d['type_contract']['roles'].pop('meta')]:
   d=plan();mutate(d)
   with self.assertRaises(GateError):validate(d)
if __name__=='__main__':unittest.main()
