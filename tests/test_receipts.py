import json,subprocess,sys,unittest
import test_pipeline as fixtures

class ReceiptTests(unittest.TestCase):
    setUp=fixtures.LoopTests.setUp;tearDown=fixtures.LoopTests.tearDown
    write=fixtures.LoopTests.write;hash=fixtures.LoopTests.hash;call=fixtures.LoopTests.call
    def normalize(self,data,ok=True,out='normalized.json'):
        self.write('receipt.json',data)
        result=subprocess.run([sys.executable,str(fixtures.CLI.parent/'tool_receipt.py'),'--workspace',str(self.root),'--receipt','receipt.json','--out',out],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0 if ok else 2,result.stdout+result.stderr);return json.loads(result.stdout)
    def mobbin_fixture(self):
        return {'provider':'mobbin','tool':'mcp__mobbin__search_screens','retrieved_at':'2026-01-01T00:00:00Z','request':{'platform':'web','query':'Synthetic fixture register','limit':2,'image_format':'jpg','output_destination':'code','task_intent':'Synthetic test task.'},'result':{'screens':[{'id':'provider-id','app_name':'Fixture App','platform':'web','mobbin_url':'https://mobbin.com/screens/fixture','image_url':'https://example.org/fixture.jpg'}],'ai_usage_notice':{'text':'**Synthetic notice**\n\nPreserve this formatting.'}},'selected_id':'provider-id','expected_app':'Fixture App','id':'mobbin-fixture','asset_path':'reference.png','asset_sha256':self.hash('reference.png'),'observed':self.analysis['observed'],'rights':self.analysis['rights'],'traits':self.analysis['traits'],'notice_presented_verbatim':True,'presented_notice_text':'**Synthetic notice**\n\nPreserve this formatting.'}
    def test_actual_receipt_shape_notice_and_reference_provenance(self):
        data=self.mobbin_fixture();report=self.normalize(data);self.assertEqual(report['required_usage_notice'],data['result']['ai_usage_notice']['text'])
        self.call('reference','--campaign','crm','--analysis','normalized.json');self.write('spec.json',self.spec)
        self.call('compile','--campaign','crm','--variant','one','--reference','mobbin-fixture','--spec','spec.json')
        data['result']['screens'][0]['app_name']='Changed receipt';self.write('receipt.json',data)
        self.call('render','--campaign','crm','--variant','one','--iteration','1','--source','generated.html','--png','render.png','--generator','fixture',ok=False)
    def test_notice_identity_and_unsupported_argument_rejected(self):
        for mode in ('notice','identity','platform','argument','metadata-only'):
            data=self.mobbin_fixture()
            if mode=='notice':data['presented_notice_text']='Paraphrased notice'
            if mode=='identity':data['expected_app']='Different app'
            if mode=='platform':data['result']['screens'][0]['platform']='ios'
            if mode=='argument':data['request']['output_mode']='code'
            if mode=='metadata-only':data['observed']['method']='metadata-only'
            self.normalize(data,ok=False)
    def test_same_campaign_task_intent_must_match(self):
        data=self.mobbin_fixture();self.normalize(data);self.call('reference','--campaign','crm','--analysis','normalized.json')
        # Preserve first receipt; a second distinct raw receipt cannot silently redefine task intent.
        first=(self.root/'receipt.json').read_bytes();self.write('first-receipt.json',first)
        analysis=json.loads((self.root/'campaigns/crm/references/mobbin-fixture.json').read_text());analysis['adapter_receipt']['path']='first-receipt.json';self.write('campaigns/crm/references/mobbin-fixture.json',analysis)
        data['id']='second-fixture';data['request']['task_intent']='A different product task.';self.normalize(data,out='second.json')
        self.call('reference','--campaign','crm','--analysis','second.json',ok=False)
    def test_component_api_license_and_real_source_hashes(self):
        self.write('component-sources/dialog.tsx','// Synthetic original fixture, not actual shadcn source\nexport const Dialog=()=>null;')
        data={'provider':'shadcn','tool':'mcp__shadcn__view_items_in_registries','retrieved_at':'2026-01-01T00:00:00Z','request':{'items':['@fixture/dialog']},'result':{'content':['Synthetic test source receipt']},'registry':'@fixture','registry_style':'synthetic','framework_version':'synthetic-test-version','files':[{'path':'component-sources/dialog.tsx','sha256':self.hash('component-sources/dialog.tsx')}],'license_evidence':'Original synthetic fixture rights','api':{'controlled':'Fixture API'},'local_library_gate':'not-run'}
        self.normalize(data);data['files'][0]['sha256']='0'*64;self.normalize(data,ok=False,out='bad.json')
        data['files'][0]['sha256']=self.hash('component-sources/dialog.tsx');data['local_library_gate']='pass';self.normalize(data,ok=False,out='pass.json')

if __name__=='__main__':unittest.main(verbosity=2)
