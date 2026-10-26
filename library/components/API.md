# Native Workbench 0.1.1

Original ES modules and CSS with no registry/library attribution claim. Load `native-workbench.mjs` in a browser module and `native-workbench.css` in the document. CSS values are proposed defaults, not a brand skin. No downloads, fonts, analytics or network requests are performed by the module.

| Export | Contract | State and keyboard |
|---|---|---|
| `el(tag, attrs, ...children)` | Creates DOM; nested children flattened; strings escaped via text nodes; event functions use `on*`; Boolean `aria-*` values become the strings `true`/`false`; trusted Node children allowed | Native element semantics; no HTML injection API |
| `createSelectionModel(ids, {onChange}?)` | Immutable ID universe; `selected` snapshot Set, `count`, `has(id)`, `toggle(id)`, `clear()`, `subscribe(fn)` unsubscribe | Uncontrolled memory state; unknown ID throws; caller wires native checkboxes and contextual actions; does not persist selection |
| `createSortableTable({columns,rows,initialKey?,caption?,onSort?})` | Columns `{key,label,numeric?,value?(row),render?(row)}`; stable numeric/text sort; returns DOM node with `setRows(rows)`, `getSort()` | Native table/caption/header buttons; `aria-sort`; live status; Tab/Enter/Space sort; region keyboard scroll; does not implement ARIA grid or remote pagination |
| `createListDetail({items,getLabel?,renderDetail,onOpen?,label?})` | Items require stable unique `id`; renderer returns a Node; returns DOM with `getCurrentId()`, `setItems(items)` | Buttons open region/focus; Back restores origin focus; touch CSS replaces list with detail; selection is independent; no URL history or persistence |
| `createRecoveryForm({id?,steps,initialValues?,storage?,storageKey?,onSave})` | Steps `{label,fields:[{name,label,type?,required?,hint?}]}`; names unique; supported field types listed below; checkbox values are Boolean, other edited values are strings; optional synchronous Storage; async onSave; DOM methods `getState()`, `resetDraft()` | Native labels/validation; previous/continue; draft load/write; pending disabled inputs; failed save retains values/retry; successful save clears draft; reload persistence only with supplied Storage |

Supported field types: `text` (default), `textarea`, `email`, `url`, `tel`, `search`, `number`, `date`, `time`, `datetime-local`, `month`, `week`, and `checkbox`. Other types throw `TypeError`; grouped radio controls, file uploads and secret/password retention need separate task-specific components. Checkboxes default to false, use `checked` state, and retain Boolean draft values. An invalid stored field type is ignored with visible recovery feedback.

Retained source revision 0.1.1 corrects Boolean ARIA attributes and checkbox state. This package preserves the module, CSS and MIT notice with integrity hashes. Verify the consuming application independently; source integrity alone does not establish correct integration.

The form callback is the source of committed state; the component stores drafts only. Use synthetic/non-sensitive fixture data. It does not prove backend authorization, autosave conflicts, multi-tab consistency or irreversible-action idempotency. Native validation messages depend on browser language. Storage failure is visible and does not silently become a persistence pass. The caller must explain constraints and provide a cancel policy appropriate to the product.

The list/detail source currently preserves keyboard focus, not URL navigation or list scroll after a document reload. Extend those explicitly when promised by a task contract. A virtualized large dataset or a task needing grid keyboard navigation should use a verified suitable library instead of this small native table.

The host also owns updating the list after an `onSave` callback commits a change. The recovery form does not automatically rebuild labels already rendered by `createListDetail`; supply updated items through `setItems` and deliberately restore focus when your task needs the edited value visible in the queue. Callback success alone does not prove automatic row refresh.

Build a task-specific representative screen and verify its actual render and interactions separately from source/API inspection. The offline demo is a separate synthetic smoke example, not a complete application.
