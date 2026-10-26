import json,unittest
import test_pipeline as fixtures
class TaskAmendTests(unittest.TestCase):
    setUp=fixtures.LoopTests.setUp;tearDown=fixtures.LoopTests.tearDown
    write=fixtures.LoopTests.write;hash=fixtures.LoopTests.hash;call=fixtures.LoopTests.call;prepare=fixtures.LoopTests.prepare;render=fixtures.LoopTests.render;review=fixtures.LoopTests.review
    def correction(self):
        task=json.loads((self.root/'task.json').read_text());task['factual_data'].append('Audited original fixture weekly totals2,1,4,3,2,4,2');self.write('corrected.json',task)
        return self.call('task-amend','--campaign','crm','--task','corrected.json','--reason','Synthetic fixture transcription correction; source unchanged','--author','Fixture coordinator')
    def test_logged_correction_preserves_history_and_budget(self):
        self.prepare();self.render();self.review(visual='candidate',findings=False);old_prompt_hash=self.hash('campaigns/crm/one/1/prompt.json');old_review_hash=self.hash('campaigns/crm/one/1/review.json')
        change=self.correction();self.assertFalse(change['budgets_changed']);self.assertEqual(change['revision'],1)
        original=json.loads((self.root/'campaigns/crm/task-origin.json').read_text());self.assertEqual(original['task'],json.loads((self.root/'task.json').read_text()))
        self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False);self.call('export','--campaign','crm','--variant','one','--iteration','1',ok=False)
        self.write('spec.json',self.spec);self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json')
        self.assertEqual(self.hash('campaigns/crm/one/1/prompt.json'),old_prompt_hash);self.assertEqual(self.hash('campaigns/crm/one/1/review.json'),old_review_hash)
        latest=json.loads((self.root/'campaigns/crm/one/2/prompt.json').read_text());self.assertEqual(latest['task_sha256'],change['new_task_sha256']);self.assertEqual(latest['task_revision'],1)
        self.render(2);self.review(2,visual='candidate',findings=False);self.call('export','--campaign','crm','--variant','one','--iteration','2');self.call('cleanup','--campaign','crm')
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)
    def test_unlogged_mutation_cannot_be_legitimized(self):
        self.prepare();self.render();self.review();state=json.loads((self.root/'campaigns/crm/campaign.json').read_text());state['task']['job']='Unlogged change';self.write('campaigns/crm/campaign.json',state)
        task=json.loads((self.root/'task.json').read_text());task['job']='Different correction';self.write('corrected.json',task)
        self.call('task-amend','--campaign','crm','--task','corrected.json','--reason','Attempt to disguise mutation','--author','Fixture',ok=False)
        self.assertFalse((self.root/'campaigns/crm/task-origin.json').exists())
    def test_amendment_chain_tamper_invalidates_next_compile(self):
        self.prepare();self.render();self.review(visual='candidate',findings=False);self.correction()
        path='campaigns/crm/task-amendments/1.json';record=json.loads((self.root/path).read_text());record['reason']='Changed historical reason';self.write(path,record)
        self.write('spec.json',self.spec);self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)
if __name__=='__main__':unittest.main(verbosity=2)
