/* Original composition, MIT; uses retained actual shadcn APIs. Integration/visual review not-run. */
import * as React from 'react';
import { Button } from '../components/react-shadcn/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '../components/react-shadcn/ui/dialog';
import { Textarea } from '../components/react-shadcn/ui/textarea';

type Record = {id:string;title:string;nextAction:string};
export function QueueDetail({records,save}:{records:Record[];save:(id:string,action:string)=>Promise<void>}) {
  const [id,setId]=React.useState<string|null>(null);
  const [draft,setDraft]=React.useState('');
  const [pending,setPending]=React.useState(false);
  const [error,setError]=React.useState('');
  const selected=records.find(item=>item.id===id);
  function close(){if(!pending){setId(null);setDraft('');setError('')}}
  async function commit(event:React.FormEvent){
    event.preventDefault();if(!selected||pending)return;
    if(!draft.trim()){setError('A next action is required.');return}
    setPending(true);setError('');
    try{await save(selected.id,draft.trim());setId(null);setDraft('')}
    catch{setError('Save failed. Edits remain available for retry.')}
    finally{setPending(false)}
  }
  return <section aria-label="Original work queue">
    <ul>{records.map(item=><li key={item.id}><Button variant="ghost" onClick={()=>{setId(item.id);setDraft(item.nextAction)}}>{item.title}</Button></li>)}</ul>
    <Dialog open={!!selected} onOpenChange={open=>{if(!open)close()}}>
      <DialogContent showCloseButton={!pending} onEscapeKeyDown={event=>{if(pending)event.preventDefault()}} onPointerDownOutside={event=>{if(pending)event.preventDefault()}}>
        <DialogTitle>{selected?.title}</DialogTitle><DialogDescription>Edit one record; failed save preserves this draft.</DialogDescription>
        <form onSubmit={commit}><label htmlFor="example-next-action">Next action</label><Textarea id="example-next-action" value={draft} onChange={event=>setDraft(event.target.value)} disabled={pending} required aria-describedby={error?'example-save-error':undefined}/>
          {error&&<p id="example-save-error" role="alert">{error}</p>}<Button type="submit" disabled={pending}>{pending?'Saving…':error?'Retry save':'Save'}</Button><Button type="button" variant="outline" disabled={pending} onClick={close}>Cancel</Button>
        </form>
      </DialogContent>
    </Dialog>
  </section>
}
