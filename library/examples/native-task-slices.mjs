/* Original compositional examples, MIT. Browser behavior not yet evaluated as this example. */
import { el, createSelectionModel, createListDetail, createRecoveryForm } from '../components/native-workbench.mjs';

export function selectionActions(items, onApply) {
  const model=createSelectionModel(items.map(item=>item.id));
  const action=el('button',{type:'button',disabled:true,onclick:()=>onApply([...model.selected])},'Apply to selected');
  const live=el('p',{role:'status','aria-live':'polite'},'No records selected');
  const checkboxes=new Map();
  const rows=items.map(item=>{
    const checkbox=el('input',{type:'checkbox','aria-label':`Select ${item.label}`,onchange:()=>model.toggle(item.id)});
    checkboxes.set(item.id,checkbox);return el('li',{},el('label',{},checkbox,item.label));
  });
  model.subscribe(selected=>{action.disabled=!selected.size;live.textContent=`${selected.size} records selected`;checkboxes.forEach((node,id)=>{node.checked=selected.has(id)});});
  return el('section',{'aria-label':'Selection task'},el('ul',{},rows),live,action);
}
export function mobileListDetail(items) {
  return createListDetail({items,label:'Fixture records',getLabel:item=>item.label,renderDetail:item=>el('article',{},el('h2',{},item.label),el('p',{},item.context))});
}
export function recoverySlice(onSave) {
  return createRecoveryForm({id:'original-recovery-example',steps:[{label:'Next action',fields:[{name:'nextAction',label:'Next action',type:'textarea',required:true}]}],initialValues:{nextAction:''},onSave});
}
