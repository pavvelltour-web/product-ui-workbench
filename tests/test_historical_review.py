import json,unittest
import test_pipeline as fixtures
class HistoricalReviewTests(unittest.TestCase):
    setUp=fixtures.LoopTests.setUp;tearDown=fixtures.LoopTests.tearDown
    write=fixtures.LoopTests.write;hash=fixtures.LoopTests.hash;call=fixtures.LoopTests.call;prepare=fixtures.LoopTests.prepare;render=fixtures.LoopTests.render
    def record(self,best=False,human='not-run'):
        return {'observer':'actual fixture test','inspected_at':'2026-01-01T00:00:00Z','source_sha256':self.hash('generated.html'),'png_sha256s':[self.hash('render.png')],'pixel_observations':[{'png_sha256':self.hash('render.png'),'observation':'Synthetic recovery-route test attestation'}],'technical':{'status':'fail','evidence':'Synthetic actual failure record'},'visual':{'status':'revise','evidence':'Synthetic defect'},'human':{'status':human,'evidence':'No approval'},'independent':{'technical':'not-run','visual':'not-run','evidence':'No independent'},'findings':[{'id':'failed-save','category':'technical','severity':'major','evidence':'Fixture failure','action':'Repair next generation'}],'best_so_far':best,'replace_reference':False}
    def amend(self):
        task=json.loads((self.root/'task.json').read_text());task['factual_data'].append('Audited correction');self.write('corrected.json',task);self.call('task-amend','--campaign','crm','--task','corrected.json','--reason','Actual fixture correction','--author','Fixture coordinator')
    def test_failed_round_review_after_amend_is_historical_only(self):
        self.prepare();self.render();self.write('review.json',self.record(best=True))
        self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
        self.amend();self.write('review.json',self.record());self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
        value=self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json','--historical-task');self.assertTrue(value['historical_only']);self.assertIsNone(value['best_so_far'])
        self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False);self.call('export','--campaign','crm','--variant','one','--iteration','1',ok=False)
        self.spec['delta_findings']=['failed-save'];self.write('spec.json',self.spec);self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json')
        review=json.loads((self.root/'campaigns/crm/one/1/review.json').read_text());self.assertIn('historical-only',review['historical_task_context']['status'])
    def test_historical_route_cannot_select_accept_or_reuse_stale_source(self):
        self.prepare();self.render();self.amend()
        for best,human in ((True,'not-run'),(False,'accepted')):
            self.write('review.json',self.record(best,human));self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json','--historical-task',ok=False)
        self.write('review.json',self.record());self.write('generated.html','Changed actual source');self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json','--historical-task',ok=False)
if __name__=='__main__':unittest.main(verbosity=2)
